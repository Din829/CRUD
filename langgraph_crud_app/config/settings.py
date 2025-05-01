# settings.py: 存储配置变量，如 API 密钥和数据库凭证。
import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 如果需要代理，可以在这里添加 API Base URL
# OPENAI_API_BASE = "你的代理地址" 

# OpenAI API 密钥 - 从环境变量获取或在本地开发时手动设置
# 注意: 不要在代码中直接存储密钥，应该使用环境变量
# 可以在本地创建.env文件或设置系统环境变量
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # 获取环境变量中的API密钥

# 在本地开发时，如果环境变量未设置，请手动添加你的API密钥:
# OPENAI_API_KEY = "你的API密钥"  # 仅在本地开发使用，不要提交到版本控制 

# 可以考虑将错误信息放入 agent_output 以便展示给用户
def handle_error(error_message):
    return {"agent_output": error_message, "error_flag": True}

# Flask API 的基础 URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000") # 默认为本地开发地址

# OpenAI 模型名称
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4.1") # 默认模型 