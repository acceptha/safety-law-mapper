"""The static demo ships a JavaScript port of the matcher so GitHub Pages can
run without a server. Two implementations of a ranking drift — the inline copy
this replaced had already diverged, tie-breaking with localeCompare where
Python sorts by code point. This runs both over the golden fixtures and fails
when they disagree, which is the only thing keeping the port honest.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from safety_law_mapper.matcher import Query, match
from safety_law_mapper.models import WorkCategory

from .conftest import FIXTURES

REPO_ROOT = Path(__file__).resolve().parents[1]
MATCHER_JS = REPO_ROOT / "web" / "matcher.js"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is not installed"
)

_DRIVER = """
import { match } from %(module)s;
import { readFileSync } from "node:fs";
const { mappings, queries } = JSON.parse(readFileSync(process.argv[2], "utf8"));
const out = queries.map((q) => match(mappings, q).map((r) => r.mapping.mapping_id));
process.stdout.write(JSON.stringify(out));
"""


def _run_node(mappings: list[dict], queries: list[dict], tmp_path: Path) -> list[list[str]]:
    """One node process per call. Process startup dominates the runtime here
    (seconds, not milliseconds, on a Windows dev box), so every query set in
    this module goes through a single invocation."""
    payload = tmp_path / "payload.json"
    payload.write_text(
        json.dumps({"mappings": mappings, "queries": queries}, ensure_ascii=False),
        encoding="utf-8",
    )
    driver = tmp_path / "driver.mjs"
    driver.write_text(
        _DRIVER % {"module": json.dumps(MATCHER_JS.as_uri())}, encoding="utf-8"
    )
    proc = subprocess.run(
        ["node", str(driver), str(payload)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, f"node failed:\n{proc.stderr}"
    return json.loads(proc.stdout)


def _py_ids(mappings, q: dict) -> list[str]:
    query = Query(
        keywords=q.get("keywords", []),
        category=WorkCategory(q["category"]) if q.get("category") else None,
        employees=q.get("employees"),
    )
    return [r.mapping.mapping_id for r in match(mappings, query)]


@pytest.fixture(scope="module")
def exported_data(tmp_path_factory) -> dict:
    """The demo reads scripts/export_web_data.py output, so the port is checked
    against that exact payload rather than a hand-built one."""
    out = tmp_path_factory.mktemp("export") / "data.json"
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "export_web_data.py"), str(out)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(out.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def parity(exported_data, tmp_path_factory) -> dict:
    """Every query set this module needs, through one node invocation."""
    golden = [
        c["query"]
        for c in yaml.safe_load(
            (FIXTURES / "golden_queries.yaml").read_text(encoding="utf-8")
        )
    ]
    assert golden, "golden fixture file is empty"
    # Code-point vs locale ordering only shows up on ties, so force some: a
    # bare category query gives every member of that category the same score.
    ties = [{"category": c.value} for c in WorkCategory]

    queries = golden + ties
    js = _run_node(exported_data["mappings"], queries, tmp_path_factory.mktemp("node"))
    return {"golden": list(zip(golden, js[: len(golden)], strict=True)),
            "ties": list(zip(ties, js[len(golden):], strict=True))}


def test_js_port_ranks_identically_to_python(parity, dataset):
    mappings = list(dataset.mappings.values())
    for q, got_js in parity["golden"]:
        got_py = _py_ids(mappings, q)
        assert got_js == got_py, (
            f"JS/Python 랭킹 불일치\n  query: {q}\n  js: {got_js[:5]}\n  py: {got_py[:5]}"
        )


def test_parity_holds_on_ties_sorted_by_id(parity, dataset):
    mappings = list(dataset.mappings.values())
    for q, got_js in parity["ties"]:
        got_py = _py_ids(mappings, q)
        assert got_js == got_py, f"tie-break 불일치 ({q['category']}): {got_js} != {got_py}"


def test_export_carries_every_field_the_port_reads(exported_data):
    """A field dropped from the export would make the port silently score
    differently rather than fail loudly."""
    m = exported_data["mappings"][0]
    assert {"mapping_id", "work_type", "conditions"} <= set(m)
    assert {"name_ko", "category", "keywords"} <= set(m["work_type"])
