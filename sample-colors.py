#!/usr/bin/env python3
"""
Pixel-sample a NJ Transit ticket screenshot and print the color.css values to apply.

Usage:
    python3 sample-colors.py <ticket-image.jpg>

The script scans for the actual colored regions rather than using hardcoded pixel
offsets, so it handles different image sizes and slight layout shifts correctly.
"""
import sys
from pathlib import Path
from collections import Counter
from PIL import Image


def dominant_color(img, x1, y1, x2, y2):
    crop = img.crop((x1, y1, x2, y2))
    pixels = [p[:3] for p in crop.getdata()]
    return Counter(pixels).most_common(1)[0][0]


def find_yellow_border(img):
    """Sweep horizontally to find the leftmost yellow pixel row, then sample center."""
    w, h = img.size
    for y in range(int(h * 0.1), int(h * 0.6), 2):
        for x in range(int(w * 0.1), int(w * 0.9), 2):
            r, g, b = img.getpixel((x, y))[:3]
            if r > 180 and g > 150 and b < 100:
                # Found yellow region -- sample a stable center strip of this row
                stripe_y = y + 10
                yellows = []
                for sx in range(int(w * 0.15), int(w * 0.85), 4):
                    rr, gg, bb = img.getpixel((sx, stripe_y))[:3]
                    if rr > 180 and gg > 150 and bb < 100:
                        yellows.append((rr, gg, bb))
                if len(yellows) > 5:
                    avg = tuple(sum(c[i] for c in yellows) // len(yellows) for i in range(3))
                    return avg
    return None


def saturation(r, g, b):
    return max(r, g, b) - min(r, g, b)


def find_color_strip(img):
    """Find the 3-band color strip by locating the row with the most saturated pixels,
    then sample the most-saturated pixel in the center fifth of each band."""
    w, h = img.size

    # Find the row with the highest total saturation (the solid strip row)
    best_y, best_sat = None, 0
    for y in range(int(h * 0.7), h, 1):
        total_sat = 0
        colorful = 0
        for x in range(int(w * 0.05), int(w * 0.95), 4):
            r, g, b = img.getpixel((x, y))[:3]
            s = saturation(r, g, b)
            if s > 40:
                total_sat += s
                colorful += 1
        if colorful > 15 and total_sat > best_sat:
            best_sat = total_sat
            best_y = y

    if best_y is None:
        return None, None, None

    # Collect colorful pixels from a ±3px band around the best row
    pixels_by_x = {}
    for dy in range(-3, 4):
        y = best_y + dy
        if y < 0 or y >= h:
            continue
        for x in range(int(w * 0.05), int(w * 0.95), 2):
            r, g, b = img.getpixel((x, y))[:3]
            if saturation(r, g, b) > 40:
                if x not in pixels_by_x or saturation(*pixels_by_x[x]) < saturation(r, g, b):
                    pixels_by_x[x] = (r, g, b)

    if len(pixels_by_x) < 9:
        return None, None, None

    xs = sorted(pixels_by_x)
    xmin, xmax = xs[0], xs[-1]
    third = (xmax - xmin) // 3

    def sample_band(lo, hi):
        # Take the center 60% of the band to avoid blend edges
        margin = (hi - lo) // 5
        center_pixels = [pixels_by_x[x] for x in xs if lo + margin <= x <= hi - margin]
        if not center_pixels:
            center_pixels = [pixels_by_x[x] for x in xs if lo <= x <= hi]
        # Return the most-saturated pixel in this band
        return max(center_pixels, key=lambda c: saturation(*c))

    s1 = sample_band(xmin, xmin + third)
    s2 = sample_band(xmin + third, xmin + 2 * third)
    s3 = sample_band(xmin + 2 * third, xmax)
    return s1, s2, s3


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 sample-colors.py <ticket-image.jpg>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    img = Image.open(path)
    print(f"Image: {path.name}  size: {img.size[0]}x{img.size[1]}")

    first = find_yellow_border(img)
    s1, s2, s3 = find_color_strip(img)

    if first is None:
        print("WARNING: Could not detect QR border color -- check the image")
        first_hex = "#UNKNOWN"
    else:
        first_hex = rgb_to_hex(first)

    s1_hex = rgb_to_hex(s1) if s1 else "#UNKNOWN"
    s2_hex = rgb_to_hex(s2) if s2 else "#UNKNOWN"
    s3_hex = rgb_to_hex(s3) if s3 else "#UNKNOWN"

    print("\nSampled colors:")
    print(f"  QR border  (--first):     {first_hex}")
    print(f"  Strip left (--stripone):  {s1_hex}")
    print(f"  Strip mid  (--striptwo):  {s2_hex}")
    print(f"  Strip right(--stripthree):{s3_hex}")

    print("\n--- paste into static/color.css ---")
    print(":root {")
    print(f'    --first:      {first_hex};')
    print(f'    --stripone:   {s1_hex};')
    print(f'    --striptwo:   {s2_hex};')
    print(f'    --stripthree: {s3_hex};')
    print("}")


if __name__ == "__main__":
    main()
