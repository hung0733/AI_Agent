import pyautogui
from PIL import Image
import os

class VisionSensor:
    def __init__(self):
        # 獲取螢幕原生解析度
        self.width, self.height = pyautogui.size()

    def capture_screen(self, filename="current_state.png"):
        """截取全螢幕並保存，供 Qwen2.5-VL 讀取"""
        path = os.path.join("data/screenshots", filename)
        screenshot = pyautogui.screenshot()
        screenshot.save(path)
        return path

    def get_element_coordinate(self, agent_output):
        """
        將 Qwen2.5-VL 輸出的歸一化坐標 [0-1000] 
        轉換為實際螢幕像素坐標，以便 ActionExecutor 點擊
        """
        # 假設 Qwen 返回 [ymin, xmin, ymax, xmax]
        # 這裡需要解析 Agent 的 string 輸出，轉為像素點
        pass