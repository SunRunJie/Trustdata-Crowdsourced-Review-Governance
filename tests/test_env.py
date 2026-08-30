from __future__ import annotations

import os

from trustdata.env import load_env_file


def test_load_env_file_ignores_comments_and_preserves_existing_value(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# local secrets\n"
        "TEST_ENV_NEW='new value'\n"
        "TEST_ENV_EXISTING=from-file\n"
        "invalid key=value\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_ENV_EXISTING", "from-process")
    monkeypatch.delenv("TEST_ENV_NEW", raising=False)

    loaded = load_env_file(env_file)

    assert loaded == ["TEST_ENV_NEW"]
    assert os.environ["TEST_ENV_NEW"] == "new value"
    assert os.environ["TEST_ENV_EXISTING"] == "from-process"


def test_load_env_file_can_override_and_handles_missing_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("export TEST_ENV_OVERRIDE=from-file\n", encoding="utf-8")
    monkeypatch.setenv("TEST_ENV_OVERRIDE", "from-process")

    assert load_env_file(tmp_path / "missing.env") == []
    assert load_env_file(env_file, override=True) == ["TEST_ENV_OVERRIDE"]
    assert os.environ["TEST_ENV_OVERRIDE"] == "from-file"
