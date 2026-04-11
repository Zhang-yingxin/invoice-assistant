import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from store.db import Database
from ui.main_window import MainWindow

DB_PATH = Path.home() / ".invoice_assistant" / "data.db"


def _migrate_keyring_to_db(db: Database):
    """将旧版 keyring 中的 AK/SK 迁移到 db，迁移后删除 keyring 条目，只执行一次。"""
    if db.get_setting("keyring_migrated") == "1":
        return
    try:
        import keyring
        ak = keyring.get_password("invoice-assistant", "api_key") or ""
        sk = keyring.get_password("invoice-assistant", "secret_key") or ""
        if ak:
            db.set_setting("api_key", ak)
        if sk:
            db.set_setting("secret_key", sk)
        # 删除 keyring 条目，避免以后再触发系统弹窗
        try:
            keyring.delete_password("invoice-assistant", "api_key")
            keyring.delete_password("invoice-assistant", "secret_key")
        except Exception:
            pass
    except Exception:
        pass
    db.set_setting("keyring_migrated", "1")


def show_consent_dialog(db: Database) -> bool:
    """返回 True 表示用户同意，False 表示拒绝。首次启动弹出，同意后不再重复。"""
    if db.get_setting("consent_given") == "1":
        return True

    msg = QMessageBox()
    msg.setWindowTitle("数据使用说明")
    msg.setText(
        "本应用使用百度智能云增值税发票识别服务。\n"
        "在识别发票时，您的发票图片/PDF将上传至百度服务器处理。\n\n"
        "• 本应用不会永久存储您的发票图片\n"
        "• 识别结果仅保存在您本机的数据库中\n"
        "• 如需了解百度的数据处理方式，请查看其隐私政策"
    )
    agree_btn = msg.addButton("同意并继续", QMessageBox.ButtonRole.AcceptRole)
    msg.addButton("不同意，退出", QMessageBox.ButtonRole.RejectRole)
    msg.exec()

    if msg.clickedButton() == agree_btn:
        db.set_setting("consent_given", "1")
        return True
    return False


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
    QMainWindow, QWidget { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
    QScrollBar:vertical { width: 6px; background: #F5F5F5; border-radius: 3px; }
    QScrollBar::handle:vertical { background: #CCCCCC; border-radius: 3px; min-height: 20px; }
    QScrollBar::handle:vertical:hover { background: #AAAAAA; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QToolTip { background: #333; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; }
""")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = Database(DB_PATH)

    _migrate_keyring_to_db(db)

    if not show_consent_dialog(db):
        sys.exit(0)

    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
