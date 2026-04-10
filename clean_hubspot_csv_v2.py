"""
clean_hubspot_csv_v2.py  —  Ai Médic
──────────────────────────────────────────────────────────────────
Cleans HubSpot contacts CSV and outputs TWO files:

  1. zoho_import_CLEAN.csv      → ready to import into Zoho CRM
  2. azure_contacts_CLEAN.csv   → ready to INSERT into Azure SQL
                                  (crm.contacto + crm.contacto_empresa)

Real data observations from your export:
  - "Nombre" contains REPS CodigoPrestador codes (e.g. 110010899501)
    NOT actual first names — all real names are missing
  - "Apellidos" is always empty
  - "NombrePrestador", "EmailSede", "DireccionSede" all empty
    (data came from REPS import, not manual prospecting)
  - "Associated Company" IS populated → use as company name
  - "Associated Company IDs" can have multiples separated by ";"
    (keep only first ID to avoid duplicates)
  - Phone: "4254550- 3123511070- 3142314793" → keep first number
  - "Estado del lead": "Nuevo" → maps to Zoho "New"
  - "Estado del contacto de marketing": "Contacto de marketing" /
    "Contacto que no es de marketing" → use as qualification flag

Usage:
  python3 clean_hubspot_csv_v2.py contacts.csv
  python3 clean_hubspot_csv_v2.py contacts.csv --out-dir ~/GoogleDrive/
"""

import sys, re, argparse, uuid
from pathlib import Path
from datetime import datetime
import pandas as pd

# ── Azure SQL column mapping (exact field names from our schema) ──────────────
AZURE_COLS = [
    "contacto_id",       # UUID generated here
    "first_name",        # from Nombre (if real name) or empty
    "last_name",         # from Apellidos
    "email",             # from Correo
    "telefono",          # cleaned phone
    "linkedin_url",      # empty (not in HubSpot export)
    "fuente",            # always "HubSpot"
    "hubspot_contact_id",# from ID de registro
    # empresa info (for crm.contacto_empresa join)
    "_company_name",     # from Associated Company (cleaned)
    "_company_id_hs",    # from Associated Company IDs (first one)
    # metadata
    "_es_marketing",     # from Estado del contacto de marketing
    "_lead_status",      # from Estado del lead
    "_fecha_creacion",   # from Fecha de creación
    "_codigo_reps",      # from Nombre field (when it's a REPS code)
]

# ── Zoho CRM field mapping ────────────────────────────────────────────────────
ZOHO_COLS = {
    "First Name":    "",          # filled from cleaned data
    "Last Name":     "",
    "Email":         "Correo",
    "Phone":         "Número de teléfono",
    "Account Name":  "Associated Company",
    "Lead Status":   "Estado del lead",
    "Lead Source":   "",          # hardcoded "Cold Call"
    "Description":   "",          # filled from REPS code + marketing status
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_reps_code(value: str) -> bool:
    """Detect REPS CodigoPrestador codes like '110010899501'."""
    if not value or pd.isna(value):
        return False
    return bool(re.match(r'^\d{9,15}$', str(value).strip()))

def clean_phone(raw: str) -> str:
    """Keep only the first phone number from multi-phone strings."""
    if not raw or pd.isna(raw):
        return ""
    s = str(raw).strip()
    # Split on separators: - / | ; (but not leading country code -)
    for sep in ["/", "|", ";"]:
        if sep in s:
            s = s.split(sep)[0].strip()
    # Handle "4254550- 3123511070" style (dash with space = separator)
    parts = re.split(r'\s*-\s+', s)
    if len(parts) > 1:
        s = parts[0].strip()
    # Remove extensions
    s = re.sub(r'[Ee]xt\.?\s*\d+', '', s).strip()
    # Keep only digits, +, spaces
    s = re.sub(r'[^\d\+\s]', '', s).strip()
    # Remove trailing/leading spaces
    return s.strip()

def clean_company(raw: str) -> str:
    """Clean company name — handle semicolon-separated duplicates."""
    if not raw or pd.isna(raw):
        return ""
    # "MESSER COLOMBIA S.A.;MESSER COLOMBIA S.A.;Messer CO" → "MESSER COLOMBIA S.A."
    parts = [p.strip() for p in str(raw).split(";") if p.strip()]
    if not parts:
        return ""
    # Return the most common or first unique value
    seen = []
    for p in parts:
        if p.upper() not in [x.upper() for x in seen]:
            seen.append(p)
    # Prefer the shortest clean version (usually the canonical name)
    return min(seen, key=len) if seen else parts[0]

def first_company_id(raw: str) -> str:
    """Extract first HubSpot company ID from semicolon-separated list."""
    if not raw or pd.isna(raw):
        return ""
    return str(raw).split(";")[0].strip()

def map_lead_status(raw: str) -> str:
    """Map HubSpot lead status to Zoho equivalent."""
    if not raw or pd.isna(raw):
        return "New"
    mapping = {
        "nuevo": "New",
        "new": "New",
        "contactado": "Contacted",
        "contacted": "Contacted",
        "en progreso": "Contacted",
        "in_progress": "Contacted",
        "conectado": "Contacted",
        "connected": "Contacted",
        "no calificado": "Not Converted",
        "unqualified": "Not Converted",
    }
    return mapping.get(str(raw).strip().lower(), "New")

def is_valid_email(email: str) -> bool:
    if not email or pd.isna(email):
        return False
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$', str(email).strip()))

# ── Main cleaner ──────────────────────────────────────────────────────────────

def clean(input_path: str, out_dir: str):
    stem = Path(input_path).stem
    zoho_path  = str(Path(out_dir) / f"{stem}_zoho_import.csv")
    azure_path = str(Path(out_dir) / f"{stem}_azure_contacts.csv")

    print(f"\n📂 Reading: {input_path}")

    df = None
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(input_path, encoding=enc, dtype=str,
                             on_bad_lines='skip')
            print(f"   Encoding detected: {enc}")
            break
        except Exception:
            continue
    if df is None:
        print("❌ Could not read file.")
        sys.exit(1)

    original = len(df)
    print(f"   Rows: {original:,}   Columns: {len(df.columns)}")

    # ── 1. Detect and extract REPS codes from Nombre ──────────────────────
    df['_codigo_reps'] = df['Nombre'].apply(
        lambda x: str(x).strip() if is_reps_code(x) else "")
    reps_count = (df['_codigo_reps'] != "").sum()
    # Clear Nombre when it's a REPS code (not a real name)
    df['Nombre'] = df['Nombre'].apply(
        lambda x: "" if is_reps_code(x) else str(x).strip())
    print(f"\n✅ 1. Detected {reps_count:,} REPS codes in Nombre field → moved to _codigo_reps")

    # ── 2. Clean company name (deduplicate semicolons) ────────────────────
    if 'Associated Company' in df.columns:
        df['_company_clean'] = df['Associated Company'].apply(clean_company)
        duped = (df['Associated Company'].str.contains(';', na=False)).sum()
        print(f"✅ 2. Cleaned {duped} company names with duplicate entries")
    else:
        df['_company_clean'] = ""
        print("⚠️  2. 'Associated Company' column not found")

    # ── 3. Extract first company ID ───────────────────────────────────────
    if 'Associated Company IDs' in df.columns:
        df['_company_id_hs'] = df['Associated Company IDs'].apply(first_company_id)
    else:
        df['_company_id_hs'] = ""
    print(f"✅ 3. Extracted first HubSpot company ID from {df['_company_id_hs'].notna().sum()} rows")

    # ── 4. Clean phone numbers ────────────────────────────────────────────
    if 'Número de teléfono' in df.columns:
        df['_phone_clean'] = df['Número de teléfono'].apply(clean_phone)
        changed = (df['_phone_clean'] != df['Número de teléfono'].fillna("")).sum()
        print(f"✅ 4. Cleaned {changed} phone numbers")
    else:
        df['_phone_clean'] = ""

    # ── 5. Validate emails ────────────────────────────────────────────────
    invalid = df['Correo'].apply(lambda x: not is_valid_email(x)).sum() \
              if 'Correo' in df.columns else 0
    if 'Correo' in df.columns:
        df.loc[~df['Correo'].apply(is_valid_email), 'Correo'] = ""
    print(f"✅ 5. Cleared {invalid} invalid email addresses")

    # ── 6. Drop rows with no email AND no company ─────────────────────────
    no_email   = df['Correo'].isna() | (df['Correo'].str.strip() == "") \
                 if 'Correo' in df.columns else pd.Series([True]*len(df))
    no_company = df['_company_clean'].isna() | (df['_company_clean'] == "")
    dropped = (no_email & no_company).sum()
    df = df[~(no_email & no_company)]
    print(f"✅ 6. Dropped {dropped} rows with no email and no company")

    # ── 7. Deduplicate by email ───────────────────────────────────────────
    before = len(df)
    has_email = df['Correo'].notna() & (df['Correo'].str.strip() != "")
    df_em  = df[has_email].drop_duplicates(subset=['Correo'], keep='first')
    df_no  = df[~has_email]
    df = pd.concat([df_em, df_no], ignore_index=True)
    dupes = before - len(df)
    print(f"✅ 7. Removed {dupes} duplicate emails")

    # ── 8. Map lead status ────────────────────────────────────────────────
    df['_lead_status_mapped'] = df['Estado del lead'].apply(map_lead_status) \
                                if 'Estado del lead' in df.columns \
                                else "New"
    print(f"✅ 8. Mapped lead status to Zoho values")

    # ── BUILD OUTPUT A: Zoho CRM import CSV ───────────────────────────────
    zoho = pd.DataFrame()
    zoho['First Name']    = df['Nombre'].fillna("")
    zoho['Last Name']     = df['Apellidos'].fillna("") if 'Apellidos' in df.columns else ""
    zoho['Email']         = df['Correo'].fillna("")
    zoho['Phone']         = df['_phone_clean']
    zoho['Account Name']  = df['_company_clean']
    zoho['Lead Status']   = df['_lead_status_mapped']
    zoho['Lead Source']   = "Cold Call"
    zoho['Description']   = df.apply(
        lambda r: f"REPS: {r['_codigo_reps']} | HubSpot ID: {r.get('ID de registro','')} | {r.get('Estado del contacto de marketing','')}",
        axis=1)
    zoho['Tag']           = df['Estado del contacto de marketing'].fillna("") \
                            if 'Estado del contacto de marketing' in df.columns else ""
    zoho.to_csv(zoho_path, index=False, encoding='utf-8-sig')

    # ── BUILD OUTPUT B: Azure SQL contacts CSV ────────────────────────────
    azure = pd.DataFrame()
    azure['contacto_id']        = [str(uuid.uuid4()) for _ in range(len(df))]
    azure['first_name']         = df['Nombre'].fillna("")
    azure['last_name']          = df['Apellidos'].fillna("") if 'Apellidos' in df.columns else ""
    azure['email']              = df['Correo'].fillna("")
    azure['telefono']           = df['_phone_clean']
    azure['linkedin_url']       = ""
    azure['fuente']             = "HubSpot"
    azure['hubspot_contact_id'] = df['ID de registro'].fillna("") \
                                  if 'ID de registro' in df.columns else ""
    azure['company_name']       = df['_company_clean']       # for crm.contacto_empresa join
    azure['company_id_hubspot'] = df['_company_id_hs']       # for matching prestador
    azure['codigo_reps']        = df['_codigo_reps']          # links to reps.prestador
    azure['es_marketing']       = df['Estado del contacto de marketing'].fillna("") \
                                  if 'Estado del contacto de marketing' in df.columns else ""
    azure['lead_status']        = df['_lead_status_mapped']
    azure['fecha_creacion_hs']  = df['Fecha de creación'].fillna("") \
                                  if 'Fecha de creación' in df.columns else ""
    azure.to_csv(azure_path, index=False, encoding='utf-8-sig')

    # ── Summary ───────────────────────────────────────────────────────────
    final = len(df)
    has_name  = ((zoho['First Name'] != "") | (zoho['Last Name'] != "")).sum()
    has_phone = (zoho['Phone'] != "").sum()

    print(f"""
{'='*58}
📊 SUMMARY
{'='*58}
  Input rows:          {original:>7,}
  Output rows:         {final:>7,}
  Removed:             {original-final:>7,}  ({(original-final)/max(original,1)*100:.1f}%)

  With real name:      {has_name:>7,}  ({has_name/max(final,1)*100:.1f}%)
  With phone:          {has_phone:>7,}  ({has_phone/max(final,1)*100:.1f}%)
  With REPS code:      {reps_count:>7,}  ({reps_count/max(final,1)*100:.1f}%)

📁 Zoho import:        {zoho_path}
📁 Azure contacts:     {azure_path}
{'='*58}

⚠️  NOTE: {reps_count:,} contacts have REPS codes instead of real names.
   These are institutional emails (IPS/EPS), not personal contacts.
   The REPS code links them to reps.prestador in Azure SQL via
   the 'codigo_reps' column in the Azure file.

ZOHO: Contacts → Import → CSV → select {Path(zoho_path).name}
      Duplicate check: by Email
      
AZURE: python3 etl/load_crm_excel.py --file {azure_path}
""")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("input", help="HubSpot contacts CSV path")
    p.add_argument("--out-dir", default=".", help="Output directory (default: current dir)")
    args = p.parse_args()
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    clean(args.input, args.out_dir)
