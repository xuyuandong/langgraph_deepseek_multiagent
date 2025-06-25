#!/usr/bin/env python3
"""
命令行界面，用于与多Agent框架交互
"""

import asyncio
import json
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
from src.framework.multi_agent_framework import create_agent_framework

app = typer.Typer()
console = Console()

# 全局框架实例
framework = None


@app.command()
def chat():
    """启动聊天模式"""
    console.print(Panel.fit("🤖 多Agent框架聊天模式", style="bold green"))
    console.print("输入 'quit' 或 'exit' 退出聊天")
    console.print("输入 'help' 查看可用命令")
    console.print()
    
    asyncio.run(_chat_loop())


async def _chat_loop():
    """聊天循环"""
    global framework
    
    # 初始化框架
    console.print("正在初始化框架...")
    try:
        framework = await create_agent_framework()
        console.print("✅ 框架初始化成功!", style="green")
    except Exception as e:
        console.print(f"❌ 框架初始化失败: {e}", style="red")
        return
    
    conversation_id = None
    user_id = "cli_user"
    
    while True:
        try:
            # 获取用户输入
            user_input = Prompt.ask("\n[bold blue]你[/bold blue]")
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                break
            elif user_input.lower() == 'help':
                _show_help()
                continue
            elif user_input.lower().startswith('add_knowledge '):
                # 添加知识
                content = user_input[13:]  # 去掉 'add_knowledge '
                await _add_knowledge(content)
                continue
            elif user_input.lower().startswith('search_knowledge '):
                # 搜索知识
                query = user_input[17:]  # 去掉 'search_knowledge '
                await _search_knowledge(query)
                continue
            elif user_input.lower() == 'stats':
                # 显示统计信息
                await _show_stats()
                continue
            
            # 处理正常聊天
            with console.status("🤔 思考中..."):
                result = await framework.process_message(
                    user_input=user_input,
                    conversation_id=conversation_id,
                    user_id=user_id
                )
            
            conversation_id = result.get("conversation_id")
            
            # 显示响应
            response = result.get("response", "")
            confidence = result.get("confidence", 0.0)
            tool_calls = result.get("tool_calls", [])
            
            # 格式化输出
            console.print(f"\n[bold green]🤖 助手[/bold green] (置信度: {confidence:.2f})")
            console.print(Panel(Markdown(response), expand=False))
            
            # 显示工具调用信息
            if tool_calls:
                console.print("\n[dim]🔧 使用的工具:[/dim]")
                for tool_call in tool_calls:
                    console.print(f"  • {tool_call.get('tool_name', 'unknown')}")
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"❌ 错误: {e}", style="red")
    
    # 清理资源
    if framework:
        await framework.close()
    
    console.print("\n👋 再见!")


def _show_help():
    """显示帮助信息"""
    help_table = Table(title="可用命令")
    help_table.add_column("命令", style="cyan")
    help_table.add_column("描述", style="white")
    
    help_table.add_row("quit/exit", "退出聊天")
    help_table.add_row("help", "显示此帮助信息")
    help_table.add_row("add_knowledge <内容>", "添加知识到RAG")
    help_table.add_row("search_knowledge <查询>", "搜索知识库")
    help_table.add_row("stats", "显示框架统计信息")
    
    console.print(help_table)


async def _add_knowledge(content: str):
    """添加知识"""
    try:
        result = await framework.add_knowledge(content, "cli")
        if result.get("success"):
            console.print("✅ 知识已添加", style="green")
        else:
            console.print(f"❌ 添加失败: {result.get('error', '未知错误')}", style="red")
    except Exception as e:
        console.print(f"❌ 添加知识时出错: {e}", style="red")


async def _search_knowledge(query: str):
    """搜索知识"""
    try:
        result = await framework.search_knowledge(query)
        results = result.get("results", [])
        
        if results:
            console.print(f"\n🔍 找到 {len(results)} 个相关结果:")
            for i, result in enumerate(results, 1):
                doc = result.get("document", "")
                metadata = result.get("metadata", {})
                source = metadata.get("source", "未知")
                
                console.print(f"\n{i}. 来源: {source}")
                console.print(Panel(doc[:200] + "..." if len(doc) > 200 else doc, expand=False))
        else:
            console.print("❌ 未找到相关结果", style="yellow")
    except Exception as e:
        console.print(f"❌ 搜索知识时出错: {e}", style="red")


async def _show_stats():
    """显示统计信息"""
    try:
        stats_table = Table(title="框架统计信息")
        stats_table.add_column("项目", style="cyan")
        stats_table.add_column("值", style="white")
        
        stats_table.add_row("注册的Agent数量", str(len(framework.coordinator.agents)))
        stats_table.add_row("Agent列表", ", ".join(framework.coordinator.agents.keys()) or "无")
        
        # RAG信息
        if framework.rag_manager:
            try:
                rag_info = await framework.rag_manager.rag.get_collection_info()
                stats_table.add_row("知识库文档数", str(rag_info.get("count", 0)))
                stats_table.add_row("嵌入模型", rag_info.get("embedding_model", "未知"))
            except:
                stats_table.add_row("知识库状态", "不可用")
        else:
            stats_table.add_row("知识库状态", "未初始化")
        
        console.print(stats_table)
    except Exception as e:
        console.print(f"❌ 获取统计信息时出错: {e}", style="red")


@app.command()
def add_knowledge_file(file_path: str):
    """从文件添加知识到RAG"""
    async def _add_file():
        framework = await create_agent_framework()
        try:
            result = await framework.add_knowledge_file(file_path)
            if result.get("success"):
                console.print(f"✅ 文件 {file_path} 已添加到知识库", style="green")
            else:
                console.print(f"❌ 添加失败: {result.get('error', '未知错误')}", style="red")
        except Exception as e:
            console.print(f"❌ 添加文件时出错: {e}", style="red")
        finally:
            await framework.close()
    
    asyncio.run(_add_file())


@app.command()
def server():
    """启动API服务器"""
    console.print(Panel.fit("🚀 启动API服务器", style="bold green"))
    
    # 导入并运行服务器
    import uvicorn
    from src.api.server import app as api_app
    from src.core.config import settings
    
    uvicorn.run(
        api_app,
        host=settings.mcp_server_host,
        port=settings.mcp_server_port,
        log_level=settings.log_level.lower()
    )


@app.command()
def test():
    """运行框架测试"""
    async def _test():
        console.print("🧪 运行框架测试...")
        
        framework = await create_agent_framework()
        
        try:
            # 测试基本聊天
            console.print("测试基本聊天...")
            result = await framework.process_message("你好")
            console.print(f"响应: {result['response']}")
            
            # 测试意图识别
            console.print("\n测试复杂任务...")
            result = await framework.process_message("帮我制定一个周末旅行计划")
            console.print(f"响应: {result['response']}")
            
            console.print("\n✅ 测试完成", style="green")
            
        except Exception as e:
            console.print(f"❌ 测试失败: {e}", style="red")
        finally:
            await framework.close()
    
    asyncio.run(_test())


if __name__ == "__main__":
    app()
