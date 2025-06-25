"""
多Agent框架示例：家庭医生助手
"""

from typing import Dict, Any
from src.core.models import BaseAgent, AgentType, AgentState, AgentResponse, Task
from src.core.logger import LoggerMixin
from src.llm.client_factory import LLMClientFactory, get_llm_response


class MedicalAgent(BaseAgent, LoggerMixin):
    """医疗专用Agent"""
    
    def __init__(self, llm_factory: LLMClientFactory = None):
        super().__init__("medical_agent", AgentType.SPECIALIST)
        LoggerMixin.__init__(self)
        self.llm_factory = llm_factory or LLMClientFactory()
        
        # 医疗相关关键词
        self.medical_keywords = [
            "症状", "病症", "疼痛", "发烧", "咳嗽", "头痛", "腹痛",
            "治疗", "药物", "医院", "医生", "健康", "疾病", "体检",
            "药品", "副作用", "诊断", "检查", "手术"
        ]
    
    async def process(self, state: AgentState) -> AgentResponse:
        """处理医疗相关请求"""
        try:
            if not state.messages:
                return AgentResponse(
                    content="请告诉我您的健康问题或症状",
                    confidence=0.7
                )
            
            latest_message = state.messages[-1]
            user_input = latest_message.content
            
            # 医疗专用系统提示
            system_prompt = """
            你是一个专业的医疗健康助手。请注意：
            
            1. 提供健康建议和基本医疗知识
            2. 不能替代专业医生的诊断和治疗
            3. 对于严重症状，建议及时就医
            4. 回答要准确、负责任
            5. 如果不确定，明确说明并建议咨询医生
            
            请基于用户描述的症状或问题，提供专业的健康建议。
            """
            
            # 构建对话上下文
            conversation_context = ""
            if len(state.messages) > 1:
                recent_messages = state.messages[-5:]  # 最近5条消息
                conversation_context = "\n".join([
                    f"{msg.sender}: {msg.content}" 
                    for msg in recent_messages[:-1]
                ])
            
            full_prompt = f"""
            对话历史：
            {conversation_context}
            
            当前问题：{user_input}
            
            请提供专业的医疗健康建议。
            """
            
            messages = [{"role": "user", "content": full_prompt}]
            
            response_content = await get_llm_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.3  # 医疗建议需要更加保守
            )
            
            # 添加免责声明
            medical_disclaimer = "\n\n⚠️ 重要提醒：本建议仅供参考，不能替代专业医疗诊断。如症状持续或加重，请及时就医。"
            response_content += medical_disclaimer
            
            self.log_info(f"医疗Agent处理请求: {user_input[:50]}...")
            
            return AgentResponse(
                content=response_content,
                confidence=0.8,
                metadata={"agent_type": "medical", "disclaimer_added": True}
            )
            
        except Exception as e:
            self.log_error(f"医疗Agent处理失败: {str(e)}")
            return AgentResponse(
                content="抱歉，处理您的健康咨询时出现了问题。建议您咨询专业医生。",
                confidence=0.3
            )
    
    async def can_handle(self, task: Task) -> bool:
        """判断是否为医疗相关任务"""
        task_text = f"{task.name} {task.description}".lower()
        
        # 检查是否包含医疗关键词
        return any(keyword in task_text for keyword in self.medical_keywords)


# 使用示例
async def medical_agent_example():
    """医疗Agent使用示例"""
    from src.framework.multi_agent_framework import create_agent_framework
    from src.core.models import Message, MessageType
    import uuid
    
    # 创建框架
    framework = await create_agent_framework()
    
    # 创建并注册医疗Agent
    medical_agent = MedicalAgent()
    framework.register_agent(medical_agent)
    
    # 添加医疗知识（实际使用中应该从专业医疗数据库加载）
    medical_knowledge = """
    感冒症状通常包括：鼻塞、流鼻涕、咳嗽、低烧、头痛、肌肉酸痛。
    轻度感冒的处理建议：多休息、多喝水、保持室内通风、可以服用对症药物。
    如果出现高烧（38.5°C以上）、呼吸困难、胸痛等症状，应及时就医。
    
    头痛的常见原因：紧张性头痛、偏头痛、感冒引起、睡眠不足、压力过大。
    缓解头痛的方法：充足休息、放松肌肉、热敷或冷敷、按摩太阳穴。
    如果头痛剧烈或持续时间长，建议就医检查。
    """
    
    await framework.add_knowledge(medical_knowledge, "medical_database")
    
    # 测试医疗咨询
    test_cases = [
        "我最近总是头痛，该怎么办？",
        "感冒了，有什么好的治疗方法吗？",
        "孩子发烧38.5度，需要去医院吗？"
    ]
    
    for i, question in enumerate(test_cases, 1):
        print(f"\n{'='*50}")
        print(f"测试案例 {i}: {question}")
        print('='*50)
        
        result = await framework.process_message(
            user_input=question,
            conversation_id=f"medical_test_{i}",
            user_id="test_user"
        )
        
        print(f"回答: {result['response']}")
        print(f"置信度: {result['confidence']}")
    
    await framework.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(medical_agent_example())
