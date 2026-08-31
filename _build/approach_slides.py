#!/usr/bin/env python3
"""
Crops for the slideshow behind the homepage "Approach" band.

Same two-shape approach as the hero (see hero_slides.py): the band is wide and
short on a desktop and narrow and tall on a phone, so one set of files cannot
serve both without throwing most of the frame away.

    aw   16:9  for landscape boxes
    at    2:3  for portrait boxes

Every slide shares its shape within a breakpoint, so none looks more zoomed in
than the others as the slideshow runs.

The four photographs are ones that had never been used in a featured position —
they appeared only inside a long category gallery. Nothing in the library was
completely unused; all 93 photographs already appear somewhere.

FOCUS is where the subject sits in the source, as a fraction of image height.

    python3 _build/approach_slides.py
"""

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")
TMP = "/tmp/ol-approach-slides"
# The landscape shape is 3:2 rather than 16:9. The media box is 24% taller than
# the band (the parallax overhang), so at desktop widths it sits around 1.4-1.6
# — a 16:9 crop had to be scaled up hard to cover that, which turned a portrait
# into a close-up of a chin. 3:2 is close to the box, so almost nothing is
# thrown away and the subject reads as a portrait.
SHAPES = [("aw", 3 / 2), ("at", 2 / 3)]
WIDTHS = [800, 1200, 1800]
QUALITY = {800: 68, 1200: 58, 1800: 54}
SUBJECT_AT = 0.40          # where the subject should land inside the crop

# folder, slug, subject centre (fraction of source height)
SLIDES = [
    # The one in use. Face sits high in the frame, so the crop is pulled up to
    # keep it in the band's quiet upper area rather than behind the paragraph.
    ("headshots", "vancouver-headshot-studio-01", 0.30),
    # Alternates, kept so swapping the pick is a one-line change in generate.py.
    ("headshots", "vancouver-headshot-professional-14", 0.19),
    # Three more alternates lived here — a bridal portrait and two concert
    # frames — until the wedding and concert sets were replaced from
    # Portfolio/. Their sources went with the old sets, so every run of this
    # script died on the first missing file. Removed rather than left to fail
    # again; the guard below covers the next time it happens.
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
    """Crop by embedding the JPEG in a one-page PDF behind a clipping rectangle.

    sips cannot crop at an arbitrary offset, but it will rasterise a PDF, so the
    page carries the image shifted under a clip path of the wanted size.
    """
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
    for folder, slug, focus in SLIDES:
        src = os.path.join(IMG, folder, slug + "-1800.jpg")
        # Portfolio/ is the source of truth for galleries, so a photograph
        # named here can disappear when a category is replaced. Say so and
        # carry on: one retired alternate should not stop the slide that is
        # actually in use from being rebuilt.
        if not os.path.exists(src):
            print(f"  ! {slug}: no {os.path.basename(src)} on disk — skipping")
            continue
        iw, ih = dims(src)

        for tag, ratio in SHAPES:
            cw, ch = iw, int(round(iw / ratio))
            if ch > ih:
                ch = ih
                cw = int(round(ch * ratio))
            oy = max(0, min(int(round(focus * ih - SUBJECT_AT * ch)), ih - ch))
            ox = max(0, (iw - cw) // 2)

            pdf = os.path.join(TMP, f"{slug}-{tag}.pdf")
            crop_pdf(src, pdf, cw, ch, ox, oy)

            made = []
            for w in WIDTHS:
                if w > cw:
                    continue
                dst = os.path.join(IMG, folder, f"{slug}-{tag}-{w}.jpg")
                subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(QUALITY[w]),
                                "--resampleWidth", str(w), pdf, "--out", dst], capture_output=True)
                made.append(w)
            manifest.append(f"{folder}|{slug}|{tag}|{cw}x{ch}|{','.join(map(str, made))}")
            print(f"{slug:40} {tag}  {iw}x{ih} -> {cw}x{ch} @y={oy:4}  {made}")

    with open(os.path.join(IMG, "approach-slides.txt"), "w") as fh:
        fh.write("\n".join(manifest) + "\n")


if __name__ == "__main__":
    main()
