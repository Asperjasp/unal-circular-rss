#!/usr/bin/env python3
"""
Generate RSS feeds for UNAL Circular events.
Outputs: public/feed.xml, public/feed-bogota.xml, public/feed-ciencia.xml
"""

import json
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from email.utils import formatdate
import time

UNAL_API = "https://circular.unal.edu.co/rest/eventos/"

CAMPUS_MAP = {
    "bogota": 2,
    "medellin": 3,
    "manizales": 4,
    "palmira": 5,
}

CATEGORY_KEYWORDS = {
    "arte": "Arte",
    "ciencia": "Ciencia",
    "educacion": "Educación",
    "salud": "Salud",
    "sociedad": "Sociedad",
}


def escape_xml(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def to_rfc822(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            return formatdate(usegmt=True)
    return formatdate(dt.timestamp(), usegmt=True)


def fetch_events():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(UNAL_API, context=ctx, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def filter_events(events, campus=None, category=None):
    result = events[:]
    if campus:
        uid = CAMPUS_MAP.get(campus.lower())
        if uid:
            result = [e for e in result if e.get("campusUid") == uid]
    if category:
        kw = CATEGORY_KEYWORDS.get(category.lower())
        if kw:
            result = [
                e for e in result
                if any(kw in a["name"] for a in e.get("categories", {}).get("areaTematica", []))
            ]
    result.sort(key=lambda e: e["date"]["current"])
    return result


def build_item(e: dict) -> str:
    tipo = ", ".join(t["name"] for t in e.get("categories", {}).get("tipo", []))
    area = ", ".join(a["name"] for a in e.get("categories", {}).get("areaTematica", []))
    ticket = (
        "Entrada libre" if e.get("ticketsType") == "ENTRADA_LIBRE"
        else f"Con boletería" if e.get("ticketsType") == "BOLETERIA"
        else (e.get("ticketsType") or "")
    )
    campus_name = escape_xml(e.get("campus") or "")
    dep = escape_xml((e.get("dependencia") or {}).get("name") or "")
    address = escape_xml((e.get("location") or {}).get("address") or "")
    img = escape_xml(e.get("imagen") or "")

    desc = f"""<p><strong>{campus_name}</strong>{f" — {dep}" if dep else ""}</p>
<p><strong>Fecha:</strong> {escape_xml(e["date"]["current"])}{f' → {escape_xml(e["date"]["final"])}' if e["date"].get("final") and e["date"]["final"] != e["date"]["current"] else ""}</p>
{f"<p><strong>Lugar:</strong> {address}</p>" if address else ""}
<p><strong>Tipo:</strong> {escape_xml(tipo)}{f" | {escape_xml(area)}" if area else ""}</p>
<p><strong>Acceso:</strong> {escape_xml(ticket)}</p>
{f'<p><img src="{img}" alt="{escape_xml(e["title"])}" /></p>' if img else ""}
{e.get("description") or ""}
{f'<p><a href="{escape_xml(e["ticketsUrl"])}">Obtener boletas</a></p>' if e.get("ticketsUrl") else ""}"""

    categories = "".join(
        f"      <category>{escape_xml(a['name'])}</category>\n"
        for a in e.get("categories", {}).get("areaTematica", [])
    )
    if e.get("campus"):
        categories += f"      <category>{campus_name}</category>\n"

    return f"""    <item>
      <title>{escape_xml(e["title"])}</title>
      <link>{escape_xml(e["url"])}</link>
      <guid isPermaLink="true">{escape_xml(e["url"])}</guid>
      <pubDate>{to_rfc822(e.get("recordDate", ""))}</pubDate>
      <description><![CDATA[{desc}]]></description>
      {f'<enclosure url="{img}" type="image/jpeg" />' if img else ""}
      {categories.strip()}
    </item>"""


def build_feed(title: str, events: list, self_url: str = "") -> str:
    items = "\n".join(build_item(e) for e in events)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape_xml(title)}</title>
    <link>https://circular.unal.edu.co/</link>
    <description>Agenda Nacional de eventos y actividades académicas — Universidad Nacional de Colombia</description>
    <language>es-CO</language>
    <lastBuildDate>{formatdate(usegmt=True)}</lastBuildDate>
    {f'<atom:link href="{escape_xml(self_url)}" rel="self" type="application/rss+xml"/>' if self_url else ""}
{items}
  </channel>
</rss>"""


def main():
    print("Fetching events from UNAL Circular API...")
    events = fetch_events()
    print(f"  Got {len(events)} events")

    out = Path("public")
    out.mkdir(exist_ok=True)

    feeds = [
        ("feed.xml", "Circular UNAL — Todos los eventos", None, None),
        ("feed-bogota.xml", "Circular UNAL — Sede Bogotá", "bogota", None),
        ("feed-bogota-ciencia.xml", "Circular UNAL — Bogotá · Ciencia y Tecnología", "bogota", "ciencia"),
        ("feed-bogota-arte.xml", "Circular UNAL — Bogotá · Arte y Cultura", "bogota", "arte"),
        ("feed-bogota-salud.xml", "Circular UNAL — Bogotá · Salud", "bogota", "salud"),
        ("feed-medellin.xml", "Circular UNAL — Sede Medellín", "medellin", None),
    ]

    for filename, title, campus, category in feeds:
        filtered = filter_events(events, campus=campus, category=category)
        xml = build_feed(title, filtered)
        path = out / filename
        path.write_text(xml, encoding="utf-8")
        print(f"  Written {filename} ({len(filtered)} events)")

    print("Done.")


if __name__ == "__main__":
    main()
