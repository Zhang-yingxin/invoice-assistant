"""
发票识别助手 - 统一色彩主题定义

本文件集中定义了应用的所有颜色常量，便于维护和一致性。
"""

# ============================================================================
# 主色调定义
# ============================================================================
COLOR_PRIMARY_BLUE = "#1E5BA8"          # 企业蓝 - 主色调
COLOR_PRIMARY_BLUE_DARK = "#0D47A1"     # 企业蓝深 - 悬停/选中
COLOR_PRIMARY_BLUE_LIGHT = "#90CAF9"    # 企业蓝浅 - 背景/提示
COLOR_ACCENT_ORANGE = "#FF9800"         # 辅助橙 - 强调色
COLOR_ACCENT_ORANGE_DARK = "#F57C00"    # 辅助橙深 - 悬停

# ============================================================================
# 状态色定义
# ============================================================================
COLOR_STATUS_PENDING = "#666666"         # 待处理 - 中性灰
COLOR_STATUS_PROCESSING = "#1E5BA8"      # 处理中 - 企业蓝
COLOR_STATUS_OCR_DONE = "#FF9800"        # 识别完成 - 辅助橙
COLOR_STATUS_CONFIRMED = "#388E3C"       # 已确认 - 深绿
COLOR_STATUS_FAILED = "#D32F2F"          # 识别失败 - 深红
COLOR_STATUS_MANUAL_EDITING = "#9C27B0"  # 手动编辑 - 紫色
COLOR_STATUS_MANUAL_DONE = "#388E3C"     # 手动完成 - 深绿

# 状态色字典（便于快速查询）
STATUS_COLORS = {
    "pending": COLOR_STATUS_PENDING,
    "processing": COLOR_STATUS_PROCESSING,
    "ocr_done": COLOR_STATUS_OCR_DONE,
    "confirmed": COLOR_STATUS_CONFIRMED,
    "failed": COLOR_STATUS_FAILED,
    "manual_editing": COLOR_STATUS_MANUAL_EDITING,
    "manual_done": COLOR_STATUS_MANUAL_DONE,
}

# ============================================================================
# 背景色层级定义
# ============================================================================
COLOR_BG_PRIMARY = "#FFFFFF"             # 主背景 - 应用主体
COLOR_BG_SECONDARY = "#F5F5F5"           # 次背景 - 工具栏/边框
COLOR_BG_CARD = "#FFFFFF"                # 卡片背景
COLOR_BG_CARD_HOVER = "#F8F8F8"          # 卡片悬停
COLOR_BG_INFO = "#E3F2FD"                # 信息提示条 - 浅蓝
COLOR_BG_WARNING = "#FFF3CD"             # 警告提示条 - 浅黄
COLOR_BG_DRAG_ACTIVE = "#BBDEFB"         # 拖拽激活 - 深蓝提示
COLOR_BG_DISABLED = "#EEEEEE"            # 禁用背景

# ============================================================================
# 文字色层级定义
# ============================================================================
COLOR_TEXT_PRIMARY = "#212121"           # 主文字 - 最高对比度
COLOR_TEXT_SECONDARY = "#666666"         # 次文字 - 辅助信息
COLOR_TEXT_WEAK = "#999999"              # 弱文字 - 占位符/提示
COLOR_TEXT_DISABLED = "#CCCCCC"          # 禁用文字
COLOR_TEXT_INVERSE = "#FFFFFF"           # 反白文字 - 深色背景上

# ============================================================================
# 边框与分割线定义
# ============================================================================
COLOR_BORDER_PRIMARY = "#E0E0E0"         # 主边框 - 卡片/输入框
COLOR_BORDER_DIVIDER = "#EEEEEE"         # 分割线 - 列表/区域
COLOR_BORDER_FOCUS = "#1E5BA8"           # 高亮边框 - 聚焦/选中
COLOR_BORDER_ERROR = "#D32F2F"           # 错误边框 - 低置信度

# ============================================================================
# 其他颜色定义
# ============================================================================
COLOR_SUCCESS_GREEN = "#388E3C"           # 成功绿
COLOR_SUCCESS_GREEN_DARK = "#2E7D32"      # 成功绿深 - 悬停
COLOR_ERROR_RED = "#D32F2F"               # 错误红
COLOR_ERROR_RED_DARK = "#C62828"          # 错误红深 - 悬停
COLOR_WARNING_YELLOW = "#FFC107"          # 警告黄
COLOR_INFO_TEAL = "#1565C0"               # 信息靛蓝

# ============================================================================
# 通用样式字符串模板（用于 setStyleSheet）
# ============================================================================

def get_button_stylesheet(
    bg_color=COLOR_PRIMARY_BLUE,
    hover_color=COLOR_PRIMARY_BLUE_DARK,
    text_color=COLOR_TEXT_INVERSE,
    disabled_text_color=COLOR_TEXT_DISABLED
):
    """获取按钮的标准样式表"""
    return (
        f"QPushButton {{"
        f"  background: {bg_color};"
        f"  color: {text_color};"
        f"  border: none;"
        f"  border-radius: 3px;"
        f"  padding: 4px 8px;"
        f"  font-weight: bold;"
        f"}}"
        f"QPushButton:hover {{"
        f"  background: {hover_color};"
        f"}}"
        f"QPushButton:pressed {{"
        f"  background: {hover_color};"
        f"  opacity: 0.8;"
        f"}}"
        f"QPushButton:disabled {{"
        f"  background: {COLOR_BG_DISABLED};"
        f"  color: {disabled_text_color};"
        f"}}"
    )


def get_input_stylesheet(
    border_color=COLOR_BORDER_PRIMARY,
    focus_color=COLOR_BORDER_FOCUS
):
    """获取输入框的标准样式表"""
    return (
        f"QLineEdit, QDoubleSpinBox, QComboBox {{"
        f"  border: 1px solid {border_color};"
        f"  border-radius: 3px;"
        f"  padding: 4px 6px;"
        f"  color: {COLOR_TEXT_PRIMARY};"
        f"  background: {COLOR_BG_PRIMARY};"
        f"}}"
        f"QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{"
        f"  border: 2px solid {focus_color};"
        f"}}"
    )


def get_card_stylesheet(
    bg_color=COLOR_BG_CARD,
    hover_color=COLOR_BG_CARD_HOVER,
    border_color=COLOR_BORDER_PRIMARY
):
    """获取卡片的标准样式表"""
    return (
        f"QFrame {{"
        f"  background: {bg_color};"
        f"  border: 1px solid {border_color};"
        f"  border-radius: 4px;"
        f"}}"
        f"QFrame:hover {{"
        f"  background: {hover_color};"
        f"}}"
    )


def get_toolbar_stylesheet():
    """获取工具栏的标准样式表"""
    return f"background: {COLOR_BG_SECONDARY}; border-bottom: 1px solid {COLOR_BORDER_DIVIDER};"


def get_status_color(status):
    """根据状态字符串获取对应的颜色"""
    return STATUS_COLORS.get(status, COLOR_STATUS_PENDING)


# ============================================================================
# 快速调用示例
# ============================================================================

# 使用示例：
# button.setStyleSheet(get_button_stylesheet())
# input_field.setStyleSheet(get_input_stylesheet())
# card.setStyleSheet(get_card_stylesheet())
# toolbar.setStyleSheet(get_toolbar_stylesheet())
