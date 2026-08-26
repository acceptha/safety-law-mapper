"""Load YAML data files into pydantic models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import Law, Mapping

# Bundled data (packaged); repo layout puts data/ at project root instead.
_PACKAGED_DATA = Path(__file__).parent / "data"
_REPO_DATA = Path(__file__).resolve().parents[2] / "data"


def default_data_dir() -> Path:
    if _PACKAGED_DATA.is_dir():
        return _PACKAGED_DATA
    return _REPO_DATA


@dataclass(frozen=True)
class Dataset:
    laws: dict[str, Law]
    mappings: dict[str, Mapping]


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: expected a YAML mapping at top level")
    return doc


def iter_law_files(data_dir: Path) -> list[Path]:
    return sorted((data_dir / "laws").glob("*.yaml"))


def iter_mapping_files(data_dir: Path) -> list[Path]:
    return sorted((data_dir / "mappings").glob("*.yaml"))


def load_laws(data_dir: Path | None = None) -> dict[str, Law]:
    data_dir = data_dir or default_data_dir()
    laws: dict[str, Law] = {}
    for path in iter_law_files(data_dir):
        law = Law.model_validate(_load_yaml(path))
        if law.law_id in laws:
            raise ValueError(f"duplicate law_id: {law.law_id} ({path})")
        laws[law.law_id] = law
    return laws


def load_mappings(data_dir: Path | None = None) -> dict[str, Mapping]:
    data_dir = data_dir or default_data_dir()
    mappings: dict[str, Mapping] = {}
    for path in iter_mapping_files(data_dir):
        mapping = Mapping.model_validate(_load_yaml(path))
        if mapping.mapping_id in mappings:
            raise ValueError(f"duplicate mapping_id: {mapping.mapping_id} ({path})")
        mappings[mapping.mapping_id] = mapping
    return mappings


def load_dataset(data_dir: Path | None = None) -> Dataset:
    data_dir = data_dir or default_data_dir()
    return Dataset(laws=load_laws(data_dir), mappings=load_mappings(data_dir))
