from __future__ import annotations
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from typing_extensions import Self
import smtplib
import os


class SMTPConfigError(Exception):
    pass


class SMTPUtils:
    _instance: Optional[Self] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def send(
        self, to_email: str, subject: str, text: str, from_email: Optional[str] = None
    ) -> Optional[Exception]:
        user = os.environ.get("SMTP_LOGIN_USER")
        password = os.environ.get("SMTP_LOGIN_PASSWORD")
        if not user or not password:
            return SMTPConfigError(
                "SMTP_LOGIN_USER / SMTP_LOGIN_PASSWORD not set; skipping email."
            )

        sender = from_email or user
        content = MIMEMultipart()
        content["subject"] = subject
        content["from"] = sender
        content["to"] = to_email
        content.attach(MIMEText(text))

        try:
            with smtplib.SMTP(host="smtp.gmail.com", port=587, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(content)
        except Exception as e:
            return e
        return None
