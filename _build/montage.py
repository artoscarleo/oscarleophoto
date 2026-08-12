#!/usr/bin/env python3
"""
Build a 6x6 contact-sheet montage from the processed headshots.

No PIL, no ImageMagick on this machine — so the grid is assembled as a PDF that
embeds each JPEG losslessly (/DCTDecode) inside a clipped cell, then handed to
`sips` for rasterising. Each source JPEG is copied in byte-for-byte, so there is
no intermediate re-compression.
"""

import os
import subprocess

SITE = "/Users/oscarleo/Desktop/portfolio ozgur/site"
SRC = os.path.join(SITE, "assets", "img", "headshots")
OUT_PDF = "/private/tmp/claude-501/-Users-oscarleo-CLOUDAI-WEB-COD-web-test/390ee8c3-7e91-4e0e-a75b-19144f0a9a12/scratchpad/montage.pdf"

COLS, ROWS = 6, 6
CELL = 400                      # points == px at 72dpi scale factor 1
GAP = 0                         # flush grid, like the reference
FOCUS_Y = 0.30                  # crop bias: keep faces (upper third) in frame


def load_manifest():
    rows = []
    with open(os.path.join(SRC, "aspect.txt")) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            slug, w, h = line.split("|")
            rows.append((slug, int(w), int(h)))
    rows.sort()
    return rows


def esc(b):
    return b


def build():
    imgs = load_manifest()
    # 22 unique frames tiled across 36 cells, in a shuffled-but-fixed order so
    # repeats never land next to each other.
    order = []
    n = len(imgs)
    step = 7  # coprime with 22 -> walks the whole set before repeating
    for i in range(COLS * ROWS):
        order.append(imgs[(i * step) % n])

    objs = {}          # number -> bytes body
    next_num = [1]

    def add(body):
        num = next_num[0]
        next_num[0] += 1
        objs[num] = body
        return num

    # Embed each distinct file once, reuse the XObject for repeats.
    xobj_for = {}
    for slug, w400, h400 in imgs:
        path = os.path.join(SRC, slug + "-800.jpg")
        with open(path, "rb") as fh:
            data = fh.read()
        w = 800
        h = round(800 * h400 / w400)
        body = (
            b"<< /Type /XObject /Subtype /Image /Width " + str(w).encode()
            + b" /Height " + str(h).encode()
            + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length "
            + str(len(data)).encode() + b" >>\nstream\n" + data + b"\nendstream"
        )
        xobj_for[slug] = (add(body), w, h)

    # Content stream: clip each cell, draw the image scaled to cover it.
    parts = []
    page_w = COLS * CELL
    page_h = ROWS * CELL
    for idx, (slug, w400, h400) in enumerate(order):
        num, iw, ih = xobj_for[slug]
        col = idx % COLS
        row = idx // COLS
        x = col * CELL
        # PDF origin is bottom-left; fill top-down to match the reference.
        y = page_h - (row + 1) * CELL

        # cover: scale so the shorter side fills the cell
        scale = max(CELL / iw, CELL / ih)
        dw, dh = iw * scale, ih * scale
        off_x = x - (dw - CELL) / 2.0
        off_y = y - (dh - CELL) * (1.0 - FOCUS_Y)

        parts.append(
            b"q\n"
            + f"{x} {y} {CELL} {CELL} re W n\n".encode()
            + f"{dw:.3f} 0 0 {dh:.3f} {off_x:.3f} {off_y:.3f} cm\n".encode()
            + f"/Im{num} Do\n".encode()
            + b"Q\n"
        )
    content = b"".join(parts)
    content_num = add(
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream"
    )

    res = b"<< /XObject << " + b" ".join(
        f"/Im{num} {num} 0 R".encode() for num, _, _ in xobj_for.values()
    ) + b" >> >>"

    page_num = next_num[0]
    pages_num = page_num + 1
    add(
        b"<< /Type /Page /Parent " + str(pages_num).encode()
        + b" 0 R /MediaBox [0 0 " + str(page_w).encode() + b" " + str(page_h).encode()
        + b"] /Resources " + res + b" /Contents " + str(content_num).encode() + b" 0 R >>"
    )
    add(b"<< /Type /Pages /Kids [" + str(page_num).encode() + b" 0 R] /Count 1 >>")
    cat_num = add(b"<< /Type /Catalog /Pages " + str(pages_num).encode() + b" 0 R >>")

    # Serialise with a correct xref table.
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += str(num).encode() + b" 0 obj\n" + objs[num] + b"\nendobj\n"
    xref_at = len(out)
    count = max(objs) + 1
    out += b"xref\n0 " + str(count).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, count):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer\n<< /Size " + str(count).encode() + b" /Root "
            + str(cat_num).encode() + b" 0 R >>\nstartxref\n"
            + str(xref_at).encode() + b"\n%%EOF\n")

    with open(OUT_PDF, "wb") as fh:
        fh.write(bytes(out))
    print("pdf:", OUT_PDF, len(out) // 1024, "KB", f"{page_w}x{page_h}pt")


if __name__ == "__main__":
    build()
