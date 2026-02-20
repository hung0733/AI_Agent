# main.py
import time
import json
import base64
import requests
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
# 你指定的新 API Key
API_KEY = "QUktSFVORyBTZXJ2ZXIgQUkgQWdlbnQ"

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# --- 3. 初始化大腦 ---
# 確保在全域初始化一次，避免每次 Request 都重連 Qdrant
agent = RouteAgent()

# --- 4. OpenAI 相容的資料結構 ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "qwen3-trinity"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = True

# --- 5. OpenAI 標準 Model List API ---
@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    models = [
        {"id": "qwen3-trinity", "object": "model", "created": int(time.time()), "owned_by": "trinity"},
        {"id": "qwen3-omni", "object": "model", "created": int(time.time()), "owned_by": "trinity"},
    ]
    return {"object": "list", "data": models}

# --- 6. 核心路由：/v1/chat/completions (支援 Stream) ---
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: ChatCompletionRequest):
    user_input = request.messages[-1].content
    chat_id = f"chatcmpl-{int(time.time())}"
    created_time = int(time.time())
    
    # --- 支援 Non-stream (例如 Dify 校驗) ---
    if not request.stream:
        full_answer = "".join([chunk for chunk in agent.route_question(user_input, allowDeepThink=True)])
        return {
            "id": chat_id, "object": "chat.completion", "created": created_time,
            "model": request.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": full_answer}, "finish_reason": "stop"}]
        }
    
    # --- 真正的 Streaming 轉發 ---
    async def stream_generator():
        try:
            # 這裡確保 agent.route_question 內部也是用 yield 實時產出
            for chunk in agent.route_question(user_input, allowDeepThink=True):
                if not chunk: continue
                chunk_data = {
                    "id": chat_id, "object": "chat.completion.chunk", "created": created_time,
                    "model": request.model,
                    "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            
            # 結束標記
            yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = {"error": {"message": str(e), "type": "server_error"}}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

# --- 7. 多模態路由：/api/omni ---
@app.post("/api/omni", dependencies=[Depends(verify_api_key)])
async def omni_endpoint(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    try:
        content_list = []
        user_prompt = text if text else "請分析內容。"
        content_list.append({"type": "text", "text": user_prompt})

        if image:
            img_bytes = await image.read()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            content_list.append({
                "type": "image_url",
                "image_url": {"url": f"data:{image.content_type};base64,{img_b64}"}
            })

        if audio:
            audio_bytes = await audio.read()
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            content_list.append({
                "type": "audio_url",
                "audio_url": {"url": f"data:{audio.content_type};base64,{audio_b64}"}
            })

        # 呼叫 Omni 模型理解
        omni_payload = {
            "model": global_var.MODELS["30B_OMNI"],
            "messages": [{"role": "user", "content": content_list}],
            "temperature": 0.2
        }
        resp = requests.post(global_var.PORTS["30B_OMNI"], json=omni_payload, timeout=60)
        omni_text = resp.json()['choices'][0]['message']['content'].strip()

        # 將理解後的文字送入大腦路由
        final_answer = agent.route_question(omni_text, allowDeepThink=True)

        return {
            "status": "success",
            "agent_response": {
                "text": final_answer,
                "expression": "Smile",
                "action": "Nodding"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/v1/knowledge/add")
async def add_knowledge(data: dict):
    text = data.get("content")
    filename = data.get("filename", "manual_input")
    if not text:
        return {"error": "No content provided"}

    # 調用 MemoryBank 的 add_to_knowledge
    count = agent.mb.add_to_knowledge(text, {"filename": filename})
    return {"status": "success", "chunks_added": count}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8600, reload=True)