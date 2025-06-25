from typing import Any, Dict, List, Optional, Union, Type
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
import json
import asyncio
from src.core.models import Intent, IntentType, AgentState, AgentResponse
from src.core.config import settings
from src.core.logger import LoggerMixin

try:
    from langchain_deepseek import ChatDeepSeek
    HAS_LANGCHAIN_DEEPSEEK = True
except ImportError:
    # 如果没有安装langchain-deepseek，使用langchain-openai作为替代
    from langchain_openai import ChatOpenAI as ChatDeepSeek
    HAS_LANGCHAIN_DEEPSEEK = False


class StructuredIntent(BaseModel):
    """结构化意图模型"""
    type: str = Field(description="意图类型: casual_chat, information_query, complex_task, task_execution")
    confidence: float = Field(description="置信度 0-1", ge=0.0, le=1.0)
    entities: Dict[str, Any] = Field(default_factory=dict, description="实体信息")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class StructuredTaskAnalysis(BaseModel):
    """结构化任务分析模型"""
    name: str = Field(description="任务名称")
    description: str = Field(description="任务描述")
    complexity: str = Field(description="任务复杂度: simple, medium, complex")
    subtasks: List[Dict[str, Any]] = Field(default_factory=list, description="子任务列表")
    required_info: List[str] = Field(default_factory=list, description="所需信息")
    estimated_steps: int = Field(description="预估步骤数", ge=1)


class StructuredContext(BaseModel):
    """结构化上下文模型"""
    key_topics: List[str] = Field(default_factory=list, description="关键话题")
    mentioned_entities: Dict[str, List[str]] = Field(default_factory=dict, description="提及的实体")
    user_preferences: Dict[str, str] = Field(default_factory=dict, description="用户偏好")
    context_summary: str = Field(description="上下文摘要")


class LangChainDeepSeekClient(LoggerMixin):
    """基于LangChain的DeepSeek客户端，支持结构化输出"""
    
    def __init__(self):
        super().__init__()
        
        # 根据base_url判断使用哪种客户端
        if "siliconflow" in settings.deepseek_base_url.lower():
            # SiliconFlow使用OpenAI兼容接口
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=settings.deepseek_model,
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                    temperature=0.7,
                    max_tokens=4000
                )
                self.logger.info("使用OpenAI兼容客户端连接SiliconFlow")
            except ImportError:
                self.logger.error("需要安装langchain-openai: pip install langchain-openai")
                raise
        else:
            # DeepSeek官方API
            if HAS_LANGCHAIN_DEEPSEEK:
                self.llm = ChatDeepSeek(
                    model=settings.deepseek_model,
                    api_key=settings.deepseek_api_key,
                    temperature=0.7,
                    max_tokens=4000
                )
                self.logger.info("使用LangChain DeepSeek客户端")
            else:
                # 回退到OpenAI兼容方式
                try:
                    from langchain_openai import ChatOpenAI
                    self.llm = ChatOpenAI(
                        model=settings.deepseek_model,
                        api_key=settings.deepseek_api_key,
                        base_url=settings.deepseek_base_url,
                        temperature=0.7,
                        max_tokens=4000
                    )
                    self.logger.info("使用OpenAI兼容客户端作为备用")
                except ImportError:
                    self.logger.error("需要安装langchain-openai: pip install langchain-openai")
                    raise
        
        # 创建结构化输出解析器
        self.intent_parser = PydanticOutputParser(pydantic_object=StructuredIntent)
        self.task_parser = PydanticOutputParser(pydantic_object=StructuredTaskAnalysis)
        self.context_parser = PydanticOutputParser(pydantic_object=StructuredContext)
        
        # 创建通用JSON解析器
        self.json_parser = JsonOutputParser()
    
    def _create_temp_client(self, temperature: float = 0.7, max_tokens: int = 4000):
        """创建临时客户端"""
        if "siliconflow" in settings.deepseek_base_url.lower():
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.deepseek_model,
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            if HAS_LANGCHAIN_DEEPSEEK:
                return ChatDeepSeek(
                    model=settings.deepseek_model,
                    api_key=settings.deepseek_api_key,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=settings.deepseek_model,
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """生成响应"""
        try:
            # 构建消息
            chat_messages = []
            
            if system_prompt:
                chat_messages.append(SystemMessage(content=system_prompt))
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    chat_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    chat_messages.append(AIMessage(content=content))
                elif role == "system":
                    chat_messages.append(SystemMessage(content=content))
            
            # 创建临时客户端（如果需要不同的参数）
            if temperature != 0.7 or max_tokens:
                temp_llm = self._create_temp_client(temperature, max_tokens or 4000)
                response = await temp_llm.ainvoke(chat_messages)
            else:
                response = await self.llm.ainvoke(chat_messages)
            
            return response.content
            
        except Exception as e:
            self.log_error(f"LangChain DeepSeek生成响应失败: {str(e)}")
            raise
    
    async def generate_structured_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        pydantic_model: Optional[Type[BaseModel]] = None,
        temperature: float = 0.7
    ) -> Union[Dict[str, Any], BaseModel]:
        """生成结构化响应"""
        try:
            # 选择合适的解析器
            if pydantic_model:
                parser = PydanticOutputParser(pydantic_object=pydantic_model)
            else:
                parser = self.json_parser
            
            # 构建提示模板
            format_instructions = parser.get_format_instructions()
            
            # 更新系统提示以包含格式说明
            if system_prompt:
                enhanced_system_prompt = f"{system_prompt}\n\n{format_instructions}"
            else:
                enhanced_system_prompt = f"请按照以下格式回复：\n{format_instructions}"
            
            # 构建消息
            chat_messages = [SystemMessage(content=enhanced_system_prompt)]
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    chat_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    chat_messages.append(AIMessage(content=content))
            
            # 创建链
            temp_llm = self._create_temp_client(temperature, 4000)
            
            chain = temp_llm | parser
            
            # 执行链
            result = await chain.ainvoke(chat_messages)
            
            return result
            
        except Exception as e:
            self.log_error(f"LangChain DeepSeek生成结构化响应失败: {str(e)}")
            # 尝试常规响应作为备选
            try:
                response = await self.generate_response(messages, system_prompt, temperature)
                # 尝试解析JSON
                return json.loads(response)
            except:
                return {"content": response, "error": "failed_to_parse"}
    
    async def recognize_intent_structured(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Intent:
        """使用结构化输出识别意图"""
        system_prompt = """
        你是一个意图识别专家。请分析用户输入，识别其意图类型。
        
        意图类型包括：
        - casual_chat: 日常聊天、问候、闲聊
        - information_query: 简单的信息查询
        - complex_task: 需要多步骤处理的复杂任务
        - task_execution: 具体的任务执行请求
        
        请准确识别意图并提供置信度。
        """
        
        messages = [{"role": "user", "content": message}]
        
        if context:
            system_prompt += f"\n\n当前上下文：{json.dumps(context, ensure_ascii=False)}"
        
        try:
            structured_result = await self.generate_structured_response(
                messages=messages,
                system_prompt=system_prompt,
                pydantic_model=StructuredIntent,
                temperature=0.3
            )
            
            return Intent(
                type=IntentType(structured_result.type),
                confidence=structured_result.confidence,
                entities=structured_result.entities,
                context=structured_result.context
            )
            
        except Exception as e:
            self.log_error(f"结构化意图识别失败: {str(e)}")
            # 返回默认意图
            return Intent(
                type=IntentType.CASUAL_CHAT,
                confidence=0.5,
                entities={},
                context={}
            )
    
    async def analyze_task_structured(
        self,
        task_description: str
    ) -> StructuredTaskAnalysis:
        """使用结构化输出分析任务"""
        system_prompt = """
        请分析用户的任务描述，提供结构化的任务分析结果。
        
        任务复杂度：
        - simple: 简单任务，一步即可完成
        - medium: 中等复杂度，需要2-3个步骤
        - complex: 复杂任务，需要多个步骤和子任务
        
        请提供详细的任务分析。
        """
        
        messages = [{"role": "user", "content": f"任务：{task_description}"}]
        
        try:
            result = await self.generate_structured_response(
                messages=messages,
                system_prompt=system_prompt,
                pydantic_model=StructuredTaskAnalysis,
                temperature=0.5
            )
            
            return result
            
        except Exception as e:
            self.log_error(f"结构化任务分析失败: {str(e)}")
            # 返回默认分析
            return StructuredTaskAnalysis(
                name=task_description,
                description=task_description,
                complexity="medium",
                subtasks=[],
                required_info=[],
                estimated_steps=1
            )
    
    async def extract_context_structured(
        self,
        current_message: str,
        conversation_history: List[Dict[str, Any]],
        max_messages: int = 10
    ) -> StructuredContext:
        """使用结构化输出提取上下文"""
        system_prompt = """
        根据当前消息和对话历史，提取相关的上下文信息。
        请识别关键话题、实体和用户偏好。
        """
        
        # 构建上下文文本
        context_text = f"当前消息：{current_message}\n\n"
        
        recent_messages = conversation_history[-max_messages:] if conversation_history else []
        if recent_messages:
            context_text += "对话历史：\n"
            for msg in recent_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_text += f"{role}: {content}\n"
        
        messages = [{"role": "user", "content": context_text}]
        
        try:
            result = await self.generate_structured_response(
                messages=messages,
                system_prompt=system_prompt,
                pydantic_model=StructuredContext,
                temperature=0.3
            )
            
            return result
            
        except Exception as e:
            self.log_error(f"结构化上下文提取失败: {str(e)}")
            # 返回默认上下文
            return StructuredContext(
                key_topics=[],
                mentioned_entities={},
                user_preferences={},
                context_summary="无可用上下文"
            )
    
    async def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成带工具调用的响应"""
        # 这里可以集成LangChain的工具调用功能
        # 目前先实现基础版本
        
        enhanced_prompt = system_prompt or ""
        if tools:
            tools_desc = "\n可用工具：\n"
            for tool in tools:
                tools_desc += f"- {tool.get('name', '')}: {tool.get('description', '')}\n"
            enhanced_prompt += tools_desc
        
        try:
            response = await self.generate_response(
                messages=messages,
                system_prompt=enhanced_prompt
            )
            
            return {
                "content": response,
                "tool_calls": []  # 可以在这里实现工具调用解析
            }
            
        except Exception as e:
            self.log_error(f"带工具调用的响应生成失败: {str(e)}")
            return {"content": "生成响应时出现错误", "tool_calls": []}


class EnhancedIntentRecognizer(LoggerMixin):
    """增强的意图识别器，支持结构化输出"""
    
    def __init__(self, llm_client: LangChainDeepSeekClient):
        super().__init__()
        self.llm_client = llm_client
    
    async def recognize_intent(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Intent:
        """识别用户意图"""
        return await self.llm_client.recognize_intent_structured(message, context)
    
    async def batch_recognize_intents(
        self,
        messages: List[str],
        context: Dict[str, Any] = None
    ) -> List[Intent]:
        """批量识别意图"""
        tasks = [
            self.recognize_intent(msg, context)
            for msg in messages
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        intents = []
        for result in results:
            if isinstance(result, Exception):
                self.log_error(f"批量意图识别部分失败: {result}")
                intents.append(Intent(
                    type=IntentType.CASUAL_CHAT,
                    confidence=0.0,
                    entities={},
                    context={}
                ))
            else:
                intents.append(result)
        
        return intents
