from __future__ import annotations
import sys
from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QDialog

from dotenv import load_dotenv

from ..utils import paths
from .theme import STYLESHEET
from .main_window import MainWindow
from .widgets.auth_dialog import AuthDialog
from .widgets.update_dialog import UpdateDialog
from .workers import UpdateCheckWorker


def _load_app_icon() -> QIcon:
    """Resolve the bundled icon.png; works in dev tree and PyInstaller frozen mode."""
    candidates = [
        paths.bundle_dir() / "icon.png",
        paths.bundle_dir() / "build" / "icons" / "icon.png",
    ]
    for p in candidates:
        if p.exists():
            return QIcon(str(p))
    return QIcon()


def run() -> int:
    load_dotenv(paths.env_path())

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("準點搶")
    app.setOrganizationName("準點搶")
    app.setApplicationDisplayName("準點搶")
    icon = _load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    app.setStyleSheet(STYLESHEET)

    font = QFont()
    font.setPointSize(13)
    app.setFont(font)

    auth = AuthDialog()
    if auth.exec() != QDialog.Accepted:
        return 0

    window = MainWindow()
    window.show()

    # Background update check; if a newer release exists, show modal dialog.
    _schedule_update_check(window)
    # Pre-warm the OCR model in background so the first CAPTCHA isn't a 2-3s wait.
    _prewarm_ocr()

    return app.exec()


def _prewarm_ocr() -> None:
    """Load ddddocr's ONNX model + run a dummy inference on a background
    thread, so the first real CAPTCHA arrives with a hot model."""
    import threading

    def worker():
        try:
            from PIL import Image
            from ..utils.ocrutils import OcrUtils
            OcrUtils().read_code(Image.new("RGB", (120, 50), "white"))
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True, name="ocr-warmup").start()


def _schedule_update_check(window: MainWindow) -> None:
    """Spawn a one-shot worker thread that checks GitHub for a newer release.
    Runs once per app launch — declining the dialog still re-prompts next time."""
    state = {"thread": None, "worker": None}

    def on_done(info) -> None:
        try:
            if state["thread"] is not None:
                state["thread"].quit()
                state["thread"].wait(2000)
        except Exception:
            pass
        state["thread"] = None
        state["worker"] = None
        if info is None or not getattr(info, "has_update", False):
            return
        dlg = UpdateDialog(info, parent=window)
        dlg.exec()

    def kick() -> None:
        worker = UpdateCheckWorker()
        thread = QThread(window)
        worker.moveToThread(thread)
        worker.finished.connect(on_done)
        thread.started.connect(worker.run)
        thread.start()
        state["worker"] = worker
        state["thread"] = thread

    # Defer 1s so the main window finishes drawing first.
    QTimer.singleShot(1000, kick)
