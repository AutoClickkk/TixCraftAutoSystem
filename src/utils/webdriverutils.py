from __future__ import annotations
from typing import Optional, Type, List, Union
from typing_extensions import Self
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import NoSuchElementException, NoAlertPresentException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
import base64
import time
from PIL import Image
from PIL.ImageFile import ImageFile
import requests
from io import BytesIO


WebRoot = Union[WebDriver, WebElement]


class WebDriverUtils:
    _instance: Optional[Self] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _sleep(self) -> None:
        time.sleep(0.01)

    def find_element(
        self, root: WebRoot, by: str = By.ID, value: Optional[str] = None
    ) -> Optional[WebElement]:
        try:
            return root.find_element(by, value)
        except NoSuchElementException:
            return None

    def find_elements(
        self, root: WebRoot, by: str = By.ID, value: Optional[str] = None
    ) -> List[WebElement]:
        # Selenium's find_elements returns [] when nothing matches; never None.
        return root.find_elements(by, value)

    def wait_element_visible(
        self, root: WebRoot, by: str = By.ID, value: Optional[str] = None
    ) -> WebElement:
        element = self.find_element(root, by, value)
        while element is None:
            self._sleep()
            element = self.find_element(root, by, value)
        return element

    def wait_element_invisible(
        self, root: WebRoot, by: str = By.ID, value: Optional[str] = None
    ) -> None:
        element = self.find_element(root, by, value)
        while element is not None:
            self._sleep()
            element = self.find_element(root, by, value)

    def wait_elements_visible(
        self, root: WebRoot, by: str = By.ID, value: Optional[str] = None
    ) -> List[WebElement]:
        elements = self.find_elements(root, by, value)
        while len(elements) == 0:
            self._sleep()
            elements = self.find_elements(root, by, value)
        return elements

    def scroll_to_element(self, driver: WebDriver, element: WebElement) -> None:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
            element,
        )
        while not element.is_displayed():
            self._sleep()

    def element_click(self, driver: WebDriver, element: WebElement) -> None:
        self.scroll_to_element(driver, element)
        element.click()

    # legacy camelCase alias kept for any external callers
    scrollToElement = scroll_to_element

    def wait_url_change(self, driver: WebDriver, prev_url: str) -> None:
        while driver.current_url == prev_url:
            self._sleep()

    def wait_url_is_equal(self, driver: WebDriver, url: str) -> None:
        while driver.current_url != url:
            self._sleep()

    def wait_url_is_not_equal(self, driver: WebDriver, url: str) -> None:
        while driver.current_url == url:
            self._sleep()

    def get_same_session_image_by_url(
        self, driver: WebDriver, img_url: str
    ) -> ImageFile:
        """Re-fetch a URL using the browser's cookies. Often blocked by sites
        that check User-Agent / Referer — prefer get_image_from_element()."""
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        ua = driver.execute_script("return navigator.userAgent;")
        headers = {
            "User-Agent": ua,
            "Referer": driver.current_url,
            "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8",
        }
        response = requests.get(img_url, cookies=cookies, headers=headers, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))

    def get_image_from_element(
        self, driver: WebDriver, img_element: WebElement
    ) -> ImageFile:
        """Read the already-rendered <img> via a canvas so we don't have to
        re-fetch the URL. Avoids 403 from CDN-side header checks."""
        data_url = driver.execute_script(
            """
            const img = arguments[0];
            const w = img.naturalWidth || img.width;
            const h = img.naturalHeight || img.height;
            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, w, h);
            return canvas.toDataURL('image/png');
            """,
            img_element,
        )
        if not data_url or "," not in data_url:
            raise RuntimeError("canvas.toDataURL returned empty result")
        b64 = data_url.split(",", 1)[1]
        return Image.open(BytesIO(base64.b64decode(b64)))

    def get_alert(self, driver: WebDriver) -> Optional[Alert]:
        try:
            return driver.switch_to.alert
        except NoAlertPresentException:
            return None
