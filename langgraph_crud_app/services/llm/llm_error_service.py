"""
错误处理LLM服务 - 将技术性错误转换为用户友好信息
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, Any, Optional
import json
import re

from langgraph_crud_app.config import settings

def translate_flask_error(
    error_info: str, 
    operation_context: Dict[str, Any],
    schema_info: Optional[str] = None
) -> str:
    """
    将Flask技术错误转换为用户友好的错误信息
    
    Args:
        error_info: Flask返回的原始错误信息
        operation_context: 操作上下文，包含用户查询、操作类型、涉及的表等
        schema_info: 可选的数据库结构信息，用于更准确的错误解释
    
    Returns:
        用户友好的错误信息
    """
    print(f"---LLM 错误服务: 转换Flask错误---")
    print(f"原始错误: {error_info}")
    print(f"操作上下文: {operation_context}")
    
    # 分析错误类型
    error_type = _analyze_error_type(error_info)
    
    # 构建提示词
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """你是一个友好的数据库助手。你的任务是将技术性的错误信息转换为普通用户能理解的友好提示。

请重点关注以下错误类型的精准处理：

1. **重复值错误** (Duplicate entry):
   - 从错误信息中提取具体的字段名和重复的值
   - 例如："Duplicate entry '张三丰' for key 'users.username'"
   - 应转换为："用户名'张三丰'已经存在，请使用其他用户名。"

2. **外键约束错误** (Foreign key constraint):
   - 指出具体哪个ID或关联不存在
   - 给出创建相关记录的建议

3. **非空字段错误** (NOT NULL constraint):
   - 明确指出哪个必填字段缺失
   - 说明该字段的作用和要求

4. **数据类型错误**:
   - 指出具体哪个字段格式错误
   - 给出正确格式的示例

5. **表名错误** (Table doesn't exist):
   - 明确指出哪个表名不存在
   - 列出可用的表名供用户选择

6. **字段名错误** (Unknown column):
   - 明确指出哪个字段名不存在
   - 提供该表的可用字段名列表

7. **SQL语法错误**:
   - 避免暴露SQL细节
   - 引导用户重新描述需求

8. **批量操作冲突**:
   - 说明是复合操作中的哪一步失败
   - 解释失败原因和影响

处理要求：
- 从错误信息中精确提取关键信息（字段名、值、表名等）
- 将技术术语转换为通俗说法（username→用户名，email→邮箱等）
- 保持语调友好、专业
- 回复简洁，重点信息明确，不超过30字（可以适当灵活调整但还是要简洁）
- 直接提取具体值和字段名  
- 不要解释、不要建议、不要客套话
- 如果是复合操作，说明具体在哪一步失败"""),

        
        ("user", """请分析以下错误信息，提供精准的用户友好提示：

**用户原始请求**: {user_query}
**操作类型**: {operation_type}
**错误信息**: {error_info}

请仔细分析错误信息中的具体细节（如字段名、重复值、表名等），给出精准的错误解释和解决建议。注意：
- 如果是重复值错误，请明确指出是哪个字段的哪个值重复了
- 如果是外键错误，请说明是哪个关联数据不存在
- 如果是批量操作错误，请说明在第几步失败了什么操作

直接输出用户友好的错误信息，不要包含技术术语。""")
    ])
    
    # 构建上下文
    context = {
        "user_query": operation_context.get("user_query", "未知操作"),
        "operation_type": operation_context.get("operation_type", "数据操作"),
        "error_info": error_info
    }
    
    try:
        llm = ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0.3)
        chain = prompt_template | llm
        
        response = chain.invoke(context)
        friendly_error = response.content.strip()

        print(f"LLM转换后的友好错误: {friendly_error}")
        return friendly_error
        
    except Exception as e:
        print(f"LLM错误转换失败: {e}")
        # 提供基于规则的回退处理
        return _fallback_error_translation(error_info, operation_context)
        
               
def _analyze_error_type(error_info: str) -> str:
    """分析错误类型"""
    error_lower = error_info.lower()
    
    if "duplicate entry" in error_lower or "unique constraint" in error_lower:
        return "DUPLICATE_KEY"
    elif "foreign key constraint" in error_lower:
        return "FOREIGN_KEY"
    elif "cannot be null" in error_lower or "not null constraint" in error_lower:
        return "NOT_NULL"
    elif "1146" in error_info or "table" in error_lower and "doesn't exist" in error_lower:
        return "TABLE_NOT_EXISTS"
    elif "1054" in error_info or "unknown column" in error_lower:
        return "COLUMN_NOT_EXISTS"
    elif "syntax error" in error_lower or "1064" in error_info:
        # 检查是否是SQL注入尝试导致的语法错误
        if _is_sql_injection_attempt(error_info):
            return "SQL_INJECTION"
        return "SYNTAX_ERROR"
    elif "data type" in error_lower or "invalid" in error_lower:
        return "DATA_TYPE"
    elif "access denied" in error_lower or "permission" in error_lower:
        return "PERMISSION"
    elif "connection" in error_lower or "timeout" in error_lower:
        return "CONNECTION"
    else:
        return "UNKNOWN"
    

def _is_sql_injection_attempt(error_info: str) -> bool:
    """检查是否是SQL注入尝试导致的语法错误"""
    # 检查错误信息中是否包含常见的SQL注入模式
    injection_patterns = [
        "drop table",
        "delete from", 
        "insert into",
        "update.*set",
        "union.*select",
        "exec.*(",
        "--.*'",
        ";.*drop",
        ";.*delete",
        ";.*insert",
        ";.*update"
    ]
    
    error_lower = error_info.lower()
    
    # 检查是否包含注入模式
    for pattern in injection_patterns:
        if re.search(pattern, error_lower):
            return True
    
    # 检查特定的SQL注入错误消息模式
    # 例如: "syntax error near ''; DROP TABLE users' at line 1"
    if re.search(r"near\s+['\"][^'\"]*(?:drop|delete|insert|update|union)", error_lower):
        return True
        
    return False

def _fallback_error_translation(error_info: str, operation_context: Dict[str, Any]) -> str:
    """基于规则的错误转换回退方案"""
    error_type = _analyze_error_type(error_info)
    operation_type = operation_context.get("operation_type", "操作")
    
    error_templates = {
        "DUPLICATE_KEY": f"抱歉，{operation_type}失败，因为您提供的某个值已经存在。请检查邮箱、用户名等唯一字段，使用不同的值重试。",
        "FOREIGN_KEY": f"{operation_type}失败，因为引用的关联数据不存在。请确保相关的记录已经创建。",
        "NOT_NULL": f"{operation_type}失败，因为缺少必要的信息。请提供所有必填字段。",
        "SYNTAX_ERROR": f"查询条件可能有问题，请用更简单清晰的语言重新描述您的需求。",
        "DATA_TYPE": f"{operation_type}失败，因为某些字段的格式不正确。请检查日期、数字等字段的格式。",
        "PERMISSION": f"抱歉，您没有执行此{operation_type}的权限。",
        "CONNECTION": f"服务暂时不可用，请稍后重试。",
        "SQL_INJECTION": "输入包含特殊字符，请使用普通的查询条件。",
        "TABLE_NOT_EXISTS": "表名不存在。可用的表包括：users（用户）、prompts（提示词）、api_tokens（API令牌）、ocr_tasks（OCR任务）。",
        "COLUMN_NOT_EXISTS": "字段名不存在，请检查字段名是否正确。",
        "UNKNOWN": f"{operation_type}遇到了问题。请检查您的输入或联系管理员。"
    }
    
    return error_templates.get(error_type, error_templates["UNKNOWN"])

def format_database_constraint_error(
    constraint_error: Dict[str, Any],
    table_info: Optional[str] = None
) -> str:
    """
    专门处理数据库约束错误的格式化
    
    Args:
        constraint_error: 结构化的约束错误信息
        table_info: 表结构信息
    
    Returns:
        格式化的错误信息
    """
    error_type = constraint_error.get("type", "")
    
    if error_type == "IntegrityError.DuplicateEntry":
        key_name = constraint_error.get("key_name", "某个字段")
        conflicting_value = constraint_error.get("conflicting_value", "")
        table_name = constraint_error.get("table_name", "")
        
        # 友好化字段名
        friendly_field = _get_friendly_field_name(key_name)
        
        return f"添加失败：{friendly_field}'{conflicting_value}'已经存在。请使用不同的{friendly_field}重试。"
    
    return "数据约束错误，请检查您的输入。"

def _get_friendly_field_name(field_name: str) -> str:
    """将数据库字段名转换为用户友好的名称"""
    field_mapping = {
        "email": "邮箱地址",
        "username": "用户名", 
        "phone": "电话号码",
        "id": "ID",
        "title": "标题",
        "name": "名称"
    }
    
    # 移除可能的表名前缀和索引后缀
    clean_field = field_name.split(".")[-1]  # 移除表名前缀
    clean_field = re.sub(r"_\d+$", "", clean_field)  # 移除索引后缀
    
    return field_mapping.get(clean_field, clean_field) 