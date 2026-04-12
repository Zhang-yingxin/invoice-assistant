import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
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
    from PyQt6.QtCore import Qt as _Qt
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        _Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = Database(DB_PATH)

    _migrate_keyring_to_db(db)

    if not show_consent_dialog(db):
        sys.exit(0)

    from core.auth import AuthService
    auth = AuthService(db)

    current_user = None

    if not db.has_admin():
        # 首次启动：初始化管理员
        from ui.init_admin_window import InitAdminWindow
        init_win = InitAdminWindow(db, auth)
        created_users = []
        init_win.admin_created.connect(lambda u: created_users.append(u))
        if init_win.exec() != QDialog.DialogCode.Accepted or not created_users:
            sys.exit(0)
        current_user = created_users[0]
    else:
        # 正常启动：显示登录窗口
        from ui.login_window import LoginWindow
        from ui.register_window import RegisterWindow
        from ui.reset_password_window import ResetPasswordWindow

        while current_user is None:
            login_win = LoginWindow(db, auth)
            logged_in = []
            login_win.login_success.connect(lambda u: logged_in.append(u))

            def open_register():
                reg = RegisterWindow(db, auth)
                reg.exec()

            def open_reset():
                reset = ResetPasswordWindow(db, auth)
                reset.exec()

            login_win.register_requested.connect(open_register)
            login_win.forgot_password_requested.connect(open_reset)

            result = login_win.exec()
            if result != QDialog.DialogCode.Accepted:
                sys.exit(0)
            if logged_in:
                current_user = logged_in[0]

    window = MainWindow(db, current_user)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
