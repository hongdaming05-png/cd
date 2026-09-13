# 教學內容怎麼維護

先從 `content/guides/iphone-text-size.json` 看完整範例。每個 JSON 檔是一份完整教學，
新增內容不用改 UI；新增全新視覺種類才需修改 frontend/components.py。

## 必要欄位

| 欄位 | 用途 |
| --- | --- |
| id / revision | 穩定唯一識別碼；更動操作時增加 revision |
| title / summary | 長輩看見的名稱與一句用途 |
| platform / app | 目前提供 ios + iphone/line |
| version_note | 記錄參考的版本、已實測裝置、尚未確認之處 |
| aliases | 真實使用者可能怎麼問；加入有意義的同義句 |
| prerequisites | 操作前需要準備的事情 |
| sources | 官方頁面名稱、URL、實際核對日期 |
| steps | 每步包含 title、instruction、hint、checkpoint、illustration |
| faqs | 只回答這份教學範圍內有根據的問題 |
| outcome | 最後請使用者親自檢查的結果 |

## 寫作原則

一次只給一個明確動作；用「點一下」或「慢慢往右拖」，少用「進入選單」「啟用功能」等抽象詞。
`hint` 回答找不到時可以怎麼找；`checkpoint` 讓使用者知道做完應該看到什麼。
開關如果已經符合目標，應明確寫「保持原樣」，避免使用者不小心反向切換。

不要把不同手機或作業系統版本合成一條模糊路徑。名稱差異大時，建立分開的 guide，
未來再擴充版本篩選器。這次四份教學是依官方文件整理，**尚未做 iPhone 實機驗證**。
`checked_at` 代表核對文件的日期，不代表當天完成實機測試。

`illustration.kind` 支援 app、row、slider、toggle、choice。
目前示意圖不是實機截圖；`rows` 只展示少量定位項目，不保證與所有版本的排序一致。

## 新增一份教學

1. 複製最接近的 JSON，改唯一 id、內容及來源。
2. 逐一核對官方文件。若實機測過，在 version_note 明確記下版本與機型。
3. 增加幾個真實問法到 aliases；加入一個正例和一個容易混淆的反例到測試。
4. 執行 `python -m tools.validate_content` 與 `python -m pytest -q`。
5. 重啟後端。從首頁建立新教學進度，實際走到最後一步。

舊進度保留舊版內容，這是刻意的設計；要試新版本，從首頁重新開始該份教學。

## 第一批來源

- iPhone 文字大小／粗體：[Apple 顯示與文字設定](https://support.apple.com/zh-tw/guide/iphone/-iphd6804774e/ios)
- iPhone 亮度：[Apple 亮度和色彩](https://support.apple.com/zh-tw/guide/iphone/iph60ba71065/ios)
- LINE 字體：[LINE 聊天室顯示設定](https://help.line.me/line/smartphone?contentId=20005811&lang=zh-Hant)

日後若提供投稿介面，應先進入待審稿資料區，核對版本與內容後才納入教學檢索。
