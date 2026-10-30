import pytest

import database


@pytest.fixture(autouse=True)
def isolate_sqlite_database(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "justifi-test.db")
    yield
