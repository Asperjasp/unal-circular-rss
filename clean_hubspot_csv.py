"""
clean_hubspot_csv.py
────────────────────
Cleans the HubSpot contacts export and produces a Zoho CRM-ready CSV.

Usage:
    python clean_hubspot_csv.py input.csv
    python clean_hubspot_csv.py input.csv --output zoho_import.csv

What it fixes based on the actual data:
  - Removes HubSpot-only columns Zoho doesn't need
  - Merges NombrePrestador → company when company is empty
  - Merges EmailSede / EmailPrestador → email when email is empty
  - Cleans phone numbers (removes "/" separators, keeps first number only)
  - Removes quote artifacts in names like: "Jefe TI FNC -  Iván Suárez"
  - Drops contacts with no email AND no company (unusable rows)
  - Deduplicates by email
  - Maps HubSpot columns → exact Zoho CRM field names
  - Adds Lead Source = "Cold Call" and Lead Status = "New" defaults
  - Reports a summary of what was cleaned
"""

import sys
import re
import argparse
import pandas as pd

# ── Column mapping: HubSpot name → Zoho CRM field name ──────────────────────
# Only the columns Zoho actually uses
COLUMN_MAP = {
    "Nombre":           "First Name",
    "Apellidos":        "Last Name",
    "Correo":           "Email",
    "Número de teléfono": "Phone",
    "NombrePrestador":  "Account Name",      # company fallback
    "Associated Company": "Account Name",    # preferred company source
    "NombreSede":       "Department",
    "DireccionSede":    "Mailing Street",
    "DireccionPrestador": "Mailing Street",  # fallback address
    "Estado del lead":  "Lead Status",
    "Propietario del contacto": "Lead Owner",
}

# Columns to DROP completely (HubSpot internals, useless for Zoho)
DROP_COLS = [
    "ID de registro",
    "Correo de miembro",
    "EmailSede",
    "EmailPrestador",
    "Última actividad",
    "Fecha de creación",
    "Código postal",
    "Dirección",
    "Dirección alternativa",
    "Dirección alternativas",
    "Associated Company IDs",
    "Estado del contacto de marketing",
]

def clean_phone(phone: str) -> str:
    """Keep only the first phone number when multiple are listed."""
    if not phone or pd.isna(phone):
        return ""
    phone = str(phone).strip()
    # Split on common separators: / - | ;
    for sep in ["/", "|", ";"]:
        if sep in phone:
            phone = phone.split(sep)[0].strip()
    # Remove extensions like "Ext 671", "ext. 123"
    phone = re.sub(r'[Ee]xt\.?\s*\d+', '', phone).strip()
    # Remove non-numeric except + and spaces
    phone = re.sub(r'[^\d\+\s\-]', '', phone).strip()
    return phone

def clean_name(name: str) -> str:
    """Remove quote artifacts and fix formatting."""
    if not name or pd.isna(name):
        return ""
    name = str(name).strip()
    # Remove leading/trailing quotes
    name = name.strip('"').strip("'")
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name)
    return name

def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    if not email or pd.isna(email):
        return False
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email).strip()))

def is_generic_email(email: str) -> bool:
    """Flag likely generic/functional emails that aren't personal contacts."""
    if not email:
        return False
    generics = ['info@', 'contacto@', 'calidad@', 'gerencia@', 'recepcion@',
                'notificaciones@', 'sistemas@', 'admin@', 'ventas@', 'general@']
    return any(email.lower().startswith(g) for g in generics)

def clean_csv(input_path: str, output_path: str):
    print(f"\n📂 Reading: {input_path}")

    # Try common encodings
    df = None
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(input_path, encoding=enc, dtype=str, on_bad_lines='skip')
            print(f"   Encoding: {enc} ✓")
            break
        except Exception as e:
            continue
    if df is None:
        print("❌ Could not read file. Try saving as UTF-8 CSV.")
        sys.exit(1)

    original_count = len(df)
    print(f"   Rows loaded: {original_count:,}")
    print(f"   Columns: {list(df.columns)}\n")

    # ── Step 1: Fill missing email from EmailSede / EmailPrestador ─────────
    if 'Correo' in df.columns:
        email_col = 'Correo'
    else:
        email_col = None

    emails_filled = 0
    for fallback_col in ['EmailSede', 'EmailPrestador']:
        if fallback_col in df.columns and email_col:
            mask = (df[email_col].isna() | (df[email_col].str.strip() == '')) & \
                   df[fallback_col].notna() & (df[fallback_col].str.strip() != '')
            df.loc[mask, email_col] = df.loc[mask, fallback_col]
            emails_filled += mask.sum()
    print(f"✅ Step 1: Filled {emails_filled} missing emails from EmailSede/EmailPrestador")

    # ── Step 2: Fill missing company from NombrePrestador ─────────────────
    company_filled = 0
    if 'Associated Company' in df.columns and 'NombrePrestador' in df.columns:
        mask = (df['Associated Company'].isna() | (df['Associated Company'].str.strip() == '')) & \
               df['NombrePrestador'].notna()
        df.loc[mask, 'Associated Company'] = df.loc[mask, 'NombrePrestador']
        company_filled = mask.sum()
    print(f"✅ Step 2: Filled {company_filled} missing companies from NombrePrestador")

    # ── Step 3: Clean names (remove quote artifacts) ───────────────────────
    names_cleaned = 0
    for col in ['Nombre', 'Apellidos']:
        if col in df.columns:
            original = df[col].copy()
            df[col] = df[col].apply(clean_name)
            changed = (original != df[col]).sum()
            names_cleaned += changed
    print(f"✅ Step 3: Cleaned {names_cleaned} name fields")

    # ── Step 4: Clean phone numbers ────────────────────────────────────────
    phones_cleaned = 0
    if 'Número de teléfono' in df.columns:
        original_phones = df['Número de teléfono'].copy()
        df['Número de teléfono'] = df['Número de teléfono'].apply(clean_phone)
        phones_cleaned = (original_phones != df['Número de teléfono']).sum()
    # Also fix scientific notation (pandas reads long numbers as float)
    if 'Número de teléfono' in df.columns:
        def fix_sci(p):
            if pd.isna(p) or str(p).strip() in ('', 'nan'): return ''
            s = str(p).strip()
            if 'e+' in s.lower() or (s.replace('.','').replace('-','').isdigit() and '.' in s):
                try: return str(int(float(s)))
                except: pass
            return s
        df['Número de teléfono'] = df['Número de teléfono'].apply(fix_sci)
    print(f"✅ Step 4: Cleaned {phones_cleaned} phone numbers")

    # ── Step 5: Drop useless columns ──────────────────────────────────────
    cols_to_drop = [c for c in DROP_COLS if c in df.columns]
    df = df.drop(columns=cols_to_drop)
    print(f"✅ Step 5: Dropped {len(cols_to_drop)} unnecessary columns")

    # ── Step 6: Drop rows with no email AND no company ─────────────────────
    if 'Correo' in df.columns and 'Associated Company' in df.columns:
        mask_no_email = df['Correo'].isna() | (df['Correo'].str.strip() == '')
        mask_no_company = df['Associated Company'].isna() | (df['Associated Company'].str.strip() == '')
        unusable = mask_no_email & mask_no_company
        dropped_unusable = unusable.sum()
        df = df[~unusable]
        print(f"✅ Step 6: Dropped {dropped_unusable} rows with no email and no company")
    else:
        print("⚠️  Step 6: Skipped (columns not found)")

    # ── Step 7: Remove invalid emails ─────────────────────────────────────
    invalid_emails = 0
    if 'Correo' in df.columns:
        mask_invalid = df['Correo'].notna() & ~df['Correo'].apply(is_valid_email)
        invalid_emails = mask_invalid.sum()
        df.loc[mask_invalid, 'Correo'] = ''
    print(f"✅ Step 7: Cleared {invalid_emails} malformed email addresses")

    # ── Step 8: Deduplicate by email ───────────────────────────────────────
    before_dedup = len(df)
    if 'Correo' in df.columns:
        # Keep the most recently modified (first in the sorted export = most recent)
        df_with_email = df[df['Correo'].notna() & (df['Correo'].str.strip() != '')]
        df_no_email = df[df['Correo'].isna() | (df['Correo'].str.strip() == '')]
        df_with_email = df_with_email.drop_duplicates(subset=['Correo'], keep='first')
        df = pd.concat([df_with_email, df_no_email], ignore_index=True)
    dupes_removed = before_dedup - len(df)
    print(f"✅ Step 8: Removed {dupes_removed} duplicate emails")

    # ── Step 9: Rename columns → Zoho field names ──────────────────────────
    # Merge address columns before renaming to avoid duplicates
    if 'DireccionSede' in df.columns and 'DireccionPrestador' in df.columns:
        mask = df['DireccionSede'].isna() | (df['DireccionSede'].str.strip() == '')
        df.loc[mask, 'DireccionSede'] = df.loc[mask, 'DireccionPrestador']
        df = df.drop(columns=['DireccionPrestador'])
    # Drop NombrePrestador if Associated Company already exists (already merged in step 2)
    if 'Associated Company' in df.columns and 'NombrePrestador' in df.columns:
        df = df.drop(columns=['NombrePrestador'])
    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename_map)
    df = df.loc[:, ~df.columns.duplicated()]
    print(f"✅ Step 9: Renamed {len(rename_map)} columns to Zoho field names")



    # ── Step 10: Add Zoho defaults ─────────────────────────────────────────
    if 'Lead Source' not in df.columns:
        df['Lead Source'] = 'Cold Call'
    if 'Lead Status' not in df.columns:
        df['Lead Status'] = 'New'
    else:
        # Map HubSpot statuses to Zoho equivalents
        status_map = {
            'NEW': 'New', 'OPEN': 'Contacted', 'IN_PROGRESS': 'Contacted',
            'OPEN_DEAL': 'Contacted', 'UNQUALIFIED': 'Not Converted',
            'ATTEMPTED_TO_CONTACT': 'Contacted', 'CONNECTED': 'Contacted',
            'BAD_TIMING': 'Not Converted', '': 'New',
        }
        df['Lead Status'] = df['Lead Status'].fillna('New')
        df['Lead Status'] = df['Lead Status'].map(lambda x: status_map.get(str(x).upper(), x))
    print(f"✅ Step 10: Added Lead Source and Lead Status defaults")

    # ── Step 11: Flag generic emails (don't drop, just tag) ────────────────
    if 'Email' in df.columns:
        df['Is Generic Email'] = df['Email'].apply(
            lambda x: 'Yes' if is_generic_email(str(x)) else 'No')
        generic_count = (df['Is Generic Email'] == 'Yes').sum()
        print(f"✅ Step 11: Flagged {generic_count} generic/functional emails (info@, calidad@, etc)")

    # ── Final: Save ────────────────────────────────────────────────────────
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    final_count = len(df)
    print(f"""
{'='*55}
📊 SUMMARY
{'='*55}
  Original rows:    {original_count:>6,}
  Final rows:       {final_count:>6,}
  Removed:          {original_count - final_count:>6,} ({(original_count-final_count)/original_count*100:.1f}%)

  Emails rescued:   {emails_filled:>6,}
  Companies filled: {company_filled:>6,}
  Dupes removed:    {dupes_removed:>6,}
  Bad phones fixed: {phones_cleaned:>6,}

📁 Output saved to: {output_path}
{'='*55}

NEXT STEP → Zoho CRM:
  Contacts → Import → CSV → upload {output_path}
  Map columns (Zoho auto-detects most of them)
  Set duplicate check: by Email
""")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean HubSpot CSV for Zoho CRM import")
    parser.add_argument("input", help="Path to HubSpot contacts export CSV")
    parser.add_argument("--output", default="zoho_import_clean.csv",
                        help="Output file path (default: zoho_import_clean.csv)")
    args = parser.parse_args()
    clean_csv(args.input, args.output)

# ── PATCH: post-process after save ────────────────────────────────────────────
# This runs automatically when imported as module to fix column/phone issues.
