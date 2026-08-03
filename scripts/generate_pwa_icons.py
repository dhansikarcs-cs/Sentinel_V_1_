"""Generate PWA icons for Sentinel using PIL. Design: dark rounded square with a pulse line + heart."""
from PIL import Image, ImageDraw
import os

PUBLIC = os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
os.makedirs(PUBLIC, exist_ok=True)

BG = (21, 24, 36)          # #151824
ACCENT = (196, 158, 164)   # #c49ea4
ACCENT_SOFT = (216, 180, 186)  # #d8b4ba
GREEN = (34, 197, 94)      # #22c55e


def draw_icon(size, maskable=False):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if maskable:
        d.rectangle([0, 0, size, size], fill=BG)
    else:
        radius = int(size * 0.22)
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BG)

    cx = size * 0.5
    lw = max(2, int(size * 0.045))

    # Pulse line across the center
    left = size * 0.14
    right = size * 0.86
    mid = size * 0.5
    amp = size * 0.20

    # flat-left, sharp peak up, sharp peak down, flat-right
    points = [
        (left, mid),
        (size * 0.40, mid),
        (size * 0.47, mid - amp),
        (size * 0.55, mid + amp),
        (size * 0.63, mid),
        (right, mid),
    ]
    d.line(points, fill=ACCENT, width=lw, joint="curve")

    # Heart in the middle on the line
    hx = size * 0.5
    hy = size * 0.5
    hs = size * 0.055
    heart = [
        (hx, hy + hs * 1.4),
        (hx - hs * 1.2, hy + hs * 0.2),
        (hx - hs * 0.9, hy - hs * 0.7),
        (hx, hy - hs * 0.25),
        (hx + hs * 0.9, hy - hs * 0.7),
        (hx + hs * 1.2, hy + hs * 0.2),
    ]
    d.polygon(heart, fill=ACCENT_SOFT)

    return img


for size in (192, 512):
    draw_icon(size).save(os.path.join(PUBLIC, f"icon-{size}.png"))
    print(f"icon-{size}.png written")

draw_icon(512, maskable=True).save(os.path.join(PUBLIC, "icon-maskable-512.png"))
print("icon-maskable-512.png written")

# apple touch icon (non-maskable, opaque)
apple = draw_icon(180)
apple_bg = Image.new("RGBA", (180, 180), BG)
apple_bg.alpha_composite(apple)
apple_bg.convert("RGB").save(os.path.join(PUBLIC, "apple-touch-icon.png"))
print("apple-touch-icon.png written")
