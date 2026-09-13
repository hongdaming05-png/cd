# 一起維護「慢慢來」

目前以小而容易理解的 Python 專案為主。先讀根目錄 README、`MAINTENANCE.md` 與
`ARCHITECTURE.md`；日常啟動、查詢除錯和檢查指令都集中在維護手冊。

## 修改流程

1. 在自己的分支修改，保持每次改動的目的清楚。
2. 修改教學，先讀 `CONTENT.md`，記錄裝置、語言、系統與 App 版本。
3. 執行 `python -m tools.validate_content`、`python -m pytest -q`、
   `python -m ruff check backend frontend etl tools tests main.py`。
4. 改前端時，用桌面與手機寬度實際走完一次教學，確認可返回、可休息、可接續。
5. PR 說明改了什麼、如何驗證、哪些裝置仍待確認。

## 模組邊界

- 前端透過 HTTP 呼叫後端，不直接 import backend 或存取 SQLite。
- 路由只處理 HTTP，業務協調放 services/、LangGraph 流程放 agents/；知識內容放 JSON。
- 新增資料庫或模型供應商時，保持 adapter 邊界，不把特例散落到 UI。
- 避免為尚未開始的功能引入大量抽象層。

目前尚未提供公開投稿或影片上傳。請勿將真實聊天內容、電話、金鑰或錄影放進測試資料。
來源網站的內容與品牌圖像仍受原本的權利約束；請用自己的敘述與有授權的示意素材。
