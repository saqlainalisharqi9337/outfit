"""Save a labeled photo for later detector training.

Examples:
  python teach_outfit.py --image photo.jpg --label pent
  python teach_outfit.py --image photo.jpg --label tshirt
  python teach_outfit.py --image photo.jpg --label trousers
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from app.teach import save_example


def main() -> int:
    parser = argparse.ArgumentParser(description="Teach Adore a clothing photo.")
    parser.add_argument("--image", required=True, help="Path to the photo")
    parser.add_argument(
        "--label",
        required=True,
        help="What it is: pants, pent, tshirt, shirt, dress, …",
    )
    args = parser.parse_args()
    path = Path(args.image)
    if not path.is_file():
        raise SystemExit(f"Image not found: {path}")
    with Image.open(path) as image:
        result = save_example(image, args.label)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
