from __future__ import annotations
import hashlib
import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox,
)

from ...utils import paths


_MAX_ATTEMPTS = 5
_AUTH_FILE = "auth.json"


def _load_password_hash() -> str:
    """Load the expected SHA-256 hash from (in order):
    1. env var AUTH_PASSWORD_HASH (for CI)
    2. bundled / dev-tree auth.json (gitignored)
    Returns empty string if missing -> verify() will always fail."""
    env = os.environ.get("AUTH_PASSWORD_HASH", "").strip().lower()
    if env:
        return env
    try:
        path = paths.find_resource(_AUTH_FILE)
        if path and path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return str(data.get("password_sha256", "")).strip().lower()
    except Exception:
        pass
    return ""


def verify(password: str) -> bool:
    expected = _load_password_hash()
    if not expected:
        return False
    cleaned = password.strip().strip("　")
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest().lower() == expected


class AuthDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("準點搶")
        self.setModal(True)
        self.setFixedSize(380, 230)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._attempts = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("請輸入啟動密碼")
        title.setObjectName("h1")
        layout.addWidget(title)

        hint = QLabel("此 App 受密碼保護，輸入密碼後即可使用。")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._input = QLineEdit()
        self._input.setEchoMode(QLineEdit.Password)
        self._input.setPlaceholderText("密碼 (全小寫英文 + 數字)")
        self._input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._input)

        self._show_pw = QCheckBox("顯示密碼")
        self._show_pw.setStyleSheet("color: #6b7394; font-size: 12px;")
        self._show_pw.toggled.connect(
            lambda on: self._input.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password
            )
        )
        layout.addWidget(self._show_pw)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #f7768e; font-size: 12px;")
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel = QPushButton("離開")
        cancel.setObjectName("ghost")
        cancel.clicked.connect(self.reject)
        unlock = QPushButton("解鎖")
        unlock.setObjectName("primary")
        unlock.setDefault(True)
        unlock.clicked.connect(self._on_submit)
        button_row.addWidget(cancel)
        button_row.addWidget(unlock)
        layout.addLayout(button_row)

        self._input.setFocus()

    def _on_submit(self) -> None:
        text = self._input.text()
        if verify(text):
            self.accept()
            return
        self._attempts += 1
        if self._attempts >= _MAX_ATTEMPTS:
            self._error_label.setText("錯誤次數過多，請重新啟動 App")
            self._error_label.setVisible(True)
            self._input.setDisabled(True)
            return
        remaining = _MAX_ATTEMPTS - self._attempts
        self._error_label.setText(f"密碼錯誤，還可嘗試 {remaining} 次")
        self._error_label.setVisible(True)
        self._input.clear()
        self._input.setFocus()
