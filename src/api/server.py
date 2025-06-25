from typing import Any, Dict, List, Optional
import asyncio
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from src.framework.multi_agent_framework import create_agent_framework, MultiAgentFramework
from src.core.config import settings
from src.core.logger import get_logger

# 初始化日志
logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Multi-Agent Framework API",
    description="基于LangGraph和DeepSeek的多Agent框架",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局框架实例
framework: Optional[MultiAgentFramework] = None


# 请求/响应模型
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    confidence: float
    conversation_id: str
    message_id: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = []
    next_action: Optional[str] = None
    error: Optional[str] = None


class KnowledgeRequest(BaseModel):
    content: str
    source: str = "api"


class KnowledgeFileRequest(BaseModel):
    file_path: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化框架"""
    global framework
    try:
        framework = await create_agent_framework()
        logger.info("多Agent框架初始化成功")
    except Exception as e:
        logger.error(f"框架初始化失败: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    global framework
    if framework:
        await framework.close()
        logger.info("多Agent框架已关闭")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Multi-Agent Framework API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "framework_initialized": framework is not None
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    if not framework:
        raise HTTPException(status_code=500, detail="框架未初始化")
    
    try:
        result = await framework.process_message(
            user_input=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            metadata=request.metadata
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"聊天处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge/add")
async def add_knowledge(request: KnowledgeRequest):
    """添加知识"""
    if not framework:
        raise HTTPException(status_code=500, detail="框架未初始化")
    
    try:
        result = await framework.add_knowledge(
            content=request.content,
            source=request.source
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加知识失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge/add-file")
async def add_knowledge_file(request: KnowledgeFileRequest):
    """从文件添加知识"""
    if not framework:
        raise HTTPException(status_code=500, detail="框架未初始化")
    
    try:
        result = await framework.add_knowledge_file(request.file_path)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加知识文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge/search")
async def search_knowledge(request: SearchRequest):
    """搜索知识库"""
    if not framework:
        raise HTTPException(status_code=500, detail="框架未初始化")
    
    try:
        result = await framework.search_knowledge(
            query=request.query,
            limit=request.limit
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """获取对话历史"""
    if not framework:
        raise HTTPException(status_code=500, detail="框架未初始化")
    
    try:
        history = await framework.get_conversation_history(conversation_id)
        return {"conversation_id": conversation_id, "history": history}
        
    except Exception as e:
        logger.error(f"获取对话历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """获取统计信息"""
    if not framework:
        raise HTTPException(status_code=500, detail="框架未初始化")
    
    try:
        stats = {
            "framework_status": "running",
            "registered_agents": len(framework.coordinator.agents),
            "agent_names": list(framework.coordinator.agents.keys())
        }
        
        # 获取RAG统计信息
        if framework.rag_manager:
            rag_info = await framework.rag_manager.rag.get_collection_info()
            stats["rag_info"] = rag_info
        
        return stats
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host=settings.mcp_server_host,
        port=settings.mcp_server_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
