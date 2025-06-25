from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import sqlite3
import json
import asyncio
from datetime import datetime
import redis.asyncio as redis
from src.core.models import BaseMemory
from src.core.config import settings
from src.core.logger import LoggerMixin


class SqliteMemory(BaseMemory, LoggerMixin):
    """基于SQLite的记忆模块"""
    
    def __init__(self, db_path: str = None):
        super().__init__()
        self.db_path = db_path or settings.sqlite_db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_created_at 
                ON memories(created_at)
            """)
            
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
                USING fts5(key, value, content='memories', content_rowid='rowid')
            """)
    
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> None:
        """存储记忆"""
        try:
            value_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            metadata_str = json.dumps(metadata or {}, ensure_ascii=False)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO memories (key, value, metadata, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, value_str, metadata_str))
                
                # 更新全文搜索索引
                conn.execute("""
                    INSERT OR REPLACE INTO memories_fts (key, value)
                    VALUES (?, ?)
                """, (key, value_str))
                
                conn.commit()
            
            self.log_info(f"存储记忆: {key}")
            
        except Exception as e:
            self.log_error(f"存储记忆失败: {str(e)}")
            raise
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """检索记忆"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT value FROM memories WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                
                if row:
                    try:
                        return json.loads(row[0])
                    except json.JSONDecodeError:
                        return row[0]
                
                return None
                
        except Exception as e:
            self.log_error(f"检索记忆失败: {str(e)}")
            return None
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索记忆"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT m.key, m.value, m.metadata, m.created_at
                    FROM memories m
                    JOIN memories_fts fts ON m.rowid = fts.rowid
                    WHERE memories_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, limit))
                
                results = []
                for row in cursor.fetchall():
                    try:
                        value = json.loads(row[1])
                    except json.JSONDecodeError:
                        value = row[1]
                    
                    try:
                        metadata = json.loads(row[2])
                    except json.JSONDecodeError:
                        metadata = {}
                    
                    results.append({
                        "key": row[0],
                        "value": value,
                        "metadata": metadata,
                        "created_at": row[3]
                    })
                
                return results
                
        except Exception as e:
            self.log_error(f"搜索记忆失败: {str(e)}")
            return []


class RedisMemory(BaseMemory, LoggerMixin):
    """基于Redis的记忆模块"""
    
    def __init__(self, redis_url: str = None):
        super().__init__()
        self.redis_url = redis_url or settings.redis_url
        self.redis_client = None
    
    async def _get_client(self) -> redis.Redis:
        """获取Redis客户端"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(self.redis_url)
        return self.redis_client
    
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> None:
        """存储记忆"""
        try:
            client = await self._get_client()
            
            # 存储主要数据
            value_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            await client.set(f"memory:{key}", value_str)
            
            # 存储元数据
            if metadata:
                metadata_str = json.dumps(metadata, ensure_ascii=False)
                await client.set(f"memory:meta:{key}", metadata_str)
            
            # 添加到搜索索引
            await client.sadd("memory:keys", key)
            
            self.log_info(f"存储记忆到Redis: {key}")
            
        except Exception as e:
            self.log_error(f"存储记忆到Redis失败: {str(e)}")
            raise
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """检索记忆"""
        try:
            client = await self._get_client()
            value_str = await client.get(f"memory:{key}")
            
            if value_str:
                try:
                    return json.loads(value_str)
                except json.JSONDecodeError:
                    return value_str.decode('utf-8') if isinstance(value_str, bytes) else value_str
            
            return None
            
        except Exception as e:
            self.log_error(f"从Redis检索记忆失败: {str(e)}")
            return None
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索记忆"""
        try:
            client = await self._get_client()
            
            # 获取所有键
            keys = await client.smembers("memory:keys")
            
            results = []
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                
                # 简单的关键词匹配
                if query.lower() in key_str.lower():
                    value = await self.retrieve(key_str)
                    if value:
                        # 获取元数据
                        metadata_str = await client.get(f"memory:meta:{key_str}")
                        metadata = {}
                        if metadata_str:
                            try:
                                metadata = json.loads(metadata_str)
                            except json.JSONDecodeError:
                                pass
                        
                        results.append({
                            "key": key_str,
                            "value": value,
                            "metadata": metadata
                        })
                
                if len(results) >= limit:
                    break
            
            return results
            
        except Exception as e:
            self.log_error(f"从Redis搜索记忆失败: {str(e)}")
            return []
    
    async def close(self):
        """关闭连接"""
        if self.redis_client:
            await self.redis_client.close()


class MemoryManager(LoggerMixin):
    """记忆管理器"""
    
    def __init__(self, primary_memory: BaseMemory, fallback_memory: BaseMemory = None):
        super().__init__()
        self.primary_memory = primary_memory
        self.fallback_memory = fallback_memory
    
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> None:
        """存储记忆"""
        try:
            await self.primary_memory.store(key, value, metadata)
        except Exception as e:
            self.log_warning(f"主记忆存储失败: {str(e)}")
            if self.fallback_memory:
                await self.fallback_memory.store(key, value, metadata)
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """检索记忆"""
        try:
            result = await self.primary_memory.retrieve(key)
            if result is not None:
                return result
        except Exception as e:
            self.log_warning(f"主记忆检索失败: {str(e)}")
        
        if self.fallback_memory:
            try:
                return await self.fallback_memory.retrieve(key)
            except Exception as e:
                self.log_warning(f"备用记忆检索失败: {str(e)}")
        
        return None
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索记忆"""
        try:
            return await self.primary_memory.search(query, limit)
        except Exception as e:
            self.log_warning(f"主记忆搜索失败: {str(e)}")
            if self.fallback_memory:
                try:
                    return await self.fallback_memory.search(query, limit)
                except Exception as e:
                    self.log_warning(f"备用记忆搜索失败: {str(e)}")
        
        return []
    
    async def store_conversation(self, conversation_id: str, messages: List[Dict[str, Any]]) -> None:
        """存储对话"""
        await self.store(
            f"conversation:{conversation_id}",
            messages,
            {"type": "conversation", "message_count": len(messages)}
        )
    
    async def retrieve_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """检索对话"""
        result = await self.retrieve(f"conversation:{conversation_id}")
        return result if isinstance(result, list) else []
    
    async def store_user_preference(self, user_id: str, preferences: Dict[str, Any]) -> None:
        """存储用户偏好"""
        await self.store(
            f"user_preference:{user_id}",
            preferences,
            {"type": "user_preference", "user_id": user_id}
        )
    
    async def retrieve_user_preference(self, user_id: str) -> Dict[str, Any]:
        """检索用户偏好"""
        result = await self.retrieve(f"user_preference:{user_id}")
        return result if isinstance(result, dict) else {}
