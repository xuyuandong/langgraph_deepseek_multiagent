"""
MCP (Model Context Protocol) 客户端实现
用于与MCP服务器进行通信和工具调用
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from src.core.logger import LoggerMixin
from src.core.config import settings


class MCPClient(LoggerMixin):
    """MCP客户端，用于与MCP服务器通信"""
    
    def __init__(self, server_url: Optional[str] = None):
        super().__init__()
        self.server_url = server_url or f"http://{settings.mcp_server_host}:{settings.mcp_server_port}"
        self.session = None
        self.tools = {}
        self.connected = False
    
    async def connect(self):
        """连接到MCP服务器"""
        try:
            # 模拟MCP连接逻辑
            self.log_info(f"连接到MCP服务器: {self.server_url}")
            
            # 初始化会话
            self.session = {
                "id": "mcp_session_001",
                "server_url": self.server_url,
                "capabilities": ["tools", "prompts", "resources"]
            }
            
            # 获取可用工具列表
            await self._fetch_tools()
            
            self.connected = True
            self.log_info("MCP客户端连接成功")
            
        except Exception as e:
            self.log_error(f"MCP连接失败: {str(e)}")
            self.connected = False
    
    async def _fetch_tools(self):
        """获取MCP服务器提供的工具"""
        try:
            # 模拟获取工具列表
            self.tools = {
                "file_read": {
                    "name": "file_read",
                    "description": "读取文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "文件路径"}
                        },
                        "required": ["file_path"]
                    }
                },
                "file_write": {
                    "name": "file_write",
                    "description": "写入文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "文件路径"},
                            "content": {"type": "string", "description": "文件内容"}
                        },
                        "required": ["file_path", "content"]
                    }
                },
                "execute_command": {
                    "name": "execute_command",
                    "description": "执行系统命令",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "要执行的命令"}
                        },
                        "required": ["command"]
                    }
                }
            }
            
            self.log_info(f"获取到 {len(self.tools)} 个MCP工具")
            
        except Exception as e:
            self.log_error(f"获取MCP工具失败: {str(e)}")
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        if not self.connected:
            raise RuntimeError("MCP客户端未连接")
        
        if tool_name not in self.tools:
            raise ValueError(f"未知的工具: {tool_name}")
        
        try:
            self.log_info(f"调用MCP工具: {tool_name}")
            
            # 模拟工具调用
            result = await self._execute_tool(tool_name, parameters)
            
            return {
                "success": True,
                "result": result,
                "tool_name": tool_name,
                "parameters": parameters
            }
            
        except Exception as e:
            self.log_error(f"MCP工具调用失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "parameters": parameters
            }
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """执行具体的工具操作"""
        if tool_name == "file_read":
            return await self._file_read(parameters.get("file_path"))
        elif tool_name == "file_write":
            return await self._file_write(parameters.get("file_path"), parameters.get("content"))
        elif tool_name == "execute_command":
            return await self._execute_command(parameters.get("command"))
        else:
            raise ValueError(f"不支持的工具: {tool_name}")
    
    async def _file_read(self, file_path: str) -> str:
        """读取文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            raise Exception(f"读取文件失败: {str(e)}")
    
    async def _file_write(self, file_path: str, content: str) -> str:
        """写入文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"文件写入成功: {file_path}"
        except Exception as e:
            raise Exception(f"写入文件失败: {str(e)}")
    
    async def _execute_command(self, command: str) -> str:
        """执行系统命令"""
        try:
            import subprocess
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except Exception as e:
            raise Exception(f"执行命令失败: {str(e)}")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return list(self.tools.values())
    
    async def disconnect(self):
        """断开MCP连接"""
        if self.connected:
            self.log_info("断开MCP连接")
            self.connected = False
            self.session = None
            self.tools = {}


class MCPManager(LoggerMixin):
    """MCP管理器，负责管理多个MCP客户端"""
    
    def __init__(self):
        super().__init__()
        self.clients: Dict[str, MCPClient] = {}
        self.default_client = None
    
    async def add_client(self, name: str, server_url: Optional[str] = None) -> MCPClient:
        """添加MCP客户端"""
        client = MCPClient(server_url)
        await client.connect()
        
        self.clients[name] = client
        
        # 设置默认客户端
        if self.default_client is None:
            self.default_client = client
        
        self.log_info(f"添加MCP客户端: {name}")
        return client
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any], 
                       client_name: Optional[str] = None) -> Dict[str, Any]:
        """调用MCP工具"""
        client = self.clients.get(client_name) if client_name else self.default_client
        
        if not client:
            raise ValueError("没有可用的MCP客户端")
        
        return await client.call_tool(tool_name, parameters)
    
    def get_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有客户端的工具"""
        all_tools = {}
        for name, client in self.clients.items():
            all_tools[name] = client.get_available_tools()
        return all_tools
    
    async def disconnect_all(self):
        """断开所有客户端连接"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
        self.default_client = None
