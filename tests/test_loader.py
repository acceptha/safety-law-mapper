import json

import yaml

from safety_law_mapper.loader import iter_mapping_files
from safety_law_mapper.models import Mapping

from .conftest import DATA_DIR


def test_loads_all_laws_and_mappings(dataset):
    assert len(dataset.laws) >= 2
    assert len(dataset.mappings) >= 3
    assert "osh-rule" in dataset.laws
    assert "confined-space-welding" in dataset.mappings


def test_roundtrip_yaml_to_model_to_dict():
    """YAML -> model -> dict equals source (dates normalized to ISO strings)."""
    for path in iter_mapping_files(DATA_DIR):
        src = yaml.safe_load(path.read_text(encoding="utf-8"))
        model = Mapping.model_validate(src)
        dumped = model.model_dump(mode="json", exclude_unset=True)
        normalized_src = json.loads(json.dumps(src, default=str, ensure_ascii=False))
        assert dumped == normalized_src, f"round-trip mismatch: {path.name}"
