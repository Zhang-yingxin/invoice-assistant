# core/auth.py
import random
import time
from store.db import Database


class AuthService:
    def __init__(self, db: Database):
        self._db = db

    def register(self, username: str, email: str, password: str, role: str = "user"):
        """注册新用户。返回 (ok: bool, message: str)。"""
        import bcrypt
        if self._db.get_user_by_username(username):
            return False, "用户名已存在"
        if self._db.get_user_by_email(email):
            return False, "邮箱已被注册"
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self._db.create_user(username, email, pw_hash, role)
        return True, "注册成功"

    def login(self, username: str, password: str) -> dict:
        """登录。返回 {"success": bool, "message": str, "user": dict|None}。"""
        import bcrypt
        user = self._db.get_user_by_username(username)
        if user is None:
            return {"success": False, "message": "账号不存在", "user": None}
        if not user["is_active"]:
            return {"success": False, "message": "账号已被禁用，请联系管理员", "user": None}
        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return {"success": False, "message": "密码错误", "user": None}
        return {"success": True, "message": "登录成功", "user": user}

    def change_password(self, user_id: int, old_password: str, new_password: str):
        """修改密码（需验证旧密码）。返回 (ok, message)。"""
        import bcrypt
        users = self._db.get_all_users()
        user = next((u for u in users if u["id"] == user_id), None)
        if user is None:
            return False, "用户不存在"
        if not bcrypt.checkpw(old_password.encode(), user["password_hash"].encode()):
            return False, "当前密码错误"
        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self._db.update_user_password(user_id, new_hash)
        return True, "密码修改成功"

    def generate_reset_code(self, email: str) -> str:
        """生成 6 位验证码，存入 settings，有效期 10 分钟。返回验证码。"""
        code = f"{random.randint(0, 999999):06d}"
        expire_ts = int(time.time()) + 600  # 10 分钟
        self._db.set_setting(f"reset_code_{email}", f"{code}:{expire_ts}")
        return code

    def verify_reset_code(self, email: str, code: str):
        """校验验证码。验证成功后立即删除，防止重复使用。返回 (ok, message)。"""
        stored = self._db.get_setting(f"reset_code_{email}", "")
        if not stored:
            return False, "验证码不存在或已过期"
        parts = stored.split(":")
        if len(parts) != 2:
            return False, "验证码格式错误"
        stored_code, expire_ts = parts[0], int(parts[1])
        if int(time.time()) > expire_ts:
            self._db.set_setting(f"reset_code_{email}", "")
            return False, "验证码已过期"
        if code != stored_code:
            return False, "验证码错误"
        # 验证成功，立即删除
        self._db.set_setting(f"reset_code_{email}", "")
        return True, "验证码正确"

    def reset_password(self, email: str, new_password: str):
        """重置密码（verify_reset_code 通过后调用）。返回 (ok, message)。"""
        import bcrypt
        user = self._db.get_user_by_email(email)
        if user is None:
            return False, "邮箱不存在"
        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self._db.update_user_password(user["id"], new_hash)
        return True, "密码重置成功"
