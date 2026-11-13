"""news-image-01 entry: reproduce the bundled news image as the output.

The image beside this program (entry.png) is an editorial infographic
summing up the world news of Friday 13 November 2026: a night-side globe
ringed by six stories -- the US Senate summoning the former Nvidia chief,
Zelensky meeting US envoys, a drone strike on a Russian warship, Iran's
claimed strike on a US radar in Bahrain, the FBI's $400m North Korea
crypto-hack attribution, and the worldwide Microsoft outage. The file
holds JPEG bytes under a .png name, which the competition allows.

Running this program writes those exact bytes to /output/entry.png (or
to $MAKEFUN_OUTPUT_DIR when that is set). The run is deterministic: the
output is always an exact copy of the source, so two runs agree byte for
byte. Before writing, the source is checked against the competition
limits (at most 1 MiB, at most 1024 by 1024 pixels); after writing, the
output is read back and compared with the source, bytes and dimensions.

Python 3.13, standard library only. No network access.
"""

import hashlib
import os
from pathlib import Path

BYTE_LIMIT = 1_048_576
PIXEL_LIMIT = 1024

SOURCE = Path(__file__).resolve().parent / "entry.png"
OUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
OUT_FILE = OUT_DIR / "entry.png"


def png_size(data: bytes) -> tuple[int, int] | None:
    """Width and height from a PNG IHDR chunk, or None if not a PNG."""
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def jpeg_size(data: bytes) -> tuple[int, int] | None:
    """Width and height from a JPEG SOF segment, or None if not a JPEG."""
    if data[:2] != b"\xff\xd8":
        return None
    pos = 2
    while pos + 4 <= len(data):
        # Skip any padding 0xFF bytes, then read the marker code.
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            return None
        marker = data[pos]
        pos += 1
        # Standalone markers carry no length field.
        if marker == 0x01 or 0xD0 <= marker <= 0xD9:
            continue
        # Start-of-scan means the compressed data follows; no SOF can
        # appear after it, so there is nothing more to look for here.
        if marker == 0xDA:
            return None
        if pos + 2 > len(data):
            return None
        size = int.from_bytes(data[pos:pos + 2], "big")
        if size < 2 or pos + size > len(data):
            return None
        if marker in (0xC0, 0xC1, 0xC2):
            # SOF layout: length(2), precision(1), height(2), width(2).
            height = int.from_bytes(data[pos + 3:pos + 5], "big")
            width = int.from_bytes(data[pos + 5:pos + 7], "big")
            return width, height
        pos += size
    return None


def image_size(data: bytes) -> tuple[int, int] | None:
    """Width and height of a PNG or JPEG byte string, else None."""
    return png_size(data) or jpeg_size(data)


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"cannot find the bundled image: {SOURCE}")
    data = SOURCE.read_bytes()
    if len(data) > BYTE_LIMIT:
        raise SystemExit(f"bundled image is {len(data)} bytes, over the 1 MiB limit")
    size = image_size(data)
    if size is None:
        raise SystemExit("bundled image is neither a PNG nor a JPEG")
    width, height = size
    if width > PIXEL_LIMIT or height > PIXEL_LIMIT:
        raise SystemExit(f"bundled image is {width}x{height}, over the 1024x1024 limit")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_bytes(data)
    written = OUT_FILE.read_bytes()
    if written != data:
        raise SystemExit("output does not match the source byte for byte")
    if image_size(written) != size:
        raise SystemExit("output dimensions do not match the source")
    digest = hashlib.sha256(written).hexdigest()
    print(f"wrote {OUT_FILE}: {len(written)} bytes, {width}x{height}, sha256={digest}")


if __name__ == "__main__":
    main()
