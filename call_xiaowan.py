import sys
import io
from letta_client import Letta

# 1. 強制修正 Terminal 輸出入編碼，防止廣東話出亂碼
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 2. 連接 Server
client = Letta(base_url="http://192.168.1.252:8283")
AGENT_ID = "agent-0be44e20-4350-48f8-b375-da49fa6c1338"

def talk_to_xiaowan(msg):
    try:
        # 確保 msg 係乾淨嘅 UTF-8 string
        clean_msg = str(msg).encode('utf-8', errors='ignore').decode('utf-8')
        
        response = client.agents.messages.create(
            agent_id=AGENT_ID,
            messages=[{"role": "user", "content": clean_msg}]
        )
        
        # 打印回覆
        print("\n🤖 小丸：", end="")
        for m in response.messages:
            # 兼容 AssistantMessage 同埋可能含有內容嘅物件
            if hasattr(m, 'content') and m.content:
                if getattr(m, 'role', '') == "assistant" or type(m).__name__ == "AssistantMessage":
                    print(f"{m.content}")
            # 如果有 internal monologue 想睇，可以 uncomment 下面
            # elif hasattr(m, 'internal_monologue') and m.internal_monologue:
            #    print(f"\n💭 (諗緊：{m.internal_monologue})")

    except Exception as e:
        print(f"\n❌ 出錯咗：{str(e)}")

if __name__ == "__main__":
    try:
        user_input = input("想同小丸講咩？ ")
        if user_input.strip():
            talk_to_xiaowan(user_input)
    except EOFError:
        pass