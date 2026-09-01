import shutil

from safety_law_mapper.validate import validate_data

from .conftest import DATA_DIR, SCHEMA_DIR


def test_seed_data_validates():
    report = validate_data(DATA_DIR, SCHEMA_DIR)
    assert report.ok, report.errors
    assert report.checked_files >= 5


def test_seed_data_has_no_unreviewed_shared_keywords():
    """일반어 소유권 결함(§7.8)이 다시 들어오면 여기서 걸린다."""
    report = validate_data(DATA_DIR, SCHEMA_DIR)
    assert report.warnings == [], report.warnings


def test_over_shared_keyword_warns(tmp_path):
    data = _copy_data(tmp_path)
    for name in ("ladder-work.yaml", "aerial-work-platform.yaml"):
        f = data / "mappings" / name
        f.write_text(
            f.read_text(encoding="utf-8").replace(
                "  keywords: [", "  keywords: [추락, ", 1
            ),
            encoding="utf-8",
        )
    report = validate_data(data, SCHEMA_DIR)
    assert report.ok, report.errors  # 경고이지 오류가 아니다
    assert any("'추락'" in w for w in report.warnings), report.warnings


def test_allowlisted_keyword_is_not_warned(tmp_path):
    """정책 파일에 근거와 함께 등록된 공유는 경고하지 않는다."""
    data = _copy_data(tmp_path)
    report = validate_data(data, SCHEMA_DIR)
    assert not any("'협착'" in w for w in report.warnings)
    (data / "keyword_policy.yaml").write_text("shared_keywords: []\n", encoding="utf-8")
    report = validate_data(data, SCHEMA_DIR)
    assert any("'협착'" in w for w in report.warnings), report.warnings


def _copy_data(tmp_path):
    dst = tmp_path / "data"
    shutil.copytree(DATA_DIR, dst)
    return dst


def test_unknown_law_fk_is_caught(tmp_path):
    data = _copy_data(tmp_path)
    f = data / "mappings" / "confined-space-work.yaml"
    f.write_text(
        f.read_text(encoding="utf-8").replace("law_id: osh-rule", "law_id: no-such-law"),
        encoding="utf-8",
    )
    report = validate_data(data, SCHEMA_DIR)
    assert not report.ok
    assert any("unknown law_id" in e for e in report.errors)


def test_bad_category_is_caught(tmp_path):
    data = _copy_data(tmp_path)
    f = data / "mappings" / "welding-cutting.yaml"
    f.write_text(
        f.read_text(encoding="utf-8").replace("category: hot-work", "category: nonsense"),
        encoding="utf-8",
    )
    report = validate_data(data, SCHEMA_DIR)
    assert not report.ok


def test_duplicate_mapping_id_is_caught(tmp_path):
    data = _copy_data(tmp_path)
    src = data / "mappings" / "welding-cutting.yaml"
    (data / "mappings" / "zz-copy.yaml").write_text(
        src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    report = validate_data(data, SCHEMA_DIR)
    assert not report.ok
    assert any("duplicate mapping_id" in e for e in report.errors)


def test_bad_date_range_is_caught(tmp_path):
    data = _copy_data(tmp_path)
    f = data / "mappings" / "welding-cutting.yaml"
    txt = f.read_text(encoding="utf-8").replace(
        'valid_from: "2025-09-01"\n        valid_until: null',
        'valid_from: "2025-09-01"\n        valid_until: "2018-01-01"',
    )
    f.write_text(txt, encoding="utf-8")
    report = validate_data(data, SCHEMA_DIR)
    assert not report.ok
    assert any("valid_from" in e for e in report.errors)
