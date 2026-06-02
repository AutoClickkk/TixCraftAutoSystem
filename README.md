# TixCraft 自動搶票 (TixCraftAutoSystem)

桌面版 TixCraft 自動搶票工具，內建 GUI、OCR 驗證碼辨識、手動補登後援與更新通知。
支援 macOS 與 Windows。

> ⚠️ 本工具僅供學術研究與個人使用，請遵守 TixCraft 服務條款與各活動規範。

---

## 📦 下載

到 [Releases](https://github.com/AutoClickkk/TixCraftAutoSystem/releases/latest) 下載對應系統的版本：

| 系統 | 檔案 |
| --- | --- |
| macOS (Apple Silicon, M1/M2/M3) | `TixCraft-mac-arm64.zip` |
| macOS (Intel) | `TixCraft-mac-x64.zip` |
| Windows 10/11 (x64) | `TixCraft-win-x64.zip` |

App 啟動時會自動到 GitHub 檢查新版本；有更新時側邊欄會顯示提示，到「關於」頁可以直接下載。

### macOS 安裝
1. 解壓縮後，把 `TixCraft.app` 拖到 `/Applications/`
2. 第一次開啟：**右鍵 → 開啟 → 開啟**（因為未簽章，Gatekeeper 會擋下雙擊）
3. 如果跳 *Operation not permitted*：到 *系統設定 → 隱私權與安全性* 點「強制開啟」

### Windows 安裝
1. 解壓縮整個 `TixCraft\` 資料夾到任意位置（建議桌面或 `C:\Tools\`）
2. 雙擊 `TixCraft.exe` 啟動
3. SmartScreen 警告：點「其他資訊 → 仍要執行」

### 先決條件
- 系統已安裝 **Google Chrome**（最新穩定版）。本工具會自動配對 chromedriver。
- 首次執行需要網路下載 chromedriver（約 15MB）。

---

## 🖥️ 操作流程

1. 打開 App，到「**設定**」頁填寫：
   - **活動 ID**（網址 `https://tixcraft.com/activity/game/<id>` 中的 `<id>`）
   - **演出時間關鍵字**、**票價/區域關鍵字**、**票數**
   - 想排程的話勾「**依排程時間開搶**」並選好時間
   - （選填）填 Gmail 帳號與 [App password](https://myaccount.google.com/apppasswords) 來啟用搶到票後的 email 通知
2. 按「**儲存設定**」
3. 切到「**執行**」頁，按「**啟動瀏覽器登入**」
4. 在跳出的 Chrome 視窗手動登入 TixCraft
5. 回到 App，按「**開始搶票**」
6. OCR 認不出驗證碼時，App 會跳出對話框讓你手動輸入

---

## 🔄 自動更新

App 啟動時會背景查詢 GitHub Releases 最新版本，若有新版會在側邊欄顯示「**✦ 有新版本**」提示，到「關於」頁可以直接點「下載更新」開啟對應檔案。

---

## 🛠️ 從原始碼開發 / 自行打包

### 需求
- Python 3.10+（建議 3.10 或 3.12）
- Google Chrome

### 安裝
```bash
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 啟動 GUI
```bash
python gui.py
```

### 啟動 CLI（原本的命令列流程）
```bash
python main.py
```

### 打包成 .app / .exe
```bash
# macOS
./build/build_mac.sh
# Windows
build\build_win.bat
```
產物在 `dist/`。

### 設定檔位置
- 開發模式：專案根目錄的 `config.json` / `.env`
- 打包後：
  - macOS: `~/Library/Application Support/TixCraftAutoSystem/`
  - Windows: `%APPDATA%\TixCraftAutoSystem\`

### config.json 欄位
詳見 [`docs/config.md`](docs/config.md)。

---

## 📦 發佈新版本

```bash
# 1. 改 version.json 的 version
# 2. 提交、打 tag、推上去
git tag v0.2.1
git push origin v0.2.1
```
推 tag 後，GitHub Actions 會自動：
- 在 macOS Apple Silicon、macOS Intel、Windows x64 三平台打包
- 把 zip 上傳到 Release
- 使用者打開 App 後即會收到更新提示

---

## 🐞 問題回報

到 [Issues](https://github.com/AutoClickkk/TixCraftAutoSystem/issues) 開單，附上：
- 作業系統 + App 版本（在「關於」頁可看到）
- log 輸出（「執行」頁右下角可複製）
- 重現步驟
