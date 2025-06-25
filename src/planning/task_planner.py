from typing import Any, Dict, List, Optional, Union
from src.core.models import Task, TaskComplexity, AgentState
from src.core.logger import LoggerMixin
from src.llm.client_factory import LLMClientFactory, get_llm_response, get_structured_response
import uuid
import json
from datetime import datetime
from pydantic import BaseModel, Field

try:
    from src.llm.langchain_deepseek_client import StructuredTaskAnalysis
    STRUCTURED_MODELS_AVAILABLE = True
except ImportError:
    STRUCTURED_MODELS_AVAILABLE = False
    
    # 定义备用模型
    class StructuredTaskAnalysis(BaseModel):
        name: str = Field(description="任务名称")
        description: str = Field(description="任务描述")
        complexity: str = Field(description="任务复杂度")
        subtasks: List[Dict[str, Any]] = Field(default_factory=list)
        required_info: List[str] = Field(default_factory=list)
        estimated_steps: int = Field(description="预估步骤数", ge=1)


class TaskPlanner(LoggerMixin):
    """任务规划器"""
    
    def __init__(self, llm_factory: LLMClientFactory = None):
        super().__init__()
        self.llm_factory = llm_factory or LLMClientFactory()
    
    async def analyze_task_complexity(self, task_description: str) -> TaskComplexity:
        """分析任务复杂度"""
        system_prompt = """
        请分析任务的复杂度。复杂度分为：
        - simple: 简单任务，一步即可完成
        - medium: 中等复杂度，需要2-3个步骤
        - complex: 复杂任务，需要多个步骤和子任务
        
        请只返回复杂度级别：simple、medium或complex
        """
        
        messages = [{"role": "user", "content": f"任务：{task_description}"}]
        
        try:
            response = await get_llm_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            complexity_str = response.strip().lower()
            if complexity_str in ["simple", "medium", "complex"]:
                return TaskComplexity(complexity_str)
            else:
                return TaskComplexity.MEDIUM
                
        except Exception as e:
            self.log_error(f"任务复杂度分析失败: {str(e)}")
            return TaskComplexity.MEDIUM
    
    async def decompose_task(self, task_description: str, max_depth: int = 3) -> Task:
        """任务分解"""
        try:
            # 尝试使用结构化输出
            if self.llm_factory.supports_structured_output():
                return await self._decompose_task_structured(task_description, max_depth)
            else:
                return await self._decompose_task_traditional(task_description, max_depth)
        except Exception as e:
            self.log_error(f"任务分解失败: {str(e)}")
            # 返回简单任务作为备选
            return Task(
                id=str(uuid.uuid4()),
                name=task_description,
                description=task_description,
                complexity=TaskComplexity.SIMPLE
            )
    
    async def _decompose_task_structured(self, task_description: str, max_depth: int) -> Task:
        """使用结构化输出分解任务"""
        system_prompt = """
        你是一个任务规划专家。请将复杂任务分解为可执行的子任务。
        请提供详细的任务分析和分解结果。
        """
        
        messages = [{"role": "user", "content": f"请分解以下任务：{task_description}"}]
        
        # 获取结构化分析结果
        llm_client = self.llm_factory.get_llm_client()
        if hasattr(llm_client, 'analyze_task_structured'):
            structured_result = await llm_client.analyze_task_structured(task_description)
        else:
            # 使用通用结构化输出
            structured_result = await get_structured_response(
                messages=messages,
                system_prompt=system_prompt,
                pydantic_model=StructuredTaskAnalysis,
                temperature=0.5
            )
        
        # 创建主任务
        main_task = Task(
            id=str(uuid.uuid4()),
            name=structured_result.name,
            description=structured_result.description,
            complexity=TaskComplexity(structured_result.complexity)
        )
        
        # 创建子任务
        subtask_map = {}
        for subtask_data in structured_result.subtasks:
            subtask = Task(
                id=str(uuid.uuid4()),
                name=subtask_data.get("name", ""),
                description=subtask_data.get("description", ""),
                complexity=TaskComplexity.SIMPLE,
                dependencies=subtask_data.get("dependencies", [])
            )
            subtask_map[subtask.name] = subtask.id
            main_task.subtasks.append(subtask)
        
        # 更新依赖关系为ID
        for subtask in main_task.subtasks:
            subtask.dependencies = [
                subtask_map.get(dep_name, dep_name) 
                for dep_name in subtask.dependencies
                if dep_name in subtask_map
            ]
        
        self.log_info(f"结构化任务分解完成: {main_task.name}, 子任务数: {len(main_task.subtasks)}")
        return main_task
    
    async def _decompose_task_traditional(self, task_description: str, max_depth: int) -> Task:
        """使用传统方式分解任务"""
        system_prompt = """
        你是一个任务规划专家。请将复杂任务分解为可执行的子任务。
        
        返回JSON格式：
        {
            "name": "任务名称",
            "description": "任务描述",
            "subtasks": [
                {
                    "name": "子任务名称",
                    "description": "子任务描述",
                    "dependencies": ["依赖的子任务名称"]
                }
            ]
        }
        
        注意：
        1. 子任务应该是具体可执行的
        2. 考虑任务之间的依赖关系
        3. 子任务数量控制在10个以内
        """
        
        messages = [{"role": "user", "content": f"请分解以下任务：{task_description}"}]
        
        response = await get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.5
        )
        
        # 创建主任务
        main_task = Task(
            id=str(uuid.uuid4()),
            name=response.get("name", task_description),
            description=response.get("description", task_description),
            complexity=await self.analyze_task_complexity(task_description)
        )
        
        # 创建子任务
        subtasks_data = response.get("subtasks", [])
        subtask_map = {}
        
        for subtask_data in subtasks_data:
            subtask = Task(
                id=str(uuid.uuid4()),
                name=subtask_data.get("name", ""),
                description=subtask_data.get("description", ""),
                complexity=TaskComplexity.SIMPLE,
                dependencies=subtask_data.get("dependencies", [])
            )
            subtask_map[subtask.name] = subtask.id
            main_task.subtasks.append(subtask)
        
        # 更新依赖关系为ID
        for subtask in main_task.subtasks:
            subtask.dependencies = [
                subtask_map.get(dep_name, dep_name) 
                for dep_name in subtask.dependencies
                if dep_name in subtask_map
            ]
        
        self.log_info(f"传统任务分解完成: {main_task.name}, 子任务数: {len(main_task.subtasks)}")
        return main_task
    
    async def create_execution_plan(self, task: Task) -> List[str]:
        """创建执行计划"""
        if not task.subtasks:
            return [task.id]
        
        # 拓扑排序确定执行顺序
        execution_order = []
        remaining_tasks = {subtask.id: subtask for subtask in task.subtasks}
        completed_tasks = set()
        
        while remaining_tasks:
            # 找到没有未完成依赖的任务
            ready_tasks = []
            for task_id, subtask in remaining_tasks.items():
                dependencies_met = all(
                    dep_id in completed_tasks or dep_id not in remaining_tasks
                    for dep_id in subtask.dependencies
                )
                if dependencies_met:
                    ready_tasks.append(task_id)
            
            if not ready_tasks:
                # 如果没有可执行的任务，打破循环依赖
                ready_tasks = [list(remaining_tasks.keys())[0]]
            
            # 添加到执行顺序并标记为完成
            for task_id in ready_tasks:
                execution_order.append(task_id)
                completed_tasks.add(task_id)
                del remaining_tasks[task_id]
        
        return execution_order


class ContextExtractor(LoggerMixin):
    """上下文提取器"""
    
    def __init__(self, llm_factory: LLMClientFactory = None):
        super().__init__()
        self.llm_factory = llm_factory or LLMClientFactory()
    
    async def extract_relevant_context(
        self,
        current_message: str,
        conversation_history: List[Dict[str, Any]],
        max_messages: int = None
    ) -> Dict[str, Any]:
        """提取相关上下文"""
        if max_messages is None:
            max_messages = 10
        
        # 获取最近的消息
        recent_messages = conversation_history[-max_messages:] if conversation_history else []
        
        try:
            # 尝试使用结构化输出
            if self.llm_factory.supports_structured_output():
                return await self._extract_context_structured(current_message, recent_messages)
            else:
                return await self._extract_context_traditional(current_message, recent_messages)
        except Exception as e:
            self.log_error(f"上下文提取失败: {str(e)}")
            return {
                "key_topics": [],
                "mentioned_entities": {},
                "user_preferences": {},
                "context_summary": "",
                "message_count": len(recent_messages),
                "extracted_at": datetime.now().isoformat()
            }
    
    async def _extract_context_structured(
        self,
        current_message: str,
        recent_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """使用结构化输出提取上下文"""
        llm_client = self.llm_factory.get_llm_client()
        
        if hasattr(llm_client, 'extract_context_structured'):
            # 使用专门的结构化上下文提取
            result = await llm_client.extract_context_structured(
                current_message, recent_messages, len(recent_messages)
            )
            return {
                "key_topics": result.key_topics,
                "mentioned_entities": result.mentioned_entities,
                "user_preferences": result.user_preferences,
                "context_summary": result.context_summary,
                "message_count": len(recent_messages),
                "extracted_at": datetime.now().isoformat()
            }
        else:
            # 使用通用结构化输出
            return await self._extract_context_traditional(current_message, recent_messages)
    
    async def _extract_context_traditional(
        self,
        current_message: str,
        recent_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """使用传统方式提取上下文"""
        system_prompt = """
        根据当前消息和对话历史，提取相关的上下文信息。
        
        返回JSON格式：
        {
            "key_topics": ["关键话题1", "关键话题2"],
            "mentioned_entities": {"实体类型": ["实体1", "实体2"]},
            "user_preferences": {"偏好类型": "偏好值"},
            "context_summary": "上下文摘要"
        }
        """
        
        context_text = f"当前消息：{current_message}\n\n"
        if recent_messages:
            context_text += "对话历史：\n"
            for msg in recent_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_text += f"{role}: {content}\n"
        
        messages = [{"role": "user", "content": context_text}]
        
        response = await get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        return {
            "key_topics": response.get("key_topics", []),
            "mentioned_entities": response.get("mentioned_entities", {}),
            "user_preferences": response.get("user_preferences", {}),
            "context_summary": response.get("context_summary", ""),
            "message_count": len(recent_messages),
            "extracted_at": datetime.now().isoformat()
        }
    
    async def generate_prompt_context(
        self,
        task: Task,
        agent_state: AgentState,
        additional_context: Dict[str, Any] = None
    ) -> str:
        """生成Agent所需的提示上下文"""
        context_parts = []
        
        # 任务信息
        context_parts.append(f"当前任务：{task.name}")
        context_parts.append(f"任务描述：{task.description}")
        
        # 对话历史摘要
        if agent_state.messages:
            recent_messages = agent_state.messages[-5:]  # 最近5条消息
            history_text = "\n".join([
                f"{msg.sender}: {msg.content}" 
                for msg in recent_messages
            ])
            context_parts.append(f"最近对话：\n{history_text}")
        
        # 上下文信息
        if agent_state.context:
            context_summary = agent_state.context.get("context_summary", "")
            if context_summary:
                context_parts.append(f"上下文摘要：{context_summary}")
            
            key_topics = agent_state.context.get("key_topics", [])
            if key_topics:
                context_parts.append(f"关键话题：{', '.join(key_topics)}")
        
        # 额外上下文
        if additional_context:
            for key, value in additional_context.items():
                context_parts.append(f"{key}：{value}")
        
        return "\n\n".join(context_parts)
