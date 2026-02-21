# main.py
import io
import httpx
import uvicorn
import json
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import StreamingResponse
from server_conf import Config

class LocalAIProxy:
    def __init__(self):
        self.app = FastAPI(title="Local AI Streaming Proxy")
        self.setup_routes()
        # 注意：timeout 要設為 None 嚟支援長對話 streaming
        self.client = httpx.AsyncClient(timeout=None)

    def setup_routes(self):
        self.app.get("/v1/models")(self.get_models)
        self.app.post("/v1/audio/transcriptions")(self.speech_to_text)
        self.app.post("/v1/audio/speech")(self.text_to_speech)
        self.app.post("/v1/chat/completions")(self.chat_completions)

    async def get_models(self):
        return {"object": "list", "data": Config.AVAILABLE_MODELS}

    def _has_image(self, messages):
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        return True
        return False

    def _get_llm_route(self, body):
        messages = body.get("messages", [])
        if self._has_image(messages):
            body["model"] = Config.MODEL_VISION
            return Config.URL_VISION, body
        else:
            body["model"] = Config.MODEL_TEXT
            return Config.URL_TEXT, body

    async def speech_to_text(self, file: UploadFile = File(...), model: str = Form("whisper-1")):
        try:
            local_model = Config.MODEL_MAPPING.get(model, model)
            audio_content = await file.read()
            files = {"file": (file.filename, audio_content, file.content_type)}
            data = {"model": local_model}
            response = await self.client.post(Config.URL_WHISPER, files=files, data=data)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def text_to_speech(self, request: Request):
        try:
            body = await request.json()
            body["model"] = Config.MODEL_MAPPING.get(body.get("model", "tts-1"), "piper-high-quality")
            
            # 建立一個 generator 嚟流式傳輸音訊
            async def audio_stream():
                async with self.client.stream("POST", Config.URL_TTS, json=body) as r:
                    async for chunk in r.aiter_bytes():
                        yield chunk

            return StreamingResponse(audio_stream(), media_type="audio/mpeg")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def chat_completions(self, request: Request):
        try:
            body = await request.json()
            is_streaming = body.get("stream", False)
            target_url, updated_body = self._get_llm_route(body)

            if is_streaming:
                # 處理 Streaming 邏輯
                async def stream_generator():
                    async with self.client.stream("POST", target_url, json=updated_body) as r:
                        async for line in r.aiter_lines():
                            if line:
                                yield f"{line}\n\n"
                
                return StreamingResponse(stream_generator(), media_type="text/event-stream")
            else:
                # 處理非 Streaming 邏輯
                response = await self.client.post(target_url, json=updated_body)
                return response.json()

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

    def run(self):
        print(f"🚀 Streaming 代理啟動！Port: {Config.SERVER_PORT}")
        uvicorn.run(self.app, host=Config.SERVER_HOST, port=Config.SERVER_PORT)

if __name__ == "__main__":
    proxy = LocalAIProxy()
    proxy.run()