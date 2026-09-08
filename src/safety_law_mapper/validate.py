"""Data validation: JSON Schema + referential integrity."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import yaml

from .loader import default_data_dir, iter_law_files, iter_mapping_files

_PACKAGED_SCHEMAS = Path(__file__).parent / "schemas"
_REPO_SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def default_schema_dir() -> Path:
    if _PACKAGED_SCHEMAS.is_dir():
        return _PACKAGED_SCHEMAS
    return _REPO_SCHEMAS


# A keyword on this many mappings makes ranking a coin flip: the scores tie and
# the outcome falls to condition-specificity or mapping_id order, so the more
# specific mapping buries the general one. Happened three times with 철거/용접/추락
# (docs/사고속보-연계-기획서.md §7.1, §7.7). Warn before a fourth.
KEYWORD_SHARE_LIMIT = 3


@dataclass
class ValidationReport:
    errors: list[str]
    checked_files: int
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_schema(schema_dir: Path, name: str) -> dict:
    with (schema_dir / name).open(encoding="utf-8") as f:
        return json.load(f)


def _schema_errors(instance: dict, schema: dict, label: str) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{label}: {loc}: {err.message}")
    return errors


def _to_jsonable(doc: dict) -> dict:
    """YAML dates come back as datetime.date; JSON Schema expects strings."""
    return json.loads(json.dumps(doc, default=str, ensure_ascii=False))


def load_shared_keyword_allowlist(data_dir: Path) -> dict[str, str]:
    """Keywords explicitly approved for sharing, mapped to their stated reason."""
    path = data_dir / "keyword_policy.yaml"
    if not path.is_file():
        return {}
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    allowed: dict[str, str] = {}
    for entry in doc.get("shared_keywords") or []:
        if isinstance(entry, dict) and entry.get("keyword"):
            allowed[entry["keyword"]] = (entry.get("reason") or "").strip()
    return allowed


def _keyword_share_warnings(
    owners: dict[str, list[str]], allowlist: dict[str, str]
) -> list[str]:
    warnings = []
    for keyword, mapping_ids in sorted(owners.items()):
        if len(mapping_ids) < KEYWORD_SHARE_LIMIT or keyword in allowlist:
            continue
        warnings.append(
            f"키워드 '{keyword}' — 매핑 {len(mapping_ids)}개가 공유합니다"
            f" ({', '.join(sorted(mapping_ids))}). 동점 시 더 좁은 매핑이 위로 올라가"
            f" 일반적인 답이 밀릴 수 있습니다. 일반어는 일반 매핑 하나가 소유하게 하거나,"
            f" 공유가 정당하면 data/keyword_policy.yaml에 근거와 함께 등록하세요."
        )
    return warnings


def validate_data(data_dir: Path | None = None, schema_dir: Path | None = None) -> ValidationReport:
    data_dir = data_dir or default_data_dir()
    schema_dir = schema_dir or default_schema_dir()
    law_schema = _load_schema(schema_dir, "law.schema.json")
    mapping_schema = _load_schema(schema_dir, "mapping.schema.json")

    errors: list[str] = []
    checked = 0

    law_ids: set[str] = set()
    for path in iter_law_files(data_dir):
        checked += 1
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        errors.extend(_schema_errors(_to_jsonable(doc), law_schema, path.name))
        law_id = doc.get("law_id") if isinstance(doc, dict) else None
        if law_id:
            if law_id in law_ids:
                errors.append(f"{path.name}: duplicate law_id '{law_id}'")
            law_ids.add(law_id)

    mapping_ids: set[str] = set()
    keyword_owners: dict[str, list[str]] = defaultdict(list)
    for path in iter_mapping_files(data_dir):
        checked += 1
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        errors.extend(_schema_errors(_to_jsonable(doc), mapping_schema, path.name))
        if not isinstance(doc, dict):
            continue
        mapping_id = doc.get("mapping_id")
        if mapping_id:
            if mapping_id in mapping_ids:
                errors.append(f"{path.name}: duplicate mapping_id '{mapping_id}'")
            mapping_ids.add(mapping_id)
            for keyword in (doc.get("work_type") or {}).get("keywords") or []:
                if isinstance(keyword, str):
                    keyword_owners[keyword].append(mapping_id)
        # Referential integrity: law_id FKs
        for al in doc.get("applicable_laws") or []:
            if isinstance(al, dict):
                fk = al.get("law_id")
                if fk and fk not in law_ids:
                    errors.append(f"{path.name}: unknown law_id '{fk}' (not in data/laws)")
                # valid_from <= valid_until when both present
                for art in al.get("articles") or []:
                    if isinstance(art, dict):
                        vf, vu = art.get("valid_from"), art.get("valid_until")
                        if vf and vu and str(vf) > str(vu):
                            errors.append(
                                f"{path.name}: {art.get('article_ref')}: valid_from {vf} > valid_until {vu}"
                            )
        # Employee range sanity
        cond = doc.get("conditions") or {}
        mn, mx = cond.get("min_employees"), cond.get("max_employees")
        if isinstance(mn, int) and isinstance(mx, int) and mn > mx:
            errors.append(f"{path.name}: min_employees {mn} > max_employees {mx}")

    warnings = _keyword_share_warnings(
        keyword_owners, load_shared_keyword_allowlist(data_dir)
    )
    return ValidationReport(errors=errors, checked_files=checked, warnings=warnings)
