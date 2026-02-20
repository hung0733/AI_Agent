# main.py
import time
import base64
import requests
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

import global_var
from route_agent import RouteAgent

app = FastAPI(title="Trinity AI Agent API")

# --- 1. CORS 設定 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. API Key 驗證設定 ---
security = HTTPBearer()
API_KEY = "sk-trinity-agent-secret-key" # ⚠️ 請修改為你的密碼

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# --- 3. OpenAI 相容的資料結構 ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "trinity-router"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

# --- 4. 路由：/v1/chat/completions (純文字大腦路由入口) ---
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: ChatCompletionRequest):
    try:
        user_message = request.messages[-1].content
        
        # 呼叫你寫好嘅 RouteAgent (根據你上傳嘅版本，使用 @staticmethod)
        answer = RouteAgent.route_question(user_message, allowDeepThink=True)
        
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
    except Exception as e:
        print(f"❌ API 發生錯誤: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- 5. 路由：/api/omni (感官接收 -> Omni 轉譯 -> 路由大腦) ---
@app.post("/api/omni", dependencies=[Depends(verify_api_key)])
async def omni_endpoint(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    try:
        print("👁️👂 啟動 Omni 感官接收...", flush=True)
        content_list = []

        # 1. 處理文字 (如果冇文字，畀個預設 prompt 佢)
        user_text = text if text else "請綜合分析提供的圖片與語音，轉化成文字描述或問題。"
        content_list.append({"type": "text", "text": user_text})

        # 2. 處理圖片轉 Base64
        if image:
            img_bytes = await image.read()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            img_mime = image.content_type or "image/jpeg"
            content_list.append({
                "type": "image_url",
                "image_url": {"url": f"data:{img_mime};base64,{img_b64}"}
            })
            print(f"📸 收到圖片: {image.filename} ({img_mime})", flush=True)

        # 3. 處理聲音轉 Base64
        if audio:
            audio_bytes = await audio.read()
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            audio_mime = audio.content_type or "audio/wav"
            # 備註：vLLM 或多模態引擎通常使用 audio_url 欄位接收音檔
            content_list.append({
                "type": "audio_url", 
                "audio_url": {"url": f"data:{audio_mime};base64,{audio_b64}"}
            })
            print(f"🎤 收到語音: {audio.filename} ({audio_mime})", flush=True)

        # 4. 呼叫 Omni 模型進行理解與轉譯
        omni_payload = {
            "model": global_var.MODELS["30B_OMNI"],
            "messages": [
                {
                    "role": "system",
                    "content": "你係AI系統的「感官神經」。請綜合理解用戶提供的語音、圖片及文字。將它們翻譯、總結並轉化為一個清晰的純文字問題或指令。只需輸出轉換後的純文字，不要包含任何解釋、問候或多餘字句。"
                },
                {
                    "role": "user",
                    "content": content_list
                }
            ],
            "temperature": 0.2
        }

        print(f"📡 傳送資料至 Omni 模型 ({global_var.MODELS['30B_OMNI']})...", flush=True)
        omni_resp = requests.post(global_var.PORTS["30B_OMNI"], json=omni_payload, timeout=60)
        
        if omni_resp.status_code != 200:
            raise Exception(f"Omni 模型 HTTP 錯誤: {omni_resp.status_code} - {omni_resp.text}")

        # 擷取 Omni 理解後轉換出的純文字
        omni_analyzed_text = omni_resp.json()['choices'][0]['message']['content'].strip()
        print(f"✅ Omni 分析完成，轉譯文字為: 「{omni_analyzed_text}」", flush=True)

        # 5. 將 Omni 分析完的純文字，交畀 Routing Agent 做難度判斷與深度回答
        print(f"🧠 將轉譯結果交畀大腦路由處理...", flush=True)
        final_answer = RouteAgent.route_question(omni_analyzed_text, allowDeepThink=True)

        # 6. 回傳最終結果 (未來可以加 TTS 將文字轉語音放喺 audio_base64)
        return {
            "status": "success",
            "agent_response": {
                "text": final_answer,
                "audio_base64": "", # 預留畀「口」
                "expression": "Smile", 
                "action": "Nodding"
            },
            # 回傳埋 Omni 嘅轉譯結果，方便前端 debug 睇吓佢理解得啱唔啱
            "omni_transcription": omni_analyzed_text 
        }
        
    except Exception as e:
        print(f"❌ Omni 端點發生錯誤: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)