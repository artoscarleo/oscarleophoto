#!/usr/bin/env python3
"""
Generates the static HTML for oscarleo.photography.

This is a convenience, not a dependency: the output in the site folder is
plain HTML you can edit by hand and deploy anywhere. Re-running this script
OVERWRITES those files, so if you hand-edit a page, either stop using the
script or fold your change back in here.

    python3 _build/generate.py
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_DIR = os.path.join(os.path.dirname(ROOT), "seo-implementation", "02-schema")
SITE_URL = "https://oscarleo.photography"


def asset(path):
    """Append a short content hash to CSS/JS URLs.

    Without this, a visitor who has the old stylesheet cached keeps it after you
    deploy a change. The hash changes only when the file does, so the asset can
    still be cached aggressively.
    """
    import hashlib
    full = os.path.join(ROOT, path.lstrip("/"))
    try:
        with open(full, "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()[:8]
        return path + "?v=" + h
    except OSError:
        return path

# --------------------------------------------------------------------------
# Image data
# --------------------------------------------------------------------------

def load_images(folder):
    out = []
    path = os.path.join(ROOT, "assets", "img", folder, "aspect.txt")
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            slug, w, h = line.split("|")
            out.append({"slug": slug, "w": int(w), "h": int(h),
                        "ratio": int(w) / int(h), "folder": folder})
    out.sort(key=lambda d: d["slug"])
    return out

def load_wide():
    """Slugs that have a landscape hero crop, from _build/hero_crops.py."""
    out = {}
    path = os.path.join(ROOT, "assets", "img", "hero-wide.txt")
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            slug, w, h, widths = line.split("|")
            out[slug] = {"w": int(w), "h": int(h),
                         "widths": [int(x) for x in widths.split(",")]}
    return out

WIDE = load_wide()

HEADSHOTS = load_images("headshots")
CONCERTS = load_images("concerts")

WIDTHS = [400, 800, 1200, 1800]

# Alt text is descriptive at the level the frame supports. It is honest and
# screen-reader-usable, but it is not a substitute for a human writing one
# sentence per image once the final selects are locked.
HEADSHOT_ALT = [
    "Studio headshot of a woman against a softly textured backdrop, photographed in Vancouver.",
    "Professional portrait lit with a single soft key light, shoulders square to camera.",
    "Editorial portrait with muted warm tones and a shallow depth of field.",
    "Corporate headshot on a neutral background, natural expression, waist-up framing.",
    "Natural-light portrait against a plain wall, relaxed posture.",
    "Business headshot with even lighting and a clean, uncluttered background.",
    "Three-quarter portrait with warm sage tones and soft shadow falloff.",
    "Close portrait with the subject looking directly into the lens.",
]

CONCERT_ALT = [
    "Live music performance photographed from the audience under blue stage lighting.",
    "Performer mid-song, lit from behind by stage wash, in a Vancouver venue.",
    "Wide shot of a stage and audience during a live concert.",
    "Musician in silhouette against coloured stage lights.",
    "Band performing to a full room, shot from the photo pit.",
    "Festival stage viewed across a crowd at dusk.",
    "Detail of a performer's hands on an instrument under warm stage light.",
    "Concert crowd with arms raised, backlit by stage haze.",
]


def srcset(img):
    widths = WIDTHS + [2400] if img["folder"] == "grid" else WIDTHS
    parts = []
    for w in widths:
        parts.append(f"/assets/img/{img['folder']}/{img['slug']}-{w}.jpg {w}w")
    return ", ".join(parts)


def alt_for(img, i):
    pool = HEADSHOT_ALT if img["folder"] == "headshots" else CONCERT_ALT
    return pool[i % len(pool)]


def tile(img, i, sizes, stagger=True):
    """A gallery tile. The width/height attributes give the browser the image's
    intrinsic ratio, so the masonry column reserves the exact box before the
    file arrives — that is what holds CLS at zero, and it lets every photograph
    keep its own proportions instead of being cropped to a shared cell."""
    delay = f' style="--i:{min(i % 8, 7)}"' if stagger else ""
    return f"""          <button type="button" class="tile" data-lightbox-item
                  data-full="/assets/img/{img['folder']}/{img['slug']}-1800.jpg"
                  data-reveal-img{delay}>
            <img src="/assets/img/{img['folder']}/{img['slug']}-800.jpg"
                 srcset="{srcset(img)}"
                 sizes="{sizes}"
                 width="{img['w']}" height="{img['h']}"
                 loading="lazy" decoding="async"
                 alt="{alt_for(img, i)}">
          </button>"""


def gallery(images, sizes, extra_class=""):
    tiles = "\n".join(tile(im, i, sizes) for i, im in enumerate(images))
    return f'        <div class="gallery {extra_class}">\n{tiles}\n        </div>'


# --------------------------------------------------------------------------
# Shared chrome
# --------------------------------------------------------------------------

NAV = [
    ("/", "Home", ""),
    ("/vancouver-headshot-photographer/", "Headshots", "From $395"),
    ("/vancouver-event-photographer/", "Events", "From $500"),
    ("/vancouver-brand-photography-video/", "Brand", "From $650"),
    ("/vancouver-concert-photographer/", "Concerts", "From $450"),
    ("/vancouver-bts-unit-stills-photographer/", "Behind the Scenes", "From $700"),
    ("/about/", "About", ""),
    ("/contact/", "Contact", ""),
]

ICON = {
    "moon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>',
    "sun": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" aria-hidden="true"><path d="M3 7h18M3 12h18M3 17h18"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" aria-hidden="true"><path d="M5 5l14 14M19 5L5 19"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "left": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M11 18l-6-6 6-6"/></svg>',
    "right": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>',
    "instagram": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg>',
    "facebook": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h-2.5A3.5 3.5 0 0 0 9 6.5V9H7v3h2v9h3v-9h2.5l.5-3H12V6.75c0-.41.34-.75.75-.75H15V3Z"/></svg>',
    "pinterest": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.5 20c-.4-1.4-.2-3 .1-4.3l1-4.2M8.8 9.6c0-2 1.6-3.6 3.9-3.6 2 0 3.6 1.3 3.6 3.4 0 2.5-1.4 4.5-3.4 4.5-.9 0-1.6-.7-1.4-1.6"/></svg>',
}


def head(page):
    schema_blocks = ""
    for name in page.get("schema", []):
        with open(os.path.join(SCHEMA_DIR, name)) as fh:
            data = json.load(fh)
        schema_blocks += (
            '  <script type="application/ld+json">\n'
            + json.dumps(data, ensure_ascii=False, indent=2)
            + "\n  </script>\n"
        )

    og_image = page.get("og_image", "/assets/img/concerts/vancouver-concert-stage-01-1200.jpg")
    canonical = SITE_URL + page["url"]

    return f"""<!DOCTYPE html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page['title']}</title>
  <meta name="description" content="{page['desc']}">
  <link rel="canonical" href="{canonical}">

  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Oscar Léo Photography">
  <meta property="og:title" content="{page['title']}">
  <meta property="og:description" content="{page['desc']}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{SITE_URL}{og_image}">
  <meta property="og:locale" content="en_CA">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{page['title']}">
  <meta name="twitter:description" content="{page['desc']}">
  <meta name="twitter:image" content="{SITE_URL}{og_image}">

  <meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0A0A0A" media="(prefers-color-scheme: dark)">

  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preload" as="image" fetchpriority="high"
        imagesrcset="{page['hero_srcset']}"
        imagesizes="100vw" href="{page['hero_src']}">
  <link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600&display=swap">
  <link rel="stylesheet" href="{asset('/assets/css/site.css')}">

  <!-- Sets the theme before first paint so there is no flash of the wrong one. -->
  <script>
    (function () {{
      var d = document.documentElement;
      d.classList.add('js');
      try {{
        var t = localStorage.getItem('ol-theme');
        if (t === 'light' || t === 'dark') d.setAttribute('data-theme', t);
      }} catch (e) {{}}
    }})();
  </script>

{schema_blocks}</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
"""


def header():
    links = "\n".join(
        f'          <a href="{url}" data-nav-link>{label}</a>'
        for url, label, _ in NAV if url != "/"
    )
    return f"""  <header class="header" data-header>
    <div class="header__inner">
      <a class="brand" href="/"><span class="logo-mark brand__mark" aria-hidden="true"></span>Oscar Léo <span>Photography</span></a>
      <nav class="nav" aria-label="Primary">
{links}
      </nav>
      <div class="header__actions">
        <button type="button" class="icon-btn theme-toggle" data-theme-toggle aria-label="Switch theme">
          <span class="icon-moon">{ICON['moon']}</span>
          <span class="icon-sun">{ICON['sun']}</span>
        </button>
        <button type="button" class="icon-btn nav-toggle" data-nav-open
                aria-label="Open menu" aria-expanded="false" aria-controls="mobile-nav">
          {ICON['menu']}
        </button>
      </div>
    </div>
  </header>

  <div class="mobile-nav" id="mobile-nav" data-mobile-nav data-open="false" aria-hidden="true">
    <div class="mobile-nav__head">
      <a class="brand" href="/"><span class="logo-mark brand__mark" aria-hidden="true"></span>Oscar Léo <span>Photography</span></a>
      <button type="button" class="icon-btn" data-nav-close aria-label="Close menu">{ICON['close']}</button>
    </div>
    <nav aria-label="Mobile">
      <ul class="mobile-nav__list">
{chr(10).join(f'        <li style="--i:{i}"><a href="{url}">{label}<span class="price">{price}</span></a></li>' for i, (url, label, price) in enumerate(NAV))}
      </ul>
    </nav>
  </div>
"""


def footer():
    services = "\n".join(
        f'            <li><a href="{url}">{label}</a></li>'
        for url, label, _ in NAV[1:6]
    )
    return f"""  <footer class="footer">
    <div class="container">
      <div class="footer__cta" data-reveal>
        <span class="eyebrow">Enquiries</span>
        <h2>Tell me about your project.</h2>
        <p class="text-muted">Send your date, location and the type of photography you need, and
           I will reply with availability and a quote.</p>
        <p style="margin-top:var(--space-l)">
          <a class="btn" href="/contact/">Request a quote {ICON['arrow']}</a>
        </p>
      </div>

      <div class="footer__grid">
        <div>
          <span class="logo-mark footer__mark" role="img" aria-label="Oscar Léo Photography"></span>
          <p class="fine-print">Professional photography in Vancouver, British Columbia.
             Serving Metro Vancouver and available across Canada.</p>
        </div>
        <div>
          <h3 class="footer__head">Services</h3>
          <ul>
{services}
          </ul>
        </div>
        <div>
          <h3 class="footer__head">Studio</h3>
          <ul>
            <li><a href="/about/">About</a></li>
            <li><a href="/contact/">Contact</a></li>
          </ul>
        </div>
        <div>
          <h3 class="footer__head">Areas served</h3>
          <p class="fine-print">Vancouver · Burnaby · Richmond · North Vancouver ·
             West Vancouver · Surrey · Coquitlam · Delta · Langley · the wider Lower Mainland.
             Travel included within 30&nbsp;km of Vancouver.</p>
        </div>
      </div>

      <div class="footer__bottom">
        <p class="fine-print">© 2026 Oscar Léo Photography. All prices in Canadian dollars, plus GST.</p>
        <div class="footer__social">
          <a href="https://www.instagram.com/oscarleophotography/" rel="me noopener" target="_blank" aria-label="Instagram">{ICON['instagram']}</a>
          <a href="https://www.facebook.com/profile.php?id=61577219900688" rel="me noopener" target="_blank" aria-label="Facebook">{ICON['facebook']}</a>
          <a href="https://www.pinterest.com/oscarleophotography/" rel="me noopener" target="_blank" aria-label="Pinterest">{ICON['pinterest']}</a>
        </div>
      </div>
    </div>
  </footer>
"""


def lightbox():
    js_url = asset("/assets/js/site.js")
    return f"""  <div class="lightbox" data-lightbox data-open="false" aria-hidden="true"
       role="dialog" aria-modal="true" aria-label="Photograph viewer">
    <div class="lightbox__bar">
      <span class="lightbox__count" data-lightbox-count>1 / 1</span>
      <button type="button" class="icon-btn" data-lightbox-close aria-label="Close viewer">{ICON['close']}</button>
    </div>
    <div class="lightbox__stage">
      <img data-lightbox-image src="" alt="">
    </div>
    <div class="lightbox__foot">
      <button type="button" class="icon-btn" data-lightbox-prev aria-label="Previous photograph">{ICON['left']}</button>
      <p class="lightbox__caption" data-lightbox-caption></p>
      <button type="button" class="icon-btn" data-lightbox-next aria-label="Next photograph">{ICON['right']}</button>
    </div>
  </div>

  <script src="{js_url}" defer></script>
</body>
</html>
"""


def hero(page):
    scroll = f"""      <div class="hero__scroll" aria-hidden="true"><span>Scroll</span><i></i></div>""" if page.get("tall") else ""
    actions = ""
    if page.get("hero_actions"):
        buttons = "\n".join(
            f'        <a class="btn{" btn--on-image" if i else ""}" href="{href}">{label}</a>'
            for i, (href, label) in enumerate(page["hero_actions"])
        )
        actions = f'      <div class="hero__actions">\n{buttons}\n      </div>'

    lines = "".join(
        f'<span class="line" style="--i:{i}"><span>{ln}</span></span>'
        for i, ln in enumerate(page["h1_lines"])
    )

    extra = (" " + page["hero_class"]) if page.get("hero_class") else ""
    slug = page.get("hero_slug")
    wide = WIDE.get(slug)
    if wide:
        folder = page["hero_folder"]
        wide_srcset = ", ".join(
            f"/assets/img/{folder}/{slug}-wide-{w}.jpg {w}w" for w in wide["widths"]
        )
        # A portrait photograph in a landscape window loses most of its height to
        # `cover` — including the subject's head. Above a square window shape the
        # browser takes a 16:9 crop cut around the subject instead. The switch is
        # on aspect-ratio, not width, because the hero is full-height so its box
        # is exactly the shape of the window.
        # The switch has to describe the shape of the *hero box*, not the window.
        # A full-height hero is the window's shape, but the short heroes are
        # 72svh, so their box turns landscape while the window is still portrait
        # — at 768x1024 that was still costing 8-11% off the top of the frame.
        switch = "1/1" if page.get("tall") else "18/25"   # 1.00 vs 0.72
        media = f"""      <picture>
        <source media="(min-aspect-ratio: {switch})"
                srcset="{wide_srcset}" sizes="100vw"
                width="{wide['w']}" height="{wide['h']}">
        <img src="{page['hero_src']}" srcset="{page['hero_srcset']}" sizes="100vw"
             width="{page['hero_w']}" height="{page['hero_h']}"
             fetchpriority="high" decoding="async"
             alt="{page['hero_alt']}">
      </picture>"""
    else:
        media = f"""      <img src="{page['hero_src']}" srcset="{page['hero_srcset']}" sizes="100vw"
           width="{page['hero_w']}" height="{page['hero_h']}"
           fetchpriority="high" decoding="async"
           alt="{page['hero_alt']}">"""

    return f"""  <section class="hero{'' if page.get('tall') else ' hero--short'}{extra}">
    <div class="hero__media">
{media}
    </div>
    <div class="hero__inner">
      <span class="eyebrow" data-reveal>{page['eyebrow']}</span>
      <h1 class="reveal-lines" data-reveal>{lines}</h1>
      <p class="hero__sub" data-reveal style="--i:2">{page['hero_sub']}</p>
{actions}
{scroll}
    </div>
  </section>
"""


def faq_block(items):
    rows = ""
    for q, a in items:
        rows += f"""        <details>
          <summary>{q}<span class="marker" aria-hidden="true"></span></summary>
          <div class="faq__answer"><p>{a}</p></div>
        </details>
"""
    return rows


def price_card(tag, name, amount, note, features, featured=False):
    lis = "\n".join(
        f'            <li>{ICON["check"]}<span>{f}</span></li>' for f in features
    )
    tag_html = f'<p class="price-card__tag">{tag}</p>' if tag else ""
    return f"""        <div class="price-card{' price-card--featured' if featured else ''}" data-reveal>
          {tag_html}
          <h3>{name}</h3>
          <span class="price-card__amount">{amount} <small>{note}</small></span>
          <ul>
{lis}
          </ul>
          <a class="btn btn--ghost" href="/contact/">Enquire</a>
        </div>"""


def render(page, body):
    return head(page) + header() + hero(page) + '  <main id="main">\n' + body + "  </main>\n" + footer() + lightbox()


def relativize(html, depth):
    """Rewrite root-relative URLs so the site works from any base path.

    Served from a domain root, `/assets/...` is correct. Served from a subfolder
    — which is what GitHub Pages does for a project repo — every one of those
    URLs points outside the site and 404s. Relative paths are correct in both
    places, so the same build can sit on Pages today and on the real domain
    later without a rebuild.

    Absolute URLs (canonical, og:image, JSON-LD) are deliberately left alone:
    those must keep naming the production domain wherever the page is hosted.
    """
    prefix = "../" * depth
    home = prefix if depth else "./"

    def one(m):
        attr, val = m.group(1), m.group(2)
        return f'{attr}="{home}"' if val == "/" else f'{attr}="{prefix}{val[1:]}"'

    html = re.sub(r'\b(href|src|data-full)="(/[^"]*)"', one, html)

    def many(m):                      # srcset / imagesrcset hold several URLs
        attr, val = m.group(1), m.group(2)
        val = re.sub(r'(^|,\s*)/', lambda mm: mm.group(1) + prefix, val)
        return f'{attr}="{val}"'

    return re.sub(r'\b(srcset|imagesrcset)="([^"]*)"', many, html)


def write(url, html):
    if url == "/":
        path = os.path.join(ROOT, "index.html")
        depth = 0
    else:
        d = os.path.join(ROOT, url.strip("/"))
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "index.html")
        depth = url.strip("/").count("/") + 1
    with open(path, "w") as fh:
        fh.write(relativize(html, depth))
    return path


def hero_fields(img, alt):
    return {
        "hero_slug": img["slug"],
        "hero_folder": img["folder"],
        "hero_src": f"/assets/img/{img['folder']}/{img['slug']}-1800.jpg",
        "hero_srcset": srcset(img),
        "hero_w": img["w"], "hero_h": img["h"],
        "hero_alt": alt,
        "og_image": f"/assets/img/{img['folder']}/{img['slug']}-1200.jpg",
    }


# ==========================================================================
# PAGES
# ==========================================================================

def build_home():
    # Contact-sheet montage of the portrait work, built from the original files
    # by _build/montage.py. Square, so it crops gracefully at any hero shape.
    hero_img = {"slug": "vancouver-photographer-portrait-grid", "folder": "grid",
                "w": 2400, "h": 2400, "ratio": 1.0}
    page = dict(
        url="/", tall=True,
        title="Vancouver Photographer | Headshots, Events & Brand Content",
        desc="Professional photographer in Vancouver, BC. Headshots from $395, event coverage from $500, brand content and BTS. Transparent pricing. Book today.",
        eyebrow="Vancouver, British Columbia",
        h1_lines=["Photography that", "feels like you."],
        hero_sub="Headshots, events, brand content, live music and behind-the-scenes production work — with every price published before you make contact.",
        hero_actions=[("/contact/", "Request a quote"), ("#services", "See services")],
        schema=["homepage-professionalservice.json"],
        hero_class="hero--grid",
        **hero_fields(hero_img, "A grid of thirty-six portraits from Oscar Léo Photography\u2019s Vancouver studio work \u2014 headshots, personal branding and editorial portraits.")
    )

    services = [
        ("/vancouver-headshot-photographer/", "Headshots & Portraits",
         "Corporate, LinkedIn and personal branding", "From $395"),
        ("/vancouver-event-photographer/", "Event Photography",
         "Conferences, galas and celebrations", "From $500"),
        ("/vancouver-brand-photography-video/", "Brand Photography & Video",
         "Content for web, social and marketing", "From $650"),
        ("/vancouver-concert-photographer/", "Concert & Live Performance",
         "Artists, venues, promoters and festivals", "From $450"),
        ("/vancouver-bts-unit-stills-photographer/", "Behind the Scenes & Unit Stills",
         "Film, television and commercial production", "From $700"),
    ]
    rows = ""
    for i, (url, name, desc, price) in enumerate(services):
        rows += f"""        <a class="service-row" href="{url}" data-preview-index="{i}" data-reveal style="--i:{i}">
          <span class="service-row__num">0{i+1}</span>
          <h3 class="service-row__title">{name}</h3>
          <span class="service-row__price">{price}</span>
          <p class="service-row__desc">{desc}</p>
        </a>
"""

    preview_imgs = [HEADSHOTS[0], CONCERTS[11], HEADSHOTS[4], CONCERTS[2], CONCERTS[13]]
    previews = "\n".join(
        f'      <img src="/assets/img/{im["folder"]}/{im["slug"]}-800.jpg" alt="" width="{im["w"]}" height="{im["h"]}" loading="lazy" decoding="async">'
        for im in preview_imgs
    )

    picks = [HEADSHOTS[1], CONCERTS[12], HEADSHOTS[7], CONCERTS[20],
             HEADSHOTS[10], CONCERTS[27], HEADSHOTS[14], CONCERTS[35]]

    body = f"""    <section class="section container">
      <div class="section-head section-head--split">
        <div data-reveal>
          <span class="eyebrow">The studio</span>
          <h2>A professional photography studio in Vancouver.</h2>
        </div>
        <p class="lead" data-reveal style="--i:1">Oscar Léo Photography is a professional photography
           studio based in Vancouver, British Columbia, serving Metro Vancouver and available for
           projects across Canada. Services include headshots and portraits from $395, event
           photography from $500, brand photography and video from $650, concert and live performance
           coverage from $450, and behind-the-scenes production photography from $700. All prices are
           published, and all packages include professional editing and high-resolution delivery.</p>
      </div>

      <div class="stat-row">
        <div data-reveal style="--i:0">
          <span class="stat__value">3–5</span>
          <span class="stat__label">business days to your event gallery. Most Vancouver studios take 5–7.</span>
        </div>
        <div data-reveal style="--i:1">
          <span class="stat__value">$395</span>
          <span class="stat__label">Starting price for a professional headshot session, published up front.</span>
        </div>
        <div data-reveal style="--i:2">
          <span class="stat__value">30&nbsp;km</span>
          <span class="stat__label">Travel included around Vancouver, across the Lower Mainland.</span>
        </div>
        <div data-reveal style="--i:3">
          <span class="stat__value">5</span>
          <span class="stat__label">Specialisms, one photographer, one consistent style.</span>
        </div>
      </div>
    </section>

    <section class="section container" id="services">
      <div class="section-head" data-reveal>
        <span class="eyebrow">Services</span>
        <h2>What I photograph</h2>
      </div>
      <div class="service-index" data-service-list>
{rows}      </div>
    </section>

    <div class="service-preview" data-service-preview aria-hidden="true">
{previews}
    </div>

    <section class="section section--sunken">
      <div class="container">
        <div class="section-head section-head--split">
          <div data-reveal>
            <span class="eyebrow">Selected work</span>
            <h2>Recent frames</h2>
          </div>
          <p class="text-muted" data-reveal style="--i:1">A cross-section of portrait and live
             performance work. Every gallery on this site opens full-screen — click any photograph.</p>
        </div>
{gallery(picks, "(min-width: 78em) 21vw, (min-width: 48em) 30vw, 47vw", "gallery--wide")}
      </div>
    </section>

    <section class="section container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">Approach</span>
          <h2>Polished, but never staged.</h2>
          <div class="prose">
            <p class="callout">Good photography should feel like you.</p>
            <p>I combine documentary observation with thoughtful direction — stepping in when guidance
               helps, and letting genuine moments happen on their own. The result is polished
               photography that doesn't feel staged: images with personality, atmosphere and a story
               behind them.</p>
            <p><a class="text-link" href="/about/">More about how I work</a></p>
          </div>
        </div>
        <div data-reveal style="--i:1">
          <span class="eyebrow">Why clients book</span>
          <div class="prose">
            <p><strong>Published pricing.</strong> Every service page shows real numbers, so you know
               the cost before you make contact.</p>
            <p><strong>Fast delivery.</strong> Event galleries arrive within 3–5 business days.
               Most Vancouver studios take 5–7.</p>
            <p><strong>Clear licensing.</strong> Business bookings include commercial digital usage for
               your website, social media, press and internal communications at no extra charge.</p>
            <p><strong>One photographer, five specialisms.</strong> Consistent style whether you need a
               headshot, an event covered or a production documented.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="section--tight container">
      <hr class="rule">
      <div class="section-head" style="padding-top: var(--space-xl)" data-reveal>
        <span class="eyebrow">Areas served</span>
        <h2>Based in Vancouver. Available across Canada.</h2>
        <p class="text-muted">Covering Metro Vancouver including Burnaby, Richmond, North Vancouver,
           West Vancouver, Surrey, Coquitlam, Delta and Langley. Travel is included within 30 km of
           Vancouver. Available for commissions throughout British Columbia and across Canada.</p>
      </div>
    </section>
"""
    return page, body


def build_headshots():
    hero_img = HEADSHOTS[2]
    page = dict(
        url="/vancouver-headshot-photographer/",
        title="Headshot Photographer Vancouver | From $395 | Oscar Léo",
        desc="Professional headshots in Vancouver from $395. Corporate, LinkedIn and personal branding portraits. Team rates from $135 per person. See full pricing.",
        eyebrow="Headshots & Portraits",
        h1_lines=["Headshot photographer", "in Vancouver, BC"],
        hero_sub="Corporate, LinkedIn and personal branding portraits — in studio or at your office.",
        hero_actions=[("#pricing", "See pricing"), ("#work", "See the work")],
        schema=["faq-headshots.json"],
        **hero_fields(hero_img, "Editorial portrait with muted warm tones, photographed in a Vancouver studio.")
    )

    cards = "\n".join([
        price_card("Individual", "Essential Headshot", "$395", "45 minutes",
                   ["Up to 45 minutes", "2 outfits", "Private proof gallery",
                    "3 retouched high-resolution images", "Web-ready versions"]),
        price_card("Individual", "Personal Branding Portrait", "$595", "90 minutes",
                   ["Planning consultation", "Up to 90 minutes", "Multiple outfits",
                    "Headshots, half-body and lifestyle portraits",
                    "6 retouched high-resolution images"], featured=True),
        price_card("Teams", "Team &amp; Corporate", "from $450", "on-site setup",
                   ["$450 on-site setup", "5–9 people: $185 each", "10–24 people: $155 each",
                    "25+ people: $135 each", "One retouched image per person",
                    "Commercial licence included"]),
    ])

    faqs = [
        ("How much do professional headshots cost in Vancouver?",
         "Individual headshots in Vancouver generally run between $325 and $850 in 2026. At Oscar Léo Photography an individual session is $395 for three retouched images, and corporate team bookings drop to $135–$185 per person depending on group size."),
        ("How long does a headshot session take?",
         "45 minutes for an Essential Headshot and up to 90 minutes for a Personal Branding Portrait. Corporate team sessions run 10–15 minutes per person."),
        ("What should I wear for a headshot?",
         "Solid colours photograph best. Bring two outfits — usually one more formal and one more relaxed — and avoid busy patterns or large logos. Any layer that lets you change the level of formality in seconds is useful."),
        ("How soon do I get my photos?",
         "Retouched images are delivered within five business days of your final selection. A 48-hour priority option is available for $95."),
        ("Do you photograph teams at our office?",
         "Yes. I bring a full mobile studio to offices anywhere in Metro Vancouver, with consistent lighting and background across everyone on your team."),
    ]

    body = f"""    <section class="section container">
      <p class="lead" data-reveal>Professional headshots in Vancouver start at $395 for a 45-minute
         session with three retouched images. Corporate team headshots are $135–$185 per person plus a
         $450 on-site setup fee, depending on group size. Sessions take place in studio or on location
         at your Vancouver office, and finished images are delivered within five business days of your
         selection.</p>
    </section>

    <section class="section--tight container" id="work">
      <div class="section-head section-head--split">
        <div data-reveal>
          <span class="eyebrow">Selected work</span>
          <h2>Portraits</h2>
        </div>
        <p class="text-muted" data-reveal style="--i:1">Click any photograph to open it full-screen.</p>
      </div>
{gallery(HEADSHOTS, "(min-width: 78em) 21vw, (min-width: 48em) 30vw, 47vw", "gallery--wide")}
    </section>

    <section class="section container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">The session</span>
          <h2>You don't need to know how to pose.</h2>
        </div>
        <div class="prose" data-reveal style="--i:1">
          <p>Most people feel awkward in front of a camera, and that's the actual problem a headshot
             photographer solves. I guide you through positioning, expression and small adjustments
             throughout the session, so the final photographs look natural rather than performed.</p>
          <p>Sessions run 45 to 90 minutes depending on the package. You review a private proof gallery
             afterwards and choose which images get retouched.</p>
        </div>
      </div>
    </section>

    <section class="section section--sunken" id="pricing">
      <div class="container">
        <div class="section-head" data-reveal>
          <span class="eyebrow">Pricing</span>
          <h2>Headshot pricing in Vancouver</h2>
        </div>
        <div class="grid-3">
{cards}
        </div>
        <p class="fine-print" style="margin-top: var(--space-l)" data-reveal>
          Add-ons: additional retouched image $65 · additional location from $95 ·
          additional 30 minutes $150 · 48-hour priority delivery $95.
          All prices in CAD, plus GST.</p>
      </div>
    </section>

    <section class="section container">
      <div class="section-head" data-reveal>
        <span class="eyebrow">Questions</span>
        <h2>Frequently asked</h2>
      </div>
      <div class="faq">
{faq_block(faqs)}      </div>
    </section>
"""
    return page, body


def build_events():
    # STAND-IN IMAGERY: no dedicated event photographs were supplied. These are
    # live-event frames from the concert set. Swap for corporate event work.
    hero_img = CONCERTS[2]
    picks = [CONCERTS[i] for i in (2, 5, 20, 26, 32, 41)]
    page = dict(
        url="/vancouver-event-photographer/",
        title="Event Photographer Vancouver | Corporate Events | From $500",
        desc="Vancouver event photography from $500 for 2 hours. Corporate events, conferences, galas and celebrations. Gallery delivered in 3–5 business days.",
        eyebrow="Event Photography",
        h1_lines=["Event photographer", "in Vancouver, BC"],
        hero_sub="Documentary coverage of conferences, galas, launches and celebrations across Metro Vancouver.",
        hero_actions=[("#pricing", "See pricing"), ("/contact/", "Check your date")],
        schema=["faq-events.json"],
        **hero_fields(hero_img, "Wide view of a live event stage and audience, photographed in Vancouver.")
    )

    rates = [("2 hours", "$500"), ("3 hours", "$720"), ("4 hours", "$940"),
             ("6 hours", "$1,380"), ("8 hours", "$1,800")]
    best = ' class="is-best"'
    rows = "\n".join(
        "            <tr{}><td>{}</td><td>{}</td></tr>".format(best if h == "8 hours" else "", h, p)
        for h, p in rates
    )

    included = ["Professional on-location photography", "Candid documentary coverage",
                "Directed group photographs where appropriate", "Curated final gallery",
                "Colour correction and retouching on every delivered image",
                "High-resolution files and web-ready versions", "Private online gallery",
                "Commercial digital licence", "Delivery within 3–5 business days"]
    inc = "\n".join(f'            <li>{ICON["check"]}<span>{x}</span></li>' for x in included)

    faqs = [
        ("How much does an event photographer cost in Vancouver?",
         "Metro Vancouver event photography typically runs $150–$400 per hour, with most established professionals sitting in the $250–$300 range. Oscar Léo Photography starts at $250 per hour with a two-hour minimum, and the effective hourly rate drops to $225 on an eight-hour booking."),
        ("How many photos will I receive?",
         "Roughly 40–60 professionally edited images per hour, depending on the event. A four-hour event typically produces 160–240 finished photographs."),
        ("Can we use the photos for marketing?",
         "Yes. Business bookings include a commercial digital licence for your own website, social media, press releases and internal communications. Paid advertising campaigns and third-party licensing are quoted separately."),
        ("How far in advance should we book?",
         "Two to six weeks for most events. Conference season in spring and holiday parties in December book earlier."),
        ("Do you cover events outside Vancouver?",
         "Yes. Travel is included within 30 km. A $75 flat fee applies for 30–60 km, covering Surrey, Coquitlam, Langley and Delta. Beyond that, quoted individually."),
    ]

    body = f"""    <section class="section container">
      <p class="lead" data-reveal>Event photography in Vancouver starts at $500 for two hours of
         coverage, with a full eight-hour day at $1,800. Every booking includes professional editing on
         every delivered image, high-resolution files, a private online gallery, and a commercial
         digital licence covering your organisation's website, social media, press releases and
         internal communications. Galleries are delivered within 3–5 business days.</p>
    </section>

    <section class="section--tight container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">Coverage</span>
          <h2>Events I photograph</h2>
        </div>
        <div class="prose" data-reveal style="--i:1">
          <p>Corporate events, conferences, product launches, award nights, galas, fundraisers,
             networking events, community and cultural events, birthdays, anniversaries and private
             celebrations — throughout Metro Vancouver.</p>
          <p>The approach is documentary: people, atmosphere, décor, candid interactions, speakers and
             performances, plus properly directed group photographs when they're needed.</p>
        </div>
      </div>
    </section>

    <!-- STAND-IN IMAGERY: live-event frames from the concert set. Replace with
         corporate event photographs when available. -->
    <section class="section container">
{gallery(picks, "(min-width: 48em) 30vw, 47vw")}
    </section>

    <section class="section section--sunken" id="pricing">
      <div class="container">
        <div class="section-head" data-reveal>
          <span class="eyebrow">Pricing</span>
          <h2>Event photography pricing</h2>
        </div>
        <div class="grid-2">
          <div data-reveal>
            <div class="table-scroll">
              <table class="rate-table">
                <caption>Minimum booking two hours. Additional hours beyond eight: $215.</caption>
                <thead><tr><th scope="col">Coverage</th><th scope="col">Investment</th></tr></thead>
                <tbody>
{rows}
                </tbody>
              </table>
            </div>
            <p class="fine-print" style="margin-top: var(--space-m)">
              Add-ons: 1-minute vertical highlight video $250 · 48-hour priority gallery $150 ·
              second photographer $175/hr · travel free within 30 km of Vancouver, $75 flat for 30–60 km.</p>
          </div>
          <div class="price-card" data-reveal style="--i:1">
            <p class="price-card__tag">Included in every booking</p>
            <ul>
{inc}
            </ul>
            <p class="fine-print" style="margin-bottom: var(--space-m)">
               Most events yield 40–60 finished photographs per hour.</p>
            <a class="btn" href="/contact/">Check availability</a>
          </div>
        </div>
      </div>
    </section>

    <section class="section container">
      <div class="section-head" data-reveal>
        <span class="eyebrow">Questions</span>
        <h2>Frequently asked</h2>
      </div>
      <div class="faq">
{faq_block(faqs)}      </div>
    </section>
"""
    return page, body


def build_brand():
    # STAND-IN IMAGERY: no dedicated brand/commercial shoot was supplied.
    # Portrait frames stand in — personal branding portraits are genuinely part
    # of this service, but product, workspace and team frames are missing.
    hero_img = HEADSHOTS[5]
    picks = [HEADSHOTS[i] for i in (3, 9, 13, 18, 6, 20)]
    page = dict(
        url="/vancouver-brand-photography-video/",
        title="Brand Photography & Video Vancouver | From $650 | Oscar Léo",
        desc="Brand photography and short-form video for Vancouver businesses. Packages from $650. Commercial licence included. Content for web, social and marketing.",
        eyebrow="Brand Photography & Video",
        h1_lines=["Brand content for", "Vancouver businesses"],
        hero_sub="Photography and vertical video built for websites, social media and marketing.",
        hero_actions=[("#packages", "See packages"), ("/contact/", "Start a project")],
        schema=["faq-brand-content.json"],
        **hero_fields(hero_img, "Business portrait with even lighting and a clean background, photographed in Vancouver.")
    )

    cards = "\n".join([
        price_card("Half session", "Brand Essential", "$650", "90 minutes",
                   ["Planning consultation", "Up to 90 minutes", "One location",
                    "25+ edited photographs", "Commercial licence",
                    "Delivery in 5 business days"]),
        price_card("Photo + video", "Brand Photo + Video", "$950", "2 hours",
                   ["Planning consultation", "Up to 2 hours", "40+ edited photographs",
                    "One edited vertical video up to 60 seconds", "Commercial licence",
                    "Delivery in 5–7 business days"], featured=True),
        price_card("Content day", "Content Library", "$1,650", "4 hours",
                   ["Creative consultation", "Up to 4 hours", "Up to 2 locations",
                    "75+ edited photographs", "Two edited vertical videos",
                    "Commercial licence", "Delivery in 7 business days"]),
        price_card("Ongoing", "Monthly Retainer", "from $1,200", "per month",
                   ["One half-day session monthly", "Priority scheduling",
                    "Minimum 3 months"]),
    ])

    faqs = [
        ("How much does commercial photography cost in Vancouver?",
         "Mid-tier commercial day rates in North America run roughly $1,500 to $5,000. Oscar Léo Photography sits at the accessible end: $650 for a half-session and $1,650 for a four-hour content day, aimed at small and mid-sized Vancouver businesses."),
        ("Do I own the photos?",
         "You receive a commercial digital-use licence covering your own website, social media and standard marketing. Copyright remains with the photographer. Paid advertising campaigns and third-party licensing are quoted separately."),
        ("Do you shoot video as well as photos?",
         "Yes. The Photo + Video and Content Library packages both include professionally edited vertical video optimised for social platforms."),
        ("How often should a business refresh its content?",
         "Most businesses publishing weekly benefit from a quarterly shoot at minimum. The monthly retainer exists for businesses that publish more often than that."),
    ]

    body = f"""    <section class="section container">
      <p class="lead" data-reveal>Brand content packages start at $650 for a 90-minute session with
         25+ edited photographs, and run to $1,650 for a four-hour session producing 75+ photographs
         and two edited vertical videos. Every package includes a commercial digital-use licence for
         your own website, social media and marketing. A monthly retainer is available from $1,200.</p>
    </section>

    <section class="section--tight container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">Scope</span>
          <h2>What brand content includes</h2>
        </div>
        <div class="prose" data-reveal style="--i:1">
          <p>Depending on your business: professional portraits, team photography, lifestyle and
             in-action imagery, products, services, workspace, customer experience, details and
             behind-the-scenes content — plus short vertical video built for Instagram Reels, TikTok
             and YouTube Shorts.</p>
        </div>
      </div>
    </section>

    <!-- STAND-IN IMAGERY: portrait frames. Replace with brand, product and
         workspace photographs when available. -->
    <section class="section container">
{gallery(picks, "(min-width: 48em) 30vw, 47vw")}
    </section>

    <section class="section section--sunken" id="packages">
      <div class="container">
        <div class="section-head" data-reveal>
          <span class="eyebrow">Packages</span>
          <h2>Brand content packages</h2>
        </div>
        <div class="grid-2">
{cards}
        </div>
        <p class="fine-print" style="margin-top: var(--space-l)" data-reveal>
          Add-ons: additional hour $395 · additional vertical video $250 ·
          48-hour priority delivery $150 · advanced retouching $95/hr.</p>
      </div>
    </section>

    <section class="section container">
      <div class="section-head" data-reveal>
        <span class="eyebrow">Questions</span>
        <h2>Frequently asked</h2>
      </div>
      <div class="faq">
{faq_block(faqs)}      </div>
    </section>
"""
    return page, body


def build_concerts():
    hero_img = CONCERTS[17]
    page = dict(
        url="/vancouver-concert-photographer/",
        title="Concert Photographer Vancouver | Live Music & Festivals",
        desc="Live music photography in Vancouver from $450. Concerts, festivals, showcases and venues. Fast turnaround for promoters, artists and labels.",
        eyebrow="Concert & Live Performance",
        h1_lines=["Concert photographer", "in Vancouver, BC"],
        hero_sub="Stage, audience and atmosphere for artists, venues, promoters and festivals.",
        hero_actions=[("#pricing", "See pricing"), ("#work", "See the work")],
        schema=["faq-concerts.json"],
        **hero_fields(hero_img, "Performer under coloured stage lighting during a live concert in Vancouver.")
    )

    cards = "\n".join([
        price_card("Single set", "Live Performance", "$450", "90 minutes",
                   ["Up to 90 minutes", "50+ edited photographs",
                    "Promotional licence for the commissioning artist, venue or promoter",
                    "Delivery in 3–5 business days"]),
        price_card("Half day", "Half-Day Performance", "$950", "4 hours",
                   ["Up to 4 hours", "Multiple performers", "Stage, audience and atmosphere",
                    "120+ edited photographs", "Delivery in 5 business days"], featured=True),
        price_card("Festival", "Full-Day Festival", "$1,800", "8 hours",
                   ["Up to 8 hours", "Multiple artists", "Venue and event details",
                    "150+ edited photographs", "Delivery in 5–7 business days"]),
    ])

    faqs = [
        ("How much does concert photography cost in Vancouver?",
         "From $450 for a single performance up to $1,800 for a full festival day. Rates depend on coverage length and the number of performers."),
        ("Can the venue and the artist both use the images?",
         "The promotional licence covers whoever commissions the shoot. If the artist, venue and promoter all need usage rights, that's arranged before the booking."),
        ("Do you need a photo pass?",
         "Yes, for ticketed venue shows. If you're the promoter or the artist, you can usually arrange it. I'm familiar with standard three-song and no-flash restrictions."),
    ]

    body = f"""    <section class="section container">
      <p class="lead" data-reveal>Live performance photography in Vancouver starts at $450 for up to
         90 minutes with 50+ edited images. A four-hour half day is $950 and a full festival day is
         $1,800. Coverage includes stage, audience and atmosphere, with backstage access where
         permitted, and galleries delivered within 3–7 business days.</p>
    </section>

    <section class="section--tight container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">Clients</span>
          <h2>Who I work with</h2>
        </div>
        <div class="prose" data-reveal style="--i:1">
          <p>Individual artists, bands, concert promoters, venues, cultural performances, showcases and
             festivals throughout Vancouver and British Columbia.</p>
          <p>Live work is about timing and low light. I shoot fast, quietly, and without blocking
             anyone's view of the stage.</p>
        </div>
      </div>
    </section>

    <section class="section container" id="work">
      <div class="section-head section-head--split">
        <div data-reveal>
          <span class="eyebrow">Selected work</span>
          <h2>On stage</h2>
        </div>
        <p class="text-muted" data-reveal style="--i:1">Click any photograph to open it full-screen.</p>
      </div>
{gallery(CONCERTS, "(min-width: 78em) 21vw, (min-width: 48em) 30vw, 47vw", "gallery--wide")}
    </section>

    <section class="section section--sunken" id="pricing">
      <div class="container">
        <div class="section-head" data-reveal>
          <span class="eyebrow">Pricing</span>
          <h2>Live performance pricing</h2>
        </div>
        <div class="grid-3">
{cards}
        </div>
        <p class="fine-print" style="margin-top: var(--space-l)" data-reveal>
          Add-ons: additional hour $215 · second photographer $175/hr ·
          48-hour priority selects $150. Record label, publication, sponsor and advertising usage
          quoted separately.</p>
      </div>
    </section>

    <section class="section container">
      <div class="section-head" data-reveal>
        <span class="eyebrow">Questions</span>
        <h2>Frequently asked</h2>
      </div>
      <div class="faq">
{faq_block(faqs)}      </div>
    </section>
"""
    return page, body


def build_bts():
    # STAND-IN IMAGERY: no behind-the-scenes or unit stills work was supplied.
    # These are live-production frames from the concert set and are the weakest
    # substitute on the site — this page needs real set photography.
    hero_img = CONCERTS[4]
    picks = [CONCERTS[i] for i in (4, 13, 22, 31, 8, 44)]
    page = dict(
        url="/vancouver-bts-unit-stills-photographer/",
        title="BTS & Unit Stills Photographer Vancouver | Film & Music",
        desc="Behind-the-scenes and unit stills photography for Vancouver productions. Half day $700, full day $1,200. EPK and press licence included. See pricing.",
        eyebrow="Behind the Scenes & Unit Stills",
        h1_lines=["BTS and unit stills", "in Vancouver"],
        hero_sub="Production photography for film, television, music video and commercial shoots.",
        hero_actions=[("#pricing", "See pricing"), ("/contact/", "Discuss a production")],
        schema=["faq-bts.json"],
        **hero_fields(hero_img, "Behind-the-scenes frame of a live production under stage lighting.")
    )

    cards = "\n".join([
        price_card("Half day", "BTS Half Day", "$700", "up to 4 hours",
                   ["Up to 4 consecutive hours", "Production, crew and talent coverage",
                    "Production-use licence", "Delivery in 3–5 business days"]),
        price_card("Full day", "BTS Full Day", "$1,200", "up to 8 hours",
                   ["Up to 8 consecutive hours", "Crew, talent, set and process",
                    "Production-use licence", "Delivery in 5 business days"], featured=True),
        price_card("Fast turnaround", "Full Day + Priority Selects", "$1,400", "up to 8 hours",
                   ["Everything in the Full Day package",
                    "15–20 edited priority images within 24 hours"]),
    ])

    faqs = [
        ("What does a BTS photographer do on set?",
         "A behind-the-scenes or unit stills photographer documents the production itself — crew at work, talent between takes, the set, the equipment and the atmosphere. The images are used for EPKs, press kits, social media and production marketing."),
        ("How much does BTS photography cost in Vancouver?",
         "$700 for a half day and $1,200 for a full day, which sits within the standard range for professional unit stills work on independent and mid-budget productions."),
        ("Can we get images the same day?",
         "The Full Day + Priority Selects package delivers 15–20 finished images within 24 hours, with the complete gallery following in five business days."),
    ]

    body = f"""    <section class="section container">
      <p class="lead" data-reveal>Behind-the-scenes production photography is $700 for a half day of
         up to four hours and $1,200 for a full day of up to eight hours. A full day with 15–20
         priority selects delivered inside 24 hours is $1,400. All packages include a production-use
         licence covering EPK, press, social media and production marketing.</p>
    </section>

    <section class="section--tight container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">On set</span>
          <h2>Set etiquette matters more than anything else.</h2>
        </div>
        <div class="prose" data-reveal style="--i:1">
          <p>Film and television productions, music videos, recording sessions, commercial shoots,
             advertising campaigns and creative projects — in Vancouver, across British Columbia and
             throughout Canada.</p>
          <p>I work around the production without interrupting it, documenting the crew, the talent,
             the process and the atmosphere that never makes it into the final cut.</p>
        </div>
      </div>
    </section>

    <!-- STAND-IN IMAGERY: live-production frames from the concert set. This page
         most needs real unit stills work — see the README. -->
    <section class="section container">
{gallery(picks, "(min-width: 48em) 30vw, 47vw")}
    </section>

    <section class="section section--sunken" id="pricing">
      <div class="container">
        <div class="section-head" data-reveal>
          <span class="eyebrow">Pricing</span>
          <h2>Production photography pricing</h2>
        </div>
        <div class="grid-3">
{cards}
        </div>
        <p class="fine-print" style="margin-top: var(--space-l)" data-reveal>
          Add-ons: additional hour $175 · 24-hour priority selection $175 ·
          advanced retouching $95/hr. Travel and accommodation may apply outside the Vancouver area.</p>
      </div>
    </section>

    <section class="section container">
      <div class="section-head" data-reveal>
        <span class="eyebrow">Questions</span>
        <h2>Frequently asked</h2>
      </div>
      <div class="faq">
{faq_block(faqs)}      </div>
    </section>
"""
    return page, body


def build_about():
    hero_img = HEADSHOTS[16]
    page = dict(
        url="/about/",
        title="About Oscar Léo | Vancouver Headshot & Event Photographer",
        desc="Meet Oscar Léo, a Vancouver-based photographer specialising in headshots, events, brand content, concerts and behind-the-scenes production work.",
        eyebrow="About",
        h1_lines=["Oscar Léo"],
        hero_sub="Photographer, Vancouver, British Columbia.",
        **hero_fields(hero_img, "Portrait photographed on location in Vancouver.")
    )

    services = "\n".join(
        f'            <li><a class="text-link" href="{url}">{label}</a> — {price.lower()}</li>'
        for url, label, price in NAV[1:6]
    )

    body = f"""    <section class="section container">
      <p class="lead" data-reveal>Oscar Léo is a professional photographer based in Vancouver, British
         Columbia, working across headshots, events, brand content, live music and behind-the-scenes
         production photography.
         <mark class="todo">[ONE SENTENCE: how long you have been shooting professionally, and where
         you worked or trained before Vancouver.]</mark>
         <mark class="todo">[ONE SENTENCE: the kind of client you work with most — corporate teams,
         musicians, small businesses, productions.]</mark></p>
    </section>

    <section class="section--tight container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">Background</span>
          <h2>How I got here</h2>
        </div>
        <div class="prose" data-reveal style="--i:1">
          <p><mark class="todo">[Where you're from, how you came to photography, and what brought you
             to Vancouver. Two or three sentences. Concrete details work far better than adjectives —
             a place, a year, a first camera, a first paid job. This is the paragraph an AI engine
             quotes when someone asks "who is Oscar Léo".]</mark></p>
          <p><mark class="todo">[What you did before, or alongside, photography, if it informs the
             work. Delete this paragraph if it doesn't.]</mark></p>
        </div>
      </div>
    </section>

    <section class="section container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">Approach</span>
          <h2>How I work</h2>
          <p class="callout">Good photography should feel like you.</p>
        </div>
        <div class="prose" data-reveal style="--i:1">
          <p>I combine documentary observation with thoughtful direction — stepping in when guidance
             helps, and letting genuine moments happen on their own. The result is polished photography
             that doesn't feel staged: images with personality, atmosphere and a story behind them.</p>
          <p><mark class="todo">[Optional: your practical working style. How you handle nervous
             subjects, how you behave on a set, how you plan a shoot. One short paragraph.]</mark></p>
        </div>
      </div>
    </section>

    <section class="section section--sunken">
      <div class="container">
        <div class="section-head" data-reveal>
          <span class="eyebrow">Clients and work</span>
          <h2>Who I've photographed</h2>
        </div>
        <div class="prose" data-reveal>
          <p><mark class="todo">[List real clients, venues, productions or publications you have
             worked with — only ones you can name. This is the strongest trust signal on the site for a
             human reader, and exactly the kind of verifiable specific an AI engine cites. If you can't
             name clients, describe the work instead.]</mark></p>
        </div>
      </div>
    </section>

    <section class="section container">
      <div class="section-head" data-reveal>
        <span class="eyebrow">Services</span>
        <h2>What I photograph</h2>
      </div>
      <div class="prose" data-reveal>
        <ul>
{services}
        </ul>
        <p>Based in Vancouver, working throughout British Columbia and across Canada.
           <a class="text-link" href="/contact/">Get in touch</a> about a project.</p>
      </div>
    </section>
"""
    return page, body


def build_contact():
    hero_img = CONCERTS[38]
    page = dict(
        url="/contact/",
        title="Contact Oscar Léo Photography | Vancouver, British Columbia",
        desc="Enquire about photography in Vancouver and across Canada. Tell me your date, location and project and I will reply with availability and a quote.",
        eyebrow="Contact",
        h1_lines=["Let's talk about", "your project."],
        hero_sub="Vancouver, British Columbia. Available across Canada.",
        **hero_fields(hero_img, "Live performance photographed in a Vancouver venue.")
    )

    services = "\n".join(
        f'            <li><a class="text-link" href="{url}">{label}</a> — {price.lower()}</li>'
        for url, label, price in NAV[1:6]
    )

    body = f"""    <section class="section container">
      <p class="lead" data-reveal>Oscar Léo Photography is based in Vancouver, British Columbia,
         serving Metro Vancouver and available across Canada. To request availability and a quote,
         send your preferred date, location, the type of photography you need and your approximate
         coverage time.</p>
    </section>

    <section class="section--tight container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">Your enquiry</span>
          <h2>What to include</h2>
          <div class="prose">
            <ul>
              <li>Preferred date</li>
              <li>City and location</li>
              <li>Type of photography</li>
              <li>Approximate coverage time</li>
              <li>Details about your event, business or project</li>
            </ul>
            <p>For commercial projects, tell me how you plan to use the photographs or video.</p>
            <p class="fine-print">A booking retainer of 30% reserves your date.
               All prices in Canadian dollars, plus GST.</p>
          </div>
        </div>

        <div class="price-card" data-reveal style="--i:1">
          <p class="price-card__tag">Send an enquiry</p>
          <!-- FORM: mailto has no back end and silently fails for anyone without a
               configured mail client. Point the action at Formspree, Netlify Forms,
               Basin or your host's form handler before launch — see the README. -->
          <form class="form" action="mailto:hello@oscarleo.photography" method="post" enctype="text/plain">
            <div class="field">
              <label for="f-name">Your name</label>
              <input id="f-name" name="name" type="text" autocomplete="name" required>
            </div>
            <div class="field">
              <label for="f-email">Email</label>
              <input id="f-email" name="email" type="email" autocomplete="email" required>
            </div>
            <div class="field">
              <label for="f-type">Type of photography</label>
              <select id="f-type" name="type">
                <option>Headshots &amp; portraits</option>
                <option>Event photography</option>
                <option>Brand photography &amp; video</option>
                <option>Concert &amp; live performance</option>
                <option>Behind the scenes / unit stills</option>
                <option>Something else</option>
              </select>
            </div>
            <div class="field">
              <label for="f-date">Preferred date</label>
              <input id="f-date" name="date" type="date">
            </div>
            <div class="field">
              <label for="f-detail">Your project</label>
              <textarea id="f-detail" name="detail" rows="5"></textarea>
              <span class="hint">Location, approximate coverage time, and how you plan to use the images.</span>
            </div>
            <button class="btn" type="submit">Send enquiry</button>
          </form>
        </div>
      </div>
    </section>

    <section class="section container">
      <div class="grid-2">
        <div data-reveal>
          <span class="eyebrow">Areas served</span>
          <h2>Vancouver and beyond</h2>
          <p class="text-muted">Vancouver, Burnaby, Richmond, North Vancouver, West Vancouver, Surrey,
             Coquitlam, Delta, Langley and the wider Lower Mainland. Available throughout British
             Columbia and across Canada.</p>
        </div>
        <div class="prose" data-reveal style="--i:1">
          <span class="eyebrow">Services and starting prices</span>
          <ul>
{services}
          </ul>
        </div>
      </div>
    </section>
"""
    return page, body


BUILDERS = [build_home, build_headshots, build_events, build_brand,
            build_concerts, build_bts, build_about, build_contact]


def main():
    for builder in BUILDERS:
        page, body = builder()
        path = write(page["url"], render(page, body))
        print("wrote", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
