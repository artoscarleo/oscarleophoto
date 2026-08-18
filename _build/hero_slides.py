#!/usr/bin/env python3
"""
Crops for the homepage hero slideshow.

The hero fills the window, so its shape swings from about 1.60 on a desktop to
about 0.46 on a phone. One set of files cannot serve both without throwing most
of the frame away, so each photograph is cut twice:

    hw   16:9  for landscape windows   (close to 1.60, very little further crop)
    ht    2:3  for portrait windows    (0.667 against a 0.46 box, so the sides
                                        are trimmed but the subject survives)

Every slide shares its shape within a breakpoint, so none of them looks more
zoomed in than the others as the slideshow runs.

FOCUS is where the subject sits in the source, as a fraction of image height.

    python3 _build/hero_slides.py
"""

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")
TMP = "/tmp/ol-hero-slides"
# hw is 3:2, not 16:9 — the hero box is about 1.6 at a desktop window, and a
# 16:9 slide had to be scaled up 11% to cover it.
SHAPES = [("hw", 3 / 2), ("ht", 2 / 3)]
WIDTHS = [800, 1200, 1800]
QUALITY = {800: 68, 1200: 58, 1800: 54}
SUBJECT_AT = 0.36

# folder, slug, subject centre (fraction of source height)
SLIDES = [
    # Landscape windows only — phones use MOBILE_SLIDES instead. Subjects sit
    # near the centre of the frame so the 3:2 cut keeps them whole. Order is
    # shuffled in the browser.
    #
    # Two concert frames (live-11x, live-13x) were dropped on request and not
    # replaced, so this is seven slides: three weddings, three headshots, one
    # concert.
    ("headshots", "vancouver-headshot-studio-01x", 0.30),
    ("weddings", "vancouver-wedding-story-01x", 0.42),
    ("concerts", "vancouver-concert-live-12x", 0.42),
    ("headshots", "vancouver-headshot-studio-03x", 0.28),
    ("weddings", "vancouver-wedding-story-03x", 0.45),
    ("headshots", "vancouver-headshot-studio-04x", 0.28),
    ("weddings", "vancouver-wedding-story-05x", 0.45),
]

# Portrait windows get natively-vertical photographs rather than a landscape
# frame cropped down to 2:3. Cropping a 3:2 stage shot to a phone screen throws
# away two thirds of its width and leaves the subject small in a tall box; a
# photograph shot vertical fills that shape as taken. Paired to SLIDES by
# index, so each slide keeps its category in both orientations.
MOBILE_SLIDES = [
    # Phones get headshots only — all six, and nothing else. They are the one
    # category shot vertical throughout, so each one fills a phone screen as
    # taken rather than being cropped down from a wide frame.
    #
    # There are six of these against nine desktop slides, so they cycle: slide
    # 7 reuses the first, 8 the second, 9 the third. Six distinct photographs
    # appear on a phone, which is what was asked for; the desktop rotation is
    # untouched.
    ("headshots", "vancouver-headshot-studio-01x", 0.30),
    ("headshots", "vancouver-headshot-studio-02x", 0.28),
    ("headshots", "vancouver-headshot-studio-03x", 0.28),
    ("headshots", "vancouver-headshot-studio-04x", 0.28),
    ("headshots", "vancouver-headshot-studio-05x", 0.28),
    ("headshots", "vancouver-headshot-studio-06x", 0.28),
]


def dims(path):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                         capture_output=True, text=True).stdout
    w = h = 0
    for line in out.splitlines():
        if "pixelWidth" in line:
            w = int(line.split(":")[1])
        elif "pixelHeight" in line:
            h = int(line.split(":")[1])
    return w, h


def crop_pdf(src, out_pdf, cw, ch, ox, oy):
    with open(src, "rb") as fh:
        data = fh.read()
    iw, ih = dims(src)
    objs = []

    def add(b):
        objs.append(b)
        return len(objs)

    num = add(b"<< /Type /XObject /Subtype /Image /Width " + str(iw).encode()
              + b" /Height " + str(ih).encode()
              + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length "
              + str(len(data)).encode() + b" >>\nstream\n" + data + b"\nendstream")
    content = (b"q\n" + f"0 0 {cw} {ch} re W n\n".encode()
               + f"{iw} 0 0 {ih} {-ox} {-(ih - ch - oy)} cm\n".encode()
               + f"/Im{num} Do\nQ\n".encode())
    cnum = add(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    pnum = len(objs) + 1
    psnum = pnum + 1
    add(b"<< /Type /Page /Parent " + str(psnum).encode() + b" 0 R /MediaBox [0 0 "
        + str(cw).encode() + b" " + str(ch).encode()
        + b"] /Resources << /XObject << /Im" + str(num).encode() + b" " + str(num).encode()
        + b" 0 R >> >> /Contents " + str(cnum).encode() + b" 0 R >>")
    add(b"<< /Type /Pages /Kids [" + str(pnum).encode() + b" 0 R] /Count 1 >>")
    cat = add(b"<< /Type /Catalog /Pages " + str(psnum).encode() + b" 0 R >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offs = {}
    for i, b in enumerate(objs, 1):
        offs[i] = len(out)
        out += str(i).encode() + b" 0 obj\n" + b + b"\nendobj\n"
    xr = len(out)
    cnt = len(objs) + 1
    out += b"xref\n0 " + str(cnt).encode() + b"\n0000000000 65535 f \n"
    for i in range(1, cnt):
        out += ("%010d 00000 n \n" % offs[i]).encode()
    out += (b"trailer\n<< /Size " + str(cnt).encode() + b" /Root " + str(cat).encode()
            + b" 0 R >>\nstartxref\n" + str(xr).encode() + b"\n%%EOF\n")
    with open(out_pdf, "wb") as fh:
        fh.write(bytes(out))


def main():
    os.makedirs(TMP, exist_ok=True)
    manifest = []

    def largest(folder, slug):
        for w in (1800, 2400, 1200, 800):
            cand = os.path.join(IMG, folder, f"{slug}-{w}.jpg")
            if os.path.exists(cand):
                return cand
        return os.path.join(IMG, folder, f"{slug}-1800.jpg")

    def cut(idx, entry, tag, ratio):
        folder, slug, focus = entry[0], entry[1], entry[2]
        focus_x = entry[3] if len(entry) > 3 else 0.5
        src = largest(folder, slug)
        iw, ih = dims(src)

        landscape_to_portrait = ratio < 1 and iw > ih
        if landscape_to_portrait:
            # A landscape photo cropped to a portrait shape: taking the full
            # source height leaves oy nowhere to go (ih - ch is 0), so the crop
            # starts at row 0 no matter where the subject actually is. Capping
            # the height opens up room to reposition.
            ch = int(round(ih * 0.78))
            cw = int(round(ch * ratio))
            subject_at = 0.20
        else:
            cw, ch = iw, int(round(iw / ratio))
            if ch > ih:
                ch = ih
                cw = int(round(ch * ratio))
            subject_at = SUBJECT_AT
        oy = max(0, min(int(round(focus * ih - subject_at * ch)), ih - ch))
        ox = max(0, min(int(round(focus_x * iw - 0.5 * cw)), iw - cw))

        pdf = os.path.join(TMP, f"{slug}-{tag}.pdf")
        crop_pdf(src, pdf, cw, ch, ox, oy)

        made = []
        for w in WIDTHS:
            # A landscape-source portrait crop can be narrower than the smallest
            # served width, so allow a slight upscale rather than skipping it.
            if w > cw and not landscape_to_portrait:
                continue
            dst = os.path.join(IMG, folder, f"{slug}-{tag}-{w}.jpg")
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(QUALITY[w]),
                            "--resampleWidth", str(w), pdf, "--out", dst], capture_output=True)
            made.append(w)
        manifest.append(f"{idx}|{folder}|{slug}|{tag}|{cw}x{ch}|{','.join(map(str, made))}")
        print(f"{idx} {slug:38} {tag}  {iw}x{ih} -> {cw}x{ch} @y={oy:4} x={ox:4}  {made}")

    hw_ratio = dict(SHAPES)["hw"]
    ht_ratio = dict(SHAPES)["ht"]
    for i, entry in enumerate(SLIDES):
        cut(i, entry, "hw", hw_ratio)
    for i in range(len(SLIDES)):
        cut(i, MOBILE_SLIDES[i % len(MOBILE_SLIDES)], "ht", ht_ratio)

    with open(os.path.join(IMG, "hero-slides.txt"), "w") as fh:
        fh.write("\n".join(manifest) + "\n")


if __name__ == "__main__":
    main()
