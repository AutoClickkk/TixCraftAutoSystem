from __future__ import annotations
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
)

from ...services import updater


class UpdateDialog(QDialog):
    """Modal shown at startup when a newer release exists."""

    def __init__(self, info: updater.UpdateInfo, parent=None) -> None:
        super().__init__(parent)
        self._info = info
        self.setWindowTitle("發現新版本")
        self.setModal(True)
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(10)

        title = QLabel(f"新版本 v{info.latest_version} 可用")
        title.setObjectName("h1")
        layout.addWidget(title)

        sub = QLabel(f"目前版本 v{info.current_version}")
        sub.setObjectName("hint")
        layout.addWidget(sub)

        if info.body:
            label = QLabel("更新內容:")
            label.setObjectName("h2")
            layout.addWidget(label)
            body = QPlainTextEdit()
            body.setReadOnly(True)
            body.setPlainText(info.body)
            body.setMaximumHeight(160)
            layout.addWidget(body)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        later = QPushButton("稍後提醒")
        later.setObjectName("ghost")
        later.clicked.connect(self.reject)
        update_now = QPushButton("立即下載更新")
        update_now.setObjectName("primary")
        update_now.setDefault(True)
        update_now.clicked.connect(self._on_download)
        btn_row.addWidget(later)
        btn_row.addWidget(update_now)
        layout.addLayout(btn_row)

    def _on_download(self) -> None:
        asset = updater.pick_platform_asset(self._info.assets)
        url = asset.download_url if asset and asset.download_url else self._info.release_url
        if url:
            webbrowser.open(url)
        self.accept()
