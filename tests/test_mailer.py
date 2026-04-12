# tests/test_mailer.py
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from store.db import Database
from core.mailer import Mailer


def _make_db_with_smtp(tmpdir):
    db = Database(Path(tmpdir) / "test.db")
    db.set_setting("smtp_host", "smtp.example.com")
    db.set_setting("smtp_port", "465")
    db.set_setting("smtp_user", "sender@example.com")
    db.set_setting("smtp_password", "secret")
    db.set_setting("smtp_ssl", "true")
    return db


def test_mailer_sends_email():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = _make_db_with_smtp(tmpdir)
        mailer = Mailer(db)
        with patch("smtplib.SMTP_SSL") as mock_ssl:
            mock_server = MagicMock()
            mock_ssl.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_ssl.return_value.__exit__ = MagicMock(return_value=False)
            ok, msg = mailer.send_reset_code("receiver@example.com", "123456")
        assert ok is True, msg
        mock_server.login.assert_called_once_with("sender@example.com", "secret")
        mock_server.sendmail.assert_called_once()


def test_mailer_no_smtp_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        mailer = Mailer(db)
        ok, msg = mailer.send_reset_code("receiver@example.com", "123456")
        assert ok is False
        assert "SMTP" in msg
