from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import os

from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QCheckBox,
    QPlainTextEdit, QPushButton, QFrame, QScrollArea, QMessageBox,
)

from ...services.datacenter import DataCenter, Config
from ...utils import paths


def _card(title: str, hint: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(10)
    title_label = QLabel(title)
    title_label.setObjectName("h2")
    layout.addWidget(title_label)
    if hint:
        hint_label = QLabel(hint)
        hint_label.setObjectName("hint")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
    return frame, layout


class ConfigPage(QWidget):
    saved = Signal()

    def __init__(self, data_center: DataCenter, parent=None) -> None:
        super().__init__(parent)
        self._dc = data_center

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("設定")
        title.setObjectName("h1")
        sub = QLabel("修改完按下方「儲存設定」才會生效")
        sub.setObjectName("hint")
        col = QVBoxLayout()
        col.addWidget(title)
        col.addWidget(sub)
        header.addLayout(col)
        header.addStretch(1)
        outer.addLayout(header)

        guide = QFrame()
        guide.setObjectName("card")
        guide_layout = QVBoxLayout(guide)
        guide_layout.setContentsMargins(20, 14, 20, 14)
        guide_layout.setSpacing(4)
        gtitle = QLabel("欄位說明")
        gtitle.setObjectName("h2")
        guide_layout.addWidget(gtitle)
        for line in (
            "活動 ID: tixcraft 活動頁網址末段, 例: https://tixcraft.com/activity/game/24_straykids → 填 24_straykids",
            "演出時間關鍵字: 多場次活動才需要; 例 \"2024/11/03 (日) 18:00\" — 程式只會抓含此關鍵字的場次",
            "票區關鍵字: 填「可點擊的區域名稱」, 例 GA-A、2B、搖滾; 多個用逗號 GA-A,GA-B = 任一; 留空 = 不限。注意 NTD 價格通常在類別標題上, 不是可點擊文字, 所以填 3080 常無效",
            "購買票數: 1~8 張; 程式會在票區頁過濾出剩餘票數 ≥ 此值的區域",
            "會員預售序號: 一般售票留空; 只有 Planet K / ARMY 等粉俱樂部預售場次才要填",
            "依排程時間開搶: 整點開賣的場次勾起來; 蹲釋票就不勾, 進入頁面立刻開始嘗試",
            "操作延遲: 模擬人類點擊節奏, 太快可能被 tixcraft 偵測; 預設 0.2~0.5 秒適合大部分情境",
        ):
            l = QLabel(line)
            l.setObjectName("hint")
            l.setWordWrap(True)
            guide_layout.addWidget(l)
        outer.addWidget(guide)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll, 1)

        body = QWidget()
        scroll.setWidget(body)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        body_layout.addWidget(self._build_activity_card())
        body_layout.addWidget(self._build_timing_card())
        body_layout.addWidget(self._build_notification_card())
        body_layout.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        reset_btn = QPushButton("還原")
        reset_btn.setObjectName("ghost")
        reset_btn.clicked.connect(self.reload_from_disk)
        save_btn = QPushButton("儲存設定")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.save_to_disk)
        footer.addWidget(reset_btn)
        footer.addWidget(save_btn)
        outer.addLayout(footer)

        self.reload_from_disk()

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------

    def _build_activity_card(self) -> QFrame:
        frame, layout = _card(
            "活動",
            "在 tixcraft 活動頁面網址 https://tixcraft.com/activity/game/<id> 找到活動 ID。",
        )
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)

        self.game_id_input = QLineEdit()
        self.game_id_input.setPlaceholderText("例如 24_straykids")
        form.addRow("活動 ID", self.game_id_input)

        self.show_time_input = QLineEdit()
        self.show_time_input.setPlaceholderText("留空 = 不限。例如 2024/11/03 (日) 18:00")
        form.addRow("演出時間關鍵字", self.show_time_input)

        self.area_input = QLineEdit()
        self.area_input.setPlaceholderText("區域名稱: GA-A 或 2B; 多個逗號分隔: GA-A,GA-B; 留空=不限")
        form.addRow("票價/區域關鍵字", self.area_input)

        self.ticket_count = QSpinBox()
        self.ticket_count.setRange(1, 8)
        self.ticket_count.setValue(2)
        form.addRow("購買票數", self.ticket_count)

        self.presale_code_input = QLineEdit()
        self.presale_code_input.setPlaceholderText("一般售票留空; 會員預售才填 (Planet K / ARMY 等)")
        form.addRow("會員預售序號", self.presale_code_input)

        layout.addLayout(form)
        return frame

    def _build_timing_card(self) -> QFrame:
        frame, layout = _card(
            "排程與操作節奏",
            "排程時間到了才會開始搶；不勾選的話進入畫面就直接嘗試 (適合蹲釋票)。",
        )

        sched_row = QHBoxLayout()
        self.use_schedule = QCheckBox("依排程時間開搶")
        self.use_schedule.toggled.connect(self._on_schedule_toggle)
        self.schedule_input = QDateTimeEdit()
        self.schedule_input.setCalendarPopup(True)
        self.schedule_input.setDisplayFormat("yyyy/MM/dd HH:mm:ss")
        self.schedule_input.setDateTime(QDateTime.currentDateTime().addDays(1))
        sched_row.addWidget(self.use_schedule)
        sched_row.addWidget(self.schedule_input, 1)
        layout.addLayout(sched_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        grid.addWidget(QLabel("操作最短延遲 (秒)"), 0, 0)
        self.sleep_min = QDoubleSpinBox()
        self.sleep_min.setRange(0.0, 5.0)
        self.sleep_min.setSingleStep(0.05)
        self.sleep_min.setDecimals(2)
        grid.addWidget(self.sleep_min, 0, 1)
        grid.addWidget(QLabel("操作最長延遲 (秒)"), 1, 0)
        self.sleep_max = QDoubleSpinBox()
        self.sleep_max.setRange(0.0, 5.0)
        self.sleep_max.setSingleStep(0.05)
        self.sleep_max.setDecimals(2)
        grid.addWidget(self.sleep_max, 1, 1)
        layout.addLayout(grid)
        return frame

    def _build_notification_card(self) -> QFrame:
        frame, layout = _card(
            "完成通知 (選填)",
            "搶到票後寄信給下列 email。每行一個。需要先設定下方 Gmail 應用程式密碼。",
        )

        self.emails_input = QPlainTextEdit()
        self.emails_input.setPlaceholderText("user1@example.com\nuser2@example.com")
        self.emails_input.setFixedHeight(80)
        layout.addWidget(self.emails_input)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        self.smtp_user = QLineEdit()
        self.smtp_user.setPlaceholderText("your-gmail@gmail.com")
        form.addRow("Gmail 寄件帳號", self.smtp_user)
        self.smtp_pass = QLineEdit()
        self.smtp_pass.setEchoMode(QLineEdit.Password)
        self.smtp_pass.setPlaceholderText("16 碼 App password")
        form.addRow("Gmail 應用程式密碼", self.smtp_pass)
        layout.addLayout(form)

        link = QLabel(
            '提示：到 <a href="https://myaccount.google.com/apppasswords" '
            'style="color:#7aa2f7">myaccount.google.com/apppasswords</a> 建立。'
        )
        link.setOpenExternalLinks(True)
        link.setObjectName("hint")
        layout.addWidget(link)
        return frame

    # ------------------------------------------------------------------
    # State <-> form
    # ------------------------------------------------------------------

    def _on_schedule_toggle(self, on: bool) -> None:
        self.schedule_input.setEnabled(on)

    def reload_from_disk(self) -> None:
        config = self._dc.get_config(reload=True)
        self.game_id_input.setText(str(config.get("game_id") or ""))
        self.show_time_input.setText(str(config.get("show_time_text_contains") or ""))
        self.area_input.setText(str(config.get("area_price_text_contains") or ""))
        self.ticket_count.setValue(int(config.get("number_of_ticket") or 2))
        self.presale_code_input.setText(str(config.get("presale_code") or ""))

        sleep_cfg = config.get("sleep") or {}
        self.sleep_min.setValue(float(sleep_cfg.get("min_seconds", 0.2)))
        self.sleep_max.setValue(float(sleep_cfg.get("max_seconds", 0.5)))

        when = config.get("open_for_purchase_datetime")
        if when:
            try:
                dt = datetime.strptime(when, "%Y/%m/%d-%H:%M:%S")
                self.schedule_input.setDateTime(
                    QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
                )
                self.use_schedule.setChecked(True)
            except ValueError:
                self.use_schedule.setChecked(False)
        else:
            self.use_schedule.setChecked(False)
        self._on_schedule_toggle(self.use_schedule.isChecked())

        emails: List[str] = config.get("notification_emails") or []
        self.emails_input.setPlainText("\n".join(emails))

        env = self._read_env()
        self.smtp_user.setText(env.get("SMTP_LOGIN_USER", ""))
        self.smtp_pass.setText(env.get("SMTP_LOGIN_PASSWORD", ""))

    def collect(self) -> Config:
        emails = [
            line.strip()
            for line in self.emails_input.toPlainText().splitlines()
            if line.strip()
        ]
        when = None
        if self.use_schedule.isChecked():
            dt = self.schedule_input.dateTime().toPython()
            when = dt.strftime("%Y/%m/%d-%H:%M:%S")

        return {
            "game_id": self.game_id_input.text().strip(),
            "show_time_text_contains": self.show_time_input.text().strip() or None,
            "area_price_text_contains": self.area_input.text().strip() or None,
            "number_of_ticket": int(self.ticket_count.value()),
            "presale_code": self.presale_code_input.text().strip() or None,
            "open_for_purchase_datetime": when,
            "sleep": {
                "min_seconds": float(self.sleep_min.value()),
                "max_seconds": float(self.sleep_max.value()),
            },
            "notification_emails": emails or None,
        }

    def save_to_disk(self) -> None:
        config = self.collect()
        if not config["game_id"]:
            QMessageBox.warning(self, "缺少必填欄位", "請填寫活動 ID")
            return
        if config["sleep"]["max_seconds"] < config["sleep"]["min_seconds"]:
            QMessageBox.warning(self, "延遲設定錯誤", "最長延遲不可小於最短延遲")
            return
        self._dc.save(config)

        smtp_user = self.smtp_user.text().strip()
        smtp_pass = self.smtp_pass.text()
        if smtp_user or smtp_pass:
            self._write_env({
                "SMTP_LOGIN_USER": smtp_user,
                "SMTP_LOGIN_PASSWORD": smtp_pass,
            })
            os.environ["SMTP_LOGIN_USER"] = smtp_user
            os.environ["SMTP_LOGIN_PASSWORD"] = smtp_pass

        self.saved.emit()

    # ------------------------------------------------------------------
    # .env helpers
    # ------------------------------------------------------------------

    def _read_env(self) -> Dict[str, str]:
        env_file: Path = paths.env_path()
        out: Dict[str, str] = {}
        if not env_file.exists():
            return out
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
        return out

    def _write_env(self, values: Dict[str, str]) -> None:
        env_file: Path = paths.env_path()
        existing = self._read_env()
        existing.update({k: v for k, v in values.items() if v != ""})
        for k, v in values.items():
            if v == "" and k in existing:
                existing.pop(k, None)
        env_file.parent.mkdir(parents=True, exist_ok=True)
        lines = [f'{k}="{v}"' for k, v in existing.items()]
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
