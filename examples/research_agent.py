"""
多Agent框架示例：科研助手
"""

from typing import Dict, Any, List
from src.core.models import BaseAgent, AgentType, AgentState, AgentResponse, Task
from src.core.logger import LoggerMixin
from src.llm.client_factory import LLMClientFactory, get_llm_response, get_structured_response
from src.tools.web_search import SearchManager
import json
import re


class ResearchAgent(BaseAgent, LoggerMixin):
    """科研专用Agent"""
    
    def __init__(self, llm_factory: LLMClientFactory = None, search_manager: SearchManager = None):
        super().__init__("research_agent", AgentType.SPECIALIST)
        LoggerMixin.__init__(self)
        self.llm_factory = llm_factory or LLMClientFactory()
        self.search_manager = search_manager or SearchManager()
        
        # 科研相关关键词
        self.research_keywords = [
            "研究", "论文", "文献", "学术", "期刊", "会议", "数据",
            "实验", "分析", "理论", "方法", "模型", "算法", "假设",
            "综述", "调研", "统计", "结果", "结论", "创新", "发现"
        ]
    
    async def process(self, state: AgentState) -> AgentResponse:
        """处理科研相关请求"""
        try:
            if not state.messages:
                return AgentResponse(
                    content="请告诉我您的研究需求，我来帮您进行学术研究和分析！",
                    confidence=0.7
                )
            
            latest_message = state.messages[-1]
            user_input = latest_message.content
            
            # 分析研究需求
            research_type = await self._analyze_research_type(user_input)
            
            # 根据研究类型处理
            if research_type == "literature_review":
                return await self._handle_literature_review(user_input, state)
            elif research_type == "data_analysis":
                return await self._handle_data_analysis(user_input, state)
            elif research_type == "research_design":
                return await self._handle_research_design(user_input, state)
            elif research_type == "paper_writing":
                return await self._handle_paper_writing(user_input, state)
            else:
                return await self._handle_general_research(user_input, state)
                
        except Exception as e:
            self.log_error(f"科研Agent处理失败: {str(e)}")
            return AgentResponse(
                content="抱歉，处理您的研究请求时出现了问题。请提供更具体的研究需求。",
                confidence=0.3
            )
    
    async def _analyze_research_type(self, user_input: str) -> str:
        """分析研究类型"""
        system_prompt = """
        分析用户的研究需求类型。
        
        返回以下类型之一：
        - literature_review: 文献综述、文献查找
        - data_analysis: 数据分析、统计分析
        - research_design: 研究设计、实验设计
        - paper_writing: 论文写作、学术写作
        - general_research: 一般性研究问题
        
        只返回类型名称，不要其他内容。
        """
        
        messages = [{"role": "user", "content": user_input}]
        
        try:
            response = await get_llm_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            response = response.strip().lower()
            valid_types = ["literature_review", "data_analysis", "research_design", "paper_writing", "general_research"]
            
            return response if response in valid_types else "general_research"
            
        except Exception as e:
            self.log_error(f"分析研究类型失败: {str(e)}")
            return "general_research"
    
    async def _handle_literature_review(self, user_input: str, state: AgentState) -> AgentResponse:
        """处理文献综述请求"""
        # 提取研究主题
        topic = await self._extract_research_topic(user_input)
        
        # 搜索相关文献
        search_results = await self._search_academic_content(topic)
        
        # 生成文献综述
        system_prompt = """
        你是一个学术研究专家。基于搜索到的信息，为用户提供文献综述和研究建议。
        
        请包含：
        1. 研究领域概述
        2. 主要研究方向
        3. 关键发现和理论
        4. 研究空白和机会
        5. 建议的研究方法
        6. 推荐的学术资源
        
        请确保学术严谨性和客观性。
        """
        
        context = f"""
        研究主题：{topic}
        
        相关信息：
        {self._format_search_results(search_results)}
        
        用户请求：{user_input}
        """
        
        messages = [{"role": "user", "content": context}]
        
        response_content = await get_llm_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.6
        )
        
        return AgentResponse(
            content=response_content,
            confidence=0.8,
            tool_calls=[{
                "tool_name": "academic_search",
                "parameters": {"topic": topic},
                "result": search_results
            }],
            metadata={"research_type": "literature_review", "topic": topic}
        )
    
    async def _handle_data_analysis(self, user_input: str, state: AgentState) -> AgentResponse:
        """处理数据分析请求"""
        system_prompt = """
        你是一个数据分析专家。帮助用户进行数据分析和统计分析。
        
        请提供：
        1. 数据分析方法建议
        2. 统计检验选择
        3. 分析步骤指导
        4. 结果解释建议
        5. 可视化建议
        6. 常见问题和注意事项
        
        请确保方法的科学性和实用性。
        """
        
        messages = [{"role": "user", "content": user_input}]
        
        response_content = await get_llm_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.5
        )
        
        return AgentResponse(
            content=response_content,
            confidence=0.85,
            metadata={"research_type": "data_analysis"}
        )
    
    async def _handle_research_design(self, user_input: str, state: AgentState) -> AgentResponse:
        """处理研究设计请求"""
        system_prompt = """
        你是一个研究方法专家。帮助用户设计科学的研究方案。
        
        请提供：
        1. 研究问题明确化
        2. 研究假设制定
        3. 研究方法选择
        4. 样本设计建议
        5. 数据收集方案
        6. 控制变量考虑
        7. 伦理考量
        8. 时间和资源规划
        
        请确保研究设计的科学性和可行性。
        """
        
        messages = [{"role": "user", "content": user_input}]
        
        response_content = await get_llm_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.6
        )
        
        return AgentResponse(
            content=response_content,
            confidence=0.8,
            metadata={"research_type": "research_design"}
        )
    
    async def _handle_paper_writing(self, user_input: str, state: AgentState) -> AgentResponse:
        """处理论文写作请求"""
        system_prompt = """
        你是一个学术写作专家。帮助用户进行学术论文写作。
        
        请提供：
        1. 论文结构建议
        2. 写作技巧指导
        3. 引用规范说明
        4. 语言表达改进
        5. 逻辑结构优化
        6. 投稿策略建议
        
        请确保符合学术写作规范。
        """
        
        messages = [{"role": "user", "content": user_input}]
        
        response_content = await get_llm_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        return AgentResponse(
            content=response_content,
            confidence=0.8,
            metadata={"research_type": "paper_writing"}
        )
    
    async def _handle_general_research(self, user_input: str, state: AgentState) -> AgentResponse:
        """处理一般研究问题"""
        topic = await self._extract_research_topic(user_input)
        search_results = await self._search_academic_content(topic)
        
        system_prompt = """
        你是一个综合性研究助手。基于用户的研究问题，提供全面的学术支持。
        
        请根据具体问题提供相应的帮助，可能包括：
        - 研究背景介绍
        - 相关理论和概念
        - 研究方法建议
        - 实践指导
        - 学术资源推荐
        
        请确保回答的学术性和实用性。
        """
        
        context = f"""
        研究问题：{user_input}
        相关信息：{self._format_search_results(search_results)}
        """
        
        messages = [{"role": "user", "content": context}]
        
        response_content = await get_llm_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        return AgentResponse(
            content=response_content,
            confidence=0.75,
            tool_calls=[{
                "tool_name": "academic_search",
                "parameters": {"topic": topic},
                "result": search_results
            }] if search_results.get("results") else [],
            metadata={"research_type": "general_research", "topic": topic}
        )
    
    async def _extract_research_topic(self, user_input: str) -> str:
        """提取研究主题"""
        system_prompt = """
        从用户输入中提取核心的研究主题或关键词。
        只返回主题词，不要其他内容。
        """
        
        messages = [{"role": "user", "content": user_input}]
        
        try:
            topic = await get_llm_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.1
            )
            return topic.strip()
        except Exception as e:
            self.log_error(f"提取研究主题失败: {str(e)}")
            return "未指定主题"
    
    async def _search_academic_content(self, topic: str) -> Dict[str, Any]:
        """搜索学术内容"""
        if not topic or topic == "未指定主题":
            return {"results": []}
        
        try:
            # 构建学术搜索查询
            academic_query = f"{topic} research academic paper study"
            
            search_result = await self.search_manager.search(
                query=academic_query,
                search_type="web_search",
                max_results=5
            )
            
            return search_result
            
        except Exception as e:
            self.log_error(f"搜索学术内容失败: {str(e)}")
            return {"results": []}
    
    def _format_search_results(self, search_results: Dict[str, Any]) -> str:
        """格式化搜索结果"""
        results = search_results.get("results", [])
        if not results:
            return "暂无相关搜索结果"
        
        formatted = ""
        for i, result in enumerate(results[:3], 1):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            formatted += f"{i}. {title}\n{snippet}\n\n"
        
        return formatted
    
    async def can_handle(self, task: Task) -> bool:
        """判断是否为科研相关任务"""
        task_text = f"{task.name} {task.description}".lower()
        
        # 检查是否包含科研关键词
        return any(keyword in task_text for keyword in self.research_keywords)


# 使用示例
async def research_agent_example():
    """科研Agent使用示例"""
    from src.framework.multi_agent_framework import create_agent_framework
    
    # 创建框架
    framework = await create_agent_framework()
    
    # 创建并注册科研Agent
    research_agent = ResearchAgent()
    framework.register_agent(research_agent)
    
    # 添加科研知识
    research_knowledge = """
    机器学习研究方法：监督学习、无监督学习、强化学习、深度学习。
    常用算法：神经网络、决策树、支持向量机、随机森林、卷积神经网络。
    评估指标：准确率、精确率、召回率、F1分数、AUC-ROC曲线。
    
    自然语言处理研究领域：文本分类、情感分析、机器翻译、问答系统、文本生成。
    关键技术：词向量、注意力机制、Transformer、BERT、GPT系列模型。
    
    数据科学研究流程：问题定义、数据收集、数据清洗、探索性分析、建模、验证、部署。
    统计方法：描述性统计、假设检验、回归分析、方差分析、时间序列分析。
    """
    
    await framework.add_knowledge(research_knowledge, "research_database")
    
    # 测试科研助手
    test_cases = [
        "我想研究机器学习在医疗诊断中的应用，需要做文献综述",
        "如何设计一个实验来验证新的深度学习算法的有效性？",
        "我有一组用户行为数据，想分析用户偏好，应该用什么统计方法？",
        "如何撰写一篇关于自然语言处理的学术论文？"
    ]
    
    for i, request in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"测试案例 {i}: {request}")
        print('='*70)
        
        result = await framework.process_message(
            user_input=request,
            conversation_id=f"research_test_{i}",
            user_id="researcher"
        )
        
        print(f"研究建议:\n{result['response']}")
        print(f"\n置信度: {result['confidence']}")
        
        # 显示研究类型
        metadata = result.get('metadata', {})
        if 'research_type' in metadata:
            print(f"研究类型: {metadata['research_type']}")
        
        # 显示使用的工具
        if result.get('tool_calls'):
            print(f"使用工具: {[tool['tool_name'] for tool in result['tool_calls']]}")
    
    await framework.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(research_agent_example())
