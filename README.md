## TixCraftAutoSystem
### 配置 .env  
```bash
# Google SMTP (如果需要完成後通知的話)
SMTP_LOGIN_USER=email
SMTP_LOGIN_PASSWORD=password
``` 
### 配置 config.json(說明請參考 docs/config.md)
```json
{
    "chrome_driver_path": "./assets/chromedriver/win64-130.0.6723.70.exe",
    "sleep": {
        "max_seconds": 0.5,
        "min_seconds": 0.2
    },
    "game_id": "24_straykids",
    "number_of_ticket" : 2,

    "open_for_purchase_datetime": "2024/11/01-13:00:00",
    "show_time_text_contains": "2024/11/03 (日) 18:00",
    "area_price_text_contains": "4800",
    "notification_emails": ["xxx@gmail.com"]
}
```

### 安裝依賴
```bash
# 創建虛擬環境(python version 3.12.5)
python -m venv .venv
# 進入 venv
.\.venv\Scripts\activate

# 安裝依賴
pip install --upgrade pip
pip install -r requirements.txt
```

### 運行
```bash
python main.py
```

## freeze
```bash
pip freeze > requirements.txt
```

## test
```bash
pip install pytest pytest-cov
pytest --cov=src --cov-report=term-missing --cov-report=html
```
