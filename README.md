# unal-circular-rss

RSS feeds for [Circular UNAL](https://circular.unal.edu.co/) — the official academic events portal of Universidad Nacional de Colombia.

UNAL's portal has no native RSS. This project fetches their undocumented public REST API hourly and publishes static RSS feeds via GitHub Pages.

## Live feeds

| Feed | URL |
|---|---|
| All events | `https://asperjasp.github.io/unal-circular-rss/feed.xml` |
| Sede Bogotá | `https://asperjasp.github.io/unal-circular-rss/feed-bogota.xml` |
| Bogotá · Ciencia y Tecnología | `https://asperjasp.github.io/unal-circular-rss/feed-bogota-ciencia.xml` |
| Bogotá · Arte y Cultura | `https://asperjasp.github.io/unal-circular-rss/feed-bogota-arte.xml` |
| Bogotá · Salud | `https://asperjasp.github.io/unal-circular-rss/feed-bogota-salud.xml` |
| Sede Medellín | `https://asperjasp.github.io/unal-circular-rss/feed-medellin.xml` |

## How it works

`generate_feed.py` fetches `https://circular.unal.edu.co/rest/eventos/` (public, no auth) and writes static RSS XML to `public/`. GitHub Actions runs this hourly and deploys to the `gh-pages` branch via `peaceiris/actions-gh-pages`.

The UNAL API uses a self-signed certificate — the generator disables cert verification locally (`ssl.CERT_NONE`). On GitHub Actions runners this is not needed but kept for consistency.

## Run locally

```bash
python3 generate_feed.py
# Writes public/feed.xml, public/feed-bogota.xml, etc.
```

No dependencies beyond Python 3.9+ stdlib.

## Source API

`GET https://circular.unal.edu.co/rest/eventos/`

Returns a JSON array of events. Useful fields: `title`, `date.current`, `date.final`, `campusUid`, `campus`, `location.address`, `categories.areaTematica`, `categories.tipo`, `url`, `imagen`, `ticketsType`, `ticketsUrl`.

Campus UIDs: Bogotá = 2, Medellín = 3, Manizales = 4, Palmira = 5.

## Related

- RSSHub route: `DIYgod/RSSHub#21701` — upstream PR for `rsshub://unal/circular`
- [mobilizon-sync](../mobilizon-sync/) — pushes these events to a Mobilizon instance
