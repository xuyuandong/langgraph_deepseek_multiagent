from typing import Any, Dict, List, Optional, Union
import json
from datetime import datetime
import uuid
import asyncio
from src.core.models import AgentState, Message, MessageType, Task
from src.core.config import settings
from src.core.logger import LoggerMixin
from src.llm.client_factory import LLMClientFactory
from src.planning.task_planner import TaskPlanner, ContextExtractor
from src.memory.memory_manager import MemoryManager, SqliteMemory
from src.rag.rag_manager import RAGManager, DocumentProcessor
from src.tools.web_search import SearchManager
from src.tools.mcp_client import MCPManager
from src.agents.coordinator import CoordinatorAgent

# 尝试导入LangGraph相关组件
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.sqlite import SqliteSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # 定义备用类
    class StateGraph:
        def __init__(self, state_class): pass
        def add_node(self, name, func): pass
        def set_entry_point(self, name): pass
        def add_edge(self, from_node, to_node): pass
        def compile(self, **kwargs): return None
    
    class SqliteSaver:
        @staticmethod
        def from_conn_string(path): return None
    
    END = "END"

# 尝试导入RAG组件
try:
    from src.rag.rag_manager import ChromaRAG
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    ChromaRAG = None


class MultiAgentFramework(LoggerMixin):
    """多Agent框架主类"""
    
    def __init__(self):
        super().__init__()
        self.session_id = None
        self.conversation_id = None
        
        # 初始化核心组件
        self._init_components()
        
        # 初始化LangGraph
        self._init_langgraph()
    
    def _init_components(self):
        """初始化核心组件"""
        # LLM工厂
        self.llm_factory = LLMClientFactory()
        
        # 任务规划
        self.task_planner = TaskPlanner(self.llm_factory)
        self.context_extractor = ContextExtractor(self.llm_factory)
        
        # 记忆模块
        sqlite_memory = SqliteMemory()
        self.memory_manager = MemoryManager(sqlite_memory)
        
        # RAG模块
        if RAG_AVAILABLE:
            try:
                chroma_rag = ChromaRAG()
                document_processor = DocumentProcessor()
                self.rag_manager = RAGManager(chroma_rag, document_processor)
            except Exception as e:
                self.log_warning(f"RAG初始化失败: {str(e)}")
                self.rag_manager = None
        else:
            self.log_warning("RAG组件不可用")
            self.rag_manager = None
        
        # 搜索模块
        self.search_manager = SearchManager()
        
        # MCP模块
        self.mcp_manager = MCPManager()
        
        # 协调器Agent
        self.coordinator = CoordinatorAgent(
            llm_factory=self.llm_factory,
            task_planner=self.task_planner,
            context_extractor=self.context_extractor,
            memory_manager=self.memory_manager,
            rag_manager=self.rag_manager,
            search_manager=self.search_manager,
            mcp_manager=self.mcp_manager
        )
    
    def _init_langgraph(self):
        """初始化LangGraph工作流"""
        if not LANGGRAPH_AVAILABLE:
            self.log_warning("LangGraph不可用，使用简化工作流")
            self.graph = None
            return
        
        # 创建状态图
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("coordinator", self._coordinator_node)
        workflow.add_node("memory_check", self._memory_check_node)
        workflow.add_node("context_update", self._context_update_node)
        workflow.add_node("response_generation", self._response_generation_node)
        
        # 设置入口点
        workflow.set_entry_point("memory_check")
        
        # 添加边
        workflow.add_edge("memory_check", "context_update")
        workflow.add_edge("context_update", "coordinator")
        workflow.add_edge("coordinator", "response_generation")
        workflow.add_edge("response_generation", END)
        
        # 编译图
        try:
            self.graph = workflow.compile(
                checkpointer=SqliteSaver.from_conn_string(settings.sqlite_db_path)
            )
        except Exception as e:
            self.log_warning(f"LangGraph编译失败: {str(e)}")
            self.graph = None
    
    async def _coordinator_node(self, state: AgentState) -> AgentState:
        """协调器节点"""
        try:
            response = await self.coordinator.process(state)
            
            # 添加响应消息
            response_message = Message(
                id=str(uuid.uuid4()),
                type=MessageType.AGENT_RESPONSE,
                content=response.content,
                sender="coordinator",
                metadata={
                    "confidence": response.confidence,
                    "tool_calls": response.tool_calls,
                    "next_action": response.next_action
                }
            )
            
            state.messages.append(response_message)
            
            return state
            
        except Exception as e:
            self.log_error(f"协调器节点执行失败: {str(e)}")
            
            error_message = Message(
                id=str(uuid.uuid4()),
                type=MessageType.SYSTEM_MESSAGE,
                content=f"处理过程中出现错误: {str(e)}",
                sender="system"
            )
            
            state.messages.append(error_message)
            return state
    
    async def _memory_check_node(self, state: AgentState) -> AgentState:
        """记忆检查节点"""
        try:
            if self.conversation_id:
                # 检索历史对话
                conversation_history = await self.memory_manager.retrieve_conversation(
                    self.conversation_id
                )
                
                # 更新状态中的对话历史
                if conversation_history:
                    for msg_data in conversation_history:
                        message = Message(**msg_data)
                        state.messages.append(message)
            
            return state
            
        except Exception as e:
            self.log_error(f"记忆检查节点执行失败: {str(e)}")
            return state
    
    async def _context_update_node(self, state: AgentState) -> AgentState:
        """上下文更新节点"""
        try:
            if state.messages:
                latest_message = state.messages[-1]
                
                # 提取上下文
                conversation_history = [
                    {"role": msg.sender, "content": msg.content}
                    for msg in state.messages[-10:]
                ]
                
                context = await self.context_extractor.extract_relevant_context(
                    latest_message.content,
                    conversation_history
                )
                
                state.context.update(context)
            
            return state
            
        except Exception as e:
            self.log_error(f"上下文更新节点执行失败: {str(e)}")
            return state
    
    async def _response_generation_node(self, state: AgentState) -> AgentState:
        """响应生成节点"""
        try:
            # 存储对话到记忆
            if self.conversation_id and state.messages:
                conversation_data = [
                    msg.dict() for msg in state.messages
                ]
                await self.memory_manager.store_conversation(
                    self.conversation_id,
                    conversation_data
                )
            
            return state
            
        except Exception as e:
            self.log_error(f"响应生成节点执行失败: {str(e)}")
            return state
    
    async def _simple_workflow(self, initial_state: AgentState) -> AgentState:
        """简化工作流（当LangGraph不可用时）"""
        try:
            # 执行各个节点
            state = await self._memory_check_node(initial_state)
            state = await self._context_update_node(state)
            state = await self._coordinator_node(state)
            state = await self._response_generation_node(state)
            
            return state
            
        except Exception as e:
            self.log_error(f"简化工作流执行失败: {str(e)}")
            
            # 添加错误消息
            error_message = Message(
                id=str(uuid.uuid4()),
                type=MessageType.SYSTEM_MESSAGE,
                content=f"处理过程中出现错误: {str(e)}",
                sender="system"
            )
            
            initial_state.messages.append(error_message)
            return initial_state
    
    async def process_message(
        self,
        user_input: str,
        conversation_id: str = None,
        user_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """处理用户消息"""
        try:
            # 设置会话信息
            self.conversation_id = conversation_id or str(uuid.uuid4())
            self.session_id = f"{user_id or 'anonymous'}_{self.conversation_id}"
            
            # 创建用户消息
            user_message = Message(
                id=str(uuid.uuid4()),
                type=MessageType.USER_INPUT,
                content=user_input,
                sender=user_id or "user",
                metadata=metadata or {}
            )
            
            # 初始化状态
            initial_state = AgentState(
                messages=[user_message],
                context={},
                metadata={
                    "conversation_id": self.conversation_id,
                    "user_id": user_id,
                    "session_id": self.session_id
                }
            )
            
            # 执行工作流
            if self.graph:
                # 使用LangGraph
                config = {"configurable": {"thread_id": self.session_id}}
                final_state = await self.graph.ainvoke(initial_state, config=config)
            else:
                # 使用简化工作流
                final_state = await self._simple_workflow(initial_state)
            
            # 提取响应
            response_messages = [
                msg for msg in final_state.messages
                if msg.type == MessageType.AGENT_RESPONSE
            ]
            
            if response_messages:
                latest_response = response_messages[-1]
                return {
                    "response": latest_response.content,
                    "confidence": latest_response.metadata.get("confidence", 0.0),
                    "tool_calls": latest_response.metadata.get("tool_calls", []),
                    "next_action": latest_response.metadata.get("next_action"),
                    "conversation_id": self.conversation_id,
                    "message_id": latest_response.id
                }
            else:
                return {
                    "response": "抱歉，我暂时无法处理您的请求。",
                    "confidence": 0.0,
                    "conversation_id": self.conversation_id
                }
        
        except Exception as e:
            self.log_error(f"处理消息失败: {str(e)}")
            return {
                "response": f"处理过程中出现错误: {str(e)}",
                "confidence": 0.0,
                "error": str(e),
                "conversation_id": self.conversation_id
            }
    
    async def add_knowledge(self, content: str, source: str = "manual") -> Dict[str, Any]:
        """添加知识到RAG"""
        try:
            if not self.rag_manager:
                return {"error": "RAG模块未初始化"}
            
            await self.rag_manager.add_text(content, source)
            return {"success": True, "message": "知识已添加"}
            
        except Exception as e:
            self.log_error(f"添加知识失败: {str(e)}")
            return {"error": str(e)}
    
    async def add_knowledge_file(self, file_path: str) -> Dict[str, Any]:
        """从文件添加知识"""
        try:
            if not self.rag_manager:
                return {"error": "RAG模块未初始化"}
            
            await self.rag_manager.add_file(file_path)
            return {"success": True, "message": f"文件 {file_path} 已添加到知识库"}
            
        except Exception as e:
            self.log_error(f"添加知识文件失败: {str(e)}")
            return {"error": str(e)}
    
    async def search_knowledge(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """搜索知识库"""
        try:
            if not self.rag_manager:
                return {"error": "RAG模块未初始化"}
            
            results = await self.rag_manager.rag.search(query, limit)
            return {"results": results}
            
        except Exception as e:
            self.log_error(f"搜索知识库失败: {str(e)}")
            return {"error": str(e)}
    
    async def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话历史"""
        try:
            history = await self.memory_manager.retrieve_conversation(conversation_id)
            return history
            
        except Exception as e:
            self.log_error(f"获取对话历史失败: {str(e)}")
            return []
    
    def register_agent(self, agent) -> None:
        """注册新的Agent"""
        self.coordinator.register_agent(agent)
    
    async def close(self):
        """关闭资源"""
        try:
            # 关闭各种连接
            if hasattr(self.memory_manager.primary_memory, 'close'):
                await self.memory_manager.primary_memory.close()
            
            self.log_info("多Agent框架已关闭")
            
        except Exception as e:
            self.log_error(f"关闭框架失败: {str(e)}")
    
    async def initialize_mcp(self):
        """初始化MCP连接"""
        try:
            # 添加默认MCP客户端
            await self.mcp_manager.add_client("default")
            self.log_info("MCP客户端初始化成功")
            return True
        except Exception as e:
            self.log_error(f"MCP初始化失败: {str(e)}")
            return False
    
    async def get_mcp_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有MCP工具"""
        try:
            return self.mcp_manager.get_all_tools()
        except Exception as e:
            self.log_error(f"获取MCP工具失败: {str(e)}")
            return {}
    
    async def call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any], 
                           client_name: Optional[str] = None) -> Dict[str, Any]:
        """调用MCP工具"""
        try:
            return await self.mcp_manager.call_tool(tool_name, parameters, client_name)
        except Exception as e:
            self.log_error(f"调用MCP工具失败: {str(e)}")
            return {"error": str(e)}


# 便捷的工厂函数
async def create_agent_framework() -> MultiAgentFramework:
    """创建Agent框架实例"""
    framework = MultiAgentFramework()
    return framework
