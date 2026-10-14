#!/usr/bin/env python
r"""기록된 valid_from 이 그 뒤의 개정을 놓쳤는지 대조한다.

`valid_from` 은 **시행일**이다(예: 제179조는 2019. 12. 26. 공포, 2021. 1. 16.
시행이고 기록값은 2021-01-16). 그래서 "기록값 != 공포일"은 정상이며 경보가
되지 못한다. 판정은 한쪽 방향으로만 한다.

    기록값 < 그 조문의 마지막 개정 공포일  →  낡았다

시행일은 공포일보다 빠를 수 없으므로 이 판정은 오경보를 내지 않는다. 대신
"공포됐으나 아직 시행 전"인 개정은 잡지 않는다 — 그건 낡은 게 아니다.

법령 본문은 law.go.kr 이 iframe 안에서 다시 불러오기 때문에 이 스크립트가
직접 받지 않는다. 날짜표는 브라우저에서 아래를 실행해 저장한다.

    (() => {
      const d = window.frames[0].document;
      let t = d.body.innerText;
      const cut = t.search(/부\s{2,}칙/);        // 부칙 앞에서 자른다
      if (cut > 0) t = t.slice(0, cut);
      const latest = {};
      let cur = null;
      const DATE = /(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\./g;
      for (const line of t.split("\n")) {
        const m = line.match(/^\s*(제\d+조(?:의\d+)?)\(/);
        if (m) { cur = m[1]; if (!(cur in latest)) latest[cur] = null; }
        if (!cur) continue;
        if (!/<개정|<신설|\[전문개정|\[본조신설|\[제목개정/.test(line)) continue;
        let mm; DATE.lastIndex = 0;
        while ((mm = DATE.exec(line)) !== null) {
          const iso = mm[1] + "-" + String(mm[2]).padStart(2, "0")
                              + "-" + String(mm[3]).padStart(2, "0");
          if (!latest[cur] || iso > latest[cur]) latest[cur] = iso;
        }
      }
      return JSON.stringify(latest);
    })()

낡은 것이 나오면 숫자만 바꾸지 말 것. 그 개정이 무엇을 바꿨는지 원문을 읽고,
요약이 여전히 맞는지 확인한 다음 부칙에서 시행일을 찾아 적는다.

    python scripts/check_article_dates.py law-dates.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LAW_ID = "osh-rule"


def stale_entries(mappings_dir: Path, latest: dict[str, str | None]) -> list[tuple]:
    """(파일, 조문, 기록값, 마지막 개정 공포일) 목록. 날짜표에 없는 조문은 건너뛴다."""
    found = []
    for path in sorted(mappings_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for law in data["applicable_laws"]:
            if law["law_id"] != LAW_ID:
                continue
            for article in law["articles"]:
                ref = article["article_ref"]
                amended = latest.get(ref)
                if not amended:
                    continue
                if article["valid_from"] < amended:
                    found.append((path.name, ref, article["valid_from"], amended))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dates", type=Path, help="조문 → 마지막 개정 공포일 JSON")
    parser.add_argument("--mappings", type=Path, default=REPO_ROOT / "data" / "mappings")
    args = parser.parse_args()

    latest = json.loads(args.dates.read_text(encoding="utf-8"))
    rows = stale_entries(args.mappings, latest)
    if not rows:
        print("✅ 기록된 시행일 이후의 개정은 없습니다")
        return 0

    print(f"⚠️ 기록 이후 개정된 조문 {len(rows)}건 — 원문을 읽고 시행일을 확인하세요\n")
    for name, ref, recorded, amended in rows:
        print(f"  {name:32} {ref:12} 기록 {recorded}  <  개정 {amended}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
