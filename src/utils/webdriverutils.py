from typing import Self, Optional, Type, List
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import NoSuchElementException, NoAlertPresentException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
import time
from PIL import ImageFile, Image
import requests
from io import BytesIO

WebRoot = Type[WebDriver | WebElement]

class WebDriverUtils:
    _instance: Optional[Self] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _sleep(self) -> None:
        time.sleep(0.01)

    def find_element(
        self, root: WebRoot, by: str = By.ID, value: str | None = None
    ) -> Optional[WebElement]:
        try:
            return root.find_element(by, value)
        except NoSuchElementException:
            return None

    def find_elements(
        self, root: WebRoot, by: str = By.ID, value: str | None = None
    ) -> Optional[List[WebElement]]:
        try:
            return root.find_elements(by, value)
        except NoSuchElementException:
            return None

    def wait_element_visible(
        self, root: WebRoot, by: str = By.ID, value: str | None = None
    ) -> WebElement:
        element = self.find_element(root, by, value)
        while element is None:
            self._sleep()
            element = self.find_element(root, by, value)
        return element

    def wait_element_invisible(self, root: WebRoot, by: str = By.ID, value: str | None = None) -> None:
        element = self.find_element(root, by, value)
        while element is not None:
            self._sleep()
            element = self.find_element(root, by, value)

    def wait_elements_visible(
        self, root: WebRoot, by: str = By.ID, value: str | None = None
    ) -> List[WebElement]:
        elements = self.find_elements(root, by, value)
        while len(elements) == 0:
            self._sleep()
            elements = self.find_elements(root, by, value)
        return elements

    def scrollToElement(self, driver: WebDriver, element: WebElement) -> None:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", element
        )
        while True:
            self._sleep()
            if element.is_displayed(): break
    
    def element_click(self, driver: WebDriver, element: WebElement) -> None:
        self.scrollToElement(driver, element)
        element.click()

    def wait_url_change(self, driver: WebDriver, prev_url: str) -> None:
        while driver.current_url == prev_url:
            self._sleep()
    
    def wait_url_is_equal(self, driver: WebDriver, url: str) -> None:
        while driver.current_url != url:
            self._sleep()
                
    def wait_url_is_not_equal(self, driver: WebDriver, url: str) -> None:
        while driver.current_url == url:
            self._sleep()

    def get_same_session_image_by_url(self, driver: WebDriver, img_url: str) -> ImageFile:
        requests_cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
        img_data = BytesIO(requests.get(img_url, cookies=requests_cookies).content)
        return Image.open(img_data)

    def get_alert(self, driver: WebDriver) -> Optional[Alert]:
        try:
            return driver.switch_to.alert
        except NoAlertPresentException:
            return None