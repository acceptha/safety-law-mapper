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
def version() -> None:
    """버전을 출력합니다."""
    typer.echo(f"safety-law-mapper {__version__}")
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
