import time
import requests
import uuid
import global_var

from qdrant_client import QdrantClient
from qdrant_client.http import models

def get_vector(text):
    if not text: return []
    payload = {"input": text, "model": global_var.MODELS["EMBED"]}
    try:
        try:
            resp = requests.post(global_var.PORTS["EMBED"], json=payload, timeout=5)
            resp.raise_for_status()
        except:
            fallback = global_var.PORTS["EMBED"].replace("/embeddings", "/v1/embeddings")
            resp = requests.post(fallback, json=payload, timeout=5)
        data = resp.json()
        if 'data' in data: return data['data'][0]['embedding']
        if isinstance(data, list): return data[0]['embedding']
        return []
    except: return []

def ensure_collections(client):
    if not client: return
    try:
        collections = {"trinity_knowledge": 1024, "chat_memory": 1024}
        existing = [c.name for c in client.get_collections().collections]
        for name, dim in collections.items():
            if name not in existing:
                client.create_collection(name, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
    except: pass

class MemoryBank:
    client = None
    
    def __init__(self):
        # 連接記憶庫
        try:
            self.client = QdrantClient(
                host=global_var.PORTS["QDRANT"]["host"], 
                port=global_var.PORTS["QDRANT"]["port"]
            )
            ensure_collections(self.client)
            print("✅ 小丸記憶庫已連接", flush=True)
        except Exception as e:
            # 發生錯誤時，self.client 會保持 None 或拋出錯誤
            print(f"❌ 記憶庫連接失敗: {e}", flush=True)
            self.client = None
        
    def get_context(self, query_text):
        if not self.client: return ""
        
        print(f"🔍 小丸回憶中...", flush=True)
        
        vec = get_vector(query_text)
        if not vec: return ""
        parts = []
        try:
            k = self.client.search(collection_name="trinity_knowledge", query_vector=vec, limit=2)
            if k: 
                t = "\n".join([r.payload.get('text', '') for r in k if r.score > 0.4])
                if t: parts.append(f"【知識庫】：\n{t}")
        except: pass
        try:
            h = self.client.search(collection_name="chat_memory", query_vector=vec, limit=3)
            if h:
                t = "\n".join([f"- {r.payload.get('content')} ({r.payload.get('time')})" for r in h if r.score > 0.5])
                if t: parts.append(f"【回憶】：\n{t}")
        except: pass
        return "\n\n".join(parts) if parts else ""

    def save_memory(self, q, a):
        if not self.client: return
        
        prompt = f"摘要對話重點。若是閒聊/打招呼/廢話，只回 SKIP。若是重要資訊/設定/技術教學，請總結。\n問：{q}\n答：{a}"
        
        try:
            resp = requests.post(global_var.PORTS["15B"], json={
                "model": global_var.MODELS["15B"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1, "max_tokens": 100
            }, timeout=5)
            summary = resp.json()['choices'][0]['message']['content'].strip()
            
            if "SKIP" not in summary.upper() and len(summary) > 5:
                vec = get_vector(summary)
                if vec:
                    self.client.upsert(
                        collection_name="chat_memory",
                        points=[models.PointStruct(
                            id=str(uuid.uuid4()),  # <--- 改成使用 UUID
                            vector=vec,
                            payload={"content": summary, "time": time.ctime()}
                        )]
                    )
                print(f"💾 寫入記憶: {summary[:20]}...", flush=True)
        except: pass        
