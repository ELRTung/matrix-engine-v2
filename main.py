# -*- coding: utf-8 -*-
# ==============================================================================
# 📦 MATRIX ENGINE Version 2.0 - Agent Platform 視覺進化版 (Route B 強化版)
# ==============================================================================
import re
import json
import logging
import sys
import os
import requests
import datetime
import base64
from typing import Any, List, Dict
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# Google API & Cloud 相關
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google import genai
from google.genai import types
from google.cloud import pubsub_v1
import functions_framework

# ==========================================
# 🛡️ SYSTEM INIT: SILICON SHIELD
# ==========================================
logger = logging.getLogger("MatrixEngine_V2")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class MetaLayerFirewall:
    BANNED_PREFIXES = r"^[=+\-@]"
    @classmethod
    def sanitize(cls, text: str) -> str:
        text = str(text).strip()
        if re.match(cls.BANNED_PREFIXES, text): 
            return f"'{text}" 
        return text

# ==========================================
# 🛠️ DATA PRE-PROCESSING
# ==========================================
class UnitNormalizationEngine:
    @staticmethod
    def to_pure_price(raw_value: Any) -> float:
        if isinstance(raw_value, (int, float)): return float(raw_value)
        clean_str = re.sub(r'[^\d\.\-]', '', str(raw_value))
        if not clean_str or clean_str in ('-', '.'): return 0.0
        return float(clean_str)

    @staticmethod
    def to_base_million(raw_value: Any) -> float:
        if isinstance(raw_value, (int, float)): return float(raw_value)
        raw_str = str(raw_value).strip().replace(',', '')
        clean_str = re.sub(r'[^\d\.\-\+KkMmBb萬億]', '', raw_str)
        if not clean_str or clean_str in ('-', '+', '.'): return 0.0
        try:
            if '億' in clean_str: return float(re.sub(r'[^\d\.\-\+]', '', clean_str)) * 100.0
            if '萬' in clean_str: return float(re.sub(r'[^\d\.\-\+]', '', clean_str)) / 100.0
            if 'B' in clean_str.upper(): return float(clean_str.upper().replace('B', '')) * 1000.0
            if 'K' in clean_str.upper(): return float(clean_str.upper().replace('K', '')) / 1000.0
            if 'M' in clean_str.upper(): return float(clean_str.upper().replace('M', ''))
            return float(clean_str)
        except ValueError: return 0.0

    @staticmethod
    def to_decimal_percentage(raw_value: Any) -> float:
        if isinstance(raw_value, (int, float)): return float(raw_value)
        raw_str = str(raw_value).strip()
        is_percentage = '%' in raw_str
        clean_str = re.sub(r'[^\d\.\-\+]', '', raw_str)
        if not clean_str or clean_str in ('+', '-', '.'): return 0.0
        val = float(clean_str)
        return val / 100.0 if is_percentage else val

class VisionTranslator:
    @classmethod
    def collapse_vwap(cls, ocr_vwap_status: str) -> int:
        if not ocr_vwap_status: return 0
        if re.search(r"(突破|化解|站上|不).*(壓制|均線)", ocr_vwap_status): return 0
        if "壓制" in ocr_vwap_status or "低於均線" in ocr_vwap_status or "低於" in ocr_vwap_status: return 1
        return 0

# ==========================================
# 📊 DATA MODELS
# ==========================================
class DailyMetrics(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ticker: str = Field(..., description="股票代號")
    date: str = Field(..., description="YYYY/MM/DD")
    close_val: float = Field(default=0.0)
    avg_cost: float = Field(default=0.0)
    high_val: float = Field(default=0.0)
    low_val: float = Field(default=0.0)
    boll_mid: float = Field(default=0.0)
    boll_upper: float = Field(default=0.0)
    boll_lower: float = Field(default=0.0)
    target_change: float = Field(default=0.0)
    spy_change: float = Field(default=0.0)
    large_flow_m: float = Field(default=0.0)
    small_flow_m: float = Field(default=0.0)
    vwap_suppressed: int = Field(default=0)
    flux_ratio: float = Field(default=1.0)
    v_daily_m: float = Field(default=0.0)
    flux_disp_20: float = Field(default=0.0)
    flux_disp_90: float = Field(default=0.0)
    profit_ratio: float = Field(default=0.0)
    resistance_level: float = Field(default=0.0)
    support_level: float = Field(default=0.0)
    turnover_rate: float = Field(default=0.0)
    volume_ratio: float = Field(default=1.0)
    beta: float = Field(default=1.0)
    visual_divergence: bool = Field(default=False)
    late_session_flow: bool = Field(default=False)

    @model_validator(mode='before')
    @classmethod
    def preprocess_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict): return data
        norm = UnitNormalizationEngine
        if 'ticker' in data: data['ticker'] = str(data['ticker']).strip().upper()
        if 'vwap_suppressed' in data and isinstance(data['vwap_suppressed'], str):
            data['vwap_suppressed'] = VisionTranslator.collapse_vwap(data['vwap_suppressed'])
        for k in ['close_val', 'avg_cost', 'high_val', 'low_val', 'boll_mid', 'boll_upper', 'boll_lower', 'resistance_level', 'support_level', 'flux_disp_20', 'flux_disp_90', 'volume_ratio', 'beta']:
            if k in data: data[k] = norm.to_pure_price(data[k])
        for k in ['target_change', 'spy_change', 'profit_ratio', 'turnover_rate']:
            if k in data: data[k] = norm.to_decimal_percentage(data[k])
        for k in ['large_flow_m', 'small_flow_m', 'v_daily_m']:
            if k in data: data[k] = norm.to_base_million(data[k])
        return data

    @property
    def z_score(self) -> float:
        if self.boll_upper == 0 or self.boll_lower == 0 or self.boll_upper <= self.boll_lower: return 0.0
        sigma = (self.boll_upper - self.boll_lower) / 4.0
        return 0.0 if sigma == 0 else (self.close_val - self.boll_mid) / sigma

    @property
    def amplitude(self) -> float:
        return (self.high_val - self.low_val) / self.close_val if self.close_val > 0 else 0.0

    @property
    def cost_bias(self) -> float:
        return (self.close_val - self.avg_cost) / self.avg_cost if self.avg_cost > 0 else 0.0

    @property
    def true_alpha(self) -> float:
        return self.target_change - (self.spy_change * self.beta)

    @property
    def channel_position(self) -> float:
        box_height = self.resistance_level - self.support_level
        if box_height <= 0 or self.support_level == 0: return -1.0
        return (self.close_val - self.support_level) / box_height

# ==========================================
# 🌍 LAYER 2: VECTOR COUPLING MATRIX 
# ==========================================
class Layer2MatrixEngine:
    T_DISP_WARN, T_TURN_HIGH, T_VOL_HIGH, T_PROFIT_HIGH, T_ALPHA_STRONG = 60.0, 0.15, 2.0, 0.80, 0.015   
    @classmethod
    def collapse_state(cls, metrics: DailyMetrics) -> str:
        states = []
        is_distributing, is_strong_breakout = False, False
        z, disp_20, net_large_flow = metrics.z_score, metrics.flux_disp_20, metrics.large_flow_m
        if disp_20 >= cls.T_DISP_WARN:
            if metrics.volume_ratio > 1.5 and net_large_flow > 0 and not metrics.visual_divergence:
                states.append(f"🌟無敵星主升段(DISP={disp_20:.1f})"); is_strong_breakout = True
            elif metrics.visual_divergence or net_large_flow < 0:
                states.append(f"⚠️動能耗竭(頂背離)"); is_distributing = True
        if metrics.turnover_rate > cls.T_TURN_HIGH and metrics.volume_ratio > cls.T_VOL_HIGH:
            if net_large_flow < 0 or metrics.profit_ratio > cls.T_PROFIT_HIGH:
                states.append(f"🌪️巨量換手派發"); is_distributing = True
            elif disp_20 < cls.T_DISP_WARN and net_large_flow > 0:
                states.append(f"🔥極端放量洗盤"); is_strong_breakout = True
        elif 30 <= disp_20 < cls.T_DISP_WARN:
            if net_large_flow > 0 and disp_20 > metrics.flux_disp_90: states.append(f"🟢通量金叉擴張")
        pos = metrics.channel_position
        if pos != -1.0:
            if pos >= 0.85: states.append(f"🛑逼近壓力頂區")
            elif pos <= 0.15:
                if net_large_flow > 0: states.append(f"🛡️箱底防守區")
                else: states.append(f"⚠️跌破邊緣")
            elif 0.4 <= pos <= 0.6: states.append(f"⚖️箱體中軌盤整")
        if metrics.true_alpha > cls.T_ALPHA_STRONG and net_large_flow > 0: states.append(f"🟢真Alpha強勢")
        elif metrics.true_alpha < -cls.T_ALPHA_STRONG and net_large_flow < 0: states.append(f"🔴隱性疲弱")
        if z >= 2.0 and disp_20 < cls.T_DISP_WARN and metrics.volume_ratio < cls.T_VOL_HIGH: states.append(f"🔥布林擴張")
        elif z <= -2.0: states.append(f"🩸極端收縮")
        if metrics.late_session_flow:
            if is_distributing: states.append("🦊尾盤誘多") 
            elif is_strong_breakout or net_large_flow > 0: states.append("⚡尾盤真金搶籌")
            else: states.append("⚡尾盤惡意抽離")
        if not states:
            if abs(z) < 1.0 and abs(metrics.spy_change) < 0.01: return f"⚪ 核心布朗運動(Z={z:.2f})"
            return f"⚪ 隨機漫步(Z={z:.2f})"
        return f"[{' | '.join(states)}]"

# ==========================================
# 👷‍♂️ SPECIALIST WORKERS
# ==========================================
class VisionAgent:
    def __init__(self, project_id: str, location: str, credentials_json_str: str):
        cred_info = json.loads(credentials_json_str)
        self.creds = service_account.Credentials.from_service_account_info(
            cred_info, scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        self.client = genai.Client(vertexai=True, project=project_id, location=location, credentials=self.creds)
        self.model_id = "gemini-2.5-flash"

    def analyze_chart(self, image_bytes_list: List[bytes], mime_type: str = "image/jpeg") -> str:
        contents = []
        for img_bytes in image_bytes_list:
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
        prompt = """請以 JSON 格式輸出以下欄位(無數據填0): 
        ticker, date, close_val, high_val, low_val, avg_cost, boll_mid, boll_upper, boll_lower, 
        target_change, spy_change, large_flow_m, small_flow_m, vwap_suppressed, v_daily_m, 
        turnover_rate, volume_ratio, resistance_level, support_level, flux_disp_20, flux_disp_90, beta, profit_ratio"""
        contents.append(prompt)
        config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
        return self.client.models.generate_content(model=self.model_id, contents=contents, config=config).text.strip()

class QuantCoreAgent:
    @classmethod
    def process_daily(cls, raw_payload: dict) -> Dict[str, Any]:
        metrics = DailyMetrics(**raw_payload)
        matrix_result = Layer2MatrixEngine.collapse_state(metrics)
        row_data = [metrics.date, round(metrics.close_val, 2), round(metrics.amplitude, 4), 
            round(metrics.target_change, 4), round(metrics.spy_change, 4),
            round(metrics.large_flow_m, 2), round(metrics.small_flow_m, 2), metrics.vwap_suppressed, 
            round(metrics.avg_cost, 2), round(metrics.cost_bias, 4), round(metrics.profit_ratio, 4), 
            round(metrics.resistance_level, 2), round(metrics.support_level, 2),
            round(metrics.flux_ratio, 2), round(metrics.z_score, 2), round(metrics.v_daily_m, 2),
            round(metrics.flux_disp_20, 2), round(metrics.flux_disp_90, 2),
            round(metrics.turnover_rate, 4), round(metrics.volume_ratio, 2), round(metrics.beta, 3), 
            round(metrics.channel_position, 2), MetaLayerFirewall.sanitize(matrix_result)]
        return {"ticker": metrics.ticker, "target_sheet": f"{metrics.ticker}_Data", "row_data": row_data, "state": matrix_result}

class GoogleSheetsIOAgent:
    HEADERS = ["Date", "Close_Val", "Amplitude", "Target_Change", "SPY_Change", "Large_Flow_M", "Small_Flow_M", "VWAP_Suppressed", "Avg_Cost", "Cost_Bias", "Profit_Ratio", "Resistance", "Support", "Flux_Ratio", "Z_Score", "V_Daily_M", "Flux_Disp_20", "Flux_Disp_90", "Turnover_Rate", "Volume_Ratio", "Beta", "Box_Pos", "Matrix_State"]
    HEADER_FORMULA = '={"EFDT(自動運算)"; ARRAYFORMULA(IF(ISBLANK(A2:A), "", IF(P2:P=0, 0, ROUND((F2:F+G2:G)/P2:P, 4))))}'
    CACHE_SHEET = "Sys_Cache"  
    def __init__(self, spreadsheet_id: str, credentials_json_str: str):
        self.spreadsheet_id = spreadsheet_id
        cred_info = json.loads(credentials_json_str)
        self.creds = service_account.Credentials.from_service_account_info(cred_info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        self.service = build('sheets', 'v4', credentials=self.creds)

    def _ensure_sheet_exists(self, target_sheet: str):
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        existing_sheets = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]
        if target_sheet not in existing_sheets:
            self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body={'requests': [{'addSheet': {'properties': {'title': target_sheet}}}]}).execute()
            if target_sheet != self.CACHE_SHEET:
                self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id, range=f"{target_sheet}!A1:W1", valueInputOption="USER_ENTERED", body={"values": [self.HEADERS]}).execute()
                self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id, range=f"{target_sheet}!X1", valueInputOption="USER_ENTERED", body={"values": [[self.HEADER_FORMULA]]}).execute()

    def append_data(self, target_sheet: str, row_data: list):
        self._ensure_sheet_exists(target_sheet)
        self.service.spreadsheets().values().append(spreadsheetId=self.spreadsheet_id, range=f"{target_sheet}!A:W", valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body={"values": [row_data]}).execute()

    def cache_file_id(self, file_id: str):
        self._ensure_sheet_exists(self.CACHE_SHEET)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.service.spreadsheets().values().append(spreadsheetId=self.spreadsheet_id, range=f"{self.CACHE_SHEET}!A:B", valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body={"values": [[file_id, timestamp]]}).execute()

    def get_all_cached_files(self) -> List[str]:
        self._ensure_sheet_exists(self.CACHE_SHEET)
        result = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=f"{self.CACHE_SHEET}!A:A").execute()
        return [row[0] for row in result.get('values', []) if row]

    def clear_cache(self):
        self._ensure_sheet_exists(self.CACHE_SHEET)
        self.service.spreadsheets().values().clear(spreadsheetId=self.spreadsheet_id, range=f"{self.CACHE_SHEET}!A:B").execute()

# ==========================================
# 📡 SERVERLESS ENTRY POINT (雙節點路由中樞)
# ==========================================
def telegram_reply(token: str, chat_id: str, text: str):
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        logger.error(f"Telegram API 呼叫失敗: {str(e)}")

@functions_framework.http
def webhook_receiver(request):
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    project_id = os.environ.get("GCP_PROJECT_ID")
    try:
        request_json = request.get_json(silent=True)
        if not request_json or "message" not in request_json: return "No payload", 400
        chat_id = str(request_json["message"]["chat"]["id"])
        message = request_json["message"]
        io_agent = GoogleSheetsIOAgent(spreadsheet_id, credentials_json)
        if "photo" in message:
            io_agent.cache_file_id(message["photo"][-1]["file_id"])
            telegram_reply(bot_token, chat_id, "📥 *圖片已暫存大腦海馬迴*。請繼續傳送，或輸入 `Go` / `分析` 開始聯合推導...")
            return "OK", 200
        elif "text" in message:
            if message["text"].strip().lower() in ["go", "分析"]:
                logger.info(f"🚩 [Checkpoint 1] 收到指令，準備派發任務至 Pub/Sub (專案: {project_id})")
                publisher = pubsub_v1.PublisherClient()
                topic_path = publisher.topic_path(project_id, "matrix-task-queue")
                future = publisher.publish(topic_path, b"START_ANALYSIS", chat_id=chat_id)
                future.result(timeout=10)
                logger.info("🚩 [Checkpoint 3] Pub/Sub 派發成功！")
                telegram_reply(bot_token, chat_id, "✅ *任務已進入佇列*。深度聯合推導啟動中...")
                return "OK", 200
        return "OK", 200
    except Exception as e:
        logger.critical(f"外場異常: {str(e)}")
        return "Error", 500

@functions_framework.cloud_event
def background_worker(cloud_event):
    spreadsheet_id, bot_token = os.environ.get("SPREADSHEET_ID"), os.environ.get("TELEGRAM_BOT_TOKEN")
    project_id, region = os.environ.get("GCP_PROJECT_ID"), os.environ.get("GCP_REGION")
    chat_id = cloud_event.data["message"]["attributes"].get("chat_id")
    if not chat_id: return
    try:
        io_agent = GoogleSheetsIOAgent(spreadsheet_id, os.environ.get("GOOGLE_CREDENTIALS_JSON"))
        cached_files = io_agent.get_all_cached_files()
        if not cached_files: return
        image_bytes_list = []
        for fid in cached_files:
            file_path = requests.get(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={fid}").json()["result"]["file_path"]
            image_bytes_list.append(requests.get(f"https://api.telegram.org/file/bot{bot_token}/{file_path}").content)
        vision_agent = VisionAgent(project_id, region, os.environ.get("GOOGLE_CREDENTIALS_JSON"))
        analysis_result = QuantCoreAgent.process_daily(json.loads(re.sub(r'```json\n?|```', '', vision_agent.analyze_chart(image_bytes_list)).strip()))
        io_agent.append_data(analysis_result["target_sheet"], analysis_result["row_data"])
        io_agent.clear_cache()
        telegram_reply(bot_token, chat_id, f"✅ *大腦解析完成！標的: `{analysis_result['ticker']}`，矩陣: {analysis_result['state']}*")
    except Exception as e:
        logger.critical(f"內場異常: {str(e)}")
        telegram_reply(bot_token, chat_id, f"🛑 [SRE 警報] 內場運算引擎發生例外: {str(e)}")