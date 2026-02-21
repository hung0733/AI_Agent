# server_conf.py

class Config:
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 8600
    
    # --- Vision Model (A Model) ---
    URL_VISION = "http://localhost:11434/v1/chat/completions"
    MODEL_VISION = "llama3.2-vision"

    # --- Text Model (B Model - 你指定的 Qwen 80B) ---
    URL_TEXT = "http://localhost:8607/v1/chat/completions"
    MODEL_TEXT = "qwen-80b-instruct"

# --- 視覺引導語 ---
    # 確保 Vision Model 輸出最詳盡嘅描述，方便 80B 思考
    VISION_PROMPT_PREFIX = "請詳細描述圖中所有細節，包括物件、文字、環境及氛圍，作為後續分析嘅參考資料："

    # --- 其他 Backend ---
    URL_WHISPER = "http://localhost:9000/v1/audio/transcriptions"
    URL_TTS = "http://localhost:5000/v1/audio/speech"

    # --- OpenAI 兼容 Model 清單 ---
    AVAILABLE_MODELS = [
        {"id": "gpt-4o", "object": "model", "owned_by": "local-proxy"},
        {"id": "whisper-1", "object": "model", "owned_by": "local-proxy"},
        {"id": "tts-1", "object": "model", "owned_by": "local-proxy"}
    ]

    # 內部映射
    MODEL_MAPPING = {
        "whisper-1": "whisper-large-v3",
        "tts-1": "piper-high-quality"
    }

    TIMEOUTS = {
        "stt": 60.0,
        "llm": None,  # Streaming 通常唔設 Timeout，費事斷線
        "tts": 30.0
    }