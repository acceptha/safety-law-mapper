"""Fetch KOSHA 사고속보 posts into data/incidents/kosha-alerts.jsonl.

Usage:
  python scripts/fetch_kosha_incidents.py                 # newest 2 pages, incremental
  python scripts/fetch_kosha_incidents.py --pages 25      # backfill
  python scripts/fetch_kosha_incidents.py --no-store-titles
  python scripts/fetch_kosha_incidents.py --dry-run

The board API is undocumented. If its shape changes this script exits
non-zero rather than silently writing nothing — a quiet "success" that
collected no data would be worse than a visible failure.

Source: 안전보건공단 산업안전포털 사고속보 (portal.kosha.or.kr).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from safety_law_mapper.incidents import (  # noqa: E402
    BBS_ID,
    build_incident,
    load_incidents,
    load_lexicon,
    strip_html,
    write_incidents,
)
from safety_law_mapper.loader import load_dataset  # noqa: E402

API = "https://portal.kosha.or.kr/api/compn24/auth/stdtboard/process.do"
UA = "safety-law-mapper/0.2 (+https://github.com/acceptha/safety-law-mapper)"
PAGE_SIZE = 12


class ApiError(RuntimeError):
    pass


def _post(payload: dict, timeout: int = 30) -> dict:
    raw = json.dumps(payload, ensure_ascii=False)
    # The portal expects _JSON to be URL-encoded twice.
    body = "_JSON=" + urllib.parse.quote(urllib.parse.quote(raw, safe=""), safe="")
    req = urllib.request.Request(
        API,
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApiError(f"KOSHA API request failed: {exc}") from exc
    if doc.get("code") != 0:
        raise ApiError(f"KOSHA API returned code={doc.get('code')} {doc.get('message')!r}")
    return doc.get("response") or {}


def _envelope(service_id: str, data: dict) -> dict:
    return {
        "common": {
            "frontInfo": {"viewId": "", "menuId": "", "siteId": ""},
            "frontAuthKey": "",
            "auth": {},
            "securityInfo": {},
            "data": {
                "pagingInfo": None,
                "whereId": None,
                "tboard": {
                    "systemCd": "20",
                    "channel": "web",
                    "bbsId": BBS_ID,
                    "bbsGrpId": "",
                    "serviceId": service_id,
                },
            },
        },
        "service": {"info": {"id": "", "type": ""}, "data": data},
    }


def fetch_list(page: int) -> list[dict]:
    resp = _post(
        _envelope(
            "basicAccess",
            {
                "searchDefaultCndGrid": [
                    {
                        "orPstNm": "",
                        "orPstCn": "",
                        "curPageCo": page,
                        "recodePageCo": PAGE_SIZE,
                        "rowsPerPage": PAGE_SIZE,
                        "pstSeCd": "1200001",
                        "atcflCntSrchYn": "Y",
                        "artclNoList": [],
                        "pstNoOrder": "Y",
                        "isDesc": "Y",
                        "sortType": "01",
                        "sortOrder": "1",
                        "isAddPstCn": "N",
                    }
                ],
                "searchArtclCndGrid": [],
            },
        )
    )
    grid = resp.get("bbsPstGrid")
    if grid is None:
        raise ApiError("list response has no bbsPstGrid — API shape changed")
    return grid


def fetch_detail(pst_no: str) -> str:
    resp = _post(
        _envelope("basicRead", {"pstDefaultGrid": [{"bbsId": BBS_ID, "pstNo": pst_no}]})
    )
    info = resp.get("bbsDetailInfo")
    if not info:
        raise ApiError(f"detail response has no bbsDetailInfo for {pst_no}")
    return strip_html(info[0].get("pstCn"))


def _parse_ymd(value: str) -> datetime.date:
    return datetime.datetime.strptime(value, "%Y%m%d").date()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pages", type=int, default=2, help="list pages to scan (12 posts each)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--cache-dir", type=Path, default=None, help="raw post cache (gitignored)")
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    ap.add_argument(
        "--no-store-titles",
        action="store_true",
        help="omit the headline; keep only structured facts and the source link",
    )
    ap.add_argument(
        "--reprocess",
        action="store_true",
        help="rebuild the store from the local cache without any network call",
    )
    ap.add_argument("--dry-run", action="store_true", help="do not write the store")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    out = args.out or (root / "data/incidents/kosha-alerts.jsonl")
    cache_dir = args.cache_dir or (root / "data/incidents/.cache")
    today = datetime.date.today()

    lexicon = load_lexicon()
    mapping_keywords = {
        k for m in load_dataset().mappings.values() for k in m.work_type.keywords
    }
    store_title = not args.no_store_titles

    def _record(raw: dict) -> object:
        return build_incident(
            pst_no=raw["pstNo"],
            title=raw.get("pstNm") or "",
            body=raw.get("body") or "",
            posted_at=_parse_ymd(raw["regYmd"]),
            fetched_at=today,
            lexicon=lexicon,
            mapping_keywords=mapping_keywords,
            store_title=store_title,
        )

    if args.reprocess:
        cached = sorted(cache_dir.glob("*.json"))
        if not cached:
            print(f"❌ 캐시가 비어 있습니다: {cache_dir}", file=sys.stderr)
            return 1
        rebuilt = [_record(json.loads(p.read_text(encoding="utf-8"))) for p in cached]
        print(f"캐시 {len(rebuilt)}건 재처리 (네트워크 호출 없음)")
        if args.dry_run:
            print("dry-run: 저장하지 않음")
            return 0
        write_incidents(rebuilt, out)
        print(f"저장: {out}")
        return 0

    existing = {i.pst_no: i for i in load_incidents(out)}
    print(f"기존 {len(existing)}건, {args.pages}페이지 조회")

    posts: list[dict] = []
    for page in range(1, args.pages + 1):
        rows = fetch_list(page)
        if not rows:
            break
        posts.extend(rows)
        time.sleep(args.delay)

    added = 0
    for post in posts:
        pst_no = post.get("pstNo")
        if not pst_no or pst_no in existing:
            continue
        raw = {
            "pstNo": pst_no,
            "pstNm": post.get("pstNm") or "",
            "regYmd": post["regYmd"],
            "body": fetch_detail(pst_no),
        }
        time.sleep(args.delay)
        if not args.dry_run:
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / f"{pst_no}.json").write_text(
                json.dumps(raw, ensure_ascii=False), encoding="utf-8"
            )
        existing[pst_no] = _record(raw)
        added += 1

    print(f"신규 {added}건 → 총 {len(existing)}건")
    if args.dry_run:
        print("dry-run: 저장하지 않음")
        return 0
    write_incidents(list(existing.values()), out)
    print(f"저장: {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ApiError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
