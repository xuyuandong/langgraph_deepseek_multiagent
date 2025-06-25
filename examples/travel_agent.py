"""
多Agent框架示例：旅行规划助手
"""

from typing import Dict, Any, List
from src.core.models import BaseAgent, AgentType, AgentState, AgentResponse, Task
from src.core.logger import LoggerMixin
from src.llm.client_factory import LLMClientFactory, get_llm_response, get_structured_response
from src.tools.web_search import SearchManager
import json


class TravelAgent(BaseAgent, LoggerMixin):
    """旅行规划专用Agent"""
    
    def __init__(self, llm_factory: LLMClientFactory = None, search_manager: SearchManager = None):
        super().__init__("travel_agent", AgentType.SPECIALIST)
        LoggerMixin.__init__(self)
        self.llm_factory = llm_factory or LLMClientFactory()
        self.search_manager = search_manager or SearchManager()
        
        # 旅行相关关键词
        self.travel_keywords = [
            "旅行", "旅游", "出行", "度假", "景点", "酒店", "机票",
            "行程", "路线", "攻略", "签证", "预算", "住宿", "交通",
            "美食", "购物", "天气", "季节", "目的地", "游玩"
        ]
    
    async def process(self, state: AgentState) -> AgentResponse:
        """处理旅行规划请求"""
        try:
            if not state.messages:
                return AgentResponse(
                    content="请告诉我您的旅行需求，我来帮您制定详细的旅行计划！",
                    confidence=0.7
                )
            
            latest_message = state.messages[-1]
            user_input = latest_message.content
            
            # 分析旅行需求
            travel_info = await self._analyze_travel_requirements(user_input, state)
            
            # 搜索相关信息
            search_results = await self._search_travel_info(travel_info)
            
            # 生成旅行计划
            travel_plan = await self._generate_travel_plan(travel_info, search_results, state)
            
            self.log_info(f"旅行Agent生成计划: {travel_info.get('destination', '未知目的地')}")
            
            return AgentResponse(
                content=travel_plan,
                confidence=0.85,
                tool_calls=[{
                    "tool_name": "web_search",
                    "parameters": {"query": f"{travel_info.get('destination', '')} 旅游攻略"},
                    "result": search_results
                }],
                metadata={
                    "agent_type": "travel",
                    "travel_info": travel_info
                }
            )
            
        except Exception as e:
            self.log_error(f"旅行Agent处理失败: {str(e)}")
            return AgentResponse(
                content="抱歉，制定旅行计划时出现了问题。请提供更具体的旅行需求，我会重新为您规划。",
                confidence=0.3
            )
    
    async def _analyze_travel_requirements(self, user_input: str, state: AgentState) -> Dict[str, Any]:
        """分析旅行需求"""
        system_prompt = """
        分析用户的旅行需求，提取关键信息。
        
        请返回JSON格式：
        {
            "destination": "目的地",
            "duration": "旅行天数",
            "budget": "预算范围",
            "travel_style": "旅行风格（如休闲、探险、文化等）",
            "interests": ["兴趣点1", "兴趣点2"],
            "travel_date": "出行时间",
            "group_size": "人数",
            "special_requirements": "特殊要求"
        }
        
        如果某些信息未提及，可以设为null或空字符串。
        """
        
        messages = [{"role": "user", "content": user_input}]
        
        try:
            response = await get_structured_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            return response if isinstance(response, dict) else {}
            
        except Exception as e:
            self.log_error(f"分析旅行需求失败: {str(e)}")
            return {"destination": "未指定", "duration": "未指定"}
    
    async def _search_travel_info(self, travel_info: Dict[str, Any]) -> Dict[str, Any]:
        """搜索旅行相关信息"""
        destination = travel_info.get("destination", "")
        if not destination or destination == "未指定":
            return {"results": []}
        
        try:
            # 搜索目的地信息
            search_query = f"{destination} 旅游攻略 景点 美食 住宿"
            search_result = await self.search_manager.search(
                query=search_query,
                search_type="web_search",
                max_results=3
            )
            
            return search_result
            
        except Exception as e:
            self.log_error(f"搜索旅行信息失败: {str(e)}")
            return {"results": []}
    
    async def _generate_travel_plan(
        self,
        travel_info: Dict[str, Any],
        search_results: Dict[str, Any],
        state: AgentState
    ) -> str:
        """生成旅行计划"""
        system_prompt = """
        你是一个专业的旅行规划师。基于用户需求和搜索到的信息，制定详细的旅行计划。
        
        计划应该包括：
        1. 目的地介绍
        2. 推荐行程安排
        3. 景点推荐
        4. 住宿建议
        5. 美食推荐
        6. 交通建议
        7. 预算估算
        8. 注意事项
        
        请生成结构化、实用的旅行计划。
        """
        
        # 构建上下文信息
        context_info = f"""
        旅行需求：
        - 目的地：{travel_info.get('destination', '未指定')}
        - 旅行天数：{travel_info.get('duration', '未指定')}
        - 预算：{travel_info.get('budget', '未指定')}
        - 旅行风格：{travel_info.get('travel_style', '未指定')}
        - 兴趣点：{', '.join(travel_info.get('interests', []))}
        - 出行时间：{travel_info.get('travel_date', '未指定')}
        - 人数：{travel_info.get('group_size', '未指定')}
        - 特殊要求：{travel_info.get('special_requirements', '无')}
        
        搜索到的相关信息：
        """
        
        # 添加搜索结果
        results = search_results.get("results", [])
        if results:
            for i, result in enumerate(results[:3], 1):
                context_info += f"\n{i}. {result.get('title', '')}\n{result.get('snippet', '')}\n"
        else:
            context_info += "\n暂无相关搜索结果"
        
        messages = [{"role": "user", "content": context_info}]
        
        try:
            travel_plan = await get_llm_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            return travel_plan
            
        except Exception as e:
            self.log_error(f"生成旅行计划失败: {str(e)}")
            return f"抱歉，生成旅行计划时出现问题。\n\n根据您的需求（目的地：{travel_info.get('destination', '未指定')}），建议您：\n1. 提前查询目的地天气和最佳旅行时间\n2. 预订合适的住宿和交通\n3. 了解当地的文化和习俗\n4. 准备必要的证件和物品"
    
    async def can_handle(self, task: Task) -> bool:
        """判断是否为旅行相关任务"""
        task_text = f"{task.name} {task.description}".lower()
        
        # 检查是否包含旅行关键词
        return any(keyword in task_text for keyword in self.travel_keywords)


# 使用示例
async def travel_agent_example():
    """旅行Agent使用示例"""
    from src.framework.multi_agent_framework import create_agent_framework
    
    # 创建框架
    framework = await create_agent_framework()
    
    # 创建并注册旅行Agent
    travel_agent = TravelAgent()
    framework.register_agent(travel_agent)
    
    # 添加旅行知识
    travel_knowledge = """
    日本旅游最佳时间：春季（3-5月）看樱花，秋季（9-11月）看红叶。
    日本必去景点：东京塔、富士山、清水寺、金阁寺、奈良公园。
    日本美食：寿司、拉面、天妇罗、和牛、抹茶甜品。
    
    泰国旅游最佳时间：11月至次年4月，气候凉爽干燥。
    泰国必去景点：大皇宫、玉佛寺、普吉岛、清迈古城。
    泰国美食：冬阴功汤、青木瓜沙拉、芒果糯米饭、泰式炒河粉。
    
    欧洲旅游最佳时间：4-10月，气候温和，白天较长。
    欧洲必去景点：埃菲尔铁塔、罗马斗兽场、圣托里尼岛、新天鹅堡。
    """
    
    await framework.add_knowledge(travel_knowledge, "travel_database")
    
    # 测试旅行规划
    test_cases = [
        "我想去日本旅游5天，预算1万元，喜欢文化和美食",
        "计划和朋友去泰国度假一周，想要海滩和SPA",
        "蜜月旅行，想去欧洲浪漫的地方，大概10天时间"
    ]
    
    for i, request in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试案例 {i}: {request}")
        print('='*60)
        
        result = await framework.process_message(
            user_input=request,
            conversation_id=f"travel_test_{i}",
            user_id="travel_user"
        )
        
        print(f"旅行计划:\n{result['response']}")
        print(f"\n置信度: {result['confidence']}")
        
        # 显示使用的工具
        if result.get('tool_calls'):
            print(f"使用工具: {[tool['tool_name'] for tool in result['tool_calls']]}")
    
    await framework.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(travel_agent_example())
