from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
)


class CaptchaDialog(QDialog):
    def __init__(self, png_bytes: bytes, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("手動輸入驗證碼")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("OCR 無法辨識，請手動輸入下圖驗證碼")
        title.setObjectName("h2")
        layout.addWidget(title)

        image = QImage.fromData(png_bytes)
        pix = QPixmap.fromImage(image)
        if not pix.isNull():
            pix = pix.scaledToHeight(80, Qt.SmoothTransformation)
        img_label = QLabel()
        img_label.setPixmap(pix)
        img_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(img_label)

        self._input = QLineEdit()
        self._input.setMaxLength(8)
        self._input.setPlaceholderText("4 碼")
        layout.addWidget(self._input)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("ghost")
        cancel_btn.clicked.connect(self.reject)
        submit_btn = QPushButton("送出")
        submit_btn.setObjectName("primary")
        submit_btn.setDefault(True)
        submit_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(submit_btn)
        layout.addLayout(btn_row)

        self._input.setFocus()

    def code(self) -> Optional[str]:
        text = self._input.text().strip()
        return text or None
