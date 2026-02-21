from qwen_agent.memory import Memory

class MemoryManager:
    def __init__(self):
        # 初始化永久記憶庫
        self.rag = Memory(
            llm_cfg={'model': 'qwen2.5-72b-instruct'},
            files=['./data/knowledge_base/'] # 自動掃描該目錄
        )

    def remember_screen(self, description):
        """將視覺觀察到的行為存入 RAG"""
        self.rag.add_history({"role": "system", "content": f"觀察日誌: {description}"})

    def query_past(self, question):
        """詢問過去發生的事情"""
        return self.rag.search(question)