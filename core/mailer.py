# core/mailer.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from store.db import Database


class Mailer:
    def __init__(self, db: Database):
        self._db = db

    def send_reset_code(self, to_email: str, code: str):
        """发送验证码邮件。返回 (ok: bool, message: str)。"""
        host = self._db.get_setting("smtp_host", "")
        port_str = self._db.get_setting("smtp_port", "465")
        user = self._db.get_setting("smtp_user", "")
        password = self._db.get_setting("smtp_password", "")
        use_ssl = self._db.get_setting("smtp_ssl", "true").lower() == "true"

        if not host or not user or not password:
            return False, "SMTP 未配置，请先在设置页配置邮箱信息"

        try:
            port = int(port_str)
        except ValueError:
            port = 465

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "发票助手 — 密码重置验证码"
        msg["From"] = user
        msg["To"] = to_email
        body = (
            f"您好，\n\n"
            f"您的密码重置验证码为：{code}\n\n"
            f"验证码有效期 10 分钟，请勿泄露给他人。\n\n"
            f"如果您未申请重置密码，请忽略此邮件。"
        )
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            if use_ssl:
                with smtplib.SMTP_SSL(host, port) as server:
                    server.login(user, password)
                    server.sendmail(user, to_email, msg.as_string())
            else:
                with smtplib.SMTP(host, port) as server:
                    server.starttls()
                    server.login(user, password)
                    server.sendmail(user, to_email, msg.as_string())
            return True, "验证码已发送"
        except Exception as e:
            return False, f"邮件发送失败：{e}"
