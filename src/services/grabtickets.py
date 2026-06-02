from __future__ import annotations
from typing import Optional, Tuple, List, Callable
from typing_extensions import Self
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from PIL.Image import Image
from threading import Event
from datetime import datetime
import random
import time

from . import datacenter
from ..utils import logutils, webdriverutils, smtputils, ocrutils


class OrderNowButtonNotFoundException(Exception):
    pass


class StopRequested(Exception):
    pass


# (image, attempt_index) -> code typed by user; returning None aborts.
ManualCaptchaCallback = Callable[[Image, int], Optional[str]]
# (current_url, hint_text) -> True if user clicked "繼續", False to abort.
ManualResumeCallback = Callable[[str, str], bool]
StatusCallback = Callable[[str], None]


class GrabTickets:
    _instance: Optional[Self] = None

    _log_utils = logutils.LogUtils()
    _web_driver_utils = webdriverutils.WebDriverUtils()
    _smtp_utils = smtputils.SMTPUtils()
    _ocr_utils = ocrutils.OcrUtils()

    MAX_OCR_RETRIES = 30           # how many CAPTCHA images to OCR before giving up
    MAX_CAPTCHA_SUBMIT_RETRIES = 6
    MAX_RESTART_RETRIES = 30
    CAPTCHA_REFRESH_TIMEOUT_SEC = 1.0  # max wait for refreshed image to fully load

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._stop_event = None
            cls._instance._manual_captcha_cb = None
            cls._instance._manual_resume_cb = None
            cls._instance._status_cb = None
        return cls._instance

    # ------------------------------------------------------------------
    # GUI hooks
    # ------------------------------------------------------------------

    def set_stop_event(self, event: Optional[Event]) -> None:
        self._stop_event = event

    def set_manual_captcha_callback(self, cb: Optional[ManualCaptchaCallback]) -> None:
        self._manual_captcha_cb = cb

    def set_manual_resume_callback(self, cb: Optional[ManualResumeCallback]) -> None:
        self._manual_resume_cb = cb

    def set_status_callback(self, cb: Optional[StatusCallback]) -> None:
        self._status_cb = cb

    def _status(self, text: str) -> None:
        if self._status_cb is not None:
            try:
                self._status_cb(text)
            except Exception:
                pass

    def _check_stop(self) -> None:
        if self._stop_event is not None and self._stop_event.is_set():
            raise StopRequested()

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def start(self, driver: WebDriver, config: datacenter.Config) -> None:
        attempts = 0
        config = dict(config)
        if config.get("sleep") is not None:
            config["sleep"] = dict(config["sleep"])

        try:
            driver.set_window_size(1080, 720)
        except Exception:
            pass

        while True:
            try:
                self._check_stop()
                self._status("前往活動頁")
                self._to_game_page(driver, config)
                self._wait_until_open(driver, config)
                self._game_page_handler(driver, config)
                # Fanclub presale / member verify (e.g. Planet K, ARMY).
                # Only activates when URL is /ticket/verify/...; regular flow skips it.
                self._verify_page_handler(driver, config)
                # Defensive: if we still aren't on the area page, pause and let the
                # user resolve whatever extra step the site inserted.
                self._pause_if_unexpected_page(
                    driver,
                    expected_prefix=f"https://tixcraft.com/ticket/area/{config['game_id']}",
                    hint="頁面非預期, 請在瀏覽器內完成此步驟後按 '繼續'",
                )
                self._area_page_handler(driver, config)
                self._ticket_page_handler(driver, config)
                # After 確認張數 we land on a checkout page that still needs the
                # user (or us) to click "我同意本節目規則, 下一步".
                self._checkout_page_handler(driver, config)

                if not driver.current_url.startswith("https://tixcraft.com/ticket/order"):
                    if driver.current_url.startswith("https://tixcraft.com/login"):
                        raise Exception("被踢回登入頁 (session 失效)")
                    raise Exception(f"未能成功提交購票訂單 (current={driver.current_url})")
                self._status("購票流程完成")
                break

            except StopRequested:
                self._log_utils.info("使用者中止")
                self._status("已停止")
                return
            except OrderNowButtonNotFoundException as e:
                attempts += 1
                self._log_utils.error(repr(e))
                self._status(f"重試 ({attempts})")
                if attempts >= self.MAX_RESTART_RETRIES:
                    self._log_utils.error("超過最大重試次數")
                    return
                for _ in range(3):
                    self._sleep(config)
            except Exception as e:
                attempts += 1
                self._log_utils.error(repr(e))
                self._status(f"重試 ({attempts})")
                if attempts >= self.MAX_RESTART_RETRIES:
                    self._log_utils.error("超過最大重試次數")
                    return
                self._sleep(config)

        self._send_notifications(config)

    def _send_notifications(self, config: datacenter.Config) -> None:
        emails: List[str] = config.get("notification_emails") or []
        if not emails:
            return
        self._log_utils.info("通知完成訊息")
        for email in emails:
            err = self._smtp_utils.send(
                to_email=email,
                subject="搶票系統完成通知",
                text="請開啟 https://tixcraft.com/ticket/order 查看訂單",
            )
            if err is not None:
                self._log_utils.error(f"通知 {email} 失敗: {err!r}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _wait_until_open(self, driver: WebDriver, config: datacenter.Config) -> None:
        when = config.get("open_for_purchase_datetime")
        if not when:
            return
        try:
            target = datetime.strptime(when, "%Y/%m/%d-%H:%M:%S")
        except ValueError:
            self._log_utils.error(f"open_for_purchase_datetime 格式錯誤: {when}")
            return
        self._log_utils.info(f"等待售票開始時間 {when}")
        self._status(f"等待開賣 ({when})")
        while datetime.now() < target:
            self._check_stop()
            time.sleep(0.05)
        self._sleep(config)
        self._to_game_page(driver, config)
        config["open_for_purchase_datetime"] = None

    def _sleep(self, config: datacenter.Config) -> None:
        sleep_cfg = config.get("sleep") or {}
        min_seconds = max(0.0, float(sleep_cfg.get("min_seconds", 0.1)))
        max_seconds = max(min_seconds, float(sleep_cfg.get("max_seconds", 0.3)))
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _to_game_page(self, driver: WebDriver, config: datacenter.Config) -> None:
        self._log_utils.info("獲取活動頁面")
        url = f"https://tixcraft.com/activity/game/{config['game_id']}"
        driver.get(url)
        self._web_driver_utils.wait_url_is_equal(driver, url)

        cookie_reject = self._web_driver_utils.find_element(
            driver, By.XPATH, "//button[@id='onetrust-reject-all-handler']"
        )
        if cookie_reject is not None:
            self._sleep(config)
            try:
                cookie_reject.click()
            except Exception:
                pass

    def _game_page_handler(self, driver: WebDriver, config: datacenter.Config) -> None:
        handler_url = f"https://tixcraft.com/activity/game/{config['game_id']}"
        if driver.current_url != handler_url:
            raise Exception("game_page 處理地址不符合")
        self._log_utils.info("處理活動頁 (選場次)")
        self._status("選擇場次")

        show_time = config.get("show_time_text_contains") or ""
        xpath = (
            "//div[@id='gameList']/table/tbody/tr"
            f"[td[1][contains(normalize-space(text()), '{show_time}')]"
            " and td[4]/button[normalize-space(text())='立即訂購']]"
            "/td[4]/button"
        )
        buttons = self._web_driver_utils.find_elements(driver, By.XPATH, xpath)
        # filter disabled buttons (sold-out sessions sometimes keep the button visible)
        buttons = [b for b in buttons if b.is_enabled()]
        if not buttons:
            raise OrderNowButtonNotFoundException("未找到符合條件且可點擊的 '立即訂購' 按鈕")
        self._sleep(config)
        self._log_utils.info("點擊 '立即訂購'")
        self._web_driver_utils.element_click(driver, buttons[0])
        self._web_driver_utils.wait_url_is_not_equal(driver, handler_url)

    # ------------------------------------------------------------------
    # Member presale / verify page (Planet K, ARMY membership, etc.)
    # ------------------------------------------------------------------

    def _verify_page_handler(self, driver: WebDriver, config: datacenter.Config) -> None:
        verify_prefix = f"https://tixcraft.com/ticket/verify/{config['game_id']}"
        if not driver.current_url.startswith(verify_prefix):
            return  # not a member presale activity; skip

        handler_url = driver.current_url
        self._log_utils.info("偵測到會員預售驗證頁")
        self._status("處理會員驗證")

        presale_code = (config.get("presale_code") or "").strip()
        input_el = self._find_verify_input(driver)
        submit_el = self._find_verify_submit(driver)

        if presale_code and input_el is not None and submit_el is not None:
            self._sleep(config)
            try:
                input_el.clear()
            except Exception:
                pass
            input_el.send_keys(presale_code)
            self._sleep(config)
            self._log_utils.info("送出會員驗證序號")
            self._web_driver_utils.element_click(driver, submit_el)
            self._web_driver_utils.wait_url_is_not_equal(driver, handler_url)
            return

        # No code (or fields look different) → ask the user to handle it manually.
        self._log_utils.warn(
            "未設定預售序號或欄位無法自動處理, 請在瀏覽器內手動完成"
        )
        self._pause_for_manual(
            driver,
            handler_url,
            "請在瀏覽器內輸入會員序號並送出, 完成後按 '繼續'",
        )

    def _find_verify_input(self, driver: WebDriver) -> Optional[WebElement]:
        # Try a few generic selectors; member-presale pages vary slightly per activity.
        for xpath in (
            "//main//form//input[@type='text']",
            "//main//form//input[not(@type) or @type='text' or @type='password']",
            "//form//input[@type='text']",
            "//form//input[not(@type='hidden') and not(@type='submit') and not(@type='button')]",
        ):
            el = self._web_driver_utils.find_element(driver, By.XPATH, xpath)
            if el is not None:
                return el
        return None

    def _find_verify_submit(self, driver: WebDriver) -> Optional[WebElement]:
        for xpath in (
            "//main//form//button[@type='submit']",
            "//main//form//button[contains(normalize-space(.), '送出')]",
            "//form//button[@type='submit']",
            "//form//input[@type='submit']",
        ):
            el = self._web_driver_utils.find_element(driver, By.XPATH, xpath)
            if el is not None:
                return el
        return None

    # ------------------------------------------------------------------
    # Generic pause-and-resume for unexpected intermediate pages
    # ------------------------------------------------------------------

    def _pause_if_unexpected_page(
        self, driver: WebDriver, expected_prefix: str, hint: str
    ) -> None:
        if driver.current_url.startswith(expected_prefix):
            return
        self._log_utils.warn(
            f"目前 URL={driver.current_url}, 不是預期的 {expected_prefix}"
        )
        self._pause_for_manual(driver, driver.current_url, hint)

    def _pause_for_manual(
        self, driver: WebDriver, snapshot_url: str, hint: str
    ) -> None:
        """Block until the user signals 'resume' from the GUI, OR until the URL
        changes (meaning they already finished the step in the browser)."""
        self._status(hint)
        if self._manual_resume_cb is not None:
            ok = self._manual_resume_cb(snapshot_url, hint)
            if not ok:
                raise StopRequested()
        else:
            while driver.current_url == snapshot_url:
                self._check_stop()
                time.sleep(0.3)

    # ------------------------------------------------------------------
    # Area + ticket pages
    # ------------------------------------------------------------------

    def _area_page_handler(self, driver: WebDriver, config: datacenter.Config) -> None:
        prefix = f"https://tixcraft.com/ticket/area/{config['game_id']}"
        if not driver.current_url.startswith(prefix):
            raise Exception("area_page 處理地址不符合")
        handler_url = driver.current_url
        self._log_utils.info("處理票區頁")
        self._status("選擇票區")

        raw = (config.get("area_price_text_contains") or "").strip()
        keywords = [k.strip().replace("'", "") for k in raw.replace("、", ",").split(",")]
        keywords = [k for k in keywords if k]
        if not keywords:
            keywords = [""]  # match all areas

        anchors: List[WebElement] = []
        seen_texts = set()
        for kw in keywords:
            found = self._web_driver_utils.find_elements(
                driver, By.XPATH,
                f"//div[contains(@class, 'area-list')]//a[contains(text(), '{kw}')]",
            )
            for el in found:
                try:
                    key = el.text.strip()
                except Exception:
                    key = id(el)
                if key not in seen_texts:
                    seen_texts.add(key)
                    anchors.append(el)

        def parse_remainder(element: WebElement) -> Optional[Tuple[int, WebElement]]:
            try:
                font_text = element.find_element(By.XPATH, "./font").text.strip()
            except Exception:
                return None
            if font_text == "熱賣中":
                return (100, element)
            parts = font_text.split(" ")
            if len(parts) < 2 or not parts[1].isdigit():
                return None
            return (int(parts[1]), element)

        options = [opt for opt in (parse_remainder(a) for a in anchors) if opt is not None]
        need = int(config.get("number_of_ticket", 1))
        options = [opt for opt in options if opt[0] >= need]
        if not options:
            raise Exception(
                f"未找到符合「{raw or '任何價位'}」且剩 {need} 張以上的區域 "
                f"(關鍵字: {keywords})"
            )

        max_remainder = max(opt[0] for opt in options)
        best = [opt for opt in options if opt[0] == max_remainder]
        _, anchor = random.choice(best)

        self._sleep(config)
        self._log_utils.info(f"點擊購買選項 ({anchor.text.strip()})")
        self._web_driver_utils.element_click(driver, anchor)
        self._web_driver_utils.wait_url_is_not_equal(driver, handler_url)

    def _checkout_page_handler(self, driver: WebDriver, config: datacenter.Config) -> None:
        """Final confirmation page that appears after 確認張數. It lists the
        chosen tickets, payment + delivery method, and waits for the user to
        accept the activity-specific terms. Auto-click '我同意本節目規則, 下一步'."""
        # Wait up to a few seconds for the navigation triggered by 確認張數.
        for _ in range(50):
            if driver.current_url.startswith("https://tixcraft.com/ticket/checkout"):
                break
            self._check_stop()
            time.sleep(0.1)
        if not driver.current_url.startswith("https://tixcraft.com/ticket/checkout"):
            # Either we're already past it (order page) or somewhere else; let
            # the outer URL check decide.
            return

        handler_url = driver.current_url
        self._log_utils.info("處理訂單確認頁")
        self._status("確認訂單")

        # The agree-and-next button text varies slightly per activity.
        button = None
        for xpath in (
            "//button[contains(normalize-space(.), '我同意本節目規則')]",
            "//button[contains(normalize-space(.), '同意') and contains(normalize-space(.), '下一步')]",
            "//button[contains(normalize-space(.), '下一步')]",
            "//form//button[@type='submit']",
        ):
            button = self._web_driver_utils.find_element(driver, By.XPATH, xpath)
            if button is not None and button.is_enabled():
                break
            button = None

        if button is None:
            self._log_utils.warn("未找到 '我同意本節目規則, 下一步' 按鈕, 請手動點擊後按繼續")
            self._pause_for_manual(
                driver, handler_url,
                "請在瀏覽器內點擊 '我同意本節目規則, 下一步', 完成後按 '繼續'",
            )
            return

        self._sleep(config)
        self._log_utils.info("點擊 '我同意本節目規則, 下一步'")
        self._web_driver_utils.element_click(driver, button)
        self._web_driver_utils.wait_url_is_not_equal(driver, handler_url)

    def _ticket_page_handler(self, driver: WebDriver, config: datacenter.Config) -> None:
        prefix = f"https://tixcraft.com/ticket/ticket/{config['game_id']}"
        if not driver.current_url.startswith(prefix):
            raise Exception("ticket_page 處理地址不符合")
        self._log_utils.info("處理結帳頁")
        self._status("填寫票數與驗證碼")

        for attempt in range(1, self.MAX_CAPTCHA_SUBMIT_RETRIES + 1):
            self._check_stop()
            self._fill_ticket_count(driver, config)

            code = self._resolve_captcha(driver, config)
            if code is None:
                raise StopRequested()

            code_input = self._web_driver_utils.wait_element_visible(
                driver, By.XPATH,
                "//form[@id='form-ticket-ticket']//input[@id='TicketForm_verifyCode']",
            )
            self._sleep(config)
            try:
                code_input.clear()
            except Exception:
                pass
            code_input.send_keys(code)

            agree = self._web_driver_utils.wait_element_visible(
                driver, By.XPATH,
                "//form[@id='form-ticket-ticket']//input[@id='TicketForm_agree']",
            )
            if not agree.is_selected():
                self._sleep(config)
                self._web_driver_utils.element_click(driver, agree)

            submit = self._web_driver_utils.wait_element_visible(
                driver, By.XPATH,
                "//form[@id='form-ticket-ticket']//button[@type='submit']",
            )
            self._sleep(config)
            self._log_utils.info(f"點擊 '確認張數' (attempt {attempt})")
            self._web_driver_utils.element_click(driver, submit)

            time.sleep(0.15)
            alert = self._web_driver_utils.get_alert(driver)
            if alert is None:
                return
            self._log_utils.info("驗證碼錯誤, 重試")
            try:
                alert.accept()
            except Exception:
                pass
            self._sleep(config)

        raise Exception("驗證碼連續錯誤過多次")

    def _fill_ticket_count(self, driver: WebDriver, config: datacenter.Config) -> None:
        selects = self._web_driver_utils.find_elements(
            driver, By.XPATH,
            "//form[@id='form-ticket-ticket']//table[@id='ticketPriceList']//select",
        )
        self._sleep(config)
        want = int(config.get("number_of_ticket", 1))
        for tag in selects:
            driver.execute_script(
                "var opts = arguments[0].options;"
                "var target = Math.min(arguments[1], opts.length - 1);"
                "arguments[0].selectedIndex = target;"
                "arguments[0].dispatchEvent(new Event('change'));",
                tag, want,
            )

    # ------------------------------------------------------------------
    # CAPTCHA
    # ------------------------------------------------------------------

    _CAPTCHA_XPATH = (
        "//form[@id='form-ticket-ticket']"
        "//img[@id='TicketForm_verifyCode-image']"
    )

    def _wait_for_new_captcha(
        self,
        driver: WebDriver,
        old_src: Optional[str],
        timeout: float,
    ) -> Optional[WebElement]:
        """Block until the captcha image has a NEW src AND is fully loaded.
        Returns the (possibly re-found) <img> element, or None on timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            img_tag = self._web_driver_utils.find_element(
                driver, By.XPATH, self._CAPTCHA_XPATH
            )
            if img_tag is None:
                time.sleep(0.02)
                continue
            try:
                cur_src = img_tag.get_attribute("src")
                if old_src is None or (cur_src and cur_src != old_src):
                    loaded = driver.execute_script(
                        "return arguments[0].complete "
                        "&& arguments[0].naturalWidth > 0;",
                        img_tag,
                    )
                    if loaded:
                        return img_tag
            except Exception:
                pass
            time.sleep(0.02)
        return None

    def _resolve_captcha(
        self, driver: WebDriver, config: datacenter.Config
    ) -> Optional[str]:
        """OCR the CAPTCHA, refreshing and waiting for the new image to fully
        load before retrying. No manual fallback."""
        prev_src: Optional[str] = None
        for attempt in range(self.MAX_OCR_RETRIES):
            self._check_stop()
            img_tag = self._wait_for_new_captcha(
                driver, prev_src, self.CAPTCHA_REFRESH_TIMEOUT_SEC
            )
            if img_tag is None:
                # Didn't see a new image — re-find whatever is there now.
                img_tag = self._web_driver_utils.find_element(
                    driver, By.XPATH, self._CAPTCHA_XPATH
                )
                if img_tag is None:
                    return None
            try:
                cur_src = img_tag.get_attribute("src")
                img = self._web_driver_utils.get_image_from_element(driver, img_tag)
            except Exception as e:
                self._log_utils.warn(f"驗證碼圖片讀取失敗: {e!r}")
                time.sleep(0.1)
                continue

            code = self._ocr_utils.read_code(img)
            if code is not None and len(code) == 4 and code.isalnum():
                if attempt > 0:
                    self._log_utils.info(f"OCR 辨識: {code} (第 {attempt + 1} 次)")
                else:
                    self._log_utils.info(f"OCR 辨識: {code}")
                return code

            # Trigger a refresh; next iteration waits for the new image.
            prev_src = cur_src
            try:
                self._web_driver_utils.element_click(driver, img_tag)
            except Exception:
                pass

        self._log_utils.error(f"OCR 連續失敗 {self.MAX_OCR_RETRIES} 次")
        return None
