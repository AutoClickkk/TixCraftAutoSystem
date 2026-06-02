from __future__ import annotations

ACCENT = "#7aa2f7"
ACCENT_HOVER = "#89b4ff"
DANGER = "#f7768e"
SUCCESS = "#9ece6a"
WARN = "#e0af68"

BG = "#1a1b26"
PANEL = "#1f2030"
PANEL_2 = "#16161e"
BORDER = "#2a2b36"
TEXT = "#c0caf5"
TEXT_DIM = "#6b7394"
TEXT_STRONG = "#ffffff"


STYLESHEET = f"""
* {{
    font-family: -apple-system, "Segoe UI", "Microsoft JhengHei", "PingFang TC",
                  "Helvetica Neue", Arial, sans-serif;
    color: {TEXT};
}}

QMainWindow, QDialog {{
    background-color: {BG};
}}

QWidget#sidebar {{
    background-color: {PANEL_2};
    border-right: 1px solid {BORDER};
}}

QLabel#brand {{
    color: {TEXT_STRONG};
    font-size: 18px;
    font-weight: 700;
    padding: 18px 18px 6px 18px;
}}

QLabel#brandSub {{
    color: {TEXT_DIM};
    font-size: 11px;
    padding: 0 18px 18px 18px;
}}

QPushButton#navBtn {{
    text-align: left;
    padding: 10px 18px;
    margin: 2px 10px;
    background: transparent;
    color: {TEXT};
    border: none;
    border-radius: 8px;
    font-size: 14px;
}}
QPushButton#navBtn:hover {{
    background: rgba(122, 162, 247, 0.10);
}}
QPushButton#navBtn:checked {{
    background: rgba(122, 162, 247, 0.18);
    color: {TEXT_STRONG};
    font-weight: 600;
}}

QLabel#h1 {{
    color: {TEXT_STRONG};
    font-size: 22px;
    font-weight: 700;
}}
QLabel#h2 {{
    color: {TEXT_STRONG};
    font-size: 16px;
    font-weight: 600;
}}
QLabel#hint, QLabel.hint {{
    color: {TEXT_DIM};
    font-size: 12px;
}}
QLabel#status {{
    color: {TEXT_DIM};
    font-size: 12px;
    padding: 2px 8px;
}}

QFrame#card {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit, QPlainTextEdit {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {ACCENT};
    color: {TEXT};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QDateTimeEdit:focus, QPlainTextEdit:focus {{
    border-color: {ACCENT};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {TEXT_DIM};
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0px;
}}

QComboBox::drop-down {{ border: 0; }}

QPushButton {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; }}

QPushButton#primary {{
    background: {ACCENT};
    border: none;
    color: #1a1b26;
    font-weight: 600;
    padding: 10px 20px;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{
    background: rgba(122, 162, 247, 0.35);
    color: rgba(26, 27, 38, 0.7);
}}

QPushButton#danger {{
    background: {DANGER};
    border: none;
    color: #1a1b26;
    font-weight: 600;
    padding: 10px 20px;
}}

QPushButton#ghost {{
    background: transparent;
    border: 1px solid {BORDER};
}}

QPlainTextEdit#logView {{
    background: {PANEL_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    font-family: "Menlo", "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 10px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QFrame#updateBanner {{
    background: rgba(224, 175, 104, 0.12);
    border: 1px solid {WARN};
    border-radius: 8px;
}}
QFrame#updateBannerNone {{
    background: rgba(158, 206, 106, 0.10);
    border: 1px solid {SUCCESS};
    border-radius: 8px;
}}

QLabel#statusDot[state="idle"] {{ color: {TEXT_DIM}; }}
QLabel#statusDot[state="running"] {{ color: {ACCENT}; }}
QLabel#statusDot[state="success"] {{ color: {SUCCESS}; }}
QLabel#statusDot[state="error"] {{ color: {DANGER}; }}
QLabel#statusDot[state="warn"] {{ color: {WARN}; }}

QToolTip {{
    background: {PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px 8px;
}}
"""
