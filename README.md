# Multi-Agent Framework

基于LangGraph和DeepSeek的可扩展多Agent框架，支持自然对话和复杂任务处理。

## 框架工作原理

### 整体架构

本框架采用多层架构设计，通过LangGraph编排工作流，实现用户请求从输入到输出的完整处理链路：

```
用户输入 → 意图识别 → 任务分解 → Agent协调 → 工具调用 → 结果整合 → 响应输出
```

### 核心工作流程

#### 1. 意图识别阶段
- **输入处理**: 接收用户的自然语言输入
- **意图分析**: 使用DeepSeek模型分析用户意图，区分：
  - `simple_chat`: 日常聊天对话
  - `complex_task`: 需要规划执行的复杂任务
  - `question_answer`: 问答查询
- **置信度评估**: 为每个意图类型计算置信度分数
- **结构化输出**: 返回包含意图类型、置信度、实体信息的结构化结果

#### 2. 上下文管理阶段
- **历史回顾**: 从对话历史中提取相关上下文
- **记忆检索**: 查询长期记忆中的相关信息
- **动态提示**: 基于上下文生成个性化的系统提示
- **状态更新**: 更新当前对话状态和用户偏好

#### 3. 任务规划阶段（复杂任务）
- **任务分解**: 将复杂任务分解为多个可执行的子任务
- **依赖分析**: 识别子任务间的依赖关系
- **执行计划**: 生成最优的任务执行顺序
- **资源分配**: 为每个子任务分配合适的Agent和工具

#### 4. 工具决策阶段
基于任务特征和内容分析，自动决策需要调用的工具：

- **记忆工具**: 当检测到"记住"、"上次"、"之前"等关键词时触发
- **RAG工具**: 当涉及"文档"、"资料"、"知识库"等内容时调用
- **Web搜索**: 当需要"搜索"、"查询"、"最新"信息时启用
- **MCP工具**: 当涉及"文件"、"执行"、"命令"、"计算"等操作时调用

#### 5. Agent协调阶段
- **Agent选择**: 根据任务类型选择最合适的专业Agent
- **负载均衡**: 在多个Agent间分配任务负载
- **结果汇聚**: 收集各Agent的执行结果
- **质量控制**: 对Agent输出进行质量评估和过滤

#### 6. 响应生成阶段
- **结果整合**: 将工具调用结果和Agent输出整合
- **内容生成**: 使用DeepSeek生成最终的自然语言响应
- **格式优化**: 调整响应格式以提供最佳用户体验
- **元数据附加**: 添加置信度、工具调用记录等元信息

### LangGraph工作流编排

框架使用LangGraph的StateGraph进行工作流编排，主要节点包括：

```python
# 工作流节点定义
workflow.add_node("memory_check", self._memory_check_node)      # 记忆检查
workflow.add_node("context_update", self._context_update_node)  # 上下文更新
workflow.add_node("coordinator", self._coordinator_node)        # 协调器处理
workflow.add_node("response_generation", self._response_generation_node)  # 响应生成

# 工作流路径
memory_check → context_update → coordinator → response_generation
```

### 双LLM客户端架构

框架支持两种DeepSeek客户端切换：

1. **原生客户端** (`deepseek_client.py`)
   - 直接调用DeepSeek API
   - 支持流式和批量请求
   - 适合简单对话场景

2. **LangChain客户端** (`langchain_deepseek_client.py`)
   - 基于langchain-deepseek包装
   - 支持Pydantic结构化输出
   - 适合复杂任务处理

通过`LLMClientFactory`实现客户端的自动选择和无缝切换。

## 功能特性

- 🤖 **智能意图识别**: 自动识别用户意图，区分日常聊天和复杂任务
- 📋 **任务规划分解**: 将复杂任务分解为可执行的子任务
- 🧠 **动态上下文提取**: 从对话历史中提取相关上下文和提示
- 💾 **多层记忆模块**: 支持SQLite和Redis的记忆存储
- 🔍 **RAG知识检索**: 基于ChromaDB的向量搜索和知识管理
- 🌐 **Web搜索集成**: 支持DuckDuckGo和Tavily搜索引擎
- 🚀 **MCP支持**: 内置MCP客户端和服务器功能
- 🔧 **结构化输出**: Agent间交互使用结构化数据格式
- 🎯 **可扩展架构**: 易于添加新的Agent和工具
- 🔄 **LangGraph编排**: 使用状态图进行复杂工作流管理
- 🔀 **双客户端支持**: 原生DeepSeek和LangChain客户端可切换

## 核心组件详解

### 1. 意图识别模块 (`src/llm/`)

**功能**: 智能分析用户输入，识别对话意图和任务类型

**工作原理**:
- 使用专门训练的提示模板分析用户输入
- 支持多种意图类型：简单聊天、复杂任务、问答查询
- 实时置信度评估和实体抽取
- 结构化输出支持Pydantic模型验证

**关键文件**:
- `deepseek_client.py`: 原生DeepSeek API客户端
- `langchain_deepseek_client.py`: LangChain包装客户端
- `client_factory.py`: 客户端工厂和统一接口

### 2. 任务规划模块 (`src/planning/`)

**功能**: 复杂任务的分解、规划和执行计划生成

**工作原理**:
- 递归分解复杂任务为可执行子任务
- 分析任务间依赖关系和执行顺序
- 生成包含时间估算的执行计划
- 支持任务优先级和资源分配

**关键文件**:
- `task_planner.py`: 任务分解和规划逻辑
- 上下文提取和动态提示生成

### 3. 记忆管理模块 (`src/memory/`)

**功能**: 多层次记忆存储和智能检索

**工作原理**:
- **短期记忆**: 当前对话会话的临时存储
- **长期记忆**: 持久化的用户偏好和历史信息
- **语义搜索**: 基于向量相似度的记忆检索
- **自动过期**: 根据重要性和时间自动清理记忆

**存储后端**:
- SQLite: 轻量级本地存储
- Redis: 高性能缓存和分布式存储

### 4. RAG检索模块 (`src/rag/`)

**功能**: 知识库管理和语义检索

**工作原理**:
- **文档处理**: 自动分割、清洗和向量化文档
- **向量存储**: 使用ChromaDB进行高效向量存储
- **语义检索**: 基于embeddings的相似度搜索
- **上下文增强**: 将检索结果整合到对话上下文

**支持格式**: PDF, TXT, MD, JSON等多种文档格式

### 5. 工具集成模块 (`src/tools/`)

**功能**: 外部工具和服务的统一调用接口

**内置工具**:
- **Web搜索**: DuckDuckGo、Tavily搜索引擎
- **文件操作**: 通过MCP协议进行文件读写
- **系统命令**: 安全的命令执行环境
- **计算工具**: 数学计算和数据处理

**MCP支持**:
- MCP客户端: 连接外部MCP服务器
- MCP服务器: 提供工具给其他MCP客户端
- 标准化协议: 遵循Model Context Protocol规范

### 6. Agent协调模块 (`src/agents/`)

**功能**: 多Agent协作和任务分发

**协调策略**:
- **任务匹配**: 根据Agent能力自动分配任务
- **负载均衡**: 避免单个Agent过载
- **结果汇聚**: 智能整合多Agent输出
- **冲突解决**: 处理Agent间的输出冲突

### 7. 框架核心 (`src/framework/`)

**功能**: 整体框架的编排和管理

**核心特性**:
- LangGraph状态图管理
- 异步任务处理
- 错误恢复机制
- 性能监控和日志记录

## 项目结构

```
ma/
├── src/
│   ├── core/           # 核心模型和配置
│   │   ├── models.py   # 数据模型定义（Agent、Task、Message等）
│   │   ├── config.py   # 配置管理和环境变量
│   │   └── logger.py   # 日志记录和监控
│   ├── llm/           # LLM客户端和意图识别
│   │   ├── deepseek_client.py        # 原生DeepSeek客户端
│   │   ├── langchain_deepseek_client.py  # LangChain包装客户端
│   │   └── client_factory.py        # 客户端工厂和统一接口
│   ├── planning/      # 任务规划和上下文提取
│   │   └── task_planner.py          # 任务分解和执行计划
│   ├── memory/        # 记忆管理模块
│   │   └── memory_manager.py        # 多层记忆存储和检索
│   ├── rag/           # RAG检索模块
│   │   └── rag_manager.py           # 知识库管理和向量搜索
│   ├── tools/         # 工具集合
│   │   ├── web_search.py            # Web搜索引擎集成
│   │   ├── mcp_client.py            # MCP客户端实现
│   │   └── mcp_server.py            # MCP服务器实现
│   ├── agents/        # Agent实现
│   │   └── coordinator.py           # 协调器Agent
│   ├── framework/     # 多Agent框架
│   │   └── multi_agent_framework.py # 框架核心逻辑
│   ├── api/           # FastAPI服务器
│   │   └── server.py               # RESTful API接口
│   └── cli/           # 命令行界面
│       └── main.py                 # CLI入口和交互
├── examples/          # 业务场景示例
│   ├── medical_agent.py            # 医疗助手示例
│   ├── travel_agent.py             # 旅行助手示例
│   └── research_agent.py           # 科研助手示例
├── requirements.txt   # 依赖包管理
├── .env.example      # 环境变量示例
├── run.py            # 快速启动脚本
└── README.md         # 详细说明文档
```

## 使用示例

### 基础对话示例

```python
from src.framework.multi_agent_framework import MultiAgentFramework
import asyncio

async def basic_chat_example():
    # 初始化框架
    framework = MultiAgentFramework()
    
    # 初始化MCP连接
    await framework.initialize_mcp()
    
    # 简单对话
    response = await framework.process_message("你好，今天天气怎么样？")
    print(f"AI回复: {response['response']}")
    
    # 复杂任务
    response = await framework.process_message(
        "帮我制定一个三天的北京旅行计划，预算3000元"
    )
    print(f"旅行计划: {response['response']}")
    print(f"调用的工具: {response.get('tool_calls', [])}")

# 运行示例
asyncio.run(basic_chat_example())
```

### 工具调用示例

```python
async def tool_usage_example():
    framework = MultiAgentFramework()
    await framework.initialize_mcp()
    
    # 触发Web搜索
    response = await framework.process_message("搜索最新的AI技术发展动态")
    
    # 触发文件操作
    response = await framework.process_message("读取README.md文件的内容")
    
    # 触发记忆检索
    response = await framework.process_message("我们上次讨论的项目进展如何？")
    
    # 触发RAG检索
    response = await framework.process_message("根据知识库回答什么是LangGraph？")
```

### 业务Agent集成示例

```python
from src.framework.multi_agent_framework import MultiAgentFramework
from examples.medical_agent import MedicalAgent

async def medical_assistant_example():
    # 创建框架
    framework = MultiAgentFramework()
    
    # 创建并注册医疗Agent
    medical_agent = MedicalAgent()
    framework.coordinator.register_agent(medical_agent)
    
    # 添加医疗知识库
    await framework.add_knowledge_file("medical_guidelines.pdf")
    
    # 医疗咨询
    response = await framework.process_message(
        "我最近总是感觉头痛，可能是什么原因？"
    )
    print(f"医疗建议: {response['response']}")
```

## 快速开始

### 🚀 一键初始化 (推荐)

```bash
# 克隆项目
git clone <repository-url>
cd multi-agent-framework

# 完整初始化（创建虚拟环境 + 安装依赖 + 配置环境）
python run.py --setup

# 配置API密钥
# 编辑 .env 文件，填入您的DeepSeek API密钥

# 启动使用
python run.py --chat
```

### 📋 分步骤设置

#### 1. 环境准备

**选项A: 使用run.py脚本**
```bash
# 创建虚拟环境并安装依赖
python run.py --install

# 查看虚拟环境信息
python run.py --venv-info
```

**选项B: 使用平台脚本**
```bash
# macOS/Linux
./setup.sh setup

# Windows
setup.bat setup
```

#### 2. 激活虚拟环境

```bash
# macOS/Linux
source venv/bin/activate

# Windows Command Prompt
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1
```

#### 3. 配置环境变量

#### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入相应的API密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 其他配置...
```

#### 4. 运行程序

```bash
# 启动聊天模式
python run.py --chat

# 启动API服务器
python run.py --server

# 运行测试
python run.py --test
```

### 🔧 虚拟环境管理

详细的虚拟环境使用指南请参考 [VENV_GUIDE.md](VENV_GUIDE.md)

**常用命令:**
```bash
# 查看虚拟环境状态
python run.py --venv-info

# 重新安装依赖
python run.py --install

# 不使用虚拟环境运行（不推荐）
python run.py --chat --no-venv
```

## API接口

### 聊天接口

```bash
POST /chat
{
  "message": "帮我制定一个周末旅行计划",
  "conversation_id": "optional",
  "user_id": "optional"
}
```

### 知识管理

```bash
# 添加知识
POST /knowledge/add
{
  "content": "知识内容",
  "source": "来源标识"
}

# 搜索知识
POST /knowledge/search
{
  "query": "搜索关键词",
  "limit": 5
}
```

### 对话历史

```bash
GET /conversation/{conversation_id}
```

## 业务场景适配

### 家庭医生助手

```python
from src.agents.medical_agent import MedicalAgent
from src.framework.multi_agent_framework import create_agent_framework

# 创建框架实例
framework = await create_agent_framework()

# 注册医疗专用Agent
medical_agent = MedicalAgent()
framework.register_agent(medical_agent)

# 添加医疗知识库
await framework.add_knowledge_file("medical_knowledge.txt")
```

### 旅行规划助手

```python
from src.agents.travel_agent import TravelAgent

framework = await create_agent_framework()
travel_agent = TravelAgent()
framework.register_agent(travel_agent)
```

### 科研助手

```python
from src.agents.research_agent import ResearchAgent

framework = await create_agent_framework()
research_agent = ResearchAgent()
framework.register_agent(research_agent)
```

## 自定义Agent开发

### 开发指南

继承 `BaseAgent` 类创建自定义Agent：

```python
from src.core.models import BaseAgent, AgentType, AgentState, AgentResponse, Task
from src.core.logger import LoggerMixin

class CustomAgent(BaseAgent, LoggerMixin):
    def __init__(self):
        BaseAgent.__init__(self, "custom_agent", AgentType.SPECIALIST)
        LoggerMixin.__init__(self)
        
        # 初始化专业知识和工具
        self.domain_knowledge = self._load_domain_knowledge()
        self.specialized_tools = self._init_specialized_tools()
    
    async def process(self, state: AgentState) -> AgentResponse:
        """处理用户请求的核心逻辑"""
        try:
            # 1. 分析任务需求
            task_analysis = await self._analyze_task(state.current_task)
            
            # 2. 检查专业能力匹配度
            capability_score = await self._assess_capability(task_analysis)
            
            if capability_score < 0.7:
                return AgentResponse(
                    content="此任务超出我的专业能力范围",
                    confidence=0.3,
                    next_action="delegate"
                )
            
            # 3. 执行专业处理逻辑
            result = await self._execute_professional_task(state)
            
            return AgentResponse(
                content=result.content,
                confidence=result.confidence,
                tool_calls=result.tool_calls,
                metadata=result.metadata
            )
            
        except Exception as e:
            self.log_error(f"处理任务失败: {str(e)}")
            return AgentResponse(
                content="处理过程中遇到错误，请稍后重试",
                confidence=0.0,
                error=str(e)
            )
    
    async def can_handle(self, task: Task) -> bool:
        """判断是否能处理该任务"""
        # 检查任务类型和关键词
        domain_keywords = ["专业关键词1", "专业关键词2"]
        task_content = task.description.lower()
        
        return any(keyword in task_content for keyword in domain_keywords)
    
    def _load_domain_knowledge(self):
        """加载领域专业知识"""
        # 实现知识加载逻辑
        pass
    
    def _init_specialized_tools(self):
        """初始化专业工具"""
        # 实现工具初始化逻辑
        pass
```

### Agent能力扩展

```python
class AdvancedCustomAgent(CustomAgent):
    """高级自定义Agent，展示更多功能"""
    
    def __init__(self):
        super().__init__()
        # 添加学习能力
        self.learning_module = self._init_learning_module()
        # 添加协作能力
        self.collaboration_interface = self._init_collaboration()
    
    async def learn_from_feedback(self, feedback: Dict[str, Any]):
        """从用户反馈中学习"""
        await self.learning_module.process_feedback(feedback)
        self.log_info("已从反馈中学习并更新模型")
    
    async def collaborate_with_agents(self, agents: List[BaseAgent], task: Task):
        """与其他Agent协作完成任务"""
        collaboration_plan = await self._plan_collaboration(agents, task)
        results = []
        
        for step in collaboration_plan:
            agent = step['agent']
            subtask = step['subtask']
            result = await agent.process(subtask)
            results.append(result)
        
        return await self._synthesize_collaboration_results(results)
```

### Agent注册和管理

```python
async def register_custom_agents():
    """注册自定义Agent到框架"""
    framework = MultiAgentFramework()
    
    # 注册多个专业Agent
    agents = [
        CustomAgent(),
        MedicalAgent(),
        TravelAgent(),
        ResearchAgent()
    ]
    
    for agent in agents:
        framework.coordinator.register_agent(agent)
        print(f"已注册Agent: {agent.name}")
    
    return framework
```

## 配置说明

### 环境变量配置

主要配置项在 `src/core/config.py` 中定义，通过 `.env` 文件进行配置：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# LLM客户端选择 (native 或 langchain)
LLM_CLIENT_TYPE=langchain

# 数据库配置
SQLITE_DB_PATH=./data/agent_memory.db
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# Redis配置（可选）
REDIS_URL=redis://localhost:6379/0

# Web搜索配置
TAVILY_API_KEY=your_tavily_api_key_here
DUCKDUCKGO_ENABLED=true

# RAG配置
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200
RAG_TOP_K=5

# 意图识别配置
INTENT_CONFIDENCE_THRESHOLD=0.7
INTENT_MODEL_TYPE=deepseek

# MCP配置
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8080

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/agent.log
```

### 高级配置选项

```python
# src/core/config.py 中的详细配置
class Settings:
    # 模型配置
    max_tokens: int = 4000
    temperature: float = 0.7
    
    # 任务规划配置
    max_subtasks: int = 10
    task_timeout: int = 300  # 秒
    
    # 记忆配置
    memory_retention_days: int = 30
    max_memory_items: int = 1000
    
    # RAG配置
    embedding_model: str = "text-embedding-ada-002"
    similarity_threshold: float = 0.75
    
    # Agent配置
    max_concurrent_agents: int = 5
    agent_timeout: int = 60
```

### 运行时配置

```python
# 动态配置调整
async def configure_runtime():
    framework = MultiAgentFramework()
    
    # 调整模型参数
    framework.llm_factory.update_config({
        "temperature": 0.5,
        "max_tokens": 2000
    })
    
    # 配置记忆保留策略
    framework.memory_manager.configure({
        "retention_policy": "importance_based",
        "max_items": 500
    })
    
    # 配置RAG检索策略
    if framework.rag_manager:
        framework.rag_manager.configure({
            "retrieval_strategy": "hybrid",
            "rerank_enabled": True
        })
```

## 技术栈与依赖

### 核心技术栈

- **LangGraph**: 工作流编排和状态管理
- **DeepSeek**: 大语言模型和API服务
- **ChromaDB**: 向量数据库和语义搜索
- **SQLite/Redis**: 记忆存储和缓存
- **FastAPI**: Web API框架和服务器
- **Pydantic**: 数据验证和结构化输出
- **Rich/Typer**: 命令行界面和交互

### 关键依赖包

```txt
# LLM和AI相关
langgraph>=0.2.0
langchain-deepseek>=0.1.3
openai>=1.0.0  # DeepSeek兼容API

# 向量数据库和搜索
chromadb>=0.4.0
sentence-transformers>=2.2.0
duckduckgo-search>=3.9.0

# Web框架和API
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0

# 数据存储
redis>=5.0.0
sqlite3  # Python内置

# MCP支持
mcp>=1.0.0  # Model Context Protocol

# 工具和实用程序
typer>=0.9.0
rich>=13.0.0
python-dotenv>=1.0.0
```

### 可选依赖

```txt
# 高级RAG功能
faiss-cpu>=1.7.0  # Facebook AI向量搜索
elasticsearch>=8.0.0  # 全文搜索引擎

# 增强搜索
tavily-python>=0.3.0  # Tavily搜索API

# 监控和日志
prometheus_client>=0.19.0
structlog>=23.0.0

# 测试框架
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

## 扩展开发指南

### 添加新工具

1. **创建工具类**

```python
# src/tools/custom_tool.py
from src.core.logger import LoggerMixin
from typing import Dict, Any

class CustomTool(LoggerMixin):
    """自定义工具示例"""
    
    def __init__(self):
        super().__init__()
        self.name = "custom_tool"
        self.description = "自定义工具描述"
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具逻辑"""
        try:
            # 实现具体的工具逻辑
            result = self._process_parameters(parameters)
            
            self.log_info(f"工具 {self.name} 执行成功")
            return {
                "success": True,
                "result": result,
                "tool_name": self.name
            }
        except Exception as e:
            self.log_error(f"工具 {self.name} 执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": self.name
            }
    
    def _process_parameters(self, parameters: Dict[str, Any]) -> Any:
        """处理参数的具体逻辑"""
        # 实现参数处理逻辑
        pass
```

2. **注册工具到管理器**

```python
# 在相应的管理器中注册工具
from src.tools.custom_tool import CustomTool

class ToolManager:
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        # 注册自定义工具
        custom_tool = CustomTool()
        self.register_tool(custom_tool)
    
    def register_tool(self, tool):
        self.tools[tool.name] = tool
```

### 添加新的记忆存储后端

1. **继承BaseMemory类**

```python
# src/memory/custom_memory.py
from src.memory.memory_manager import BaseMemory
from typing import List, Dict, Any, Optional

class CustomMemory(BaseMemory):
    """自定义记忆存储后端"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._init_storage()
    
    async def save_memory(
        self, 
        content: str, 
        memory_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """保存记忆"""
        # 实现保存逻辑
        memory_id = self._generate_memory_id()
        await self._store_memory(memory_id, content, memory_type, metadata)
        return memory_id
    
    async def retrieve_memories(
        self, 
        query: str, 
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """检索记忆"""
        # 实现检索逻辑
        return await self._search_memories(query, memory_type, limit)
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        # 实现删除逻辑
        return await self._remove_memory(memory_id)
```

2. **集成到MemoryManager**

```python
# 在MemoryManager中配置新的存储后端
from src.memory.custom_memory import CustomMemory

memory_backend = CustomMemory("custom://connection_string")
memory_manager = MemoryManager(memory_backend)
```

### 添加新的RAG后端

1. **继承BaseRAG类**

```python
# src/rag/custom_rag.py
from src.rag.rag_manager import BaseRAG
from typing import List, Dict, Any

class CustomRAG(BaseRAG):
    """自定义RAG后端"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._init_vector_store()
    
    async def add_documents(
        self, 
        documents: List[str], 
        metadata: List[Dict[str, Any]] = None
    ) -> List[str]:
        """添加文档到向量存储"""
        # 实现文档添加逻辑
        doc_ids = []
        for i, doc in enumerate(documents):
            doc_id = await self._add_document(doc, metadata[i] if metadata else {})
            doc_ids.append(doc_id)
        return doc_ids
    
    async def search_documents(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """搜索相关文档"""
        # 实现搜索逻辑
        return await self._vector_search(query, top_k, filters)
    
    async def delete_documents(self, doc_ids: List[str]) -> bool:
        """删除文档"""
        # 实现删除逻辑
        return await self._remove_documents(doc_ids)
```

### 添加新的LLM客户端

1. **继承BaseLLMClient类**

```python
# src/llm/custom_llm_client.py
from src.llm.client_factory import BaseLLMClient
from typing import List, Dict, Any, Optional

class CustomLLMClient(BaseLLMClient):
    """自定义LLM客户端"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self._init_client()
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """生成响应"""
        # 实现响应生成逻辑
        response = await self._call_api(messages, system_prompt, **kwargs)
        return response
    
    async def generate_structured_response(
        self, 
        messages: List[Dict[str, str]],
        response_model: Any,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Any:
        """生成结构化响应"""
        # 实现结构化响应生成逻辑
        response = await self._call_structured_api(
            messages, response_model, system_prompt, **kwargs
        )
        return response
```

2. **注册到LLMClientFactory**

```python
# 在LLMClientFactory中注册新客户端
from src.llm.custom_llm_client import CustomLLMClient

class LLMClientFactory:
    @staticmethod
    def create_client(client_type: str = "auto") -> BaseLLMClient:
        if client_type == "custom":
            return CustomLLMClient(
                api_key=settings.custom_api_key,
                base_url=settings.custom_base_url
            )
        # ... 其他客户端逻辑
```

### 性能优化建议

1. **异步处理优化**
```python
# 使用并发处理提高性能
import asyncio

async def process_multiple_requests(requests):
    tasks = [process_single_request(req) for req in requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

2. **缓存策略**
```python
# 实现智能缓存
from functools import lru_cache
import time

class CachedLLMClient:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1小时
    
    async def cached_generate(self, messages, **kwargs):
        cache_key = self._create_cache_key(messages, kwargs)
        
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_result
        
        result = await self.generate_response(messages, **kwargs)
        self.cache[cache_key] = (result, time.time())
        return result
```

## 性能监控与调试

### 性能监控

框架内置了性能监控功能，可以跟踪各组件的执行时间和资源使用情况：

```python
# 启用性能监控
from src.core.logger import LoggerMixin

class PerformanceMonitor(LoggerMixin):
    def __init__(self):
        super().__init__()
        self.metrics = {}
    
    async def monitor_execution(self, func_name: str, func, *args, **kwargs):
        """监控函数执行性能"""
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            self.metrics[func_name] = self.metrics.get(func_name, [])
            self.metrics[func_name].append(execution_time)
            
            self.log_info(f"{func_name} 执行时间: {execution_time:.2f}s")
            return result
        except Exception as e:
            self.log_error(f"{func_name} 执行失败: {str(e)}")
            raise
    
    def get_performance_stats(self):
        """获取性能统计信息"""
        stats = {}
        for func_name, times in self.metrics.items():
            stats[func_name] = {
                "avg_time": sum(times) / len(times),
                "max_time": max(times),
                "min_time": min(times),
                "call_count": len(times)
            }
        return stats
```

### 调试工具

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 调试特定组件
framework = MultiAgentFramework()
framework.set_debug_mode(True)

# 查看内部状态
debug_info = await framework.get_debug_info()
print(f"当前状态: {debug_info}")

# 跟踪消息流
response = await framework.process_message(
    "测试消息", 
    debug=True
)
```

### 错误处理和恢复

```python
class RobustFramework(MultiAgentFramework):
    """具有错误恢复能力的框架"""
    
    def __init__(self):
        super().__init__()
        self.retry_count = 3
        self.fallback_responses = {
            "llm_error": "抱歉，语言模型暂时不可用，请稍后重试。",
            "tool_error": "工具调用失败，尝试使用备用方案。",
            "memory_error": "记忆系统异常，但不影响当前对话。"
        }
    
    async def process_message_with_retry(self, message: str, **kwargs):
        """带重试机制的消息处理"""
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                return await self.process_message(message, **kwargs)
            except Exception as e:
                last_error = e
                self.log_warning(f"第{attempt + 1}次尝试失败: {str(e)}")
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
        
        # 使用备用响应
        error_type = self._classify_error(last_error)
        fallback_response = self.fallback_responses.get(
            error_type, 
            "系统遇到未知错误，请稍后重试。"
        )
        
        return {
            "response": fallback_response,
            "confidence": 0.1,
            "error": str(last_error),
            "fallback": True
        }
```

## 最佳实践

### 1. Agent设计原则

- **单一职责**: 每个Agent专注于特定领域
- **松耦合**: Agent间通过标准接口通信
- **可测试**: 提供完整的单元测试覆盖
- **可观察**: 记录详细的执行日志

### 2. 性能优化

- **异步优先**: 使用async/await处理I/O密集操作
- **缓存策略**: 合理缓存LLM响应和搜索结果
- **批处理**: 批量处理相似请求
- **资源管理**: 及时释放不需要的资源

### 3. 安全考虑

- **输入验证**: 严格验证用户输入
- **权限控制**: 限制Agent的操作权限
- **敏感信息**: 避免在日志中记录敏感数据
- **API限制**: 合理设置API调用频率限制

### 4. 可维护性

- **代码结构**: 保持清晰的模块划分
- **文档完善**: 为每个组件提供详细文档
- **版本管理**: 使用语义化版本控制
- **测试覆盖**: 保持高测试覆盖率

## 故障排除

### 常见问题

1. **DeepSeek API连接失败**
   - 检查API密钥是否正确
   - 验证网络连接
   - 确认API配额是否充足

2. **ChromaDB初始化失败**
   - 检查存储目录权限
   - 验证依赖包安装
   - 清理损坏的数据文件

3. **MCP连接超时**
   - 检查MCP服务器状态
   - 验证网络配置
   - 增加连接超时时间

4. **内存使用过高**
   - 调整缓存大小限制
   - 优化文档分块策略
   - 启用内存清理机制

### 日志分析

```bash
# 查看错误日志
grep -i error logs/agent.log

# 分析性能瓶颈
grep -i "execution_time" logs/agent.log | sort -k3 -nr

# 监控API调用
grep -i "api_call" logs/agent.log | tail -n 50
```

## 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

### 贡献流程

1. **Fork项目**
   ```bash
   git clone https://github.com/your-username/multi-agent-framework.git
   cd multi-agent-framework
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **开发和测试**
   ```bash
   # 安装开发依赖
   pip install -r requirements-dev.txt
   
   # 运行测试
   pytest tests/
   
   # 代码格式化
   black src/
   isort src/
   
   # 类型检查
   mypy src/
   ```

4. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   ```

5. **推送和PR**
   ```bash
   git push origin feature/your-feature-name
   # 然后在GitHub上创建Pull Request
   ```

### 代码规范

- 遵循PEP 8代码风格
- 使用类型提示
- 编写详细的文档字符串
- 保持测试覆盖率 > 80%

### 提交消息格式

```
<type>(<scope>): <description>

<body>

<footer>
```

类型：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构代码
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

### 问题报告

提交Issue时请包含：
- 详细的问题描述
- 复现步骤
- 期望行为
- 实际行为
- 环境信息（Python版本、操作系统等）
- 相关日志或错误信息

## 更新日志

### v1.0.0 (2025-06-24)
- ✨ 初始版本发布
- 🎯 完整的多Agent框架实现
- 🤖 DeepSeek模型集成
- 📊 LangGraph工作流编排
- 🧠 多层记忆管理
- 🔍 RAG知识检索
- 🌐 Web搜索集成
- 🚀 MCP协议支持
- 💻 CLI和API接口
- 📝 详细文档和示例

### 开发路线图

#### v1.1.0 (计划中)
- [ ] 支持更多LLM模型（OpenAI、Claude等）
- [ ] 增强的Agent协作机制
- [ ] 可视化工作流编辑器
- [ ] 性能优化和监控仪表板

#### v1.2.0 (计划中)
- [ ] 多模态支持（图像、语音）
- [ ] 分布式Agent部署
- [ ] 高级安全和权限管理
- [ ] 企业级监控和告警

#### v2.0.0 (长期计划)
- [ ] 自适应学习能力
- [ ] 跨语言Agent通信
- [ ] 云原生部署支持
- [ ] 完整的开发者生态

## 许可证

本项目采用 MIT License 开源协议。

```
MIT License

Copyright (c) 2025 Multi-Agent Framework

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 致谢

感谢以下项目和社区的贡献：

- [LangGraph](https://github.com/langchain-ai/langgraph) - 工作流编排框架
- [DeepSeek](https://www.deepseek.com/) - 优秀的大语言模型
- [ChromaDB](https://github.com/chroma-core/chroma) - 向量数据库
- [FastAPI](https://github.com/tiangolo/fastapi) - 现代Web框架
- [Pydantic](https://github.com/pydantic/pydantic) - 数据验证框架

## 联系方式

- **GitHub Issues**: [提交问题和建议](https://github.com/your-username/multi-agent-framework/issues)
- **讨论**: [GitHub Discussions](https://github.com/your-username/multi-agent-framework/discussions)
- **邮件**: your-email@example.com

---

**⭐ 如果这个项目对你有帮助，请给个星标支持！**
