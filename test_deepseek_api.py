#!/usr/bin/env python3
"""
测试DeepSeek API连接
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

def test_api_connection():
    """测试API连接"""
    
    # 获取配置
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL")
    model = os.getenv("DEEPSEEK_MODEL")
    
    print("=== DeepSeek API 连接测试 ===")
    print(f"API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'None'}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print()
    
    if not api_key:
        print("❌ API Key 未配置")
        return False
    
    try:
        # 创建客户端
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        print("⏳ 正在测试API连接...")
        
        # 发送测试请求
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "你好，请简单回应一下"}
            ],
            max_tokens=50,
            temperature=0.3
        )
        
        print("✅ API连接成功!")
        print(f"响应: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ API连接失败: {str(e)}")
        
        # 详细错误分析
        error_str = str(e)
        if "401" in error_str:
            print("\n🔍 401错误分析:")
            print("- 检查API Key是否正确")
            print("- 检查API Key是否已激活")
            print("- 检查API Key权限")
        elif "404" in error_str:
            print("\n🔍 404错误分析:")
            print("- 检查Base URL是否正确")
            print("- 检查模型名称是否正确")
        elif "timeout" in error_str.lower():
            print("\n🔍 超时错误分析:")
            print("- 检查网络连接")
            print("- 尝试增加超时时间")
        
        return False

def test_different_configs():
    """测试不同的配置组合"""
    
    print("\n=== 测试不同配置组合 ===")
    
    configs = [
        {
            "name": "SiliconFlow + DeepSeek-V3",
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "deepseek-ai/DeepSeek-V3"
        },
        {
            "name": "SiliconFlow + DeepSeek-V2.5",
            "base_url": "https://api.siliconflow.cn/v1", 
            "model": "deepseek-ai/DeepSeek-V2.5"
        },
        {
            "name": "官方DeepSeek API",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat"
        }
    ]
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 无API Key，跳过测试")
        return
    
    for config in configs:
        print(f"\n📋 测试配置: {config['name']}")
        print(f"   Base URL: {config['base_url']}")
        print(f"   Model: {config['model']}")
        
        try:
            client = OpenAI(
                api_key=api_key,
                base_url=config["base_url"]
            )
            
            response = client.chat.completions.create(
                model=config["model"],
                messages=[{"role": "user", "content": "测试"}],
                max_tokens=10,
                temperature=0.1
            )
            
            print(f"   ✅ 成功: {response.choices[0].message.content[:30]}...")
            
        except Exception as e:
            print(f"   ❌ 失败: {str(e)[:100]}...")

def main():
    """主函数"""
    print("DeepSeek API 连接诊断工具")
    print("=" * 50)
    
    # 基本连接测试
    success = test_api_connection()
    
    # 如果失败，尝试不同配置
    if not success:
        test_different_configs()
    
    print("\n" + "=" * 50)
    print("测试完成")

if __name__ == "__main__":
    main()
