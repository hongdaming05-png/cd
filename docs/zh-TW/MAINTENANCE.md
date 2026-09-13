# 維護手冊

這個專案用兩個本機服務組成：NiceGUI 前端在 `8080`，FastAPI 後端在 `8000`。
一般開發只需要從專案根目錄執行：

```powershell
.venv\Scripts\python.exe main.py
```

Windows 要重啟已經在跑的服務，可執行：

```powershell
.\tools\restart_services.ps1
```

重啟後開啟 <http://127.0.0.1:8080>。啟動輸出在 `.data/server.out.log`，錯誤在
`.data/server.err.log`。

## 五分鐘看懂程式

建議依這個順序閱讀，不要一開始就把整個資料夾全部打開：

1. `main.py`：確認兩個服務怎麼啟動、埠號在哪裡設定。
2. `frontend/app.py`：看使用者畫面如何在首頁、語音、文字、結果和教學頁之間切換。
3. `backend/api/routes/`：看瀏覽器送出的每個 HTTP 請求進入哪個端點。
4. `backend/services.py`：看搜尋、開始教學、下一步和求助的主要業務流程。
5. `backend/agents/` 與 `backend/rag/`：需要理解 LangGraph 或搜尋細節時再往下追。
6. `content/guides/`：想增加或修改教學時直接編輯 JSON，不需要先改 Python。

在編輯器中先用「搜尋符號／函式」找 `main`、`create_app`、`search`、`start`、`act`，
再用「尋找參考」追呼叫者，比逐檔閱讀快很多。每個主要入口附近都有少量註解，註解只說明
責任和資料流；實際細節以函式本身與型別定義為準。

## 第一次設定

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev,speech,browser-test]"
.venv\Scripts\python.exe -m tools.prepare_speech
```

`prepare_speech` 只需執行一次，預設會把 SenseVoiceSmall INT8 模型放到 `.data/models`。
若要準備備援的 Whisper base，執行
`.venv\Scripts\python.exe -m tools.prepare_speech --provider whisper`。
若要啟用本機 Ollama，先安裝並啟動 Ollama，再下載聊天與 embedding 模型：

```powershell
ollama pull qwen2.5:7b
ollama pull bge-m3
Copy-Item .env.example .env
```

`.env` 的 `EG_LLM_PROVIDER=ollama` 才會啟用 LangGraph 搜尋 agent 與 embedding；
沒有 `.env` 時會使用不需模型的離線模式。

## 要改哪裡

| 想改的內容 | 主要檔案 |
| --- | --- |
| 首頁、語音頁、文字頁、教學頁 | `frontend/app.py` |
| 錄音、音波、上傳與權限錯誤 | `frontend/static/voice.js` |
| 前端呼叫後端、錯誤顯示 | `frontend/api.py`、`frontend/speech_proxy.py` |
| API 路徑與輸入驗證 | `backend/api/routes/`、`backend/models.py` |
| 搜尋、開始教學、進度與求助協調 | `backend/services.py` |
| LangGraph 節點與狀態 | `backend/agents/` |
| 模型 client、提示詞與 provider | `backend/llm/` |
| embedding 與檢索 | `backend/rag/semantic.py`、`backend/rag/retrieval.py` |
| 語音轉文字 | `backend/speech.py`、`backend/api/routes/speech.py`；效能工具在 `tools/benchmark_speech.py` |
| 公開網路參考 | `backend/web.py` |
| 教學文字、步驟、常用問法 | `content/guides/*.json` |
| 官方資料收集與 ETL | `etl/collect_official.py`；輸出在 `.data/official-sources/` |
| 測試 | `tests/`；瀏覽器語音測試在 `tools/test_voice_browser.py` |

依賴方向固定為「前端 → HTTP API → services → agents/rag/repositories」。前端不要直接
import 後端服務；教學步驟只放 JSON，不讓模型自行編造按鈕或操作順序。

## 修改教學內容

每份 JSON 都要有唯一 `id`、標題、`aliases`、來源、步驟和確認點。修改後先驗證，再重啟：

```powershell
.venv\Scripts\python.exe -m tools.validate_content
.venv\Scripts\python.exe -m pytest -q
```

`aliases` 請放長輩可能說的完整句子，例如「LINE 文字放大」、「聊天字太小怎麼辦」，
不要只放單一詞。embedding 會使用標題、摘要和 aliases；內容更新後重啟才會重建向量。

## 收集官方資料

收集器目前只允許 Apple 與 LINE 官方 HTTPS 網址，並只輸出標題、段落、標題和步驟等
結構化筆記。輸出放在 `.data/official-sources/`，該目錄不會提交到 Git；請人工核對版本、
畫面名稱與實機差異後，再把自己的整理寫進 `content/guides/*.json`。

```powershell
# 查看允許收集的官方網址
.venv\Scripts\python.exe -m etl.collect_official --list

# 收集全部目前列入清單的 Apple／LINE 頁面
.venv\Scripts\python.exe -m etl.collect_official

# 只更新一頁
.venv\Scripts\python.exe -m etl.collect_official --source line-chat-display

# 收集 LINE 官方繁中手機說明；先抓 50 頁確認內容
.venv\Scripts\python.exe -m etl.collect_official --crawl line-smartphone --max-pages 50 --delay 0.5

# 收集 Apple 官方繁中 iPhone 手冊；先抓 50 頁確認內容
.venv\Scripts\python.exe -m etl.collect_official --crawl apple-iphone --max-pages 50 --delay 0.5

# 確定要完整更新時才使用 0（不限制頁數），並保留請求間隔
.venv\Scripts\python.exe -m etl.collect_official --crawl all --max-pages 0 --delay 1

# 在另一個 PowerShell 視窗查看目前累積結果
.venv\Scripts\python.exe -m etl.collect_official --status

# 收集完成後建立分類資料與總索引
.venv\Scripts\python.exe -m etl.classify_official
```

收集開始時會顯示候選頁數，之後每 10 頁回報已抓、已存、略過、失敗、待處理與經過時間。
使用 `Ctrl+C` 可安全停止；已完成的 JSON 會保留，下次執行會依網址覆寫同一個檔案。

分類器使用本機 Ollama `bge-m3`，不需雲端 API。結果位於
`.data/official-sources/classified/iphone/<category>/` 與 `classified/line/<category>/`；
`classified/catalog.json` 記錄每個分類的數量和所有文件路徑。每份分類 JSON 含產品、平台、
Apple 系統版本、分類分數、來源網址、原始檔路徑及擷取內容。這些仍是待審核來源資料，
不會直接覆蓋 `content/guides/` 或自動出現在正式 RAG 教學。

新增來源時，先在 `etl/collect_official.py` 的 `OFFICIAL_SOURCES` 清單加入官方網址，
若要擴大範圍則修改 `CRAWL_TARGETS` 的官方路徑與 sitemap，並保持 `ALLOWED_HOSTS` 限制。
全集輸出會放在 `.data/official-sources/crawl/<crawl-id>/`，每頁一個 JSON；不要把爬蟲改成
任意網址，也不要直接把整篇文章當作教學回覆。Apple iPhone 手冊目前是近千頁規模，請
優先用 `--max-pages` 分批收集，避免一次產生大量流量。

### Extension 與 ETL 的位置

如果未來官方頁面需要登入或必須由人手動選取內容，可以增加 Chrome Extension。Extension
不要直接改 `content/guides/`，也不要直接寫向量索引；請把擷取結果輸出成 JSON 放在
`.data/inbox/`，再由整理程式和維護者審核後更新正式教學。欄位沿用收集器格式：
`source_url`、`provider`、`captured_at`、`title`、`headings`、`paragraphs`、`steps`、
`content_hash`。

目前的儲存選擇是：正式教學用可讀、可版控的 JSON；向量由 Ollama embedding 在服務啟動時
建立於記憶體；SQLite 只存使用者教學進度。資料量真的成長後，再把 `backend/rag/` 的
索引 adapter 換成 Qdrant、pgvector 或其他向量服務，ETL 的輸出格式不必改變。

目前 ETL 不另開 repository，先放在同一個專案的 `etl/`，和應用程式及維護工具分開。
當資料流程開始有獨立部署、排程、憑證或協作者時，再拆成資料專案；主服務只接收版本化
的教學 JSON，不直接依賴擷取程式。

## 查詢問題怎麼查

先直接看 API 回應，確認 agent 整理後的查詢、工具和命中教學：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/search -Method Post `
  -ContentType 'application/json' -Body '{"query":"LINE文字放大","platform":"ios"}'
```

回應中的 `hits` 是本地教學，`interpreted_query` 是 agent 整理後的句子，
`tool_used` 和 `agent_status` 可用來判斷是否走 RAG 或網路參考。Ollama 模式若 embedding
尚未準備好，會走服務層的無結果／網路 fallback；請先確認 `ollama list` 有 `bge-m3`。
若 `hits` 為空但 `suggestions` 有內容，代表系統找到相近教學，前端會要求使用者選擇；
若兩者都空，才會顯示無結果並視設定嘗試公開網路參考。

## 語音問題怎麼查

瀏覽器語音頁按一次開始、再按一次停止；音波高度代表實際收到的音量。停止後會出現
「播放剛才錄音」，可直接比較原音與辨識文字。後端也可單獨測試：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
.venv\Scripts\python.exe -m tools.test_voice_browser --audio .data/speech-test.wav
```

若顯示模型不可用，重新執行 `python -m tools.prepare_speech`；若瀏覽器沒有音波，
檢查網站的麥克風權限與是否使用 `localhost`／`127.0.0.1`。錄音和播放網址只在瀏覽器
記憶體中處理，開始下一次錄音或離開頁面時清除；限制 20 MB、三分鐘，沒有寫入使用者音檔。

預設 provider 是 `sensevoice`。切換後要重啟服務：

```powershell
# 測量 SenseVoiceSmall 的模型載入、音訊長度和轉錄時間
.venv\Scripts\python.exe -m tools.benchmark_speech --provider sensevoice
```

必要時在 `.env` 切回 Whisper，再重啟：

```dotenv
EG_SPEECH_PROVIDER=whisper
```

2026-09-13 在目前開發電腦的實測：SenseVoiceSmall 載入約 0.96 秒，5.6 秒錄音轉錄約
0.09 秒，8.9 秒錄音約 0.14 秒。這只代表目前電腦與兩段樣本；正式選型仍需使用多種長輩
口音、音量、環境雜音和不同問題內容做比較。

## 每次提交前

```powershell
.venv\Scripts\python.exe -m tools.validate_content
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check backend frontend etl tools tests main.py
.venv\Scripts\python.exe -m ruff format --check backend frontend etl tools tests main.py
```

若改了錄音、搜尋或頁面流程，再加跑 `tools.test_voice_browser`，並用瀏覽器實際點一次
「用語音說 → 停止 → 播放剛才錄音 → 找教學 → 開始教學」。
