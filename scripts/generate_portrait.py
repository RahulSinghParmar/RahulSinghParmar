"""Generate a transparent, theme-paired animated dot portrait.

Usage:
    python scripts/generate_portrait.py portrait-cutout-source.png assets/portrait-light.svg --theme light
    python scripts/generate_portrait.py portrait-cutout-source.png assets/portrait-dark.svg --theme dark
"""

from __future__ import annotations

import argparse
from collections import deque
import html
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def remove_checkerboard(image: Image.Image) -> Image.Image:
    """Turn the neutral checkerboard connected to the edges into transparency.

    Flood filling from the canvas edge preserves enclosed light details such as
    eyes and shirt highlights while removing the generated preview background.
    """

    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    background = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def is_background(x: int, y: int) -> bool:
        red, green, blue = pixels[x, y]
        return min(red, green, blue) >= 210 and max(red, green, blue) - min(red, green, blue) <= 20

    def add(x: int, y: int) -> None:
        index = y * width + x
        if not background[index] and is_background(x, y):
            background[index] = 1
            queue.append((x, y))

    for x in range(width):
        add(x, 0)
        add(x, height - 1)
    for y in range(height):
        add(0, y)
        add(width - 1, y)

    while queue:
        x, y = queue.popleft()
        if x:
            add(x - 1, y)
        if x + 1 < width:
            add(x + 1, y)
        if y:
            add(x, y - 1)
        if y + 1 < height:
            add(x, y + 1)

    alpha = Image.new("L", (width, height), 255)
    alpha.putdata([0 if value else 255 for value in background])
    rgba = rgb.convert("RGBA")
    rgba.putalpha(alpha.filter(ImageFilter.GaussianBlur(0.35)))
    return rgba


def render_portrait(source: Path, destination: Path, columns: int = 88, theme: str = "light") -> None:
    with Image.open(source) as original:
        image = remove_checkerboard(ImageOps.exif_transpose(original))

    width, height = image.size
    # Recruiter-facing head-and-upper-body crop: complete hairline and both
    # shoulders, with enough torso to retain the human silhouette at 300px.
    crop = (
        int(width * 0.08),
        int(height * 0.13),
        int(width * 0.92),
        int(height * 0.80),
    )
    image = image.crop(crop)
    rows = round(columns * 1.09)
    image = ImageOps.fit(image, (columns, rows), Image.Resampling.LANCZOS, centering=(0.5, 0.50))
    alpha = image.getchannel("A")
    color = image.convert("RGB")
    if theme == "dark":
        color = ImageOps.autocontrast(color, cutoff=0.7)
        color = ImageEnhance.Contrast(color).enhance(1.02)
        color = ImageEnhance.Color(color).enhance(1.02)
        color = ImageEnhance.Brightness(color).enhance(1.35)
    else:
        color = ImageEnhance.Contrast(color).enhance(1.10)
        color = ImageEnhance.Color(color).enhance(1.06)
        color = ImageEnhance.Brightness(color).enhance(0.92)
    color = color.filter(ImageFilter.UnsharpMask(radius=1.0, percent=145, threshold=2))
    image = color.convert("RGBA")
    image.putalpha(alpha)

    spacing = 3.65
    padding = 12
    canvas_width = round(columns * spacing + padding * 2)
    canvas_height = round(rows * spacing + padding * 2)

    row_groups: list[str] = []
    pixels = image.load()
    for row in range(rows):
        circles: list[str] = []
        for column in range(columns):
            red, green, blue, pixel_alpha = pixels[column, row]
            if pixel_alpha < 28:
                continue

            luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255

            normalized_x = column / max(1, columns - 1)
            normalized_y = row / max(1, rows - 1)

            # Preserve deep hair and beard detail on dark backgrounds.
            if theme == "dark" and luminance < 0.40:
                lift = int((0.40 - luminance) * 120)
                red, green, blue = min(255, red + lift), min(255, green + lift), min(255, blue + lift)
                luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255

            # A warm graphite lift makes dark hair readable on GitHub's light
            # theme without painting over the original texture or hairline.
            if (
                theme == "light"
                and 0.25 <= normalized_x <= 0.75
                and 0.04 <= normalized_y <= 0.30
                and luminance < 0.24
            ):
                strength = min(0.34, (0.24 - luminance) * 1.55)
                red = round(red * (1 - strength) + 70 * strength)
                green = round(green * (1 - strength) + 57 * strength)
                blue = round(blue * (1 - strength) + 51 * strength)
                luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255

            radius = (1.24 if theme == "dark" else 1.12) + 0.48 * ((1 - luminance) ** 0.55)
            opacity = (0.72 + 0.28 * ((1 - luminance) ** 0.30)) * (pixel_alpha / 255)
            x = padding + column * spacing + spacing / 2
            y = padding + row * spacing + spacing / 2
            circles.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
                f'fill="rgb({red},{green},{blue})" fill-opacity="{opacity:.3f}"/>'
            )
        if circles:
            row_groups.append(f'<g class="portrait-row row-{row}">{"".join(circles)}</g>')

    delays = "".join(f'.row-{row}{{animation-delay:{row * 0.014:.3f}s}}' for row in range(rows))
    title = html.escape("Rahul Singh Parmar rendered as a transparent animated dot portrait")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}" height="{canvas_height}" viewBox="0 0 {canvas_width} {canvas_height}" role="img" aria-labelledby="portrait-title">
  <title id="portrait-title">{title}</title>
  <style>
    @keyframes portrait-reveal {{ from {{ opacity: 0; transform: translateY(-6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    .portrait-row {{ animation: portrait-reveal 0.38s ease-out both; }}
    {delays}
  </style>
  {''.join(row_groups)}
</svg>
'''
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(svg, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--columns", type=int, default=88)
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    arguments = parser.parse_args()
    render_portrait(arguments.source, arguments.destination, arguments.columns, arguments.theme)


if __name__ == "__main__":
    main()
