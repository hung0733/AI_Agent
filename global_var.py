
PORTS = {
    "80B": "http://localhost:8607/v1/chat/completions",
    "30B": "http://localhost:8601/v1/chat/completions",
    "30B_OMNI": "http://localhost:8606/v1/chat/completions",
    "15B": "http://localhost:8603/v1/chat/completions",
    "VL":  "http://localhost:8604/v1/chat/completions",
    "EMBED": "http://localhost:8602/embeddings",
    "QDRANT": {"host": "localhost", "port": 6333}
}

MODELS = {
    "80B": "jart25/Qwen3-Next-80B-A3B-Instruct-Int4-GPTQ", 
    "30B": "JunHowie/Qwen3-30B-A3B-Instruct-2507-GPTQ-Int4",
    "30B_OMNI": "jart25/Qwen3-Omni-30B-A3B-Instruct-AWQ-W4A16",
    "15B": "Qwen/Qwen2.5-1.5B-Instruct",
    "VL":  "Qwen/Qwen3-VL-4B-Instruct",
    "EMBED": "BAAI/bge-m3"
}

SYSTEM_PROMPT = """
你係 **小丸 (Xiao Wan)**，一個由 Trinity 架構驅動嘅智能助理。
行為準則：
1. **身份**：你叫「小丸」，係一位得力助手。
2. **語言**：全程使用 **地道香港廣東話**，語氣活潑、親切、專業。
3. **誠實**：識就識，唔識就查記憶，查唔到就話唔知。
"""