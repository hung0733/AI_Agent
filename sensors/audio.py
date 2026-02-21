import os
import pygame  # 用於播放音頻
from gpt_sovits_python import TTS # 範例：使用 GPT-SoVITS 的封裝庫

class AudioSystem:
    def __init__(self, tts_model_path=None):
        self.is_speaking = False
        pygame.mixer.init()
        # 初始化 TTS 模型到 3090 (device="cuda:0")
        # 這裡根據你選擇的 TTS 引擎進行初始化

    def speak(self, text):
        """將文字轉為語音並播放"""
        print(f"[TTS] 正在轉換: {text}")
        output_file = "data/temp_voice.wav"
        
        # 1. 呼叫 TTS 引擎 (運行在 3090)
        # self.tts_engine.infer(text, output_path=output_file) 
        
        # 2. 播放音訊
        self._play_audio(output_file)

    def _play_audio(self, file_path):
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue

    def listen(self):
        """使用 Faster-Whisper 監聽麥克風 (運行在 3090)"""
        # 實作 STT 邏輯
        pass