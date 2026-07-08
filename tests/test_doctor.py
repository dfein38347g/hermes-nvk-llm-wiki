from runtime import run_doctor


def test_doctor_detects_missing_skill_root(tmp_path):
    result = run_doctor(
        lock_path=str(tmp_path / "upstream.lock.json"),
        vendor_dir=str(tmp_path / "vendor"),
        skill_root=str(tmp_path / "managed-skills" / "research" / "wiki"),
        config={},
    )
    assert result["healthy"] is False


def test_doctor_returns_check_list(tmp_path):
    result = run_doctor(
        lock_path=str(tmp_path / "upstream.lock.json"),
        vendor_dir=str(tmp_path / "vendor"),
        skill_root=str(tmp_path / "managed-skills" / "research" / "wiki"),
        config={},
    )
    assert "checks" in result
    assert len(result["checks"]) > 0
    for check in result["checks"]:
        assert "name" in check
        assert "ok" in check
        assert "detail" in check
