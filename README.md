# Oscar Leo Photography — website

A static, eight-page site. No framework, no build step, no dependencies: plain HTML, one stylesheet, one script. It deploys by copying the folder to any host.

---

## Preview it locally

Root-relative URLs (`/contact/`) don't resolve when you open a file by double-clicking, so run a local server:

```bash
cd "/Users/oscarleo/Desktop/portfolio ozgur/site" && python3 -m http.server 4321
```

Then open <http://localhost:4321>. Stop it with Ctrl-C.

## Deploy it

Drag the whole `site` folder onto **Netlify Drop** (<https://app.netlify.com/drop>) or **Cloudflare Pages**. Both are free for this and both serve the directory-style URLs correctly. For traditional hosting, upload the contents of `site/` to your web root over SFTP.

The URLs match the SEO plan exactly, so `/vancouver-headshot-photographer/` etc. work as designed. Remember the 301 from `/best-photographer-in-vancouver/` to `/contact/` — see `../seo-implementation/05-redirects-and-technical.md`.

---

## What's in here

```
index.html                                  Home
vancouver-headshot-photographer/            Headshots — 22 photographs
vancouver-event-photographer/               Events
vancouver-brand-photography-video/          Brand content
vancouver-concert-photographer/             Concerts — 49 photographs
vancouver-bts-unit-stills-photographer/     Behind the scenes
about/                                      About  ← unfinished copy, see below
contact/                                    Contact + enquiry form
assets/css/site.css                         The entire stylesheet
assets/js/site.js                           ~6KB, no dependencies
assets/img/                                 289 processed images
assets/img/grid/                            The contact-sheet hero montage
llms.txt  robots.txt  sitemap.xml           For search and AI answer engines
_build/generate.py                          Optional page generator
_build/montage.py                           Rebuilds the hero montage
_build/hero_crops.py                        Landscape hero crops for portrait photos
```

### The home hero

The home page opens on a 6×6 contact sheet of the portrait work. It is a real image (`assets/img/grid/`), not a CSS grid, so it also serves as the social-share card.

`_build/montage.py` regenerates it from the processed headshots. With no PIL or ImageMagick on this machine, it assembles the grid as a PDF that embeds each JPEG losslessly, then rasterises with `sips` — so the cells are full quality rather than a re-compressed screenshot:

```bash
python3 _build/montage.py && sips -s format jpeg -s formatOptions 78 --resampleWidth 2400 \
  /tmp/montage.pdf --out assets/img/grid/vancouver-photographer-portrait-grid-2400.jpg
```

Change `FOCUS_Y` in the script to shift the crop within each cell (0.30 keeps faces in frame), or edit the `step` value to reshuffle which frames land where.

### About `_build/generate.py`

The eight HTML files share a header, footer and lightbox. Rather than maintain that markup eight times, the pages are generated:

```bash
python3 _build/generate.py
```

**It overwrites every HTML file.** If you hand-edit a page, either stop using the script or fold the change back into it. The HTML is perfectly good to edit directly — the script is a convenience, not a requirement.

---

## The design system

**Colour — monochrome.** The interface is black, white and the greys between. Every colour on the site comes from inside the photographs. The palette lives in `:root` at the top of `site.css`; change it there and the whole site follows.

| | Light | Dark |
|---|---|---|
| Background | `#FFFFFF` | `#0A0A0A` |
| Text | `#0A0A0A` | `#FAFAFA` |
| Muted text | `#52525B` | `#A1A1AA` |
| Accent | `#0A0A0A` | `#FAFAFA` |

Both themes ship. The site follows the visitor's OS setting and the toggle overrides it, remembered in `localStorage`.

**Type — Archivo,** one family at weights 400/500/600. Headings run tight (-0.035em to -0.045em) and large; body text stays at a comfortable measure. A single family is quieter than a pairing and costs one font request instead of two.

**Spacing** is a fluid scale using `clamp()`, so there are no per-breakpoint font-size or spacing overrides anywhere.

**Corners are square** (`--radius: 0`) and there are no shadows. Depth is expressed with hairline rules and whitespace.

---

## Motion

Everything animates `transform` and `opacity` only — never `width`, `height`, `top` or `left` — so the compositor handles it and nothing triggers layout. There is no animation library; a 70KB dependency would cost more than the effects are worth.

- Scroll reveals via one shared `IntersectionObserver`, unobserved after firing
- Line-by-line reveal on the page headings
- Images settle from a 1.07 scale as they enter
- A cursor-following preview on the home page service list (fine pointers, wide screens)
- The header is transparent with light text over the hero, and becomes a solid surface past 40px of scroll

The home hero's slow drift is switched off deliberately — a grid of faces sliding around reads as a rendering glitch rather than as motion. Single-subject heroes on the other pages keep it.

`prefers-reduced-motion: reduce` disables all of it and shows everything immediately. The hidden state is scoped behind a `.js` class added before first paint, so **if scripting fails the page renders as plain static content** rather than a blank screen.

---

## Three things still to do

**1. The About page is unfinished.** Placeholder text is wrapped in `<mark class="todo">` and renders with a visible dashed underline, so it cannot ship unnoticed. Six passages need your words — background, how you work, and named clients. That last section is the strongest trust signal on the site and the passage AI engines quote when asked who you are.

**2. Three pages use stand-in imagery.** No event, brand or behind-the-scenes photographs were supplied, so those galleries borrow from the concert and portrait sets. Each is flagged with an HTML comment reading `STAND-IN IMAGERY`. The BTS page is the weakest — concert frames are not unit stills, and anyone in the film industry will know it at a glance. Replace these before showing the site to production clients.

**3. The contact form has no back end.** It is currently a `mailto:` form, which silently fails for visitors without a configured mail client. Point the `action` at Formspree, Netlify Forms or Basin — a one-line change in `contact/index.html`. If you deploy to Netlify, adding `netlify` to the `<form>` tag is enough.

Also worth a pass: **alt text**. Every image has descriptive alt text, but it is written from what the frame generally contains, not from what is actually in each photograph. It is honest and screen-reader-usable as it stands; one human sentence per image would be better.

---

## Images

284 files: each photograph at 400/800/1200/1800px wide, JPEG, quality 68 for the small sizes and 52 for the large ones (retina displays hide the difference, and it halves the weight). Average 29KB at 400w, 100KB at 800w, 342KB at 1800w.

### Layout

Galleries are **masonry columns**, not a grid. A grid makes every tile in a row share one height, so a 2:3 portrait sitting next to a 3:2 landscape either gets cropped or leaves a hole in the row. With columns each photograph keeps its own height, so **nothing is ever cropped or stretched** — the full frame shows at its true proportions. Two columns on phones, three on tablets, four for the wide galleries.

Every `<img>` carries its real `width` and `height`, so the browser reserves the exact box from the intrinsic ratio before the file arrives — **cumulative layout shift is zero**. The hero loads eagerly with `fetchpriority="high"`; everything else is lazy.

The lightbox shows the whole photograph, letterboxed, at its true aspect ratio — portrait frames are never cropped to a landscape slice. Clicking the picture keeps it open; clicking the empty margin beside it closes.

### Hero art direction

The hero is full-bleed, so its shape follows the browser window. A portrait photograph fits a phone perfectly and fits a desktop terribly: `cover` scales it to fill the width and hides most of its height. Measured on the headshots page at 1440×900, the original build showed **47% of the photo with 17% cut off the top** — and the subject's head was in that 17%. It got worse the wider the window went.

Five pages use portrait heroes. Each now has a second, 16:9 crop cut around the subject, served by a `<picture>` element only when the hero box is landscape-shaped:

```bash
python3 _build/hero_crops.py
```

`FACE_Y` in that script records where each subject's face sits in the original, as a fraction of image height. The crop is positioned so the face lands at 35% of the frame — clear of the headline that overlays the lower half. Re-run it after changing a hero photograph, and add a `FACE_Y` entry for the new file.

The `<source media>` threshold is the shape of the **hero box**, not the window: full-height heroes switch at `1/1`, the 72svh service-page heroes at `18/25`. Getting that wrong is subtle — a 72svh hero turns landscape while the window is still portrait, which left tablets losing 8–11% off the top.

Worst-case top trim after the fix, measured from 375px to 3440px wide: **6.5%**, against roughly 11% of headroom above each subject.

**WebP would save roughly another 25–30%.** macOS `sips` can't write it, so the site ships JPEG. If you install the tooling (`brew install webp`), the images can be converted and `<picture>` sources added.

**To swap a photograph:** replace the four files sharing a slug in `assets/img/`, keeping the same aspect ratio. To change which photographs appear, edit the index lists in `_build/generate.py` and re-run it.

---

## Verified

Checked in-browser at 375, 768, 1280 and 1440px, in both themes:

- No horizontal overflow on any of the eight pages
- No gallery photograph is cropped or stretched: box ratio matches the file's own ratio on every image, checked across 6 pages × 4 widths
- Every text/background pair on solid surfaces meets WCAG AA (113 elements per page, both themes)
- **Text over the hero photographs** measured separately, by compositing the image, the gradient and the local panel in a canvas and taking the *worst single pixel* behind each element. All eight pages pass: headlines 9.3:1 or better, labels 7.9:1 or better, nav 4.6:1 or better
- One `<h1>` per page, no skipped heading levels
- Lightbox: focus moves into the dialog, is trapped, and returns to the tile on close; Escape and arrow keys work; swipe works on touch
- Zero console errors
- Interactive controls meet the 24px minimum target size; buttons and icon controls are 44–48px

### If you change a hero photograph

Hero legibility is the one thing on this site that depends on the specific image. The local panel behind the text (section 22 of the stylesheet) exists so that a bright photograph can't push the headline below AA, but it is worth re-checking after a swap: load the page and confirm the eyebrow label and nav links are still comfortably readable at the top of a bright frame.
