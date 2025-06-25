from typing import Union, Optional, Dict, Any, List
from enum import Enum
from src.core.models import Intent
from src.core.config import settings
from src.core.logger import LoggerMixin

try:
    from src.llm.langchain_deepseek_client import LangChainDeepSeekClient, EnhancedIntentRecognizer
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from src.llm.deepseek_client import DeepSeekLLM, IntentRecognizer


class LLMClientType(Enum):
    """LLM客户端类型"""
    ORIGINAL = "original"
    LANGCHAIN = "langchain"


class LLMClientFactory(LoggerMixin):
    """LLM客户端工厂"""
    
    def __init__(self, client_type: LLMClientType = None):
        super().__init__()
        
        # 自动选择客户端类型
        if client_type is None:
            if LANGCHAIN_AVAILABLE:
                client_type = LLMClientType.LANGCHAIN
                self.log_info("使用LangChain DeepSeek客户端")
            else:
                client_type = LLMClientType.ORIGINAL
                self.log_info("使用原始DeepSeek客户端")
        
        self.client_type = client_type
        self._llm_client = None
        self._intent_recognizer = None
    
    def get_llm_client(self) -> Union['DeepSeekLLM', 'LangChainDeepSeekClient']:
        """获取LLM客户端"""
        if self._llm_client is None:
            if self.client_type == LLMClientType.LANGCHAIN and LANGCHAIN_AVAILABLE:
                self._llm_client = LangChainDeepSeekClient()
            else:
                self._llm_client = DeepSeekLLM()
        
        return self._llm_client
    
    def get_intent_recognizer(self) -> Union['IntentRecognizer', 'EnhancedIntentRecognizer']:
        """获取意图识别器"""
        if self._intent_recognizer is None:
            llm_client = self.get_llm_client()
            
            if self.client_type == LLMClientType.LANGCHAIN and LANGCHAIN_AVAILABLE:
                self._intent_recognizer = EnhancedIntentRecognizer(llm_client)
            else:
                self._intent_recognizer = IntentRecognizer(llm_client)
        
        return self._intent_recognizer
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """生成响应（统一接口）"""
        client = self.get_llm_client()
        return await client.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def generate_structured_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        response_format: Optional[Dict] = None,
        pydantic_model: Optional[Any] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """生成结构化响应（统一接口）"""
        client = self.get_llm_client()
        
        if hasattr(client, 'generate_structured_response'):
            # LangChain客户端
            if pydantic_model:
                return await client.generate_structured_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    pydantic_model=pydantic_model,
                    temperature=temperature
                )
            else:
                return await client.generate_structured_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature
                )
        else:
            # 原始客户端
            return await client.generate_structured_response(
                messages=messages,
                system_prompt=system_prompt,
                response_format=response_format,
                temperature=temperature
            )
    
    async def recognize_intent(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Intent:
        """识别意图（统一接口）"""
        recognizer = self.get_intent_recognizer()
        return await recognizer.recognize_intent(message, context)
    
    def supports_structured_output(self) -> bool:
        """检查是否支持结构化输出"""
        return self.client_type == LLMClientType.LANGCHAIN and LANGCHAIN_AVAILABLE
    
    def get_client_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            "client_type": self.client_type.value,
            "langchain_available": LANGCHAIN_AVAILABLE,
            "supports_structured_output": self.supports_structured_output(),
            "model": settings.deepseek_model
        }


# 全局工厂实例
llm_factory = LLMClientFactory()


# 便捷函数
async def get_llm_response(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> str:
    """便捷的LLM响应函数"""
    return await llm_factory.generate_response(
        messages=messages,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )


async def get_structured_response(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    response_format: Optional[Dict] = None,
    pydantic_model: Optional[Any] = None,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """便捷的结构化响应函数"""
    return await llm_factory.generate_structured_response(
        messages=messages,
        system_prompt=system_prompt,
        response_format=response_format,
        pydantic_model=pydantic_model,
        temperature=temperature
    )


async def recognize_user_intent(
    message: str,
    context: Dict[str, Any] = None
) -> Intent:
    """便捷的意图识别函数"""
    return await llm_factory.recognize_intent(message, context)
