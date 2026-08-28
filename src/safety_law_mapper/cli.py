"""CLI entrypoint: slm search / show / validate.

Exit codes: 0 ok, 1 no result, 2 validation error.
"""

from __future__ import annotations

import typer

from . import DISCLAIMER, __version__
from .loader import load_dataset
from .matcher import Query, match
from .models import Mapping, WorkCategory

app = typer.Typer(
    name="slm",
    help="안전법규 매핑 엔진 — 작업 상황으로 적용 법령·조항을 찾습니다.",
    no_args_is_help=True,
    add_completion=False,
)


def _print_mapping(mapping: Mapping, laws: dict) -> None:
    typer.echo(f"\n■ {mapping.work_type.name_ko}  [{mapping.mapping_id}]")
    typer.echo(f"  분류: {mapping.work_type.category.value}")
    typer.echo(f"  키워드: {', '.join(mapping.work_type.keywords)}")
    verified = mapping.last_verified.isoformat() if mapping.last_verified else "미검증 (사람 검토 필요)"
    typer.echo(f"  검증일: {verified}")
    for al in mapping.applicable_laws:
        law = laws.get(al.law_id)
        law_name = law.name_ko if law else al.law_id
        typer.echo(f"  ── {law_name}")
        for art in al.articles:
            title = f" ({art.article_title})" if art.article_title else ""
            typer.echo(f"     {art.article_ref}{title} — {art.summary_ko}")
            typer.echo(f"       근거: {art.source_url}")


def _finish(exit_code: int = 0) -> None:
    typer.echo(f"\n{DISCLAIMER}")
    raise typer.Exit(exit_code)


@app.command()
def search(
    keywords: list[str] = typer.Argument(..., help="검색 키워드 (예: 밀폐공간 용접)"),
    category: WorkCategory | None = typer.Option(None, "--category", "-c", help="작업 분류"),
    employees: int | None = typer.Option(None, "--employees", "-e", help="상시근로자 수"),
) -> None:
    """키워드로 적용 법령·조항을 검색합니다."""
    ds = load_dataset()
    query = Query(keywords=list(keywords), category=category, employees=employees)
    results = match(list(ds.mappings.values()), query)
    if not results:
        typer.echo("검색 결과가 없습니다.")
        _finish(1)
    typer.echo(f"검색 결과 {len(results)}건:")
    for r in results:
        _print_mapping(r.mapping, ds.laws)
    _finish(0)


@app.command()
def show(mapping_id: str = typer.Argument(..., help="매핑 ID")) -> None:
    """매핑 ID로 상세 내용을 조회합니다."""
    ds = load_dataset()
    mapping = ds.mappings.get(mapping_id)
    if mapping is None:
        typer.echo(f"매핑을 찾을 수 없습니다: {mapping_id}")
        _finish(1)
    _print_mapping(mapping, ds.laws)
    _finish(0)


@app.command()
def validate() -> None:
    """데이터 파일의 스키마·참조 무결성을 검증합니다."""
    from .validate import validate_data

    report = validate_data()
    if report.ok:
        typer.echo(f"✅ 검증 통과: {report.checked_files}개 파일")
        _finish(0)
    typer.echo(f"❌ 검증 실패: 오류 {len(report.errors)}건")
    for err in report.errors:
        typer.echo(f"  - {err}")
    _finish(2)


@app.command()
def incidents(
    gaps: bool = typer.Option(False, "--gaps", help="미매핑 사고만 표시 (데이터 공백 큐)"),
    since: str | None = typer.Option(None, "--since", help="게시일 하한 (YYYY-MM-DD)"),
    accident_type: str | None = typer.Option(None, "--type", "-t", help="사고 유형 (예: 떨어짐)"),
    limit: int = typer.Option(20, "--limit", "-n", help="표시 건수"),
) -> None:
    """KOSHA 사고속보를 적용 법령과 대조합니다 (수집: scripts/fetch_kosha_incidents.py)."""
    import datetime

    from .incidents import coverage, load_incidents, map_incidents

    records = load_incidents()
    if not records:
        typer.echo("수집된 사고속보가 없습니다. 먼저 실행하세요:")
        typer.echo("  python scripts/fetch_kosha_incidents.py")
        _finish(1)

    if since:
        try:
            floor = datetime.date.fromisoformat(since)
        except ValueError:
            typer.echo(f"--since 날짜 형식이 올바르지 않습니다: {since}")
            _finish(2)
        records = [r for r in records if r.posted_at >= floor]
    if accident_type:
        records = [r for r in records if any(t.value == accident_type for t in r.accident_type)]

    ds = load_dataset()
    matches = map_incidents(records, list(ds.mappings.values()))
    mapped, total = coverage(matches)

    shown = [m for m in matches if m.is_gap] if gaps else matches
    if not shown:
        typer.echo("조건에 맞는 사고가 없습니다.")
        _finish(1)

    typer.echo(f"사고 {total}건 중 매핑 {mapped}건 / 미매핑 {total - mapped}건")
    typer.echo("※ 아래는 해당 작업에 적용되는 조항이며, 이 사고의 위반 사실을 뜻하지 않습니다.")
    for m in shown[:limit]:
        inc = m.incident
        when = inc.occurred_at.strftime("%Y-%m-%d %H:%M") if inc.occurred_at else str(inc.posted_at)
        head = " · ".join(
            x
            for x in (
                when,
                inc.region,
                "/".join(t.value for t in inc.accident_type) or None,
                f"사망 {inc.fatalities}명" if inc.fatalities else None,
            )
            if x
        )
        typer.echo(f"\n▸ {head}")
        if inc.title:
            typer.echo(f"  {inc.title}")
        typer.echo(f"  근거: {inc.source_url}")
        if m.is_gap:
            typer.echo("  ⚠️ 미매핑 — 적용 매핑 데이터 없음 (기여 대상)")
            continue
        for r in m.results[:3]:
            arts = [
                f"{art.article_ref}"
                for al in r.mapping.applicable_laws
                for art in al.articles
            ]
            typer.echo(
                f"  → {r.mapping.work_type.name_ko} [{r.mapping.mapping_id}]"
                f" — {', '.join(arts[:6])}"
            )

    if len(shown) > limit:
        typer.echo(f"\n… 외 {len(shown) - limit}건 (--limit 로 조정)")
    _finish(0)


@app.command()
def version() -> None:
    """버전을 출력합니다."""
    typer.echo(f"safety-law-mapper {__version__}")
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
