# UNAL Circular RSS

Automated RSS feeds for [Circular UNAL](https://circular.unal.edu.co/) — updated every hour via GitHub Actions.

## Feed URLs

Once deployed to GitHub Pages (`https://asperjasp.github.io/unal-circular-rss/`):

| Feed | URL |
|---|---|
| All events | `/feed.xml` |
| Bogotá — all | `/feed-bogota.xml` |
| Bogotá — Ciencia y Tecnología | `/feed-bogota-ciencia.xml` |
| Bogotá — Arte y Cultura | `/feed-bogota-arte.xml` |
| Bogotá — Salud | `/feed-bogota-salud.xml` |
| Medellín — all | `/feed-medellin.xml` |

## Setup

1. Push this repo to GitHub as `unal-circular-rss`
2. Go to **Settings → Pages → Source**: set to `gh-pages` branch
3. Run the workflow manually once: **Actions → Generate → Run workflow**
4. Add the feed URLs to Folo under category `Eventos-UNAL`

## Contributing to RSSHub

The TypeScript route for upstream RSSHub is in `../rsshub-unal/`.
