#!/usr/bin/env python
r"""MCP grounding 실측 채점 — 답변이 인용한 조항을 검증 데이터와 대조한다.

`docs/MCP-grounding-실측.md`의 방법을 그대로 코드로 옮긴 것이다.

    .\.venv\Scripts\python.exe scripts/grounding_score.py            # 표 출력
    .\.venv\Scripts\python.exe scripts/grounding_score.py --json docs/grounding/scores.json

입력
  docs/grounding/questions.json        질문 id·상황·질문 원문
  docs/grounding/raw/<id>-before.md     도구 없이 받은 답변
  docs/grounding/raw/<id>-after.md      slm-mcp 만 연결하고 받은 답변

채점 규칙
  - 인용 조항은 본문에서 `제N조` / `제N조의M` 패턴으로 뽑는다. URL 안의 조항은 제외.
  - 같은 조항을 여러 번 적어도 1건으로 센다.
  - 분모는 **오늘 저장소가 보유한 검증된 조항**(`last_verified`가 있는 매핑의
    조항을 law_id 별로 합친 고유 article_ref). 데이터는 계속 늘어나므로 분모는
    측정일 기준으로 읽어야 한다.
  - 질문이 산업안전보건기준에 관한 규칙을 묻기 때문에 인용은 기본적으로
    `osh-rule`로 본다. 바로 앞 문맥(같은 줄 또는 직전 줄)에 "산업안전보건법"이
    "규칙" 없이 나오면 `osh-act` 인용으로 분류해 따로 센다.
  - 제목은 `제N조(제목)` / `제N조 — 제목` / `제N조: 제목` 꼴에서 뽑고, 공백·가운뎃점을
    지운 뒤 데이터 제목과 비교한다. 완전일치 = match, 한쪽이 다른 쪽을 포함 = partial,
    그 외 = mismatch, 제목을 안 적었으면 none.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from safety_law_mapper.loader import load_dataset  # noqa: E402

ARTICLE = re.compile(r"제\s?(\d+)\s?조(?:의\s?(\d+))?")
URL = re.compile(r"https?://\S+")
# 제목을 적는 꼴 (앞에서부터 차례로 시도):
#   제619조(제목) / 제619조 (제목) / **제619조(제목)**
#   | 제619조 | 제목 |            (표)
#   제619조 — 제목 / 제619조: 제목 / **제619조** — 제목
#   - 제619조 제목: 요지          (제목 뒤에 콜론)
_REF = r"제\s?\d+\s?조(?:의\s?\d+)?"
TITLE_PATTERNS = [
    re.compile(_REF + r"\**\s*[\(（]([^)）\n]{1,60})[\)）]"),
    re.compile(_REF + r"\**[ \t]*\|[ \t]*([^|\n]{1,60}?)[ \t]*\|"),
    re.compile(_REF + r"\**[ \t]*[:：\-–—][ \t]*([^\n|*]{1,60})"),
    re.compile(_REF + r"\**[ \t]+([^\n|*:：(（]{2,40}?)[ \t]*[:：]"),
]
# 제목이 아니라 다른 조항·링크·안내문을 잡은 경우는 버린다.
NOT_A_TITLE = re.compile(r"^(?:제\s?\d+\s?조|https?:|[-–—]|\s*$)")

OSH_ACT_HINT = re.compile(r"산업안전보건법(?!\s*시행)")
OSH_RULE_HINT = re.compile(r"산업안전보건기준에\s*관한\s*규칙|안전보건규칙|기준규칙|(?<!시행)규칙")
OTHER_HINT = re.compile(r"시행규칙|시행령")  # 데이터가 다루지 않는 법령
HINT_REACH = 20  # 법 이름이 인용 앞 이 거리(문자) 안에 있을 때만 그 법으로 본다


def norm_ref(num: str, sub: str | None) -> str:
    return f"제{num}조" + (f"의{sub}" if sub else "")


def norm_title(t: str) -> str:
    t = re.sub(r"[\s·ㆍ・,，\.]", "", t)
    t = re.sub(r"\s*등$", "등", t)
    return t


def verified_articles(ds) -> dict[str, dict[str, dict]]:
    """law_id -> article_ref -> {title, mappings}"""
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for m in ds.mappings.values():
        if m.last_verified is None:
            continue
        for al in m.applicable_laws:
            for a in al.articles:
                entry = out[al.law_id].setdefault(
                    a.article_ref, {"title": a.article_title, "mappings": []}
                )
                entry["mappings"].append(m.mapping_id)
    return out


def law_for_citation(text: str, pos: int) -> str:
    """같은 줄, 인용 바로 앞 HINT_REACH 자 안에 나온 법 이름을 따른다. 없으면 규칙으로 본다."""
    line_start = text.rfind("\n", 0, pos) + 1
    window = text[max(line_start, pos - 60) : pos]
    last = {"osh-rule": -1, "osh-act": -1, "other": -1}
    for law, pat in (("osh-act", OSH_ACT_HINT), ("osh-rule", OSH_RULE_HINT), ("other", OTHER_HINT)):
        for m in pat.finditer(window):
            if len(window) - m.end() <= HINT_REACH:
                last[law] = max(last[law], m.end())
    best = max(last, key=last.get)
    return best if last[best] >= 0 else "osh-rule"


def extract_citations(text: str) -> dict[str, dict[str, str | None]]:
    """ref -> {law, title}. URL 안의 조항은 제외. 첫 등장 제목을 쓴다."""
    stripped = URL.sub(lambda m: " " * len(m.group(0)), text)
    cites: dict[str, dict] = {}
    for m in ARTICLE.finditer(stripped):
        ref = norm_ref(m.group(1), m.group(2))
        key = (law_for_citation(stripped, m.start()), ref)
        title = None
        tail = stripped[m.start() : m.start() + 120]
        for pat in TITLE_PATTERNS:
            tm = pat.match(tail)
            if not tm:
                continue
            cand = tm.group(1).strip().strip("*").strip()
            if cand and not NOT_A_TITLE.match(cand) and re.search(r"[가-힣]", cand):
                title = cand
                break
        entry = cites.setdefault(f"{key[0]}|{ref}", {"law": key[0], "ref": ref, "title": None})
        if entry["title"] is None and title:
            entry["title"] = title
    return cites


def compare_title(cited: str | None, actual: str | None) -> str:
    if not cited:
        return "none"
    if not actual:
        return "n/a"
    a, b = norm_title(cited), norm_title(actual)
    if a == b:
        return "match"
    if a in b or b in a:
        return "partial"
    return "mismatch"


def score_answer(text: str, verified: dict) -> dict:
    cites = extract_citations(text)
    rows = []
    for c in cites.values():
        law, ref = c["law"], c["ref"]
        known = verified.get(law, {}).get(ref)
        rows.append(
            {
                "law": law,
                "ref": ref,
                "cited_title": c["title"],
                "in_dataset": known is not None,
                "dataset_title": known["title"] if known else None,
                "mappings": known["mappings"] if known else [],
                "title": compare_title(c["title"], known["title"]) if known else "-",
            }
        )
    rule_rows = [r for r in rows if r["law"] == "osh-rule"]
    inn = [r for r in rule_rows if r["in_dataset"]]
    return {
        "cited": len(rule_rows),
        "in_dataset": len(inn),
        "out_of_dataset": len(rule_rows) - len(inn),
        "title_match": sum(r["title"] == "match" for r in inn),
        "title_partial": sum(r["title"] == "partial" for r in inn),
        "title_mismatch": sum(r["title"] == "mismatch" for r in inn),
        "title_none": sum(r["title"] == "none" for r in inn),
        "osh_act_cited": len([r for r in rows if r["law"] == "osh-act"]),
        "law_link": "law.go.kr" in text,
        "verification_date": bool(re.search(r"검증", text)),
        "rows": rows,
    }


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "-"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, default=REPO / "docs/grounding/questions.json")
    ap.add_argument("--raw", type=Path, default=REPO / "docs/grounding/raw")
    ap.add_argument("--json", type=Path, help="상세 결과를 JSON 으로 저장")
    args = ap.parse_args()

    ds = load_dataset()
    verified = verified_articles(ds)
    denom = {law: len(refs) for law, refs in verified.items()}
    questions = json.loads(args.questions.read_text(encoding="utf-8"))

    results = []
    for q in questions:
        entry = {"id": q["id"], "situation": q["situation"], "mapping_id": q["mapping_id"]}
        for mode in ("before", "after"):
            path = args.raw / f"{q['id']}-{mode}.md"
            if not path.exists():
                entry[mode] = None
                continue
            entry[mode] = score_answer(path.read_text(encoding="utf-8"), verified)
        results.append(entry)

    out = sys.stdout
    out.reconfigure(encoding="utf-8")
    print(f"분모 (검증된 고유 조항): " + ", ".join(f"{k} {v}" for k, v in denom.items()))
    print()
    print("| id | 상황 | BEFORE 인용 | BEFORE 데이터 내 | BEFORE 데이터 밖 | BEFORE 제목 일치 | AFTER 인용 | AFTER 데이터 내 | AFTER 데이터 밖 | AFTER 제목 일치 |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    tot = {m: defaultdict(int) for m in ("before", "after")}
    for r in results:
        cells = [r["id"], r["situation"]]
        for mode in ("before", "after"):
            s = r[mode]
            if s is None:
                cells += ["-", "-", "-", "-"]
                continue
            for k in ("cited", "in_dataset", "out_of_dataset", "title_match", "title_partial", "title_mismatch", "title_none", "osh_act_cited"):
                tot[mode][k] += s[k]
            cells += [
                str(s["cited"]),
                f"{s['in_dataset']} ({pct(s['in_dataset'], s['cited'])})",
                str(s["out_of_dataset"]),
                f"{s['title_match']} / {s['in_dataset']}",
            ]
        print("| " + " | ".join(cells) + " |")
    cells = ["**합계**", ""]
    for mode in ("before", "after"):
        t = tot[mode]
        cells += [
            f"**{t['cited']}**",
            f"**{t['in_dataset']} ({pct(t['in_dataset'], t['cited'])})**",
            f"**{t['out_of_dataset']}**",
            f"**{t['title_match']} / {t['in_dataset']}**",
        ]
    print("| " + " | ".join(cells) + " |")
    print()
    for mode in ("before", "after"):
        t = tot[mode]
        print(
            f"{mode.upper()}: 인용 {t['cited']}, 데이터 내 {t['in_dataset']} ({pct(t['in_dataset'], t['cited'])}), "
            f"데이터 밖 {t['out_of_dataset']}, 제목 일치 {t['title_match']} / 부분 {t['title_partial']} / "
            f"불일치 {t['title_mismatch']} / 미기재 {t['title_none']}, 산업안전보건법 인용 {t['osh_act_cited']}"
        )
    print()
    for r in results:
        for mode in ("before", "after"):
            s = r[mode]
            if not s:
                continue
            outs = [x["ref"] for x in s["rows"] if x["law"] == "osh-rule" and not x["in_dataset"]]
            bad = [
                f"{x['ref']}: '{x['cited_title']}' ≠ '{x['dataset_title']}'"
                for x in s["rows"]
                if x["law"] == "osh-rule" and x["in_dataset"] and x["title"] in ("mismatch", "partial")
            ]
            if outs or bad:
                print(f"[{r['id']} {mode}] 데이터 밖: {', '.join(outs) or '없음'}")
                for b in bad:
                    print(f"    제목 차이 — {b}")

    if args.json:
        args.json.write_text(
            json.dumps({"denominator": denom, "results": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n저장: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
