from pathlib import Path

import pytest

from safety_law_mapper.loader import Dataset, load_dataset

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
SCHEMA_DIR = REPO_ROOT / "schemas"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def dataset() -> Dataset:
    return load_dataset(DATA_DIR)
