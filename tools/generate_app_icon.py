"""Generate deterministic Skunkworks application icons from the approved mark."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "src" / "ui" / "assets" / "icons"
COPPERPLATE = Path("/System/Library/Fonts/Supplemental/Copperplate.ttc")


def render(size=1024):
    image = Image.new("RGBA", (size, size), "black")
    font = ImageFont.truetype(str(COPPERPLATE), int(size * 0.76), index=2)
    draw = ImageDraw.Draw(image)
    bounds = draw.textbbox((0, 0), "S", font=font, stroke_width=0)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    position = (
        (size - width) / 2 - bounds[0],
        (size - height) / 2 - bounds[1] - size * 0.015,
    )
    draw.text(position, "S", fill="white", font=font)
    return image


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    image = render()
    image.save(OUTPUT / "skunkworks-app.png")
    image.save(
        OUTPUT / "skunkworks-app.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    image.save(
        OUTPUT / "skunkworks-app.icns",
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
    )


if __name__ == "__main__":
    main()
