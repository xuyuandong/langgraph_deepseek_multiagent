from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class IntentType(Enum):
    """意图类型枚举"""
    CASUAL_CHAT = "casual_chat"
    COMPLEX_TASK = "complex_task"
    INFORMATION_QUERY = "information_query"
    TASK_EXECUTION = "task_execution"


class TaskComplexity(Enum):
    """任务复杂度枚举"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class AgentType(Enum):
    """Agent类型枚举"""
    COORDINATOR = "coordinator"
    PLANNER = "planner"
    EXECUTOR = "executor"
    SPECIALIST = "specialist"


class MessageType(Enum):
    """消息类型枚举"""
    USER_INPUT = "user_input"
    AGENT_RESPONSE = "agent_response"
    TASK_RESULT = "task_result"
    SYSTEM_MESSAGE = "system_message"


class Message(BaseModel):
    """消息模型"""
    id: str = Field(description="消息ID")
    type: MessageType = Field(description="消息类型")
    content: str = Field(description="消息内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    sender: str = Field(description="发送者")
    recipient: Optional[str] = Field(default=None, description="接收者")


class Intent(BaseModel):
    """意图识别结果"""
    type: IntentType = Field(description="意图类型")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")
    entities: Dict[str, Any] = Field(default_factory=dict, description="实体信息")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class Task(BaseModel):
    """任务模型"""
    id: str = Field(description="任务ID")
    name: str = Field(description="任务名称")
    description: str = Field(description="任务描述")
    complexity: TaskComplexity = Field(description="任务复杂度")
    subtasks: List["Task"] = Field(default_factory=list, description="子任务列表")
    dependencies: List[str] = Field(default_factory=list, description="依赖任务ID")
    status: str = Field(default="pending", description="任务状态")
    result: Optional[Dict[str, Any]] = Field(default=None, description="任务结果")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class AgentState(BaseModel):
    """Agent状态模型"""
    messages: List[Message] = Field(default_factory=list, description="消息历史")
    current_task: Optional[Task] = Field(default=None, description="当前任务")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")
    memory: Dict[str, Any] = Field(default_factory=dict, description="记忆信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ToolCall(BaseModel):
    """工具调用模型"""
    tool_name: str = Field(description="工具名称")
    parameters: Dict[str, Any] = Field(description="工具参数")
    result: Optional[Any] = Field(default=None, description="调用结果")
    error: Optional[str] = Field(default=None, description="错误信息")


class AgentResponse(BaseModel):
    """Agent响应模型"""
    content: str = Field(description="响应内容")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="工具调用")
    next_action: Optional[str] = Field(default=None, description="下一步动作")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, name: str, agent_type: AgentType):
        self.name = name
        self.agent_type = agent_type
        
    @abstractmethod
    async def process(self, state: AgentState) -> AgentResponse:
        """处理状态并返回响应"""
        pass
    
    @abstractmethod
    async def can_handle(self, task: Task) -> bool:
        """判断是否能处理该任务"""
        pass


class BaseMemory(ABC):
    """记忆模块基类"""
    
    @abstractmethod
    async def store(self, key: str, value: Any) -> None:
        """存储记忆"""
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        """检索记忆"""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Any]:
        """搜索记忆"""
        pass


class BaseRAG(ABC):
    """RAG模块基类"""
    
    @abstractmethod
    async def add_documents(self, documents: List[str]) -> None:
        """添加文档"""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[str]:
        """搜索相关文档"""
        pass


class BaseTool(ABC):
    """工具基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """执行工具"""
        pass


# 更新Task模型以支持递归引用
Task.model_rebuild()
