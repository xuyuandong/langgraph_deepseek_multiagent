from typing import Any, Dict, List, Optional
from openai import OpenAI
from src.core.models import Message, Intent, IntentType, AgentState, AgentResponse
from src.core.config import settings
from src.core.logger import LoggerMixin
import json


class DeepSeekLLM(LoggerMixin):
    """DeepSeek LLM客户端"""
    
    def __init__(self):
        super().__init__()
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        self.model = settings.deepseek_model
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """生成响应"""
        try:
            formatted_messages = []
            
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            
            formatted_messages.extend(messages)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.log_error(f"LLM生成响应失败: {str(e)}")
            raise
    
    async def generate_structured_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        response_format: Optional[Dict] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """生成结构化响应"""
        try:
            formatted_messages = []
            
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            
            formatted_messages.extend(messages)
            
            # 添加结构化输出要求
            if response_format:
                system_msg = f"请以JSON格式回复，格式要求：{json.dumps(response_format, ensure_ascii=False)}"
                if system_prompt:
                    formatted_messages[0]["content"] += f"\n\n{system_msg}"
                else:
                    formatted_messages.insert(0, {"role": "system", "content": system_msg})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            
            # 尝试解析JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # 如果不是有效JSON，返回原始内容
                return {"content": content}
                
        except Exception as e:
            self.log_error(f"LLM生成结构化响应失败: {str(e)}")
            raise


class IntentRecognizer(LoggerMixin):
    """意图识别器"""
    
    def __init__(self, llm: DeepSeekLLM):
        super().__init__()
        self.llm = llm
    
    async def recognize_intent(self, message: str, context: Dict[str, Any] = None) -> Intent:
        """识别用户意图"""
        system_prompt = """
        你是一个意图识别专家。请分析用户输入，识别其意图类型。
        
        意图类型包括：
        - casual_chat: 日常聊天、问候、闲聊
        - information_query: 简单的信息查询
        - complex_task: 需要多步骤处理的复杂任务
        - task_execution: 具体的任务执行请求
        
        请返回JSON格式的结果：
        {
            "type": "意图类型",
            "confidence": 0.95,
            "entities": {"关键实体": "值"},
            "context": {"上下文信息": "值"}
        }
        """
        
        messages = [{"role": "user", "content": message}]
        
        if context:
            system_prompt += f"\n\n当前上下文：{json.dumps(context, ensure_ascii=False)}"
        
        try:
            response = await self.llm.generate_structured_response(
                messages=messages,
                system_prompt=system_prompt
            )
            
            return Intent(
                type=IntentType(response.get("type", "casual_chat")),
                confidence=response.get("confidence", 0.0),
                entities=response.get("entities", {}),
                context=response.get("context", {})
            )
            
        except Exception as e:
            self.log_error(f"意图识别失败: {str(e)}")
            # 返回默认意图
            return Intent(
                type=IntentType.CASUAL_CHAT,
                confidence=0.5,
                entities={},
                context={}
            )
