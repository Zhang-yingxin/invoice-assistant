# tests/test_auth_db.py
import tempfile
from pathlib import Path
from store.db import Database


def test_user_record_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        uid = db.create_user("alice", "alice@example.com", "hashed_pw", "user")
        assert uid > 0
        user = db.get_user_by_username("alice")
        assert user is not None
        assert user["email"] == "alice@example.com"
        assert user["role"] == "user"
        assert user["is_active"] is True


def test_admin_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        assert db.has_admin() is False
        db.create_user("admin", "admin@example.com", "hashed_pw", "admin")
        assert db.has_admin() is True


def test_invoices_has_user_id_column():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        from store.db import _db
        cursor = _db.execute_sql("PRAGMA table_info(invoices)")
        cols = {row[1] for row in cursor.fetchall()}
        assert "user_id" in cols


def test_get_user_by_email():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.create_user("bob", "bob@example.com", "hashed_pw", "user")
        user = db.get_user_by_email("bob@example.com")
        assert user is not None
        assert user["username"] == "bob"
