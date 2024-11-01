from typing import Optional, Self, Tuple, List
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from . import datacenter
from ..utils import logutils, webdriverutils, smtputils, ocrutils
import time
import random
from datetime import datetime

class OrderNowButtonNotFoundException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class GrabTickets:
    _instance: Optional[Self] = None

    # utils
    _log_utils = logutils.LogUtils()
    _web_driver_utils = webdriverutils.WebDriverUtils()
    _smtp_utils = smtputils.SMTPUtils()
    _ocr_utils = ocrutils.OcrUtils()

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def start(self, driver: WebDriver, config: datacenter.Config) -> None:
        self._to_game_page(driver, config)
        # 等待售票開始時間
        if config["open_for_purchase_datetime"] is not None:
            self._log_utils.info("等待售票開始時間")
            open_for_purchase_datetime = datetime.strptime(config["open_for_purchase_datetime"], "%Y/%m/%d-%H:%M:%S")
            while datetime.now() < open_for_purchase_datetime:
                time.sleep(0.1)
            self._sleep(config)
            self._to_game_page(driver, config)
            config["open_for_purchase_datetime"] = None

        # 開始
        try:
            self._game_page_handler(driver, config)
            self._area_page_handler(driver, config)
            self._ticket_page_handler(driver, config)
            if driver.current_url not in [
                "https://tixcraft.com/ticket/order",
                "https://tixcraft.com/ticket/checkout",
                "https://tixcraft.com/login"
            ]:
                raise Exception("未能成功提交購票訂單")
            
        except OrderNowButtonNotFoundException as e:
            self._log_utils.error(e.__repr__())
            self._sleep(config)
            self._sleep(config)
            self._sleep(config)
            self.start(driver, config)
        except Exception as e: 
            self._log_utils.error(e.__repr__())
            self._sleep(config)
            self.start(driver, config)

        # 通知信箱
        self._log_utils.info("通知完成訊息")
        notification_emails: List[str] = config["notification_emails"] if config["notification_emails"] is not None else []
        for email in notification_emails:
            try:
                self._smtp_utils.send("xxx@gmail.com", email, "搶票系統完成通知", "https://tixcraft.com/order")
            except Exception as e:
                self._log_utils.error(e.__repr__())

    def _sleep(self, config: datacenter.Config) -> None:
        max_seconds = min(1.0, config["sleep"]["max_seconds"]) 
        min_seconds = max(0.0, config["sleep"]["min_seconds"])
        sleep_seconds = random.random()
        sleep_seconds = max(sleep_seconds, min_seconds)
        sleep_seconds = min(sleep_seconds, max_seconds)
        time.sleep(sleep_seconds)
    

    def _to_game_page(self, driver: WebDriver, config: datacenter.Config) -> None:
        driver.set_window_size(1080, 610)
        self._log_utils.info("獲取 game_page 頁面")
        game_page_url = f"https://tixcraft.com/activity/game/{config['game_id']}"
        driver.get(game_page_url)
        self._web_driver_utils.wait_url_is_equal(driver, game_page_url)

        # 關閉 cookie 要求
        cookie_reject_all_btn = self._web_driver_utils.find_element(driver, By.XPATH, "//button[@id='onetrust-reject-all-handler']")
        if cookie_reject_all_btn is not None:
            self._sleep(config)
            cookie_reject_all_btn.click()


    def _ticket_page_handler(self, driver: WebDriver, config: datacenter.Config) -> None:
        handler_url_prefix = f"https://tixcraft.com/ticket/ticket/{config['game_id']}"
        if not driver.current_url.startswith(handler_url_prefix):
            raise Exception("ticket_page 處理地址不符合")
        handler_url = driver.current_url
        self._log_utils.info("開始處理 ticket_page 邏輯")

        # 選擇票數
        ticket_select_tags = self._web_driver_utils.find_elements(driver, By.XPATH, "//form[@id='form-ticket-ticket']//table[@id='ticketPriceList']//select") 
        self._sleep(config)
        for select_tag in ticket_select_tags:
            driver.execute_script(
                f"arguments[0].selectedIndex={config['number_of_ticket']}; arguments[0].dispatchEvent(new Event('change'))",
                select_tag,
            )
        
        # 輸入驗證碼
        def get_code() -> str:
            code_img_tag = self._web_driver_utils.find_element(driver, By.XPATH, "//form[@id='form-ticket-ticket']//img[@id='TicketForm_verifyCode-image']")
            code_img = self._web_driver_utils.get_same_session_image_by_url(driver, code_img_tag.get_attribute("src"))
            code = self._ocr_utils.read_code(code_img)
            if (code is None) or (len(code) != 4):
                self._web_driver_utils.element_click(driver, code_img_tag)
                self._sleep(config)
                return get_code()
            else:
                return code
        code = get_code()
        code_input_tag = self._web_driver_utils.find_element(driver, By.XPATH, "//form[@id='form-ticket-ticket']//input[@id='TicketForm_verifyCode']")
        self._sleep(config)
        code_input_tag.send_keys(code)

        # 同意條款
        agree_checkbox_tag = self._web_driver_utils.find_element(driver, By.XPATH, "//form[@id='form-ticket-ticket']//input[@id='TicketForm_agree']")
        self._sleep(config)
        self._web_driver_utils.element_click(driver, agree_checkbox_tag)

        # 提交表單
        submit_button_tag = self._web_driver_utils.find_element(driver, By.XPATH, "//form[@id='form-ticket-ticket']//button[@type='submit']")
        self._sleep(config)
        self._log_utils.info("點擊 '確認張數' 按鈕")
        self._web_driver_utils.element_click(driver, submit_button_tag)
        
        # 檢查是否成功
        time.sleep(0.1)
        code_error_alert = self._web_driver_utils.get_alert(driver)
        if code_error_alert is not None:
            self._log_utils.info("驗證碼輸入錯誤")
            self._sleep(config)
            code_error_alert.accept()
            self._ticket_page_handler(driver, config)


    def _area_page_handler(self, driver: WebDriver, config: datacenter.Config) -> None:
        handler_url_prefix = f"https://tixcraft.com/ticket/area/{config['game_id']}"
        if not driver.current_url.startswith(handler_url_prefix):
            raise Exception("area_page 處理地址不符合")
        handler_url = driver.current_url
        self._log_utils.info("開始處理 area_page 邏輯")

        area_price_text_contains = config["area_price_text_contains"] if config["area_price_text_contains"] is not None else ""
        area_a_tags = self._web_driver_utils.find_elements(driver, By.XPATH, f"//div[contains(@class, 'area-list')]//a[contains(text(), '{area_price_text_contains}')]")
        def parse_remainder(element: WebElement) -> Tuple[int, WebElement]:
            font_text = element.find_element(By.XPATH, "./font").text.strip()
            if font_text == "熱賣中":
                return (100, element)
            else:
                return (int(font_text.split(" ")[1]), element) 
        area_options: List[Tuple[int, WebElement]] = [parse_remainder(element) for element in area_a_tags]

        # self._log_utils.info("過濾出符合最小需求票數項目")
        area_options = list(filter(lambda option: option[0] >= config["number_of_ticket"], area_options))
        area_options_len = len(area_options)
        if area_options_len == 0:
            raise Exception("未找到符合價位項目")
        
        # self._log_utils.info("找出符合條件中，剩餘票數最多的項目")
        max_remainder_area_option = max(area_options, key=lambda option: option[0])
        max_remainder_area_options = list(filter(lambda option: option[0] == max_remainder_area_option[0], area_options))
        choice_area_option = random.choice(max_remainder_area_options)

        
        self._sleep(config)
        _, area_a_tag = choice_area_option
        self._log_utils.info(f"點擊購買選項({area_a_tag.text.strip()})")
        self._web_driver_utils.element_click(driver, area_a_tag)
        self._web_driver_utils.wait_url_is_not_equal(driver, handler_url)


    def _game_page_handler(self, driver: WebDriver, config: datacenter.Config) -> None:
        handler_url = f"https://tixcraft.com/activity/game/{config['game_id']}"
        if driver.current_url != handler_url:
            raise Exception("game_page 處理地址不符合")
        self._log_utils.info("開始處理 game_page 邏輯")

        show_time_text_contains = config["show_time_text_contains"] if config["show_time_text_contains"] is not None else ""
        order_now_buttons = self._web_driver_utils.find_elements(driver, By.XPATH, f"//div[@id='gameList']/table/tbody/tr[td[1][contains(normalize-space(text()), '{show_time_text_contains}')] and td[4]/button[normalize-space(text())='立即訂購']]/td[4]/button")
        if len(order_now_buttons) == 0:
            raise OrderNowButtonNotFoundException("未找到符合條件 '立即訂購' 按鈕")
        
        order_now_button = order_now_buttons[0]
        self._sleep(config)
        self._log_utils.info("點擊 '立即訂購' 按鈕")
        self._web_driver_utils.element_click(driver, order_now_button)
        self._web_driver_utils.wait_url_is_not_equal(driver, handler_url)
