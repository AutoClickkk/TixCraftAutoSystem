### config.json
```json
{
    // Require[str]
    // chromedriver 執行檔位置，下載連接:https://googlechromelabs.github.io/chrome-for-testing/
    "chrome_driver_path": "./assets/chromedriver/win64-130.0.6723.70.exe",

    // Require
    // 每個操作之間休息的秒數 介於 0.0 ~ 1.0 之間，確保 max_seconds >= min_seconds
    "sleep": {
        "max_seconds": 0.2,
        "min_seconds": 0.1
    },

    // Require[str]
    // 活動ID
    "game_id": "24_lioneers",

    // Require[int]
    // 要搶的票數
    "number_of_ticket" : 2,

    // Optional["%Y/%m/%d-%H:%M:%S"]
    // 哪時候開始搶
    "open_for_purchase_datetime": "2024/10/31-13:30:00", 
    // 直接進去開始搶(蹲釋出票)
    "open_for_purchase_datetime": null, 
    
    // Optional[str]
    // 點擊 '立即購票' 後出現的 '演出時間' 欄位數據中需包含的字串
    "show_time_text_contains": "2024/12/06",
    // 不指定時間
    "show_time_text_contains": null,

    // Optional[str]
    // 點擊 '立即訂購' 後出現的(區域與價錢)項目中需包含的字串
    "area_price_text_contains": "4880",
    // 不指定價位
    "area_price_text_contains": null,

    // Optional[List[str]]
    // 完成後寄送 email 通知
    "notification_emails": ["xxx@gmail.com", "zzz@gmail.com"],
    // 完成後不通知
    "notification_emails": null
}
```