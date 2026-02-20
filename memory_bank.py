import time
import requests
import uuid
import global_var
from qdrant_client import QdrantClient
from qdrant_client.http import models



class MemoryBank:
    def __init__(self):
        # 1. 初始化時直接連接並檢查 Collections
        try:
            self.client = QdrantClient(
                host=global_var.PORTS["QDRANT"]["host"], 
                port=global_var.PORTS["QDRANT"]["port"]
            )
            self._ensure_collections()
            print("✅ 小丸記憶庫已連接", flush=True)
        except Exception as e:
            print(f"❌ 記憶庫連接失敗: {e}", flush=True)
            self.client = None

    def _ensure_collections(self):
        """(私有方法) 確保所需的 Collection 存在"""
        if not self.client: return
        try:
            collections = {"trinity_knowledge": 1024, "chat_memory": 1024}
            existing = [c.name for c in self.client.get_collections().collections]
            for name, dim in collections.items():
                if name not in existing:
                    self.client.create_collection(
                        name, 
                        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE)
                    )
        except: pass

    def _get_dify_context(self, query_text):
        """
        根據 Dify 官方回傳結構解析知識庫內容
        """
        # 1. 基本配置 (請確保 dataset_id 正確)
        DIFY_API_KEY = "dataset-JbnVJj7QfATRC9L8OqbZCB1U"
        DATASET_ID = "949aa016-3dff-45e3-9f9a-0298b19ef304"

        DIFY_URL = f"http://localhost/v1/datasets/{DATASET_ID}/retrieve"
        
        headers = {
            "Authorization": f"Bearer {DIFY_API_KEY}",
            "Content-Type": "application/json"
        }

        # 2. 檢索參數 (對標你提供的 Retrieve 格式)
        payload = {
            "query": query_text,
            "retrieval_model": {
                "search_method": "hybrid_search",
                "reranking_enable": False, # 👈 設為 False
                "top_k": 5,
                "weights": 0.5, # 向量與關鍵字各佔一半權重
                "score_threshold_enabled": False
            }
        }

        try:
            resp = requests.post(DIFY_URL, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get('records', [])
                
                parts = []
                for rec in records:
                    # 💡 重點修正：根據你提供的 JSON 結構，內容在 segment 內
                    segment = rec.get('segment', {})
                    text_content = segment.get('content', '')
                    
                    if text_content:
                        # 獲取檔案來源名稱 (如果有)
                        doc_name = segment.get('document', {}).get('name', '知識庫文檔')
                        parts.append(f"【參考來源: {doc_name}】\n{text_content}")
                
                return "\n\n".join(parts) if parts else ""
            else:
                print(f"⚠️ Dify 檢索失敗: {resp.status_code} - {resp.text}", flush=True)
                return ""
        except Exception as e:
            print(f"❌ Dify 連線異常: {e}", flush=True)
            return ""

    def _get_vector(self, text):
        """(私有方法) 取得文字的向量"""
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
        
    def get_context(self, query_text):
        """整合所有來源的上下文"""
        if not query_text: return []
        print(f"🔍 小丸回憶中...", flush=True)

        parts = []
        
        # 1. 先去 Dify 找專業知識
        dify_knowledge = self._get_dify_context(query_text)
        if dify_knowledge:
            parts.append(f"【專業知識庫參考資料】：\n{dify_knowledge}")
            
        # 2. 再找本地 Qdrant 的對話回憶 (chat_memory)
        if self.client:
            vec = self._get_vector(query_text)
            if vec:
                try:
                    h = self.client.search(collection_name="chat_memory", query_vector=vec, limit=2)
                    mem = "\n".join([f"- {r.payload.get('content')}" for r in h if r.score > 0.5])
                    if mem:
                        parts.append(f"【過往對話回憶】：\n{mem}")
                except: pass
        
        return "\n\n".join(parts) if parts else ""

    def save_memory(self, q, a):
        """儲存並總結記憶"""
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
                vec = self._get_vector(summary)
                if vec:
                    self.client.upsert(
                        collection_name="chat_memory",
                        points=[models.PointStruct(
                            id=str(uuid.uuid4()), # 已改用 UUID
                            vector=vec,
                            payload={"content": summary, "time": time.ctime()}
                        )]
                    )
                print(f"💾 寫入記憶: {summary[:20]}...", flush=True)
        except: pass
        
    def add_to_knowledge(self, text, metadata=None):
        """
        將 Web Client 傳來的知識存入 trinity_knowledge
        """
        if not self.client: return 0
        
        # 1. 文本切片 (Chunking)
        chunk_size = 500
        overlap = 50
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]
        
        points = []
        for chunk in chunks:
            if not chunk.strip(): continue
            
            # 2. 使用私有方法 _get_vector 取得向量
            vector = self._get_vector(chunk)
            if not vector: continue
            
            # 3. 封裝 Point
            points.append(models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": chunk,  # 👈 這裡必須用 'text'，因為 get_context 是抓這個欄位
                    "metadata": metadata or {},
                    "source": "web_upload",
                    "timestamp": time.time()
                }
            ))
        
        # 4. 批量寫入 Qdrant
        if points:
            self.client.upsert(
                collection_name="trinity_knowledge",
                points=points
            )
            print(f"📚 知識入庫成功: 增加了 {len(points)} 個區塊", flush=True)
            return len(points)
        return 0