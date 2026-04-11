#!/bin/bash
set -e

echo "=== 发票识别登记助手 macOS 打包 ==="

# 安装依赖
pip3 install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

# 打包
pyinstaller invoice_assistant.spec --clean

# ad-hoc 代码签名（开发用，发布需正式证书）
codesign --deep --force --sign - dist/invoice-assistant/invoice-assistant

echo "=== 打包完成: dist/invoice-assistant/ ==="
