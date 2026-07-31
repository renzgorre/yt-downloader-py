"""Generate assets/icon.ico and assets/installer_banner.bmp for the NSIS installer."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

ASSETS = Path("assets")
ASSETS.mkdir(exist_ok=True)

# ── Palette ────────────────────────────────────────────────────────────────────
BG        = (18,  18,  24)   # near-black
ACCENT    = (30, 120, 255)   # bright blue  (matches app theme)
ACCENT2   = (0,  200, 130)   # teal-green   (secondary)
WHITE     = (255, 255, 255)
GRAY      = (160, 160, 180)

# ══════════════════════════════════════════════════════════════════════════════
#  ICON  (multi-resolution ICO: 16, 32, 48, 64, 128, 256)
# ══════════════════════════════════════════════════════════════════════════════

def draw_icon(size: int) -> Image.Image:
    """Draw the YT Downloader icon at the given square size."""
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad  = max(1, size // 16)

    # Rounded-rectangle background
    r = size // 6
    draw.rounded_rectangle([pad, pad, size - pad - 1, size - pad - 1],
                           radius=r, fill=ACCENT)

    # Subtle inner glow ring
    glow_pad = pad + max(1, size // 32)
    draw.rounded_rectangle([glow_pad, glow_pad,
                            size - glow_pad - 1, size - glow_pad - 1],
                           radius=r - 2, outline=(80, 160, 255, 120),
                           width=max(1, size // 64))

    # Download arrow  ↓  (filled triangle + stem)
    cx     = size // 2
    top    = int(size * 0.18)
    stem_b = int(size * 0.62)
    arr_t  = int(size * 0.55)
    arr_b  = int(size * 0.82)
    w_stem = max(2, size // 9)
    w_arr  = max(4, size // 4)

    # Vertical stem
    draw.rectangle([cx - w_stem // 2, top,
                    cx + w_stem // 2, stem_b], fill=WHITE)

    # Arrow-head triangle
    draw.polygon([
        (cx - w_arr // 2, arr_t),
        (cx + w_arr // 2, arr_t),
        (cx,              arr_b),
    ], fill=WHITE)

    # Baseline bar under the arrow
    bar_h  = max(2, size // 18)
    bar_y  = int(size * 0.87)
    bar_x0 = int(size * 0.20)
    bar_x1 = int(size * 0.80)
    draw.rounded_rectangle([bar_x0, bar_y, bar_x1, bar_y + bar_h],
                           radius=bar_h // 2, fill=ACCENT2)

    return img


sizes = [16, 32, 48, 64, 128, 256]
frames = [draw_icon(s).convert("RGBA") for s in sizes]

# Pillow's ICO encoder expects the largest image as the base and the rest as
# append_images; it encodes one entry per image in order.
frames[-1].save(
    ASSETS / "icon.ico",
    format="ICO",
    append_images=frames[:-1],
)
print("OK  assets/icon.ico")


# ══════════════════════════════════════════════════════════════════════════════
#  INSTALLER BANNER  (164 × 314 px, 24-bit BMP — NSIS MUI2 left panel)
# ══════════════════════════════════════════════════════════════════════════════

W, H = 164, 314
banner = Image.new("RGB", (W, H), BG)
draw   = ImageDraw.Draw(banner)

# ── Background gradient (top → bottom, dark blue tint) ─────────────────────
for y in range(H):
    t  = y / H
    r  = int(BG[0] + (ACCENT[0] - BG[0]) * t * 0.35)
    g  = int(BG[1] + (ACCENT[1] - BG[1]) * t * 0.35)
    b  = int(BG[2] + (ACCENT[2] - BG[2]) * t * 0.35)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# ── Decorative circles (subtle background geometry) ────────────────────────
for cx, cy, rad, alpha in [
    (130, 40,  70, 30),
    (-10, 200, 90, 20),
    (90,  290, 50, 25),
]:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od      = ImageDraw.Draw(overlay)
    od.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
               outline=(*ACCENT, alpha), width=2)
    banner = Image.alpha_composite(banner.convert("RGBA"), overlay).convert("RGB")
    draw   = ImageDraw.Draw(banner)

# ── Accent stripe on the right edge ────────────────────────────────────────
draw.rectangle([W - 4, 0, W - 1, H], fill=ACCENT)
draw.rectangle([W - 7, 0, W - 5, H], fill=(*ACCENT2, ))

# ── Mini icon (centred, upper third) ───────────────────────────────────────
icon_size = 64
icon_img  = draw_icon(icon_size).convert("RGBA")

# Drop-shadow
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd     = ImageDraw.Draw(shadow)
ix = (W - icon_size) // 2
iy = 40
for offset, alpha in [(4, 40), (3, 60), (2, 80)]:
    sd.rounded_rectangle(
        [ix + offset, iy + offset,
         ix + icon_size + offset, iy + icon_size + offset],
        radius=icon_size // 6, fill=(0, 0, 0, alpha)
    )
banner = Image.alpha_composite(banner.convert("RGBA"), shadow).convert("RGB")

banner.paste(icon_img, (ix, iy), icon_img)
draw = ImageDraw.Draw(banner)

# ── App name ───────────────────────────────────────────────────────────────
try:
    font_title = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", 15)
    font_sub   = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",  11)
    font_ver   = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",   9)
except OSError:
    font_title = ImageFont.load_default()
    font_sub   = font_title
    font_ver   = font_title

def centered_text(draw, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    draw.text(((W - 4 - tw) // 2, y), text, font=font, fill=fill)

text_top = iy + icon_size + 14
centered_text(draw, text_top,      "YT Downloader", font_title, WHITE)
centered_text(draw, text_top + 20, "Video & Audio",  font_sub,   GRAY)
centered_text(draw, text_top + 33, "Downloader",     font_sub,   GRAY)

# ── Divider ────────────────────────────────────────────────────────────────
div_y = text_top + 52
draw.line([(20, div_y), (W - 20, div_y)], fill=(*ACCENT, ), width=1)

# ── Feature bullets ────────────────────────────────────────────────────────
features = [
    "4K · 1080p · 720p",
    "MP4 · MKV · WebM",
    "MP3 · FLAC · AAC",
    "aria2c multi-thread",
    "ffmpeg integration",
]
try:
    font_feat = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 10)
except OSError:
    font_feat = ImageFont.load_default()

fy = div_y + 10
for feat in features:
    # Bullet dot
    draw.ellipse([18, fy + 3, 22, fy + 7], fill=ACCENT2)
    draw.text((28, fy), feat, font=font_feat, fill=GRAY)
    fy += 17

# ── Version tag at the bottom ──────────────────────────────────────────────
centered_text(draw, H - 22, "v1.2.0", font_ver, (*GRAY[:3], ))

# ── Save as 24-bit BMP ─────────────────────────────────────────────────────
banner.convert("RGB").save(ASSETS / "installer_banner.bmp", format="BMP")
print("OK  assets/installer_banner.bmp")
print("\nDone. Both assets are ready for the NSIS build.")
