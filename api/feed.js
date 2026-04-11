// Vercel serverless function: UNAL Circular → RSS feed
// Route: /api/feed?campus=bogota&category=ciencia
// Deploy: vercel --prod

const UNAL_API = 'https://circular.unal.edu.co/rest/eventos/';

const CAMPUS_MAP = {
    bogota: 2,
    medellin: 3,
    manizales: 4,
    palmira: 5,
    amazonia: 6,
    orinoquia: 7,
    caribe: 8,
    tumaco: 11,
    'la-paz': 12,
};

const CATEGORY_KEYWORDS = {
    arte: 'Arte',
    ciencia: 'Ciencia',
    educacion: 'Educación',
    salud: 'Salud',
    sociedad: 'Sociedad',
    'medio-ambiente': 'Medio Ambiente',
    derechos: 'Derechos',
    economia: 'Economía',
};

function escapeXml(str = '') {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
}

function toRfc822(dateStr) {
    if (!dateStr) return new Date().toUTCString();
    return new Date(dateStr).toUTCString();
}

export default async function handler(req, res) {
    const { campus, category } = req.query;

    let events;
    try {
        const response = await fetch(UNAL_API, {
            headers: { 'Accept': 'application/json' },
        });
        events = await response.json();
    } catch (err) {
        res.status(502).send('Error fetching UNAL Circular API');
        return;
    }

    // Filter by campus
    if (campus) {
        const campusUid = CAMPUS_MAP[campus.toLowerCase()];
        if (campusUid) {
            events = events.filter((e) => e.campusUid === campusUid);
        }
    }

    // Filter by category keyword
    if (category) {
        const keyword = CATEGORY_KEYWORDS[category.toLowerCase()];
        if (keyword) {
            events = events.filter((e) =>
                (e.categories?.areaTematica ?? []).some((a) => a.name.includes(keyword))
            );
        }
    }

    // Sort by upcoming date
    events.sort((a, b) => new Date(a.date.current) - new Date(b.date.current));

    const campusLabel = campus ? ` — ${campus.charAt(0).toUpperCase() + campus.slice(1)}` : '';
    const categoryLabel = category ? ` — ${CATEGORY_KEYWORDS[category.toLowerCase()] ?? category}` : '';
    const feedTitle = `Circular UNAL${campusLabel}${categoryLabel}`;

    const items = events.map((e) => {
        const tipo = (e.categories?.tipo ?? []).map((t) => t.name).join(', ');
        const area = (e.categories?.areaTematica ?? []).map((a) => a.name).join(', ');
        const ticketInfo =
            e.ticketsType === 'ENTRADA_LIBRE'
                ? 'Entrada libre'
                : e.ticketsType === 'BOLETERIA'
                  ? `Con boletería${e.ticketsCost ? ` — $${e.ticketsCost}` : ''}`
                  : (e.ticketsType ?? '');

        const descHtml = `
<p><strong>${escapeXml(e.campus)}</strong>${e.dependencia?.name ? ` — ${escapeXml(e.dependencia.name)}` : ''}</p>
<p><strong>Fecha:</strong> ${escapeXml(e.date.current)}${e.date.final && e.date.final !== e.date.current ? ` → ${escapeXml(e.date.final)}` : ''}</p>
${e.location?.address ? `<p><strong>Lugar:</strong> ${escapeXml(e.location.address)}</p>` : ''}
<p><strong>Tipo:</strong> ${escapeXml(tipo)}${area ? ` | ${escapeXml(area)}` : ''}</p>
<p><strong>Acceso:</strong> ${escapeXml(ticketInfo)}</p>
${e.imagen ? `<p><img src="${escapeXml(e.imagen)}" alt="${escapeXml(e.title)}" /></p>` : ''}
${e.description ?? ''}
${e.ticketsUrl ? `<p><a href="${escapeXml(e.ticketsUrl)}">Obtener boletas</a></p>` : ''}
`.trim();

        return `
    <item>
      <title>${escapeXml(e.title)}</title>
      <link>${escapeXml(e.url)}</link>
      <guid isPermaLink="true">${escapeXml(e.url)}</guid>
      <pubDate>${toRfc822(e.recordDate)}</pubDate>
      <description><![CDATA[${descHtml}]]></description>
      ${e.imagen ? `<enclosure url="${escapeXml(e.imagen)}" type="image/jpeg" />` : ''}
      ${(e.categories?.areaTematica ?? []).map((a) => `<category>${escapeXml(a.name)}</category>`).join('\n      ')}
      ${e.campus ? `<category>${escapeXml(e.campus)}</category>` : ''}
    </item>`;
    });

    const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${escapeXml(feedTitle)}</title>
    <link>https://circular.unal.edu.co/</link>
    <description>Agenda Nacional de eventos y actividades académicas — Universidad Nacional de Colombia</description>
    <language>es-CO</language>
    <atom:link href="${escapeXml(`https://${req.headers.host}/api/feed${req.url.includes('?') ? req.url.slice(req.url.indexOf('?') - 1) : ''}`)}" rel="self" type="application/rss+xml"/>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    ${items.join('\n')}
  </channel>
</rss>`;

    res.setHeader('Content-Type', 'application/rss+xml; charset=utf-8');
    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate');
    res.status(200).send(rss);
}
