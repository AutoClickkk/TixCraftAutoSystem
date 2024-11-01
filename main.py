from src.services import datacenter, grabtickets
from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.remote.webdriver import WebDriver

data_center = datacenter.DataCenter()
grab_tickets = grabtickets.GrabTickets()

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_web_deriver(config: datacenter.Config) -> WebDriver:
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager(driver_version="130.0.6723.92").install()), options=options)
    return driver

def main() -> None:
    config = data_center.get_config()
    driver = get_web_deriver(config)
    login_page_url = "https://tixcraft.com/login"
    driver.get(login_page_url)
    input("請完成登入後，按下 'Enter' 開始執行程序")

    # 操作執行
    operate = 'r'
    while True:
        match(operate):
            case 'r':
                grab_tickets.start(driver, config)
            case 'q':
                break
        operate = input((
            "輸入'q'中止程序\n"
            "輸入'r'再次嘗試\n"
            ":"
        )).strip()
    
    # 關閉 driver
    driver.quit()


if __name__ == "__main__":
    main()