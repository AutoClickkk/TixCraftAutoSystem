from __future__ import annotations
from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QPushButton, QLabel, QButtonGroup, QFrame,
)

from ..services.datacenter import DataCenter
from ..services import updater
from .pages.config_page import ConfigPage
from .pages.run_page import RunPage
from .pages.about_page import AboutPage


_NAV: List[Tuple[str, str]] = [
    ("執行", "run"),
    ("設定", "config"),
    ("關於", "about"),
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"準點搶 v{updater.get_current_version()}")
        self.resize(1080, 720)
        self.setMinimumSize(880, 600)

        self._dc = DataCenter()

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = self._build_sidebar()
        root.addWidget(sidebar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.run_page = RunPage(self._dc)
        self.config_page = ConfigPage(self._dc)
        self.about_page = AboutPage()

        self._pages = {
            "run": self.run_page,
            "config": self.config_page,
            "about": self.about_page,
        }
        for key in ("run", "config", "about"):
            self.stack.addWidget(self._pages[key])

        self.about_page.update_available.connect(self._on_update_available)
        self.config_page.saved.connect(lambda: self.statusBar().showMessage("設定已儲存", 3000))

        self._nav_buttons[0].setChecked(True)
        self._switch_to("run")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        brand = QLabel("準點搶")
        brand.setObjectName("brand")
        sub = QLabel("On-Time Ticketing")
        sub.setObjectName("brandSub")
        layout.addWidget(brand)
        layout.addWidget(sub)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #2a2b36; border: none;")
        layout.addWidget(separator)

        self._nav_buttons: List[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for idx, (label, key) in enumerate(_NAV):
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked, k=key: self._switch_to(k))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)
            self._group.addButton(btn, idx)
        layout.addSpacing(10)

        self.update_pill = QPushButton("✦ 有新版本")
        self.update_pill.setObjectName("navBtn")
        self.update_pill.setStyleSheet("color: #e0af68;")
        self.update_pill.setVisible(False)
        self.update_pill.clicked.connect(lambda: self._switch_to("about"))
        layout.addWidget(self.update_pill)

        layout.addStretch(1)
        footer = QLabel(f"v{updater.get_current_version()}")
        footer.setObjectName("hint")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)
        copyright_label = QLabel("© 2026 浩毅科技 HaoYi Tech")
        copyright_label.setObjectName("hint")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setContentsMargins(0, 0, 0, 14)
        layout.addWidget(copyright_label)
        return sidebar

    def _switch_to(self, key: str) -> None:
        widget = self._pages.get(key)
        if widget is None:
            return
        self.stack.setCurrentWidget(widget)
        for idx, (_, k) in enumerate(_NAV):
            if k == key:
                self._nav_buttons[idx].setChecked(True)
                break

    def _on_update_available(self, _info) -> None:
        self.update_pill.setVisible(True)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.run_page.shutdown()
        self.about_page.shutdown()
        super().closeEvent(event)
