"""
MCP (Model Context Protocol) 服务器实现
提供工具和资源给MCP客户端
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Callable
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from src.core.logger import LoggerMixin
from src.core.config import settings


class MCPRequest(BaseModel):
    """MCP请求模型"""
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None


class MCPResponse(BaseModel):
    """MCP响应模型"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPTool(BaseModel):
    """MCP工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None


class MCPServer(LoggerMixin):
    """MCP服务器实现"""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        super().__init__()
        self.host = host
        self.port = port
        self.app = FastAPI(title="MCP Server", description="Model Context Protocol Server")
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, Any] = {}
        self.prompts: Dict[str, Any] = {}
        
        # 设置路由
        self._setup_routes()
        
        # 注册默认工具
        self._register_default_tools()
    
    def _setup_routes(self):
        """设置API路由"""
        
        @self.app.post("/mcp/request")
        async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
            """处理MCP请求"""
            try:
                result = await self._handle_request(request)
                return MCPResponse(result=result, id=request.id)
            except Exception as e:
                self.log_error(f"处理MCP请求失败: {str(e)}")
                return MCPResponse(
                    error={"code": -1, "message": str(e)},
                    id=request.id
                )
        
        @self.app.get("/mcp/tools")
        async def list_tools():
            """获取可用工具列表"""
            return {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                    for tool in self.tools.values()
                ]
            }
        
        @self.app.get("/mcp/resources")
        async def list_resources():
            """获取可用资源列表"""
            return {"resources": list(self.resources.keys())}
        
        @self.app.get("/mcp/prompts")
        async def list_prompts():
            """获取可用提示模板列表"""
            return {"prompts": list(self.prompts.keys())}
    
    async def _handle_request(self, request: MCPRequest) -> Any:
        """处理MCP请求"""
        method = request.method
        params = request.params
        
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            return await self._call_tool(tool_name, arguments)
        
        elif method == "resources/read":
            resource_uri = params.get("uri")
            return await self._read_resource(resource_uri)
        
        elif method == "prompts/get":
            prompt_name = params.get("name")
            return await self._get_prompt(prompt_name)
        
        else:
            raise ValueError(f"不支持的方法: {method}")
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        if tool_name not in self.tools:
            raise ValueError(f"未知的工具: {tool_name}")
        
        tool = self.tools[tool_name]
        if tool.handler:
            return await tool.handler(**arguments)
        else:
            raise ValueError(f"工具 {tool_name} 没有处理函数")
    
    async def _read_resource(self, resource_uri: str) -> Any:
        """读取资源"""
        if resource_uri not in self.resources:
            raise ValueError(f"未知的资源: {resource_uri}")
        
        return self.resources[resource_uri]
    
    async def _get_prompt(self, prompt_name: str) -> Any:
        """获取提示模板"""
        if prompt_name not in self.prompts:
            raise ValueError(f"未知的提示模板: {prompt_name}")
        
        return self.prompts[prompt_name]
    
    def register_tool(self, name: str, description: str, parameters: Dict[str, Any], 
                     handler: Callable):
        """注册工具"""
        tool = MCPTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )
        self.tools[name] = tool
        self.log_info(f"注册MCP工具: {name}")
    
    def register_resource(self, uri: str, content: Any):
        """注册资源"""
        self.resources[uri] = content
        self.log_info(f"注册MCP资源: {uri}")
    
    def register_prompt(self, name: str, template: str, description: str = ""):
        """注册提示模板"""
        self.prompts[name] = {
            "name": name,
            "description": description,
            "template": template
        }
        self.log_info(f"注册MCP提示模板: {name}")
    
    def _register_default_tools(self):
        """注册默认工具"""
        
        async def echo_handler(message: str) -> str:
            """回声工具"""
            return f"Echo: {message}"
        
        async def add_numbers_handler(a: float, b: float) -> float:
            """加法工具"""
            return a + b
        
        async def get_current_time_handler() -> str:
            """获取当前时间"""
            from datetime import datetime
            return datetime.now().isoformat()
        
        # 注册默认工具
        self.register_tool(
            name="echo",
            description="回声工具，返回输入的消息",
            parameters={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "要回声的消息"}
                },
                "required": ["message"]
            },
            handler=echo_handler
        )
        
        self.register_tool(
            name="add",
            description="加法工具，计算两个数的和",
            parameters={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个数"},
                    "b": {"type": "number", "description": "第二个数"}
                },
                "required": ["a", "b"]
            },
            handler=add_numbers_handler
        )
        
        self.register_tool(
            name="current_time",
            description="获取当前时间",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=get_current_time_handler
        )
        
        # 注册默认提示模板
        self.register_prompt(
            name="system_prompt",
            description="系统提示模板",
            template="你是一个有用的AI助手。请根据用户的问题提供准确和有帮助的回答。"
        )
        
        self.register_prompt(
            name="task_analysis_prompt",
            description="任务分析提示模板",
            template="请分析以下任务，识别关键信息和所需步骤：{task_description}"
        )
    
    async def start(self):
        """启动MCP服务器"""
        self.log_info(f"启动MCP服务器: {self.host}:{self.port}")
        
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def run(self):
        """运行MCP服务器（同步版本）"""
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


# 全局MCP服务器实例
mcp_server = MCPServer(
    host=settings.mcp_server_host,
    port=settings.mcp_server_port
)


def register_agent_tools(server: MCPServer):
    """为Agent注册专用工具"""
    
    async def analyze_intent_handler(user_input: str) -> Dict[str, Any]:
        """意图分析工具"""
        # 这里可以集成实际的意图识别逻辑
        return {
            "intent": "task_request",
            "confidence": 0.8,
            "entities": []
        }
    
    async def plan_task_handler(task_description: str) -> List[Dict[str, Any]]:
        """任务规划工具"""
        # 这里可以集成实际的任务规划逻辑
        return [
            {"step": 1, "action": "analyze", "description": "分析任务需求"},
            {"step": 2, "action": "execute", "description": "执行任务"},
            {"step": 3, "action": "verify", "description": "验证结果"}
        ]
    
    # 注册Agent专用工具
    server.register_tool(
        name="analyze_intent",
        description="分析用户输入的意图",
        parameters={
            "type": "object",
            "properties": {
                "user_input": {"type": "string", "description": "用户输入"}
            },
            "required": ["user_input"]
        },
        handler=analyze_intent_handler
    )
    
    server.register_tool(
        name="plan_task",
        description="将复杂任务分解为子任务",
        parameters={
            "type": "object",
            "properties": {
                "task_description": {"type": "string", "description": "任务描述"}
            },
            "required": ["task_description"]
        },
        handler=plan_task_handler
    )


# 注册Agent工具
register_agent_tools(mcp_server)
