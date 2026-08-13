#!/usr/bin/env python3
"""
Square crops for the homepage service backdrop.

Why: the backdrop uses object-fit: cover, so every photograph is scaled until it
fills the same box. When the sources have different aspect ratios, each one gets
scaled by a different amount — measured on the live page, between 1.16x and
2.60x. The result is that some photographs look far more zoomed in than others
as they swap, which reads as inconsistent.

Cropping all of them to one ratio removes that entirely: identical sources scale
identically in any box, on desktop and on mobile.

1:1 is chosen because the backdrop box is close to square at ordinary desktop
widths (0.90 at 1280px, 1.02 at 1440px, 1.35 at 1920px), so a square source sits
in it with very little further cropping.

FOCUS_Y is where the subject sits in the original, as a fraction of image height,
so faces are not cut off by the crop.

    python3 _build/backdrop_crops.py
"""

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")
TMP = "/tmp/ol-backdrop-crops"
OUT_WIDTHS = [800, 1200, 1800]
QUALITY = {800: 68, 1200: 58, 1800: 54}
SUBJECT_AT = 0.34          # where the subject should land inside the crop

# Two shapes, because the backdrop box changes shape dramatically:
#   desktop  ~0.90-1.35 (near square)  -> a square crop barely needs cropping
#   mobile   ~0.32      (very tall)    -> a square loses 68% of its width, so a
#                                         2:3 portrait is used there instead,
#                                         which keeps 48% and still yields
#                                         800x1200 from a landscape source.
SHAPES = [("sq", 1.0), ("pt", 2 / 3)]

# folder, slug, subject centre as a fraction of the original's height
SOURCES = [
    ("headshots", "vancouver-headshot-business-07", 0.20),
    ("concerts", "vancouver-concert-crowd-12", 0.50),
    ("headshots", "vancouver-headshot-corporate-20", 0.17),
    ("weddings", "vancouver-wedding-couple-portrait-10", 0.45),
    ("concerts", "vancouver-concert-backstage-23", 0.50),
    ("concerts", "vancouver-concert-crowd-30", 0.50),
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
    pdf_y = -(ih - ch - oy)
    content = (b"q\n" + f"0 0 {cw} {ch} re W n\n".encode()
               + f"{iw} 0 0 {ih} {-ox} {pdf_y} cm\n".encode()
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
    for folder, slug, focus in SOURCES:
        src = os.path.join(IMG, folder, slug + "-1800.jpg")
        iw, ih = dims(src)

        for tag, ratio in SHAPES:
            # largest crop of this shape that fits inside the source
            ch = min(ih, int(iw / ratio))
            cw = int(round(ch * ratio))
            if cw > iw:
                cw = iw
                ch = int(round(cw / ratio))
            oy = int(round(focus * ih - SUBJECT_AT * ch))
            oy = max(0, min(oy, ih - ch))
            ox = max(0, (iw - cw) // 2)

            pdf = os.path.join(TMP, f"{slug}-{tag}.pdf")
            crop_pdf(src, pdf, cw, ch, ox, oy)

            made = []
            for w in OUT_WIDTHS:
                if w > cw:
                    continue
                dst = os.path.join(IMG, folder, f"{slug}-{tag}-{w}.jpg")
                subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(QUALITY[w]),
                                "--resampleWidth", str(w), pdf, "--out", dst], capture_output=True)
                made.append(w)
            manifest.append(f"{slug}|{tag}|{cw}x{ch}|{','.join(map(str, made))}")
            print(f"{slug:38} {tag}  {iw}x{ih} -> {cw}x{ch} @y={oy:4}  widths {made}")

    with open(os.path.join(IMG, "backdrop-square.txt"), "w") as fh:
        fh.write("\n".join(manifest) + "\n")


if __name__ == "__main__":
    main()
