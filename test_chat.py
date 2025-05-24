#!/usr/bin/env python3
"""
测试脚本：验证 LangGraph 聊天端点
"""

import requests
import json

def test_chat_endpoint():
    """测试 /chat 端点"""
    url = "http://localhost:5003/chat"
    
    # 测试数据
    test_data = {
        "message": "你好，请帮我查询用户表的数据",
        "session_id": "test_session_001"
    }
    
    print(f"发送测试请求到: {url}")
    print(f"请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(url, json=test_data, timeout=30)
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 成功响应:")
            print(f"AI 回复: {result.get('message', 'N/A')}")
            print(f"成功状态: {result.get('success', 'N/A')}")
            print(f"会话 ID: {result.get('session_id', 'N/A')}")
            
            if 'error' in result:
                print(f"错误信息: {result['error']}")
        else:
            print(f"\n❌ 请求失败:")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 连接错误: {e}")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 解析错误: {e}")
        print(f"原始响应: {response.text}")

if __name__ == "__main__":
    test_chat_endpoint() 