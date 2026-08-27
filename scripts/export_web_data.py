"""Export YAML dataset to a single JSON file for the static web demo.

Usage: python scripts/export_web_data.py <output.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from safety_law_mapper import __version__  # noqa: E402
from safety_law_mapper.loader import load_dataset  # noqa: E402


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("web/data.json")
    ds = load_dataset()
    payload = {
        "version": __version__,
        "laws": {k: v.model_dump(mode="json") for k, v in ds.laws.items()},
        "mappings": [m.model_dump(mode="json") for m in ds.mappings.values()],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} ({len(payload['mappings'])} mappings, {len(payload['laws'])} laws)")


if __name__ == "__main__":
    main()
