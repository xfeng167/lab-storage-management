import pytest
from pydantic import ValidationError

from src.core.config import Settings

def test_debug_defaults_to_false(monkeypatch) -> None:
    monkeypatch.delenv("DEBUG", raising=False)
    assert Settings(_env_file=None).debug is False


def test_database_url_has_no_built_in_credentials(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_url_is_hidden_from_settings_representation() -> None:
    settings = Settings(
        database_url="mysql+pymysql://app:super-secret@database/app",
        _env_file=None,
    )

    assert "super-secret" not in repr(settings)
