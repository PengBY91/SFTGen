"""
API 连接测试工具
用于测试 OpenAI 兼容 API 的连接性
"""


def test_api_connection(base_url: str, api_key: str, model_name: str) -> None:
    """
    测试 API 连接
    
    Args:
        base_url: API 基础 URL
        api_key: API Key
        model_name: 模型名称
        
    Raises:
        Exception: 如果连接测试失败
    """
    try:
        from openai import OpenAI
        
        # 创建客户端
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        # 发送测试请求
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        
        # 验证响应
        if not response.choices or not response.choices[0].message:
            raise Exception("API 响应无效：响应中没有 choices 或 message")
        
        # 连接成功
        return
        
    except ImportError:
        raise Exception("openai 库未安装，请运行: pip install openai")
    except Exception as e:
        error_msg = str(e)
        # 提供更友好的错误信息
        if "401" in error_msg or "Unauthorized" in error_msg or "Invalid" in error_msg:
            raise Exception(f"API Key 无效或未授权: {error_msg}")
        elif "404" in error_msg or "Not Found" in error_msg:
            raise Exception(f"模型不存在或 API 端点错误: {error_msg}")
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            raise Exception(f"连接超时，请检查网络连接: {error_msg}")
        elif "Connection" in error_msg or "connect" in error_msg.lower():
            raise Exception(f"无法连接到 API 服务器，请检查 base_url: {error_msg}")
        else:
            raise Exception(f"API 连接失败: {error_msg}")

