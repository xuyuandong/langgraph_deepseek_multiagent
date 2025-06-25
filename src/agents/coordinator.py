from typing import Any, Dict, List, Optional, Union
import asyncio
import json
from datetime import datetime
import uuid
from src.core.models import BaseAgent, AgentType, AgentState, AgentResponse, Task, Message, MessageType
from src.core.logger import LoggerMixin
from src.llm.client_factory import LLMClientFactory, get_llm_response, get_structured_response, recognize_user_intent
from src.planning.task_planner import TaskPlanner, ContextExtractor
from src.memory.memory_manager import MemoryManager
from src.rag.rag_manager import RAGManager
from src.tools.web_search import SearchManager
from src.tools.mcp_client import MCPManager


class CoordinatorAgent(BaseAgent, LoggerMixin):
    """协调器Agent - 负责整体流程协调"""
    
    def __init__(
        self,
        llm_factory: LLMClientFactory,
        task_planner: TaskPlanner,
        context_extractor: ContextExtractor,
        memory_manager: MemoryManager,
        rag_manager: RAGManager,
        search_manager: SearchManager,
        mcp_manager: MCPManager
    ):
        super().__init__("coordinator", AgentType.COORDINATOR)
        LoggerMixin.__init__(self)
        
        self.llm_factory = llm_factory
        self.task_planner = task_planner
        self.context_extractor = context_extractor
        self.memory_manager = memory_manager
        self.rag_manager = rag_manager
        self.search_manager = search_manager
        self.mcp_manager = mcp_manager
        
        # 子Agent注册表
        self.agents: Dict[str, BaseAgent] = {}
    
    def register_agent(self, agent: BaseAgent) -> None:
        """注册子Agent"""
        self.agents[agent.name] = agent
        self.log_info(f"注册Agent: {agent.name}")
    
    async def process(self, state: AgentState) -> AgentResponse:
        """处理用户请求"""
        try:
            # 获取最新消息
            if not state.messages:
                return AgentResponse(
                    content="没有接收到消息",
                    confidence=0.0
                )
            
            latest_message = state.messages[-1]
            user_input = latest_message.content
            
            # 1. 意图识别
            intent = await recognize_user_intent(
                user_input,
                state.context
            )
            
            self.log_info(f"识别意图: {intent.type.value}, 置信度: {intent.confidence}")
            
            # 2. 上下文提取
            conversation_history = [
                {"role": msg.sender, "content": msg.content}
                for msg in state.messages[-10:]  # 最近10条消息
            ]
            
            context = await self.context_extractor.extract_relevant_context(
                user_input,
                conversation_history
            )
            
            # 更新状态上下文
            state.context.update(context)
            
            # 3. 根据意图类型处理
            if intent.type.value == "casual_chat":
                return await self._handle_casual_chat(user_input, state, intent)
            elif intent.type.value == "information_query":
                return await self._handle_information_query(user_input, state, intent)
            elif intent.type.value == "complex_task":
                return await self._handle_complex_task(user_input, state, intent)
            else:
                return await self._handle_default(user_input, state, intent)
        
        except Exception as e:
            self.log_error(f"协调器处理失败: {str(e)}")
            return AgentResponse(
                content=f"处理请求时出现错误: {str(e)}",
                confidence=0.0
            )
    
    async def _handle_casual_chat(
        self,
        user_input: str,
        state: AgentState,
        intent
    ) -> AgentResponse:
        """处理日常聊天"""
        system_prompt = """
        你是一个友好的AI助手。请自然地回应用户的日常聊天。
        保持对话轻松友好，适当展现个性。
        """
        
        messages = [{"role": "user", "content": user_input}]
        
        response_content = await get_llm_response(
            messages=messages,
            system_prompt=system_prompt
        )
        
        return AgentResponse(
            content=response_content,
            confidence=0.9
        )
    
    async def _handle_information_query(
        self,
        user_input: str,
        state: AgentState,
        intent
    ) -> AgentResponse:
        """处理信息查询"""
        # 1. 首先尝试从RAG中搜索
        rag_results = await self.rag_manager.search_and_format(user_input, limit=3)
        
        # 2. 如果RAG结果不足，进行Web搜索
        web_results = None
        if "未找到相关信息" in rag_results:
            search_result = await self.search_manager.search(user_input, max_results=3)
            if "results" in search_result:
                web_results = search_result["results"]
        
        # 3. 生成综合回答
        system_prompt = """
        基于提供的信息回答用户问题。如果信息不足，请说明。
        请提供准确、有用的回答。
        """
        
        context_info = f"知识库信息：\n{rag_results}\n"
        if web_results:
            context_info += "\n网络搜索结果：\n"
            for i, result in enumerate(web_results, 1):
                context_info += f"{i}. {result.get('title', '')}\n{result.get('snippet', '')}\n\n"
        
        messages = [{"role": "user", "content": f"{context_info}\n\n用户问题：{user_input}"}]
        
        response_content = await get_llm_response(
            messages=messages,
            system_prompt=system_prompt
        )
        
        tool_calls = []
        if web_results:
            tool_calls.append({
                "tool_name": "web_search",
                "parameters": {"query": user_input},
                "result": {"results": web_results}
            })
        
        return AgentResponse(
            content=response_content,
            tool_calls=tool_calls,
            confidence=0.8
        )
    
    async def _handle_complex_task(
        self,
        user_input: str,
        state: AgentState,
        intent
    ) -> AgentResponse:
        """处理复杂任务"""
        # 1. 任务分解
        task = await self.task_planner.decompose_task(user_input)
        state.current_task = task
        
        # 2. 创建执行计划
        execution_plan = await self.task_planner.create_execution_plan(task)
        
        # 3. 检查是否需要更多信息
        missing_info = await self._check_missing_information(task, state)
        if missing_info:
            return AgentResponse(
                content=f"为了更好地完成任务，我需要以下信息：\n{missing_info}",
                confidence=0.7,
                next_action="request_info"
            )
        
        # 4. 开始执行任务
        if task.subtasks:
            # 复杂任务，需要多步执行
            result = await self._execute_complex_task(task, state)
        else:
            # 简单任务，直接执行
            result = await self._execute_simple_task(task, state)
        
        return result
    
    async def _check_missing_information(self, task: Task, state: AgentState) -> str:
        """检查缺失信息"""
        system_prompt = """
        分析任务执行所需的信息，判断是否有关键信息缺失。
        如果有缺失，请列出需要用户提供的具体信息。
        如果信息充足，返回"无"。
        """
        
        task_context = f"任务：{task.description}\n"
        if task.subtasks:
            task_context += "子任务：\n"
            for subtask in task.subtasks:
                task_context += f"- {subtask.description}\n"
        
        messages = [{"role": "user", "content": task_context}]
        
        try:
            response = await get_llm_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            return "" if response.strip() == "无" else response
            
        except Exception as e:
            self.log_error(f"检查缺失信息失败: {str(e)}")
            return ""
    
    async def _execute_simple_task(self, task: Task, state: AgentState) -> AgentResponse:
        """执行简单任务"""
        # 选择合适的Agent执行任务
        agent = await self._select_agent_for_task(task)
        
        if agent:
            return await agent.process(state)
        else:
            # 使用LLM直接处理
            system_prompt = f"""
            请完成以下任务：{task.description}
            
            任务上下文：
            {await self.context_extractor.generate_prompt_context(task, state)}
            """
            
            messages = [{"role": "user", "content": task.description}]
            
            response_content = await get_llm_response(
                messages=messages,
                system_prompt=system_prompt
            )
            
            return AgentResponse(
                content=response_content,
                confidence=0.7
            )
    
    async def _execute_complex_task(self, task: Task, state: AgentState) -> AgentResponse:
        """执行复杂任务"""
        execution_plan = await self.task_planner.create_execution_plan(task)
        results = []
        
        for subtask_id in execution_plan:
            # 找到对应的子任务
            subtask = next((st for st in task.subtasks if st.id == subtask_id), None)
            if not subtask:
                continue
            
            # 创建子任务状态
            subtask_state = AgentState(
                messages=state.messages.copy(),
                current_task=subtask,
                context=state.context.copy()
            )
            
            # 执行子任务
            result = await self._execute_simple_task(subtask, subtask_state)
            results.append({
                "subtask": subtask.name,
                "result": result.content
            })
            
            # 更新子任务状态
            subtask.status = "completed"
            subtask.result = {"content": result.content}
        
        # 汇总结果
        summary = await self._summarize_task_results(task, results)
        
        return AgentResponse(
            content=summary,
            confidence=0.8,
            metadata={"subtask_results": results}
        )
    
    async def _select_agent_for_task(self, task: Task) -> Optional[BaseAgent]:
        """为任务选择合适的Agent"""
        for agent in self.agents.values():
            if await agent.can_handle(task):
                return agent
        return None
    
    async def _summarize_task_results(self, task: Task, results: List[Dict]) -> str:
        """汇总任务结果"""
        system_prompt = """
        基于子任务执行结果，生成任务完成的汇总报告。
        报告应该简洁明了，重点突出关键成果。
        """
        
        results_text = f"主任务：{task.name}\n\n"
        results_text += "子任务执行结果：\n"
        
        for result in results:
            results_text += f"- {result['subtask']}：{result['result']}\n"
        
        messages = [{"role": "user", "content": results_text}]
        
        try:
            summary = await get_llm_response(
                messages=messages,
                system_prompt=system_prompt
            )
            return summary
        except Exception as e:
            self.log_error(f"汇总任务结果失败: {str(e)}")
            return f"任务 '{task.name}' 已完成，包含 {len(results)} 个子任务。"
    
    async def _handle_default(
        self,
        user_input: str,
        state: AgentState,
        intent
    ) -> AgentResponse:
        """默认处理"""
        return AgentResponse(
            content="我理解了您的请求，但暂时无法确定最佳的处理方式。请您提供更多详细信息。",
            confidence=0.5
        )
    
    async def can_handle(self, task: Task) -> bool:
        """协调器可以处理所有任务"""
        return True
    
    async def _decide_and_call_tools(
        self,
        user_input: str,
        state: AgentState,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """决策并调用合适的工具"""
        tool_results = {}
        
        # 基于意图和内容决定需要调用的工具
        tools_to_call = await self._determine_required_tools(user_input, intent)
        
        for tool_name in tools_to_call:
            try:
                if tool_name == "memory":
                    # 调用记忆模块
                    result = await self._call_memory_tool(user_input, state)
                    tool_results["memory"] = result
                
                elif tool_name == "rag":
                    # 调用RAG系统
                    result = await self._call_rag_tool(user_input, state)
                    tool_results["rag"] = result
                
                elif tool_name == "web_search":
                    # 调用Web搜索
                    result = await self._call_web_search_tool(user_input)
                    tool_results["web_search"] = result
                
                elif tool_name == "mcp":
                    # 调用MCP工具
                    result = await self._call_mcp_tools(user_input, intent)
                    tool_results["mcp"] = result
                
                self.log_info(f"成功调用工具: {tool_name}")
                
            except Exception as e:
                self.log_error(f"调用工具 {tool_name} 失败: {str(e)}")
                tool_results[tool_name] = {"error": str(e)}
        
        return tool_results
    
    async def _determine_required_tools(
        self,
        user_input: str,
        intent: Dict[str, Any]
    ) -> List[str]:
        """根据输入和意图确定需要的工具"""
        tools = []
        
        # 基于关键词和意图类型决定工具
        intent_type = intent.get("type", "unknown")
        content_lower = user_input.lower()
        
        # 记忆相关
        if "记住" in content_lower or "上次" in content_lower or "之前" in content_lower:
            tools.append("memory")
        
        # RAG相关
        if "文档" in content_lower or "资料" in content_lower or "知识库" in content_lower:
            tools.append("rag")
        
        # Web搜索相关
        if "搜索" in content_lower or "查询" in content_lower or "最新" in content_lower:
            tools.append("web_search")
        
        # MCP工具相关
        if ("文件" in content_lower or "执行" in content_lower or 
            "命令" in content_lower or "计算" in content_lower):
            tools.append("mcp")
        
        # 复杂任务通常需要多个工具配合
        if intent_type == "complex_task":
            if "memory" not in tools:
                tools.append("memory")
            if "rag" not in tools:
                tools.append("rag")
        
        return tools
    
    async def _call_memory_tool(self, user_input: str, state: AgentState) -> Dict[str, Any]:
        """调用记忆工具"""
        try:
            # 搜索相关记忆
            memories = await self.memory_manager.search_memories(user_input, limit=5)
            
            # 保存当前对话到记忆
            await self.memory_manager.add_memory(
                content=user_input,
                memory_type="conversation",
                metadata={"timestamp": datetime.now().isoformat()}
            )
            
            return {
                "retrieved_memories": memories,
                "saved": True
            }
        except Exception as e:
            self.log_error(f"记忆工具调用失败: {str(e)}")
            return {"error": str(e)}
    
    async def _call_rag_tool(self, user_input: str, state: AgentState) -> Dict[str, Any]:
        """调用RAG工具"""
        try:
            if not self.rag_manager:
                return {"error": "RAG系统不可用"}
            
            # 搜索相关文档
            documents = await self.rag_manager.search_documents(user_input, top_k=3)
            
            return {
                "relevant_documents": documents,
                "count": len(documents)
            }
        except Exception as e:
            self.log_error(f"RAG工具调用失败: {str(e)}")
            return {"error": str(e)}
    
    async def _call_web_search_tool(self, user_input: str) -> Dict[str, Any]:
        """调用Web搜索工具"""
        try:
            results = await self.search_manager.search(user_input, max_results=5)
            return {
                "search_results": results,
                "count": len(results)
            }
        except Exception as e:
            self.log_error(f"Web搜索工具调用失败: {str(e)}")
            return {"error": str(e)}
    
    async def _call_mcp_tools(self, user_input: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        try:
            # 初始化MCP客户端（如果还没有连接）
            if not self.mcp_manager.default_client:
                await self.mcp_manager.add_client("default")
            
            # 根据用户输入决定调用哪个MCP工具
            mcp_results = {}
            
            # 文件操作
            if "读取文件" in user_input or "file_read" in user_input.lower():
                # 这里需要从用户输入中提取文件路径
                # 简化实现，实际应该用NLP提取参数
                file_path = self._extract_file_path(user_input)
                if file_path:
                    result = await self.mcp_manager.call_tool(
                        "file_read", 
                        {"file_path": file_path}
                    )
                    mcp_results["file_read"] = result
            
            # 当前时间查询
            if "时间" in user_input or "现在几点" in user_input:
                result = await self.mcp_manager.call_tool("current_time", {})
                mcp_results["current_time"] = result
            
            # 简单计算
            if "加法" in user_input or "计算" in user_input:
                # 简化实现，提取数字
                numbers = self._extract_numbers(user_input)
                if len(numbers) >= 2:
                    result = await self.mcp_manager.call_tool(
                        "add", 
                        {"a": numbers[0], "b": numbers[1]}
                    )
                    mcp_results["add"] = result
            
            return mcp_results
            
        except Exception as e:
            self.log_error(f"MCP工具调用失败: {str(e)}")
            return {"error": str(e)}
    
    def _extract_file_path(self, text: str) -> Optional[str]:
        """从文本中提取文件路径"""
        import re
        # 简单的文件路径提取（实际应该更复杂）
        patterns = [
            r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']',  # 引号中的文件
            r'(/[^\s]+\.[a-zA-Z0-9]+)',            # Unix路径
            r'([A-Za-z]:[^\s]+\.[a-zA-Z0-9]+)'     # Windows路径
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def _extract_numbers(self, text: str) -> List[float]:
        """从文本中提取数字"""
        import re
        numbers = re.findall(r'-?\d+\.?\d*', text)
        return [float(n) for n in numbers if n]
