#!/usr/bin/env python3
"""Draw startpg's favicon: a Windows 95-style monitor showing status lights.

Pixel art on the Windows 16-colour palette, drawn here pixel by pixel at
32x32 and, as Windows 95's own icons were, separately at 16x16 rather than
shrunk. Writes src/face/static/favicon.ico, holding both, and
src/face/static/apple-touch-icon.png, the 32x32 blown up on the Windows 95
desktop's teal for phone home screens. It needs Pillow, which startpg itself
doesn't, so run it with e.g.

    uv run --no-project --with pillow python docs/favicon.py
"""

from pathlib import Path

from PIL import Image

STATIC = Path(__file__).resolve().parent.parent / "src" / "face" / "static"

PALETTE = {
    "K": (0, 0, 0),
    "W": (255, 255, 255),
    "L": (192, 192, 192),
    "D": (128, 128, 128),
    "T": (0, 128, 128),
    "G": (0, 128, 0),
    "g": (0, 255, 0),
    "R": (128, 0, 0),
    "r": (255, 0, 0),
}


class Canvas:
    def __init__(self, size: int):
        self.size = size
        self.pixels = [[None] * size for _ in range(size)]

    def set(self, x, y, colour):
        self.pixels[y][x] = colour

    def rect(self, x0, y0, x1, y1, colour):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, colour)

    def h(self, x0, x1, y, colour):
        self.rect(x0, y, x1, y, colour)

    def v(self, x, y0, y1, colour):
        self.rect(x, y0, x, y1, colour)

    def raised(self, x0, y0, x1, y1):
        """A black outline round a raised grey face: white top and left,
        darker grey bottom and right."""
        self.rect(x0, y0, x1, y1, "K")
        self.rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, "L")
        self.h(x0 + 1, x1 - 2, y0 + 1, "W")
        self.v(x0 + 1, y0 + 1, y1 - 2, "W")
        self.h(x0 + 2, x1 - 1, y1 - 1, "D")
        self.v(x1 - 1, y0 + 2, y1 - 1, "D")

    def sunken(self, x0, y0, x1, y1, fill):
        """A recess: grey then black along the top and left, white along the
        bottom and right."""
        self.rect(x0, y0, x1, y1, fill)
        self.h(x0, x1, y0, "D")
        self.v(x0, y0, y1, "D")
        self.h(x0, x1, y1, "W")
        self.v(x1, y0, y1, "W")
        self.h(x0 + 1, x1 - 1, y0 + 1, "K")
        self.v(x0 + 1, y0 + 1, y1 - 1, "K")

    def image(self) -> Image.Image:
        img = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        for y, row in enumerate(self.pixels):
            for x, colour in enumerate(row):
                if colour:
                    img.putpixel((x, y), PALETTE[colour] + (255,))
        return img


def led(c, x, y, light, dark):
    """A lit 3x3 status light: a white glint top-left, shade bottom-right."""
    c.rect(x, y, x + 2, y + 2, light)
    c.set(x, y, "W")
    c.set(x + 2, y + 2, dark)


def large() -> Canvas:
    """The 32x32: a monitor on its stand, its screen the desktop's teal with
    three status rows, two up and one down, and its power light on."""
    c = Canvas(32)
    c.raised(2, 2, 29, 23)
    c.sunken(5, 5, 26, 20, "T")
    for y, light, dark, length in ((8, "g", "G", 11), (12, "g", "G", 8), (16, "r", "R", 10)):
        led(c, 8, y, light, dark)
        c.h(12, 12 + length, y + 1, "W")
    c.h(23, 24, 21, "g")
    c.raised(12, 23, 19, 26)
    c.raised(7, 25, 24, 29)
    return c


def small() -> Canvas:
    """The 16x16: the same monitor with one-pixel lights and shorter rows."""
    c = Canvas(16)
    c.raised(1, 1, 14, 12)
    c.sunken(3, 3, 12, 10, "T")
    for y, light, length in ((5, "g", 4), (7, "g", 3), (9, "r", 4)):
        c.set(5, y, light)
        c.h(7, 6 + length, y, "W")
    c.raised(3, 13, 12, 15)
    return c


def main():
    big, little = large().image(), small().image()
    # Pillow would shrink the 32x32 for the 16x16 slot; hand it the real one.
    big.save(STATIC / "favicon.ico", sizes=[(16, 16), (32, 32)], append_images=[little])
    print(f"wrote {STATIC / 'favicon.ico'}")
    # iOS fills transparency with black, so give it the desktop to sit on.
    touch = Image.new("RGBA", (180, 180), PALETTE["T"] + (255,))
    scaled = big.resize((160, 160), Image.NEAREST)
    touch.alpha_composite(scaled, (10, 10))
    touch.convert("RGB").save(STATIC / "apple-touch-icon.png")
    print(f"wrote {STATIC / 'apple-touch-icon.png'}")


if __name__ == "__main__":
    main()
