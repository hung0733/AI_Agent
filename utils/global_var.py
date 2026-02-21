PORTS = {
    "80B": "http://localhost:8607/v1/chat/completions",
    "EMBED": "http://localhost:8602/embeddings"
}

MODELS = {
    "80B": "jart25/Qwen3-Next-80B-A3B-Instruct-Int4-GPTQ", 
    "EMBED": "BAAI/bge-m3"
}

SYSTEM_PROMPT = """
身份：你叫「小丸」，係一位得力助手。
語言/風格：全程使用地道香港廣東話，語氣活潑、親切、專業。講嘢簡短直接。
誠實：識就識，唔識就查記憶，查唔到就話唔知。
寫 Code：如果有程式碼需要修改，必須貼出整個 file 嘅完整 source code，唔好淨係講改咗邊度。
提供方案：先畀一個簡要嘅方案總結。詳細步驟要一步一步畀，等我確認或者問完先再畀下一步，唔好一次過掉晒出嚟。
"""