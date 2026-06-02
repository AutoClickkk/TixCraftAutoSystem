from __future__ import annotations
from typing import Optional
import webbrowser

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QPlainTextEdit,
)

from ...services import updater
from ..workers import UpdateCheckWorker


class AboutPage(QWidget):
    update_available = Signal(object)  # UpdateInfo

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._worker: Optional[UpdateCheckWorker] = None
        self._latest_info: Optional[updater.UpdateInfo] = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        title = QLabel("關於")
        title.setObjectName("h1")
        outer.addWidget(title)

        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 18, 20, 18)
        info_layout.setSpacing(6)

        app_label = QLabel("準點搶")
        app_label.setObjectName("h2")
        version_label = QLabel(f"目前版本 v{updater.get_current_version()}")
        version_label.setObjectName("hint")
        self.version_label = version_label
        copyright_label = QLabel("© 2026 浩毅科技 HaoYi Tech")
        copyright_label.setObjectName("hint")
        info_layout.addWidget(app_label)
        info_layout.addWidget(version_label)
        info_layout.addWidget(copyright_label)
        outer.addWidget(info_card)

        self.banner = QFrame()
        self.banner.setObjectName("updateBannerNone")
        self.banner.setVisible(False)
        banner_layout = QVBoxLayout(self.banner)
        banner_layout.setContentsMargins(20, 16, 20, 16)
        banner_layout.setSpacing(8)
        self.banner_title = QLabel("")
        self.banner_title.setObjectName("h2")
        self.banner_body = QPlainTextEdit("")
        self.banner_body.setReadOnly(True)
        self.banner_body.setFixedHeight(120)
        self.banner_action_row = QHBoxLayout()
        self.banner_action_row.addStretch(1)
        self.download_btn = QPushButton("下載更新")
        self.download_btn.setObjectName("primary")
        self.download_btn.clicked.connect(self._on_download)
        self.banner_action_row.addWidget(self.download_btn)
        banner_layout.addWidget(self.banner_title)
        banner_layout.addWidget(self.banner_body)
        banner_layout.addLayout(self.banner_action_row)
        outer.addWidget(self.banner)

        button_row = QHBoxLayout()
        self.check_btn = QPushButton("檢查更新")
        self.check_btn.setObjectName("ghost")
        self.check_btn.clicked.connect(self.check_for_update)
        button_row.addWidget(self.check_btn)
        button_row.addStretch(1)
        outer.addLayout(button_row)

        outer.addStretch(1)
        self.check_for_update()

    # ------------------------------------------------------------------
    # Update check
    # ------------------------------------------------------------------

    def check_for_update(self) -> None:
        if self._thread is not None:
            return
        self.check_btn.setEnabled(False)
        self.check_btn.setText("檢查中…")
        self._worker = UpdateCheckWorker()
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._worker.finished.connect(self._on_check_done)
        self._thread.started.connect(self._worker.run)
        self._thread.start()

    def _on_check_done(self, info: updater.UpdateInfo) -> None:
        self.check_btn.setEnabled(True)
        self.check_btn.setText("檢查更新")
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
            self._worker = None

        self._latest_info = info
        self.banner.setVisible(True)
        if info.error:
            self.banner.setObjectName("updateBannerNone")
            self.banner_title.setText(f"無法檢查：{info.error}")
            self.banner_body.setPlainText("")
            self.download_btn.setVisible(False)
        elif info.has_update:
            self.banner.setObjectName("updateBanner")
            self.banner_title.setText(
                f"有新版本 v{info.latest_version} (目前 v{info.current_version})"
            )
            self.banner_body.setPlainText(info.body or "(release 沒有說明)")
            self.download_btn.setVisible(True)
            self.update_available.emit(info)
        else:
            self.banner.setObjectName("updateBannerNone")
            shown = info.latest_version or info.current_version
            self.banner_title.setText(f"已是最新版本 (v{shown})")
            self.banner_body.setPlainText("")
            self.download_btn.setVisible(False)
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)

    def _on_download(self) -> None:
        if self._latest_info is None:
            return
        asset = updater.pick_platform_asset(self._latest_info.assets)
        url = asset.download_url if asset and asset.download_url else self._latest_info.release_url
        if url:
            webbrowser.open(url)

    def shutdown(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
            self._worker = None
