from typer.testing import CliRunner

from safety_law_mapper import DISCLAIMER
from safety_law_mapper.cli import app

runner = CliRunner()


def test_search_found_exit_0_and_disclaimer():
    result = runner.invoke(app, ["search", "밀폐공간", "용접"])
    assert result.exit_code == 0
    assert "제619조" in result.output
    assert DISCLAIMER in result.output


def test_search_not_found_exit_1():
    result = runner.invoke(app, ["search", "존재하지않는키워드xyz"])
    assert result.exit_code == 1
    assert DISCLAIMER in result.output


def test_show():
    result = runner.invoke(app, ["show", "confined-space-welding"])
    assert result.exit_code == 0
    assert "밀폐공간 용접" in result.output
    assert DISCLAIMER in result.output


def test_show_missing_exit_1():
    result = runner.invoke(app, ["show", "nope"])
    assert result.exit_code == 1


def test_validate_ok():
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "검증 통과" in result.output
