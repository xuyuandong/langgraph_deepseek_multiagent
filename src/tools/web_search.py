from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import httpx
import asyncio
from duckduckgo_search import DDGS
from src.core.models import BaseTool
from src.core.config import settings
from src.core.logger import LoggerMixin


class WebSearchTool(BaseTool, LoggerMixin):
    """Web搜索工具"""
    
    def __init__(self):
        super().__init__("web_search", "搜索互联网信息")
        LoggerMixin.__init__(self)
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行Web搜索"""
        query = parameters.get("query", "")
        max_results = parameters.get("max_results", 5)
        
        if not query:
            return {"error": "查询字符串不能为空"}
        
        try:
            # 使用DuckDuckGo搜索
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", "")
                })
            
            self.log_info(f"Web搜索完成: {query}, 结果数: {len(formatted_results)}")
            
            return {
                "query": query,
                "results": formatted_results,
                "count": len(formatted_results)
            }
            
        except Exception as e:
            self.log_error(f"Web搜索失败: {str(e)}")
            return {"error": f"搜索失败: {str(e)}"}


class TavilySearchTool(BaseTool, LoggerMixin):
    """Tavily搜索工具"""
    
    def __init__(self, api_key: str = None):
        super().__init__("tavily_search", "使用Tavily进行高质量搜索")
        LoggerMixin.__init__(self)
        self.api_key = api_key or settings.tavily_api_key
        self.base_url = "https://api.tavily.com"
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行Tavily搜索"""
        query = parameters.get("query", "")
        max_results = parameters.get("max_results", 5)
        include_answer = parameters.get("include_answer", True)
        
        if not query:
            return {"error": "查询字符串不能为空"}
        
        if not self.api_key:
            return {"error": "Tavily API密钥未配置"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "include_answer": include_answer,
                        "include_raw_content": False
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "query": query,
                        "answer": data.get("answer", ""),
                        "results": data.get("results", []),
                        "count": len(data.get("results", []))
                    }
                else:
                    return {"error": f"Tavily API错误: {response.status_code}"}
                    
        except Exception as e:
            self.log_error(f"Tavily搜索失败: {str(e)}")
            return {"error": f"搜索失败: {str(e)}"}


class WebContentTool(BaseTool, LoggerMixin):
    """网页内容获取工具"""
    
    def __init__(self):
        super().__init__("web_content", "获取网页内容")
        LoggerMixin.__init__(self)
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """获取网页内容"""
        url = parameters.get("url", "")
        
        if not url:
            return {"error": "URL不能为空"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    timeout=30.0,
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    # 简单的文本提取（实际应用中可能需要使用BeautifulSoup等库）
                    content = response.text
                    
                    # 移除HTML标签的简单方法
                    import re
                    text_content = re.sub(r'<[^>]+>', '', content)
                    text_content = re.sub(r'\s+', ' ', text_content).strip()
                    
                    return {
                        "url": url,
                        "content": text_content[:5000],  # 限制长度
                        "status": "success"
                    }
                else:
                    return {"error": f"HTTP错误: {response.status_code}"}
                    
        except Exception as e:
            self.log_error(f"获取网页内容失败: {str(e)}")
            return {"error": f"获取失败: {str(e)}"}


class SearchManager(LoggerMixin):
    """搜索管理器"""
    
    def __init__(self):
        super().__init__()
        self.tools = {
            "web_search": WebSearchTool(),
            "tavily_search": TavilySearchTool(),
            "web_content": WebContentTool()
        }
    
    async def search(
        self,
        query: str,
        search_type: str = "web_search",
        max_results: int = 5,
        include_content: bool = False
    ) -> Dict[str, Any]:
        """执行搜索"""
        try:
            if search_type not in self.tools:
                return {"error": f"不支持的搜索类型: {search_type}"}
            
            tool = self.tools[search_type]
            
            # 执行搜索
            search_result = await tool.execute({
                "query": query,
                "max_results": max_results
            })
            
            # 如果需要获取网页内容
            if include_content and "results" in search_result:
                content_tool = self.tools["web_content"]
                
                for result in search_result["results"][:3]:  # 只获取前3个结果的内容
                    if "url" in result:
                        content_result = await content_tool.execute({"url": result["url"]})
                        if "content" in content_result:
                            result["content"] = content_result["content"]
            
            return search_result
            
        except Exception as e:
            self.log_error(f"搜索失败: {str(e)}")
            return {"error": f"搜索失败: {str(e)}"}
    
    async def multi_search(
        self,
        query: str,
        search_types: List[str] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """多引擎搜索"""
        if search_types is None:
            search_types = ["web_search", "tavily_search"]
        
        results = {}
        
        # 并发执行多个搜索
        tasks = []
        for search_type in search_types:
            if search_type in self.tools:
                task = self.search(query, search_type, max_results)
                tasks.append((search_type, task))
        
        # 等待所有搜索完成
        completed_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # 整理结果
        for (search_type, _), result in zip(tasks, completed_results):
            if isinstance(result, Exception):
                results[search_type] = {"error": str(result)}
            else:
                results[search_type] = result
        
        return {
            "query": query,
            "engines": results,
            "summary": self._summarize_results(results)
        }
    
    def _summarize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """汇总搜索结果"""
        total_results = 0
        successful_engines = 0
        
        for engine, result in results.items():
            if "error" not in result:
                successful_engines += 1
                total_results += result.get("count", 0)
        
        return {
            "total_results": total_results,
            "successful_engines": successful_engines,
            "total_engines": len(results)
        }
