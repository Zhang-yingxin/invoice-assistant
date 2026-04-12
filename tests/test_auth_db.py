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


def test_get_user_not_found_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        assert db.get_user_by_username("nonexistent") is None
        assert db.get_user_by_email("nobody@example.com") is None


def test_set_user_active():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        uid = db.create_user("carol", "carol@example.com", "hash", "user")
        db.set_user_active(uid, False)
        user = db.get_user_by_username("carol")
        assert user["is_active"] is False
        db.set_user_active(uid, True)
        user = db.get_user_by_username("carol")
        assert user["is_active"] is True


def test_update_user_password():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        uid = db.create_user("dave", "dave@example.com", "old_hash", "user")
        db.update_user_password(uid, "new_hash")
        user = db.get_user_by_username("dave")
        assert user["password_hash"] == "new_hash"


def test_get_all_filters_by_user():
    from core.models import Invoice, InvoiceStatus, InvoiceSheet
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        uid1 = db.create_user("u1", "u1@example.com", "hash", "user")
        uid2 = db.create_user("u2", "u2@example.com", "hash", "user")
        admin_id = db.create_user("admin", "admin@example.com", "hash", "admin")

        def _inv(path, user_id):
            inv = Invoice(
                file_path=path, status=InvoiceStatus.PENDING,
                sheet=InvoiceSheet.NORMAL, invoice_type="", invoice_code="",
                invoice_number=path, issue_date="", goods_name="",
                seller_name="", buyer_name="", buyer_tax_id="",
                amount=0, tax_rate="", tax_amount=0, total_amount=0,
            )
            inv.user_id = user_id
            return inv

        db.save(_inv("/tmp/inv1.pdf", uid1))
        db.save(_inv("/tmp/inv2.pdf", uid2))
        db.save(_inv("/tmp/inv3.pdf", None))  # 历史数据

        # 普通用户只看自己的
        u1_invoices = db.get_all(user_id=uid1, is_admin=False)
        assert len(u1_invoices) == 1
        assert u1_invoices[0].file_path == "/tmp/inv1.pdf"

        # 管理员看全部
        admin_invoices = db.get_all(user_id=admin_id, is_admin=True)
        assert len(admin_invoices) == 3
