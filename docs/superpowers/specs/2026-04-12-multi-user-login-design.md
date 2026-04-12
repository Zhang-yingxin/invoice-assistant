# 多用户登录系统 — 设计文档

**日期：** 2026-04-12  
**状态：** 待实现

---

## 背景

现有 App 无用户概念，所有人共用同一份数据。目标：支持多用户登录，数据按用户隔离，管理员可查看所有人数据。

---

## 范围

- 多用户注册、登录
- 首次启动初始化管理员账号
- 忘记密码（邮箱验证码重置）
- 修改密码
- 管理员查看所有发票数据
- 管理员管理用户（禁用/启用/重置密码）
- 发票数据按用户隔离
- 每次功能完成后：本地打包 + 推送 GitHub + 打 tag 触发 CI 打包

---

## 架构

```
启动 main.py
  └─ 检查 users 表是否有管理员
       ├─ 无 → InitAdminWindow（初始化管理员）
       └─ 有 → LoginWindow
                 ├─ 登录成功 → MainWindow（携带 current_user）
                 ├─ 注册 → RegisterWindow → 回到 LoginWindow
                 └─ 忘记密码 → ResetPasswordWindow → 回到 LoginWindow
```

---

## 数据库变更

### 新增 `users` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | AutoField | 主键 |
| username | CharField(unique) | 用户名 |
| email | CharField(unique) | 邮箱，用于找回密码 |
| password_hash | CharField | bcrypt 哈希（使用 bcrypt 库） |
| role | CharField | `admin` 或 `user` |
| is_active | BooleanField | False 时禁止登录 |
| created_at | CharField | 注册时间 |

### `invoices` 表新增字段

- `user_id`：IntegerField，关联 users.id，NULL 表示历史数据（归属管理员）

### `settings` 表新增配置项

| key | 说明 |
|-----|------|
| smtp_host | SMTP 服务器地址 |
| smtp_port | SMTP 端口（默认 465） |
| smtp_user | 发件邮箱 |
| smtp_password | 授权码 |
| smtp_ssl | 是否使用 SSL（默认 true） |

---

## 新增文件

| 文件 | 职责 |
|------|------|
| `core/auth.py` | 用户认证逻辑：注册、登录、密码哈希、验证码生成/校验 |
| `core/mailer.py` | SMTP 发邮件：发验证码邮件 |
| `ui/login_window.py` | 登录窗口 |
| `ui/register_window.py` | 注册窗口 |
| `ui/reset_password_window.py` | 忘记密码（三步：输邮箱→输验证码→设新密码） |
| `ui/init_admin_window.py` | 首次启动初始化管理员 |
| `ui/user_management.py` | 管理员用户管理页（列表、禁用、重置密码） |

## 修改文件

| 文件 | 改动 |
|------|------|
| `store/db.py` | 新增 UserRecord 模型，invoices 表加 user_id，迁移逻辑 |
| `main.py` | 启动时判断是否有管理员，决定显示哪个窗口 |
| `ui/main_window.py` | 接收 current_user，顶部显示当前用户名，加退出登录 |
| `ui/sidebar.py` | 管理员额外显示"用户管理"入口 |
| `ui/settings.py` | 新增 SMTP 配置区块；设置页默认只读，点编辑才可修改 |
| `requirements.txt` | 新增 `bcrypt>=4.0` |

---

## 权限规则

| 操作 | 普通用户 | 管理员 |
|------|---------|-------|
| 查看发票 | 只看自己的 | 看所有人的 |
| 导入/识别发票 | 自己的 | 自己的（也可看别人的但不替别人导入） |
| 导出 Excel | 自己的 | 可选择导出全部或按用户筛选 |
| 修改密码 | 自己的 | 自己的 + 可重置任意用户密码 |
| 用户管理 | 无 | 可禁用/启用用户 |
| SMTP 配置 | 无 | 可配置 |

---

## 页面流程

### 登录窗口
- 字段：用户名、密码
- 按钮：登录、注册、忘记密码
- 登录失败提示具体原因（账号不存在 / 密码错误 / 账号已禁用）

### 注册窗口
- 字段：用户名、邮箱、密码、确认密码
- 注册成功后自动跳转登录窗口

### 忘记密码（三步）
1. 输入注册邮箱 → 点"发送验证码"
2. 输入 6 位验证码（10 分钟有效）
3. 输入新密码 + 确认密码 → 重置成功

### 初始化管理员（首次启动）
- 字段：用户名、邮箱、密码、确认密码
- 完成后直接进入主窗口（已登录状态）

### 修改密码（设置页内）
- 字段：当前密码、新密码、确认新密码

---

## 验证码机制

- 6 位随机数字
- 存入 `settings` 表：key=`reset_code_{email}`，value=`{code}:{expire_timestamp}`
- 有效期 10 分钟
- 验证后立即删除，防止重复使用

---

## 新增依赖

| 库 | 用途 |
|----|------|
| `bcrypt>=4.0` | 密码哈希 |
| `smtplib` | 发邮件（Python 标准库，无需安装） |

---

## 打包与发布流程（每次功能完成后执行）

1. 本地打包：`pyinstaller invoice_assistant.spec --clean -y`
2. 推送代码：`git push origin master`
3. 打 tag：`git tag v{version} && git push origin v{version}`
4. GitHub Actions 自动触发 macOS + Windows 打包并发布 Release

---

## 不在范围内

- 第三方 OAuth 登录（微信、Google 等）
- 云端用户同步
- 用户头像
- 操作审计日志
