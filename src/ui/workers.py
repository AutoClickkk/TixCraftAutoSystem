from __future__ import annotations
from typing import Optional
from threading import Event
import io
import time

from PySide6.QtCore import QObject, Signal
from PIL.Image import Image

from ..services.datacenter import Config
from ..services.grabtickets import GrabTickets, StopRequested
from ..services.updater import check_for_update, UpdateInfo
from ..utils.driver_factory import create_chrome_driver
from ..utils import logutils


class LogBridge(QObject):
    """Hooks LogUtils handler -> Qt signal so log lines arrive on the GUI thread."""

    line = Signal(str, str)  # (level, formatted_line)

    def __init__(self) -> None:
        super().__init__()
        self._log = logutils.LogUtils()
        self._log.add_handler(self._emit)

    def _emit(self, level: str, line: str) -> None:
        self.line.emit(level, line)

    def detach(self) -> None:
        self._log.remove_handler(self._emit)


class CaptchaRequest(QObject):
    """Worker-side handle that blocks until the GUI returns a code."""

    requested = Signal(bytes)  # PNG bytes

    def __init__(self) -> None:
        super().__init__()
        self._answer: Optional[str] = None
        self._event = Event()

    def ask(self, image: Image) -> Optional[str]:
        self._answer = None
        self._event.clear()
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        self.requested.emit(buf.getvalue())
        self._event.wait()
        return self._answer

    def respond(self, code: Optional[str]) -> None:
        self._answer = code
        self._event.set()


class ResumeRequest(QObject):
    """Worker-side handle that blocks until the user clicks '繼續' or '取消'."""

    requested = Signal(str, str)  # (current_url, hint_text)

    def __init__(self) -> None:
        super().__init__()
        self._ok: bool = False
        self._event = Event()

    def ask(self, current_url: str, hint: str) -> bool:
        self._ok = False
        self._event.clear()
        self.requested.emit(current_url, hint)
        self._event.wait()
        return self._ok

    def respond(self, ok: bool) -> None:
        self._ok = ok
        self._event.set()


class RunWorker(QObject):
    """QThread workload: open browser, wait for user login, then run grab loop."""

    log_line = Signal(str, str)
    status_changed = Signal(str)
    state_changed = Signal(str)  # "starting", "ready", "running", "paused", "finished", "success", "error"
    finished = Signal()
    success = Signal()
    error = Signal(str)
    captcha_requested = Signal(bytes)
    resume_requested = Signal(str, str)  # (url, hint)

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        self._stop_event = Event()
        self._login_done = Event()
        self._captcha = CaptchaRequest()
        self._captcha.requested.connect(self.captcha_requested)
        self._resume = ResumeRequest()
        self._resume.requested.connect(self.resume_requested)
        self._driver = None

    def request_stop(self) -> None:
        self._stop_event.set()
        self._login_done.set()
        self._captcha.respond(None)
        self._resume.respond(False)

    def signal_login_complete(self) -> None:
        self._login_done.set()

    def submit_captcha(self, code: Optional[str]) -> None:
        self._captcha.respond(code)

    def submit_resume(self, ok: bool) -> None:
        self._resume.respond(ok)

    def run(self) -> None:
        bridge = LogBridge()
        bridge.line.connect(self.log_line)
        log = logutils.LogUtils()

        try:
            self.state_changed.emit("starting")
            self.status_changed.emit("啟動瀏覽器")
            log.info("啟動 Chrome (首次執行會自動下載 chromedriver)")
            self._driver = create_chrome_driver(headless=False)
            self._driver.get("https://tixcraft.com/login")

            self.state_changed.emit("ready")
            self.status_changed.emit("等待登入 → 完成後請按 '開始搶票'")
            log.info("已開啟登入頁，請登入後回到本視窗按 '開始搶票'")

            while not self._login_done.is_set():
                if self._stop_event.is_set():
                    log.info("使用者中止")
                    self.state_changed.emit("finished")
                    self.finished.emit()
                    return
                time.sleep(0.1)

            if self._stop_event.is_set():
                self.state_changed.emit("finished")
                self.finished.emit()
                return

            def on_resume(url: str, hint: str) -> bool:
                self.state_changed.emit("paused")
                ok = self._resume.ask(url, hint)
                self.state_changed.emit("running")
                return ok

            grab = GrabTickets()
            grab.set_stop_event(self._stop_event)
            grab.set_status_callback(self.status_changed.emit)
            grab.set_manual_resume_callback(on_resume)
            # Manual CAPTCHA callback intentionally NOT wired — OCR will keep
            # retrying until it solves the puzzle or hits the attempt cap.

            self.state_changed.emit("running")
            grab.start(self._driver, self._config)
            # If grab.start returned cleanly AND we're on the order page → success.
            try:
                url = self._driver.current_url if self._driver else ""
            except Exception:
                url = ""
            if url.startswith("https://tixcraft.com/ticket/order"):
                self.state_changed.emit("success")
                self.success.emit()
            else:
                self.state_changed.emit("finished")

        except StopRequested:
            log.info("使用者中止")
            self.state_changed.emit("finished")
        except Exception as e:
            log.error(f"執行錯誤: {e!r}")
            self.state_changed.emit("error")
            self.error.emit(str(e))
        finally:
            bridge.detach()
            self.finished.emit()

    def shutdown(self, close_browser: bool = True) -> None:
        if close_browser:
            try:
                if self._driver is not None:
                    self._driver.quit()
            except Exception:
                pass
        self._driver = None

    def take_driver(self):
        """Detach the driver reference so shutdown() won't quit it.
        Caller becomes responsible for the driver's lifecycle."""
        d = self._driver
        self._driver = None
        return d


class UpdateCheckWorker(QObject):
    finished = Signal(object)  # UpdateInfo

    def run(self) -> None:
        info: UpdateInfo = check_for_update()
        self.finished.emit(info)
