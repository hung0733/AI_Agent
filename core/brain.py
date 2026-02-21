from qwen_agent.agents import Assistant
from qwen_agent.llm import get_chat_model

class QwenBrain:
    def __init__(self, model_name="qwen2.5-72b-instruct", api_key=""):
        # 連接到你 V100 上的 Qwen3-Next-80B
        self.llm_cfg = {
            'model': 'qwen3-next-80b-instruct',
            'model_server': 'http://localhost:8607/v1', # 你的本地 OpenAI 兼容接口
            'api_key': 'EMPTY',
            'generate_cfg': {
                'top_p': 0.8,
                'temperature': 0.7,
                'max_input_tokens': 32768 # 利用 80B 的長文本能力
            }
        }
        
        # 這裡會自動處理 RAG 邏輯
        self.agent = Assistant(llm=self.llm_cfg)

    def process_query(self, text_input, image_path=None, history=None):
        messages = history or []
        
        content = [{"text": text_input}]
        if image_path:
            content.append({"image": f"file://{image_path}"})
            
        messages.append({"role": "user", "content": content})
        
        # 執行 Agent 獲取回應
        responses = []
        for response in self.agent.run(messages):
            responses.append(response)
        
        return responses[-1] # 返回最後的完整結果