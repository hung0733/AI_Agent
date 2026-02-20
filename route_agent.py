import time
import requests
import global_var

from memory_bank import MemoryBank

class RouteAgent:
    _mb = None

    @classmethod
    def get_mb(cls):
        if cls._mb is None:
            cls._mb = MemoryBank()
        return cls._mb
    
    @staticmethod
    def determine_difficulty(user_input):
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
    
    @staticmethod
    def route_question(user_input, allowDeepThink = False):
        mb = RouteAgent.get_mb()
        
        # 1. 檢索 RAG 上下文
        context = mb.get_context(user_input)
        
        # 2. 判斷難度
        difficulty = RouteAgent.determine_difficulty(user_input)
        
        # 3. 決定路由參數 (這裡可以重構成一個 Dict 映射表，更優雅)
        config = {
            "HARD": (global_var.PORTS["80B"], global_var.MODELS["80B"], 900, "\n(當前模式：深度思考。請提供極具邏輯性、結構嚴謹、有深度的詳細回答。)", "🎓 召喚 80B 博士..."),
            "MEDIUM": (global_var.PORTS["30B"], global_var.MODELS["30B"], 150, "", "⚡ 使用 30B 主腦..."),
            "EASY": (global_var.PORTS["15B"], global_var.MODELS["15B"], 30, "", "🐇 使用 1.5B 快速回應...")
        }
        
        # 如果 HARD 但不允許 DeepThink，自動降級到 MEDIUM
        active_level = difficulty
        if difficulty == "HARD" and not allowDeepThink:
            active_level = "MEDIUM"
            
        target_url, target_model, timeout_val, extra_prompt, msg = config[active_level]
        
        sys_prompt = global_var.SYSTEM_PROMPT + extra_prompt
        
        print(msg, flush=True)

        # 執行生成
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"【背景資料】：\n{context}\n\n【用戶問題】：{user_input}"}
            ],
            "temperature": 0.7
        }

        try:
            start_t = time.time()
            # 發送請求
            resp = requests.post(target_url, json=payload, timeout=timeout_val)
            
            if resp.status_code != 200:
                raise Exception(f"Status {resp.status_code}")
                
            answer = resp.json()['choices'][0]['message']['content']
            duration = time.time() - start_t
            
            # 計算生成速度 (估算)
            speed = len(answer) / duration if duration > 0 else 0
            print(f"✅ 生成完畢 (耗時: {duration:.1f}s | 速度: ~{speed:.1f} chars/s)", flush=True)
            
            mb.save_memory(user_input, answer)
            return answer

        except Exception as e:
            print(f"❌ {target_model} 連接失敗/超時: {e}", flush=True)
            
            if difficulty == "HARD":
                print(f"🔄 80B 太慢/無反應，嘗試切換回 30B 救場...", flush=True)
                try:
                    payload["model"] = global_var.MODELS["30B"]
                    resp = requests.post(global_var.PORTS["30B"], json=payload, timeout=120)
                    answer = resp.json()['choices'][0]['message']['content']
                    
                    # 💡 記得補上記憶儲存
                    mb.save_memory(user_input, answer) 
                    
                    return answer + "\n(⚠️ 註：博士思考超時，此乃 30B 代答)"
                except:
                    return "抱歉，連接超時，請稍後再試。"
            return "系統繁忙，請稍後再試。"           