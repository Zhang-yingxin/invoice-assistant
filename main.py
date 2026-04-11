import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from store.db import Database
from ui.main_window import MainWindow

DB_PATH = Path.home() / ".invoice_assistant" / "data.db"


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
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = Database(DB_PATH)

    if not show_consent_dialog(db):
        sys.exit(0)

    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
