# 📦 Matrix Engine V2
> 企業級非同步架構：基於 Serverless 與大語言模型的多模態量化分析引擎
> (An Enterprise-Grade, Asynchronous Multi-Modal Quant Analysis Agent)

## 💡 1. 系統簡介 (Elevator Pitch)
Matrix Engine V2 是一套全自動化的量化交易輔助系統。系統能透過 Telegram 接收多張盤面截圖，並利用 GCP Serverless 架構將「接收響應」與「AI 運算」完全解耦。最終交由 Vertex AI (Gemini 2.5 Flash) 進行多圖聯合推導，將萃取出的 23 個量化維度與矩陣狀態自動寫入 Google Sheets 資料庫。

## 🎯 2. 解決的核心痛點 (Why we built this)
在早期的單體架構 (Monolithic) 中，處理高併發的高畫質圖片推導時，常遭遇以下瓶頸，本架構已將其全數殲滅：
* **破除 API 逾時限制**：利用 Pub/Sub 訊息佇列，徹底解決 Telegram Webhook 強制 60 秒 Timeout 的 504 崩潰與無限重試風暴。
* **解決 OOM (記憶體溢出)**：內外場雙節點各自獨立配置 1024MB 資源，確保處理超大影像陣列時算力充沛。
* **零功耗待機 (Scale to Zero)**：純事件驅動 (Event-driven)，無任務時系統縮放至零，最大化利用雲端免費額度。

## 🏗️ 3. 系統架構流 (Architecture Data Flow)
本系統採用「內外場解耦 (Decoupling)」的微服務雙節點設計：

```text
[ 📱 使用者端 ] 
   └─ Telegram App (傳送截圖與 Go 指令)
        ↓ (HTTP POST)
[ 🛎️ 外場 API 閘道 ] 
   └─ GCP Cloud Run (webhook_receiver) 
      ├─ 職責：秒回 HTTP 200、暫存圖片 ID 至海馬迴、攔截無效請求。
      └─ 派單：將運算任務打包為 Message，發佈至 Pub/Sub。
        ↓ (Async Message)
[ 📨 訊息佇列 ] 
   └─ GCP Pub/Sub (matrix-task-queue) 
      └─ 職責：緩衝高併發請求，確保任務不遺失 (At-least-once delivery)。
        ↓ (Push Trigger)
[ 🧠 內場運算引擎 ] 
   └─ GCP Cloud Functions gen2 (background_worker)
      ├─ 視覺神經：呼叫 Vertex AI 進行多圖聯合推導與 OCR 萃取。
      ├─ 量化核心：Layer 2 矩陣坍縮 (Z-Score, Alpha, 通量計算)。
      └─ 落地儲存：將標準化 JSON 轉譯，透過 Sheets API 寫入資料庫。

## 🛠️ 4. 技術棧 (Tech Stack)
* **基礎設施**: Google Cloud Platform (Cloud Run, Cloud Functions gen2, Pub/Sub)
* **AI 模型**: Vertex AI (Gemini 2.5 Flash)
* **資料庫**: Google Sheets API (無伺服器關聯式替代方案)
* **前端介面**: Telegram Bot API
* **開發語言**: Python 3.10 (搭配 Pydantic 進行嚴格資料驗證)
