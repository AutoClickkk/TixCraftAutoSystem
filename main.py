"""CLI entry point. Run `python main.py` to use the terminal flow.
For the GUI, run `python gui.py` instead."""
from __future__ import annotations

from dotenv import load_dotenv

from src.utils import paths
from src.utils.driver_factory import create_chrome_driver
from src.services.datacenter import DataCenter
from src.services.grabtickets import GrabTickets


def main() -> None:
    load_dotenv(paths.env_path())

    data_center = DataCenter()
    grab_tickets = GrabTickets()
    config = data_center.get_config()

    driver = create_chrome_driver(headless=False)
    try:
        driver.get("https://tixcraft.com/login")
        input("請完成登入後，按下 Enter 開始執行")

        operate = "r"
        while True:
            if operate == "r":
                grab_tickets.start(driver, config)
            elif operate == "q":
                break
            operate = input(
                "輸入 'q' 中止程序\n"
                "輸入 'r' 再次嘗試\n"
                ":"
            ).strip()
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
