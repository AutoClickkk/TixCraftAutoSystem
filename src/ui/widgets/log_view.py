from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit


_COLOURS = {
    "INFO": "#a9b1d6",
    "WARN": "#e0af68",
    "ERROR": "#f7768e",
}


class LogView(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("logView")
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )

    def append_line(self, level: str, line: str) -> None:
        color = _COLOURS.get(level, "#a9b1d6")
        safe = (
            line.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )
        self.appendHtml(f'<span style="color:{color}">{safe}</span>')
        self.moveCursor(QTextCursor.End)
