# main.py
import io
import httpx
import uvicorn
import json
import base64
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image
from server_conf import Config

class LocalAIProxy:
    def __init__(self):
        self.app = FastAPI(title="Local AI Chain Proxy (Full Integrated)")
        self.client = httpx.AsyncClient(timeout=None)
        self.setup_routes()

    def setup_routes(self):
        """重新掛載所有 Endpoint，確保 STT/TTS 恢復運作"""
        self.app.get("/v1/models")(self.get_models)
        self.app.post("/v1/chat/completions")(self.chat_completions)
        self.app.post("/v1/audio/transcriptions")(self.speech_to_text)
        self.app.post("/v1/audio/speech")(self.text_to_speech)

    async def get_models(self):
        return {"object": "list", "data": Config.AVAILABLE_MODELS}

    # --- 關鍵：[年月日時分秒][文字] 數據收集與 80B 糾錯 ---
    async def _fix_and_save_speech(self, raw_audio_bytes, raw_text):
        """傳送至 V100 Server 進行糾錯，並本地儲存"""
        # 使用 Qwen-80B (V100 Server) 進行廣東話糾錯
        fix_prompt = f"用戶發音唔清，請根據廣東話語境修正錯字，只需輸出修正後的廣東話文字：\n{raw_text}"
        
        try:
            # 射去 80B 大腦所在的伺服器
            resp = await self.client.post(Config.URL_TEXT, json={
                "model": Config.MODEL_TEXT,
                "messages": [{"role": "user", "content": fix_prompt}],
                "stream": False
            })
            fixed_text = resp.json()["choices"][0]["message"]["content"].strip()
            
            # 檔名格式: [20260221215508][你好呀]
            timestamp = time.strftime("%Y%m%d%H%M%S")
            # 移除檔名不合法字元
            safe_text = "".join([c for c in fixed_text if c.isalnum() or c in " "]).strip()
            filename_base = f"[{timestamp}][{safe_text}]"
            
            # 儲存到 3090 這部機的本地硬碟
            with open(os.path.join("training_data", f"{filename_base}.mp3"), "wb") as f:
                f.write(raw_audio_bytes)
            with open(os.path.join("training_data", f"{filename_base}.txt"), "w", encoding="utf-8") as f:
                f.write(fixed_text)
            
            print(f"💾 [SAVED TO DATASET] {filename_base}")
            return fixed_text
        except Exception as e:
            print(f"⚠️ 糾錯失敗: {e}")
            return raw_text

    async def speech_to_text(self, file: UploadFile = File(...)):
        audio_content = await file.read()
        # 3090 上的 Faster Whisper
        files = {"file": (file.filename, audio_content, file.content_type)}
        resp = await self.client.post(Config.URL_WHISPER, files=files, data={"model": "large-v3"})
        raw_text = resp.json().get("text", "")
        
        # 呼叫 V100 上的 80B 執字並儲存
        fixed_text = await self._fix_and_save_speech(audio_content, raw_text)
        return {"text": fixed_text}

    async def text_to_speech(self, request: Request):
        try:
            body = await request.json()
            input_text = body.get("input", "")
            print(f"🔊 [TTS] 收到語音請求: {input_text[:30]}...")
            
            body["model"] = Config.MODEL_MAPPING.get(body.get("model", "tts-1"), "piper-high-quality")
            
            async def audio_stream():
                async with self.client.stream("POST", Config.URL_TTS, json=body) as r:
                    async for chunk in r.aiter_bytes():
                        yield chunk

            return StreamingResponse(audio_stream(), media_type="audio/mpeg")
        except Exception as e:
            print(f"❌ [TTS ERROR]: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _resize_image_if_needed(self, base64_image_str):
        """圖片自動縮放至 1080p 邏輯"""
        try:
            header, encoded = base64_image_str.split(",", 1)
            img_data = base64.b64decode(encoded)
            img = Image.open(io.BytesIO(img_data))
            
            orig_w, orig_h = img.size
            max_w, max_h = 1920, 1080

            if orig_w > max_w or orig_h > max_h:
                print(f"📏 [RESIZE] 圖片太大 ({orig_w}x{orig_h}) -> 縮放至 1080p")
                ratio = min(max_w / orig_w, max_h / orig_h)
                new_size = (int(orig_w * ratio), int(orig_h * ratio))
                img = img.resize(new_size, Image.LANCZOS)
                
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=90)
                new_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                return f"{header},{new_base64}"
            return base64_image_str
        except Exception as e:
            print(f"⚠️ [RESIZE WARNING] 縮放失敗: {e}")
            return base64_image_str

    def _extract_user_text(self, messages):
        for msg in reversed(messages):
            if msg["role"] == "user":
                content = msg.get("content")
                if isinstance(content, str): return content
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text": return item.get("text")
        return "(冇文字輸入)"

    # --- 核心連鎖分析 ---

    async def _get_vision_description(self, messages):
        print("\n" + "📸" * 20 + "\n [PHASE 1] 視覺分析進行中...")
        
        # 縮放處理
        for msg in messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                for item in msg["content"]:
                    if item["type"] == "image_url":
                        url_val = item["image_url"]["url"]
                        if url_val.startswith("data:image"):
                            item["image_url"]["url"] = self._resize_image_if_needed(url_val)

        vision_body = {"model": Config.MODEL_VISION, "messages": messages, "stream": False}
        
        # 注入分析指令
        for msg in vision_body["messages"]:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                for item in msg["content"]:
                    if item["type"] == "text":
                        item["text"] = f"{Config.VISION_PROMPT_PREFIX}\n{item['text']}"
        
        resp = await self.client.post(Config.URL_VISION, json=vision_body)
        description = resp.json()["choices"][0]["message"]["content"]
        
        print(f"\n📝 [VISION NOTES]:\n{description}\n")
        print("📸" * 20)
        return description

    async def chat_completions(self, request: Request):
        try:
            body = await request.json()
            messages = body.get("messages", [])
            is_streaming = body.get("stream", False)

            user_text = self._extract_user_text(messages)
            print("\n" + "💬" * 20)
            print(f" 👤 USER INPUT: {user_text}")

            has_image = any(isinstance(m.get("content"), list) and any(i.get("type") == "image_url" for i in m["content"]) for m in messages)

            if has_image:
                description = await self._get_vision_description(messages)
                new_prompt = f"【視覺筆記】\n{description}\n\n【用戶原始問題】\n{user_text}"
                body["messages"] = [{"role": "user", "content": new_prompt}]
                body["model"] = Config.MODEL_TEXT
                target_url = Config.URL_TEXT
                print(f" 🧠 [ROUTE] 結合視覺，發送至 80B")
            else:
                body["model"] = Config.MODEL_TEXT
                target_url = Config.URL_TEXT
                print(f" 🧠 [ROUTE] 純文字，發送至 80B")
            
            print("💬" * 20 + "\n")

            if is_streaming:
                async def stream_generator():
                    async with self.client.stream("POST", target_url, json=body) as r:
                        async for line in r.aiter_lines():
                            if line: yield f"{line}\n\n"
                return StreamingResponse(stream_generator(), media_type="text/event-stream")
            else:
                resp = await self.client.post(target_url, json=body)
                return resp.json()

        except Exception as e:
            print(f"❌ [PROXY ERROR]: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def run(self):
        print(f"🚀 Proxy Server 啟動! 監聽 Port: {Config.SERVER_PORT}")
        uvicorn.run(self.app, host=Config.SERVER_HOST, port=Config.SERVER_PORT)

if __name__ == "__main__":
    LocalAIProxy().run()