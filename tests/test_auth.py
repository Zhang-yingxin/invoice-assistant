# tests/test_auth.py
import tempfile
from pathlib import Path
from store.db import Database
from core.auth import AuthService


def _make_db(tmpdir):
    return Database(Path(tmpdir) / "test.db")


def test_register_and_login():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = _make_db(tmpdir)
        auth = AuthService(db)
        ok, msg = auth.register("alice", "alice@example.com", "Password123")
        assert ok is True, msg
        result = auth.login("alice", "Password123")
        assert result["success"] is True
        assert result["user"]["username"] == "alice"


def test_login_wrong_password():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = _make_db(tmpdir)
        auth = AuthService(db)
        auth.register("bob", "bob@example.com", "Password123")
        result = auth.login("bob", "WrongPass")
        assert result["success"] is False
        assert "密码错误" in result["message"]


def test_login_disabled_user():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = _make_db(tmpdir)
        auth = AuthService(db)
        auth.register("carol", "carol@example.com", "Password123")
        user = db.get_user_by_username("carol")
        db.set_user_active(user["id"], False)
        result = auth.login("carol", "Password123")
        assert result["success"] is False
        assert "禁用" in result["message"]


def test_register_duplicate_username():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = _make_db(tmpdir)
        auth = AuthService(db)
        auth.register("dave", "dave@example.com", "Password123")
        ok, msg = auth.register("dave", "dave2@example.com", "Password123")
        assert ok is False
        assert "用户名" in msg


def test_generate_and_verify_reset_code():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = _make_db(tmpdir)
        auth = AuthService(db)
        auth.register("eve", "eve@example.com", "Password123")
        code = auth.generate_reset_code("eve@example.com")
        assert len(code) == 6
        assert code.isdigit()
        ok, msg = auth.verify_reset_code("eve@example.com", code)
        assert ok is True, msg
        # 验证后不可重复使用
        ok2, _ = auth.verify_reset_code("eve@example.com", code)
        assert ok2 is False


def test_reset_password():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = _make_db(tmpdir)
        auth = AuthService(db)
        auth.register("frank", "frank@example.com", "OldPass123")
        code = auth.generate_reset_code("frank@example.com")
        auth.verify_reset_code("frank@example.com", code)
        ok, msg = auth.reset_password("frank@example.com", "NewPass456")
        assert ok is True, msg
        result = auth.login("frank", "NewPass456")
        assert result["success"] is True
