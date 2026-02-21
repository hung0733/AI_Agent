import sys
import os

try:
    from letta_client import Letta
    from letta import LLMConfig, EmbeddingConfig
    print("✅ 成功載入 Letta 組件")
except ImportError as e:
    print(f"❌ Import 失敗: {e}")
    sys.exit(1)

def setup_xiaowan_agent():
    host_ip = "192.168.1.252"
    print(f"🔌 正在連接 Letta Server (http://{host_ip}:8283)...")
    client = Letta(base_url=f"http://{host_ip}:8283")

    # 1. 配置定義
    qwen_config = LLMConfig(
        model="qwen3-next-80b",
        model_endpoint=f"http://{host_ip}:8607/v1",
        model_wrapper="chatml",
        context_window=128000,
        model_endpoint_type="openai" 
    )

    bgem3_config = EmbeddingConfig(
        embedding_endpoint_type="openai", 
        embedding_endpoint=f"http://{host_ip}:8602", 
        embedding_model="BAAI/bge-m3",
        embedding_dim=1024
    )

    system_prompt = (
        "身份：你叫「小丸」，係一位得力助手。\n"
        "語言/風格：全程使用地道香港廣東話，語氣活潑、親切、專業。講嘢簡短直接。\n"
        "誠實：識就識，唔識就查記憶，查唔到就話唔知。\n"
        "寫 Code：如果有程式碼需要修改，必須貼出整個 file 嘅完整 source code，唔好淨係講改咗邊度。\n"
        "提供方案：先畀一個簡要嘅方案總結。詳細步驟要一步一步畀，等我確認或者問完先再畀下一步，唔好一次過掉晒出嚟。"
    )

    print("🚀 正在啟動/更新本地 Agent「小丸」...")
    
    try:
        agents = client.agents.list()
        my_agent = next((a for a in agents if a.name == "小丸"), None)
        
        if my_agent:
            print(f"📢 搵到現有嘅「小丸」(ID: {my_agent.id})，正在同步最新配置...")
            client.agents.update(
                agent_id=my_agent.id,
                llm_config=qwen_config,
                embedding_config=bgem3_config,
                system=system_prompt
            )
        else:
            my_agent = client.agents.create(
                name="小丸",
                llm_config=qwen_config,
                embedding_config=bgem3_config,
                system=system_prompt
            )
            print(f"✅ 成功建立新 Agent！ID: {my_agent.id}")

        # 2. 傳送訊息
        print("\n💬 正在傳送測試訊息...")
        response = client.agents.messages.create(
            agent_id=my_agent.id,
            messages=[{
                "role": "user",
                "content": "小丸你好！宜家連線成功喇，試下用你嘅風格同我打個招呼。"
            }]
        )
        
        # 3. 強化版訊息解析 (防止 'ToolCallMessage' 報錯)
        print("\n🤖 小丸回覆：")
        if response and hasattr(response, 'messages'):
            for msg in response.messages:
                # 判斷訊息類型並安全獲取內容
                msg_type = type(msg).__name__
                
                # Assistant 直接回覆
                if msg_type == "AssistantMessage" and hasattr(msg, 'content'):
                    if msg.content:
                        print(f"{msg.content}")
                
                # 思考過程 (Internal Thoughts)
                elif hasattr(msg, 'internal_monologue') and msg.internal_monologue:
                    # 如果你想睇佢諗緊乜，可以 print 出嚟
                    # print(f"(思考中: {msg.internal_monologue})")
                    pass
                
                # 處理 Tool Call 或其他特殊物件 (避免報錯)
                elif msg_type == "ToolCallMessage":
                    # print(f"🔧 [小丸準備行 Tool: {getattr(msg, 'tool_call', 'unknown')}]")
                    pass

    except Exception as e:
        print(f"❌ 運行時出錯：{str(e)}")

if __name__ == "__main__":
    setup_xiaowan_agent()