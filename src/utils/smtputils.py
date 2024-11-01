from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Self
import smtplib
# from email.mime.image import MIMEImage
# from pathlib import Path
import os


class SMTPUtils:
    _instance: Optional[Self] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def send(self, from_email: str, to_email: str, subject: str, text: str) -> Optional[Exception]:
        content = MIMEMultipart()  # 建立MIMEMultipart物件
        content["subject"] = subject  # 郵件標題
        content["from"] = from_email  # 寄件者
        content["to"] = to_email  # 收件者
        content.attach(MIMEText(text))  # 郵件純文字內容
        # content.attach(MIMEImage(Path("koala.jpg").read_bytes()))  # 郵件圖片內容

        with smtplib.SMTP(host="smtp.gmail.com", port=587) as smtp:  # 設定SMTP伺服器
            try:
                smtp.ehlo()  # 驗證SMTP伺服器
                smtp.starttls()  # 建立加密傳輸
                smtp.login(
                    os.environ["SMTP_LOGIN_USER"], os.environ["SMTP_LOGIN_PASSWORD"]
                )  # 登入寄件者gmail
                smtp.send_message(content)  # 寄送郵件
            except Exception as e:
                return e
            
        return None