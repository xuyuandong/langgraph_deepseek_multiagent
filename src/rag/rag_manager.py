from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from src.core.models import BaseRAG
from src.core.config import settings
from src.core.logger import LoggerMixin
import uuid
import os


class ChromaRAG(BaseRAG, LoggerMixin):
    """基于ChromaDB的RAG模块"""
    
    def __init__(self, collection_name: str = "default", embedding_model: str = "all-MiniLM-L6-v2"):
        super().__init__()
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        
        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 初始化嵌入模型
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # 获取或创建集合
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "RAG knowledge base"}
            )
    
    def _generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入"""
        return self.embedding_model.encode(text).tolist()
    
    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """添加文档"""
        try:
            if not documents:
                return
            
            # 生成ID
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in documents]
            
            # 生成嵌入
            embeddings = [self._generate_embedding(doc) for doc in documents]
            
            # 准备元数据
            if metadatas is None:
                metadatas = [{"source": "unknown"} for _ in documents]
            
            # 添加到集合
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            self.log_info(f"添加了 {len(documents)} 个文档到RAG")
            
        except Exception as e:
            self.log_error(f"添加文档失败: {str(e)}")
            raise
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索相关文档"""
        try:
            # 生成查询嵌入
            query_embedding = self._generate_embedding(query)
            
            # 搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where
            )
            
            # 格式化结果
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        "document": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        "id": results['ids'][0][i] if results['ids'] and results['ids'][0] else None,
                        "distance": results['distances'][0][i] if results['distances'] and results['distances'][0] else None
                    }
                    formatted_results.append(result)
            
            self.log_info(f"RAG搜索返回 {len(formatted_results)} 个结果")
            return formatted_results
            
        except Exception as e:
            self.log_error(f"RAG搜索失败: {str(e)}")
            return []
    
    async def delete_documents(self, ids: List[str]) -> None:
        """删除文档"""
        try:
            self.collection.delete(ids=ids)
            self.log_info(f"删除了 {len(ids)} 个文档")
        except Exception as e:
            self.log_error(f"删除文档失败: {str(e)}")
            raise
    
    async def update_documents(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """更新文档"""
        try:
            # 生成新的嵌入
            embeddings = [self._generate_embedding(doc) for doc in documents]
            
            # 更新集合
            self.collection.update(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            self.log_info(f"更新了 {len(documents)} 个文档")
            
        except Exception as e:
            self.log_error(f"更新文档失败: {str(e)}")
            raise
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            count = self.collection.count()
            return {
                "name": self.collection_name,
                "count": count,
                "embedding_model": self.embedding_model_name
            }
        except Exception as e:
            self.log_error(f"获取集合信息失败: {str(e)}")
            return {}


class DocumentProcessor(LoggerMixin):
    """文档处理器"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        super().__init__()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """分割文本为块"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在句子边界分割
            if end < len(text):
                # 寻找最近的句号、问号或感叹号
                for i in range(end, max(end - 100, start), -1):
                    if text[i] in '.!?。！？':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            
            # 防止无限循环
            if start >= end:
                start = end
        
        return chunks
    
    async def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """处理文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            chunks = self.split_text(text)
            
            # 生成元数据
            file_name = os.path.basename(file_path)
            processed_chunks = []
            
            for i, chunk in enumerate(chunks):
                metadata = {
                    "source": file_name,
                    "file_path": file_path,
                    "chunk_index": i,
                    "chunk_count": len(chunks)
                }
                processed_chunks.append({
                    "text": chunk,
                    "metadata": metadata
                })
            
            self.log_info(f"处理文件 {file_name}，生成 {len(chunks)} 个文本块")
            return processed_chunks
            
        except Exception as e:
            self.log_error(f"处理文件失败: {str(e)}")
            return []


class RAGManager(LoggerMixin):
    """RAG管理器"""
    
    def __init__(self, rag: ChromaRAG, processor: DocumentProcessor = None):
        super().__init__()
        self.rag = rag
        self.processor = processor or DocumentProcessor()
    
    async def add_file(self, file_path: str) -> None:
        """添加文件到RAG"""
        try:
            chunks = await self.processor.process_file(file_path)
            
            if chunks:
                documents = [chunk["text"] for chunk in chunks]
                metadatas = [chunk["metadata"] for chunk in chunks]
                
                await self.rag.add_documents(documents, metadatas)
                self.log_info(f"成功添加文件到RAG: {file_path}")
            
        except Exception as e:
            self.log_error(f"添加文件到RAG失败: {str(e)}")
            raise
    
    async def add_text(self, text: str, source: str = "manual") -> None:
        """添加文本到RAG"""
        try:
            chunks = self.processor.split_text(text)
            
            metadatas = [{
                "source": source,
                "chunk_index": i,
                "chunk_count": len(chunks)
            } for i in range(len(chunks))]
            
            await self.rag.add_documents(chunks, metadatas)
            self.log_info(f"成功添加文本到RAG，来源: {source}")
            
        except Exception as e:
            self.log_error(f"添加文本到RAG失败: {str(e)}")
            raise
    
    async def search_and_format(self, query: str, limit: int = 5) -> str:
        """搜索并格式化结果"""
        try:
            results = await self.rag.search(query, limit)
            
            if not results:
                return "未找到相关信息。"
            
            formatted_text = f"基于知识库搜索到 {len(results)} 个相关结果：\n\n"
            
            for i, result in enumerate(results, 1):
                doc = result["document"]
                metadata = result["metadata"]
                source = metadata.get("source", "未知来源")
                
                formatted_text += f"{i}. 来源：{source}\n"
                formatted_text += f"内容：{doc}\n\n"
            
            return formatted_text
            
        except Exception as e:
            self.log_error(f"搜索和格式化失败: {str(e)}")
            return "搜索过程中出现错误。"
