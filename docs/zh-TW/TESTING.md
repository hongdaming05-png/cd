# MVP 驗證記錄

日期：2026-09-12。環境：Windows、Python 3.12、Codex 內建 Chromium 瀏覽器。

## 自動測試

- `python -m pytest -q`：57 項通過。
- `python -m ruff check backend frontend etl tools tests main.py`：通過。
- `python -m ruff format --check backend frontend etl tools tests main.py`：通過。
- `python -m pip check`：沒有套件相依衝突。
- `python -m tools.validate_content`：4 份教學驗證通過。

測試包含查詢正反例、裝置篩選、完整教學、服務重建後恢復、返回／重練、
重複點擊、併發更新、使用者隔離、內容快照、輸入驗證、無資料時不呼叫模型、
模型失敗備援，以及 Ollama／相容 API 的 request／response 格式與錯誤引用拒絕。
上游 Starlette／AnyIO 會顯示一項棄用提示，目前不影響測試。

## 瀏覽器操作

已實際點擊並檢查：首頁、教學準備、四步教學、卡住提示、FAQ、完成、重新練習、
暫停、重新整理後接續、LINE 搜尋、有查詢但沒有教學的畫面、大字切換。
朗讀按鈕顯示「正在朗讀」，停止按鈕可結束；未對聲音品質做聽感評估。

檢查桌面與 390 × 844 手機視窗。手機版的下一步／求助固定底部，示意圖可展開，
加大字級後頁面沒有水平溢出。瀏覽器最後一次檢查沒有 error／warn 訊息。
根目錄 `main.py` 成功啟動獨立前後端服務。

## 尚待實測

- iPhone Safari、實際 iOS／LINE 畫面與不同版本的操作路徑。
- 3–5 位長輩的可用性與實際任務完成率。
- 本機 Ollama 和真實雲端 API；目前 adapter 以 mock transport 驗證。
- 螢幕閱讀器、iPhone 背景朗讀、多使用者負載與公開網路部署。

此記錄僅代表上述 MVP 檢查，不代表已完成完整無障礙認證或所有手機的相容性驗證。

## 2026-09-13：結構重整與統一啟動入口

後端依 API、agents、LLM、config、models、services、RAG、repositories 分類。
重整後 57 項測試通過；OpenAPI 文件與重整前完全相同；設定仍指向專案根目錄。
啟動器已由 run.py 改為根目錄 main.py，執行 `python main.py` 可啟動前後端。
程式碼格式、靜態檢查與四份教學資料驗證皆通過。

## 語音轉文字修復驗證

後端測試通過，新增上傳空檔／超限、模型不可用、解碼失敗、
worker thread 轉錄與 Unicode 回傳，以及「字型」口語搜尋回歸測試。
模型事先下載到 `.data/models`；實際 CPU SenseVoiceSmall INT8 與 Whisper base 轉錄已驗證。

`python -m tools.test_voice_browser --audio .data/speech-test.wav` 使用
Playwright 啟動隔離的 Brave，將 Windows Hanhan 合成中文 WAV 注入假麥克風。
錄音由真正的 MediaRecorder 產生，經 8080 同來源代理、8000 FastAPI、
本地 SenseVoiceSmall／Whisper 和 OpenCC，再回傳 NiceGUI。沒有模擬轉錄 API 的成功結果。
加上 `--with-search` 可繼續等待本地 Ollama 搜尋並進入教學；未加參數時會專注測試錄音、
實際播放、轉文字和錯誤復原，避免模型服務的等待時間干擾語音功能檢查。

辨識輸出：「我想把手機的字型放大。請教我怎麼設定。」
已確認音波高度隨音訊變動、手動停止後歸零、原音可重新播放、文字顯示、找教學、進入教學，
以及第二次錄音後離頁確實釋放音軌。另以模擬失敗驗證拒絕權限和非 JSON 回應，
真實轉錄端點驗證靜音回傳空文字、損毀音訊回傳 422。
截圖位於 `.data/voice-confirmed.png`。

另以瀏覽器輸入「字條小」驗證模糊搜尋：結果頁會顯示 LINE 字體教學與 iPhone 系統字體
教學兩個候選，兩份都可以直接進入教學；精準輸入「字太小」則不會附帶模糊雜訊。

此測試涵蓋瀏覽器錄音到模型的軟體流程；不代表已測試使用者實體麥克風硬體、
環境噪音或 iPhone Safari。執行測試需安裝 `.[browser-test]`。
