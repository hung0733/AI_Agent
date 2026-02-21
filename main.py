from sensors.vision import VisionSensor
from sensors.audio import AudioSystem
from core.brain import QwenBrain
from core.memory import MemoryManager

class OmniAgentSystem:
    def __init__(self):
        # 3090 負責的部分
        self.vision = VisionSensor()
        self.audio = AudioSystem()
        
        # V100 負責的部分
        self.memory = MemoryManager(db_path="./data/permanent_storage")
        self.brain = QwenBrain()

    def run_loop(self):
        while True:
            # 1. 監聽語音指令
            user_text = self.audio.listen() 
            
            if user_text:
                # 2. 獲取當前視覺上下文
                img_path = self.vision.capture_screen()
                
                # 3. 檢索永久記憶 (RAG)
                past_context = self.memory.query_past(user_text)
                
                # 4. 主腦思考 (Qwen3-Next-80B)
                response = self.brain.think(user_text, img_path, past_context)
                
                # 5. TTS 出聲 + 存入記憶
                self.audio.speak(response)
                self.memory.store_event(user_text, response, img_path)

if __name__ == "__main__":
    system = OmniAgentSystem()
    system.run_loop()