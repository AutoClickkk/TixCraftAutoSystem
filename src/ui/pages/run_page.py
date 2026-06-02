from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QMessageBox,
)

from ...services.datacenter import DataCenter
from ..workers import RunWorker
from ..widgets.log_view import LogView


_STATE_TEXT = {
    "idle": ("待機", "idle"),
    "starting": ("啟動中", "warn"),
    "ready": ("等待登入", "warn"),
    "running": ("執行中", "running"),
    "paused": ("等待你操作", "warn"),
    "finished": ("已結束", "success"),
    "success": ("🎉 成功購票", "success"),
    "error": ("錯誤", "error"),
}


class RunPage(QWidget):
    def __init__(self, data_center: DataCenter, parent=None) -> None:
        super().__init__(parent)
        self._dc = data_center
        self._thread: Optional[QThread] = None
        self._worker: Optional[RunWorker] = None
        self._kept_driver = None  # Chrome left open after a successful purchase
        self._state: str = "idle"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("執行")
        title.setObjectName("h1")
        self.status_label = QLabel("待機")
        self.status_label.setObjectName("hint")
        title_col.addWidget(title)
        title_col.addWidget(self.status_label)
        header.addLayout(title_col)
        header.addStretch(1)

        self.state_dot = QLabel("●  待機")
        self.state_dot.setObjectName("statusDot")
        self.state_dot.setProperty("state", "idle")
        header.addWidget(self.state_dot)
        outer.addLayout(header)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.start_browser_btn = QPushButton("啟動瀏覽器登入")
        self.start_browser_btn.setObjectName("primary")
        self.start_browser_btn.clicked.connect(self._on_start_browser)
        self.start_grab_btn = QPushButton("開始搶票")
        self.start_grab_btn.setObjectName("primary")
        self.start_grab_btn.setEnabled(False)
        self.start_grab_btn.clicked.connect(self._on_start_grab)
        self.resume_btn = QPushButton("繼續")
        self.resume_btn.setObjectName("primary")
        self.resume_btn.setVisible(False)
        self.resume_btn.clicked.connect(self._on_resume)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        button_row.addWidget(self.start_browser_btn)
        button_row.addWidget(self.start_grab_btn)
        button_row.addWidget(self.resume_btn)
        button_row.addWidget(self.stop_btn)
        button_row.addStretch(1)
        outer.addLayout(button_row)

        self.pause_card = QFrame()
        self.pause_card.setObjectName("updateBanner")
        self.pause_card.setVisible(False)
        pause_layout = QVBoxLayout(self.pause_card)
        pause_layout.setContentsMargins(20, 14, 20, 14)
        pause_layout.setSpacing(4)
        self.pause_title = QLabel("已暫停 — 等待你的操作")
        self.pause_title.setObjectName("h2")
        self.pause_hint = QLabel("")
        self.pause_hint.setObjectName("hint")
        self.pause_hint.setWordWrap(True)
        pause_layout.addWidget(self.pause_title)
        pause_layout.addWidget(self.pause_hint)
        outer.addWidget(self.pause_card)

        hint_card = QFrame()
        hint_card.setObjectName("card")
        hint_layout = QVBoxLayout(hint_card)
        hint_layout.setContentsMargins(20, 14, 20, 14)
        hint_layout.setSpacing(4)
        flow_title = QLabel("操作流程")
        flow_title.setObjectName("h2")
        hint_layout.addWidget(flow_title)
        for step in (
            "① 先到「設定」頁填活動 ID、票數、價位關鍵字等, 按「儲存設定」",
            "② 回此頁按「啟動瀏覽器登入」, App 會開啟內建 Chrome 到 tixcraft 登入頁",
            "③ 在 Chrome 內手動完成登入 (含簡訊/Email 驗證等), 登入狀態會自動記住",
            "④ 回本視窗按「開始搶票」, App 接管後續所有步驟",
            "⑤ 流程: 選場次 → (會員預售驗證, 若有) → 選票區 → 填票數 → 驗證碼 → 我同意條款 → 送出",
            "⑥ 驗證碼: OCR 全自動, 認錯就刷新重試, 不需要人工輸入",
            "⑦ 遇到非預期頁面 (年齡確認、會員驗證⋯) App 會暫停, 你在瀏覽器處理完按「繼續」",
            "⑧ 看到「🎉 成功購票」就代表訂單已送出, Chrome 視窗保留讓你付款",
        ):
            step_label = QLabel(step)
            step_label.setObjectName("hint")
            step_label.setWordWrap(True)
            hint_layout.addWidget(step_label)
        outer.addWidget(hint_card)

        log_label = QLabel("即時 log")
        log_label.setObjectName("h2")
        outer.addWidget(log_label)
        self.log_view = LogView()
        outer.addWidget(self.log_view, 1)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _apply_state(self, state: str) -> None:
        self._state = state
        text, key = _STATE_TEXT.get(state, ("待機", "idle"))
        self.state_dot.setText(f"●  {text}")
        self.state_dot.setProperty("state", key)
        self.state_dot.style().unpolish(self.state_dot)
        self.state_dot.style().polish(self.state_dot)

        self.start_browser_btn.setEnabled(state in ("idle", "finished", "success", "error"))
        self.start_grab_btn.setEnabled(state == "ready")
        self.stop_btn.setEnabled(state in ("starting", "ready", "running", "paused"))
        self.resume_btn.setVisible(state == "paused")
        self.pause_card.setVisible(state == "paused")
        if state != "paused":
            self.pause_hint.setText("")

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_start_browser(self) -> None:
        config = self._dc.get_config(reload=True)
        if not config.get("game_id"):
            QMessageBox.warning(self, "尚未設定", "請先到 '設定' 頁填寫活動 ID 並儲存")
            return

        # Close any Chrome left open from a previous successful run, otherwise
        # the new Chrome can't claim the same --user-data-dir (SingletonLock).
        self._close_kept_browser()
        self.log_view.clear()
        self._worker = RunWorker(config)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._worker.log_line.connect(self.log_view.append_line)
        self._worker.status_changed.connect(self.status_label.setText)
        self._worker.state_changed.connect(self._apply_state)
        self._worker.resume_requested.connect(self._on_pause_request)
        self._worker.error.connect(self._on_error)
        self._worker.success.connect(self._on_success)
        self._worker.finished.connect(self._on_finished)

        self._thread.started.connect(self._worker.run)
        self._thread.start()
        self._apply_state("starting")

    def _on_start_grab(self) -> None:
        if self._worker is None:
            return
        self.start_grab_btn.setEnabled(False)
        self._worker.signal_login_complete()

    def _on_stop(self) -> None:
        if self._worker is not None:
            self._worker.request_stop()

    def _on_resume(self) -> None:
        if self._worker is not None:
            self._worker.submit_resume(True)

    def _on_pause_request(self, url: str, hint: str) -> None:
        self.pause_hint.setText(
            f"{hint}\n\n目前 URL: {url}\n\n完成後請按上方「繼續」"
        )

    def _on_error(self, msg: str) -> None:
        QMessageBox.critical(self, "執行錯誤", msg)

    def _on_success(self) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("🎉 成功購票")
        box.setText("訂單已送出!")
        box.setInformativeText(
            "Chrome 視窗會保留讓你完成付款。\n"
            "想再搶下一場就直接按「啟動瀏覽器登入」, 程式會自動關掉舊視窗開新的。"
        )
        box.exec()

    def _on_finished(self) -> None:
        keep_browser = self._state == "success"
        if self._worker is not None:
            if keep_browser:
                # Detach the driver so worker.shutdown won't close it.
                self._kept_driver = self._worker.take_driver()
            self._worker.shutdown(close_browser=False)
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._worker = None
        self._thread = None
        if self._state not in ("error", "finished", "success"):
            self._apply_state("finished")

    def _close_kept_browser(self) -> None:
        if self._kept_driver is not None:
            try:
                self._kept_driver.quit()
            except Exception:
                pass
            self._kept_driver = None

    def shutdown(self) -> None:
        if self._worker is not None:
            self._worker.request_stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        # Clean up the post-success Chrome too so it doesn't outlive the app.
        self._close_kept_browser()
