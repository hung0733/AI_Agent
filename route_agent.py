import time
import requests
import json
import threading
import global_var
from memory_bank import MemoryBank

class RouteAgent:
    def __init__(self):
        # 實例化時自動綁定一個記憶庫
        self.mb = MemoryBank()
    
    def determine_difficulty(self, user_input):
        gatekeeper_prompt = f"""
        你是 AI 路由分類員。請分析用戶輸入，嚴格判斷是否需要「博士級」模型處理。
        
        【HARD 標準】(必須符合，否則不選):
        1. 深度邏輯推理 (Deep Logic / Paradox)
        2. 複雜架構設計 (Complex Architecture)
        3. 深度數學/物理推導 (Math / Physics)
        4. 哲學/倫理深度思考 (Philosophy)
        5. 創意寫作 (Novel / Script)

        【MEDIUM 標準】:
        - Coding, Translation, Explanation, General Q&A

        【EASY 標準】:
        - Greeting, Chit-chat, Simple Fact

        User: "{user_input}"
        Output ONLY: EASY, MEDIUM, or HARD.
        """
        try:
            resp = requests.post(
                global_var.PORTS["15B"],
                json={"model": global_var.MODELS["15B"], "messages": [{"role": "user", "content": gatekeeper_prompt}], "temperature": 0.1, "max_tokens": 5},
                timeout=5
            )
            level = resp.json()['choices'][0]['message']['content'].strip().upper()
            if "HARD" in level: return "HARD"
            if "MEDIUM" in level: return "MEDIUM"
            return "EASY"
        except:
            return "MEDIUM"
    
    def route_question(self, user_input, allowDeepThink=False):
        # 1. 進入思考區塊
        yield "<thinking>\n"
        yield "🔍 正在分析問題複雜度與檢索知識庫...\n"
        
        # 檢索與難度判斷 (這兩步現在是阻塞的，但前端已經收到上面的字了)
        context = self.mb.get_context(user_input)
        difficulty = self.determine_difficulty(user_input)
        
        yield f"✅ 路由判定：{difficulty}\n"
        yield "📚 知識庫檢索完成\n"
        yield "啟動大腦中...\n"
        yield "</thinking>\n\n" # 結束思考區塊，準備輸出正文
        
        config = {
            "HARD": (global_var.PORTS["80B"], global_var.MODELS["80B"], 900, "\n(當前模式：深度思考)"),
            "MEDIUM": (global_var.PORTS["30B"], global_var.MODELS["30B"], 150, ""),
            "EASY": (global_var.PORTS["15B"], global_var.MODELS["15B"], 30, "")
        }
        
        active_level = "MEDIUM" if (difficulty == "HARD" and not allowDeepThink) else difficulty
        target_url, target_model, timeout_val, extra_prompt = config[active_level][:4]
        
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": global_var.SYSTEM_PROMPT + extra_prompt},
                {"role": "user", "content": f"【背景資料】：\n{context}\n\n【用戶問題】：{user_input}"}
            ],
            "temperature": 0.7,
            "stream": True 
        }

        print(f"📡 正在請求模型: {target_model} @ {target_url}", flush=True)

        full_content = ""
        try:
            # 使用 stream=True 請求 8607/8603
            with requests.post(target_url, json=payload, timeout=timeout_val, stream=True) as resp:
                for line in resp.iter_lines(chunk_size=1):
                    if not line: continue
                    
                    line_text = line.decode("utf-8").strip()
                    if line_text.startswith("data: "):
                        data_str = line_text[6:]
                        if data_str == "[DONE]": break
                        
                        try:
                            data_json = json.loads(data_str)
                            delta = data_json['choices'][0].get('delta', {})
                            chunk = delta.get('content') or ""
                            if chunk:
                                full_content += chunk
                                yield chunk # 👈 即時 yield 給 main.py
                        except: continue

            # 全部完咗先一次過存入記憶，唔好喺 yield 中間做，費事拖慢速度
            if full_content:
                print(f"💾 正在背景儲存記憶...", flush=True)
                # 使用 threading 異步執行，不阻塞當前的 yield 流程
                save_thread = threading.Thread(
                    target=self.mb.save_memory, 
                    args=(user_input, full_content)
                )
                save_thread.start()

        except Exception as e:
            yield f"\n❌ 大腦連線中斷: {str(e)}"