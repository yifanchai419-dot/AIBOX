import os
import logging
from typing import List, Dict, Optional

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(handler)

# 尝试导入ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB未安装，将使用TF-IDF相似度索引")

# 尝试导入scikit-learn用于TF-IDF回退
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn未安装，将使用简单的Jaccard相似度")


class VectorDB:
    """
    向量数据库类：负责文章的向量存储和语义检索
    
    Attributes:
        client: ChromaDB客户端实例
        collection: 向量集合
        use_chromadb: 是否使用ChromaDB
    """
    
    def __init__(self, persist_directory: str = "./data/chromadb"):
        self.use_chromadb = CHROMADB_AVAILABLE
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        
        # TF-IDF回退方案
        self.vectorizer = None
        self.tfidf_matrix = None
        self.articles = []
        
        if self.use_chromadb:
            try:
                # 确保目录存在
                os.makedirs(persist_directory, exist_ok=True)
                
                # 初始化ChromaDB客户端
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        is_persistent=True
                    )
                )
                
                # 创建或获取集合
                self.collection = self.client.get_or_create_collection(
                    name="ai_articles",
                    metadata={"description": "AI知识日报文章向量库"}
                )
                
                logger.info("成功初始化ChromaDB向量数据库")
            except Exception as e:
                logger.warning(f"初始化ChromaDB失败: {str(e)}")
                self.use_chromadb = False
                self._init_tfidf_fallback()
        else:
            self._init_tfidf_fallback()
    
    def _init_tfidf_fallback(self):
        """
        初始化TF-IDF回退方案
        """
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            logger.info("使用TF-IDF相似度索引作为回退方案")
        else:
            logger.info("使用简单的Jaccard相似度作为回退方案")
    
    def add_articles(self, articles: List[Dict]):
        """
        将文章存入向量库
        
        Args:
            articles: 处理后的文章列表
        """
        if not articles:
            logger.warning("添加文章：输入列表为空")
            return
        
        logger.info(f"添加文章：开始处理 {len(articles)} 篇文章")
        
        if self.use_chromadb and self.collection:
            try:
                # 准备数据
                ids = []
                documents = []
                metadatas = []
                
                for i, article in enumerate(articles):
                    article_id = f"article_{i}_{hash(article.get('title', '') + article.get('link', ''))}"
                    ids.append(article_id)
                    
                    # 构建文档内容（标题+内容）
                    doc_content = f"{article.get('title', '')} {article.get('content', '')}"
                    documents.append(doc_content)
                    
                    # 元数据
                    metadatas.append({
                        "title": article.get('title', ''),
                        "link": article.get('link', ''),
                        "source": article.get('source', ''),
                        "category": article.get('category', ''),
                        "score": article.get('score', 0),
                        "published_at": article.get('published_at', ''),
                        "weight": article.get('weight', 0)
                    })
                
                # 添加到ChromaDB
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
                
                logger.info(f"添加文章：成功将 {len(articles)} 篇文章存入ChromaDB")
                
            except Exception as e:
                logger.error(f"添加文章到ChromaDB失败: {str(e)}")
                # 回退到TF-IDF
                self.use_chromadb = False
                self._init_tfidf_fallback()
                self._add_articles_tfidf(articles)
        else:
            self._add_articles_tfidf(articles)
    
    def _add_articles_tfidf(self, articles: List[Dict]):
        """
        使用TF-IDF添加文章（回退方案）
        
        Args:
            articles: 处理后的文章列表
        """
        try:
            # 构建文档内容
            documents = [
                f"{article.get('title', '')} {article.get('content', '')}"
                for article in articles
            ]
            
            # 添加到现有文章列表
            self.articles.extend(articles)
            
            if SKLEARN_AVAILABLE and self.vectorizer:
                # 重新训练TF-IDF模型
                all_docs = [
                    f"{a.get('title', '')} {a.get('content', '')}"
                    for a in self.articles
                ]
                self.tfidf_matrix = self.vectorizer.fit_transform(all_docs)
                
                logger.info(f"添加文章：成功将 {len(articles)} 篇文章存入TF-IDF索引")
            else:
                logger.info(f"添加文章：成功将 {len(articles)} 篇文章存入内存索引")
                
        except Exception as e:
            logger.error(f"添加文章到TF-IDF索引失败: {str(e)}")
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        根据主题关键词搜索最相关的文章
        
        Args:
            query: 搜索关键词
            top_k: 返回前k篇最相关的文章
            
        Returns:
            搜索结果列表，包含文章信息和相似度分数
        """
        if not query:
            logger.warning("搜索：查询词为空")
            return []
        
        logger.info(f"搜索：查询 '{query}'，返回前 {top_k} 篇")
        
        results = []
        
        if self.use_chromadb and self.collection:
            try:
                # 使用ChromaDB搜索
                search_results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
                
                # 处理结果
                for i in range(len(search_results['ids'][0])):
                    metadata = search_results['metadatas'][0][i]
                    # 距离越小越相似，转换为相似度分数
                    similarity = max(0, 1 - search_results['distances'][0][i])
                    
                    results.append({
                        "title": metadata.get("title", ""),
                        "link": metadata.get("link", ""),
                        "source": metadata.get("source", ""),
                        "category": metadata.get("category", ""),
                        "score": metadata.get("score", 0),
                        "published_at": metadata.get("published_at", ""),
                        "similarity": round(similarity, 4),
                        "content": search_results['documents'][0][i][:200] + "..."
                    })
                
                logger.info(f"搜索：ChromaDB返回 {len(results)} 条结果")
                
            except Exception as e:
                logger.error(f"ChromaDB搜索失败: {str(e)}")
                results = self._search_similar_tfidf(query, top_k)
        else:
            results = self._search_similar_tfidf(query, top_k)
        
        # 按相似度排序
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        
        return results
    
    def _search_similar_tfidf(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        使用TF-IDF搜索（回退方案）
        
        Args:
            query: 搜索关键词
            top_k: 返回前k篇最相关的文章
            
        Returns:
            搜索结果列表
        """
        results = []
        
        if SKLEARN_AVAILABLE and self.vectorizer and self.tfidf_matrix is not None:
            try:
                # 将查询转换为TF-IDF向量
                query_vec = self.vectorizer.transform([query])
                
                # 计算余弦相似度
                similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
                
                # 获取前top_k个最相似的索引
                top_indices = similarities.argsort()[::-1][:top_k]
                
                # 构建结果
                for idx in top_indices:
                    if similarities[idx] > 0:
                        article = self.articles[idx]
                        results.append({
                            "title": article.get("title", ""),
                            "link": article.get("link", ""),
                            "source": article.get("source", ""),
                            "category": article.get("category", ""),
                            "score": article.get("score", 0),
                            "published_at": article.get("published_at", ""),
                            "similarity": round(float(similarities[idx]), 4),
                            "content": article.get("content", "")[:200] + "..."
                        })
                
                logger.info(f"搜索：TF-IDF返回 {len(results)} 条结果")
                
            except Exception as e:
                logger.error(f"TF-IDF搜索失败: {str(e)}")
                results = self._search_similar_jaccard(query, top_k)
        else:
            results = self._search_similar_jaccard(query, top_k)
        
        return results
    
    def _search_similar_jaccard(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        使用Jaccard相似度搜索（最终回退方案）
        
        Args:
            query: 搜索关键词
            top_k: 返回前k篇最相关的文章
            
        Returns:
            搜索结果列表
        """
        results = []
        
        try:
            query_words = set(query.lower().split())
            
            # 计算每篇文章的相似度
            similarities = []
            for article in self.articles:
                doc_text = f"{article.get('title', '')} {article.get('content', '')}".lower()
                doc_words = set(doc_text.split())
                
                if not doc_words:
                    sim = 0
                else:
                    intersection = query_words.intersection(doc_words)
                    union = query_words.union(doc_words)
                    sim = len(intersection) / len(union)
                
                similarities.append((article, sim))
            
            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 取前top_k
            for article, sim in similarities[:top_k]:
                if sim > 0:
                    results.append({
                        "title": article.get("title", ""),
                        "link": article.get("link", ""),
                        "source": article.get("source", ""),
                        "category": article.get("category", ""),
                        "score": article.get("score", 0),
                        "published_at": article.get("published_at", ""),
                        "similarity": round(sim, 4),
                        "content": article.get("content", "")[:200] + "..."
                    })
            
            logger.info(f"搜索：Jaccard返回 {len(results)} 条结果")
            
        except Exception as e:
            logger.error(f"Jaccard搜索失败: {str(e)}")
        
        return results
    
    def get_collection_stats(self) -> Dict:
        """
        获取向量库统计信息
        
        Returns:
            统计信息字典
        """
        if self.use_chromadb and self.collection:
            try:
                count = self.collection.count()
                return {"count": count, "type": "chromadb"}
            except Exception as e:
                logger.error(f"获取ChromaDB统计信息失败: {str(e)}")
                return {"count": len(self.articles), "type": "memory"}
        else:
            return {"count": len(self.articles), "type": "tfidf" if SKLEARN_AVAILABLE else "jaccard"}


if __name__ == "__main__":
    """
    测试入口
    """
    print("=" * 60)
    print("向量数据库模块测试")
    print("=" * 60)
    
    # 示例文章数据
    sample_articles = [
        {
            "title": "Llama 3.4 发布：性能提升50%，支持中文",
            "content": "Meta今日发布了最新的Llama 3.4模型，相比上一代，性能提升了50%，并原生支持中文。",
            "link": "https://example.com/llama34",
            "source": "36氪前沿科技",
            "category": "模型发布",
            "score": 8.5,
            "published_at": "2024-07-23T10:00:00Z",
            "weight": 0.9
        },
        {
            "title": "ChatGPT 更新：新增图片理解功能",
            "content": "OpenAI宣布ChatGPT新增图片理解功能，用户现在可以上传图片并询问相关问题。",
            "link": "https://example.com/chatgpt-update",
            "source": "少数派",
            "category": "产品更新",
            "score": 8.2,
            "published_at": "2024-07-23T09:00:00Z",
            "weight": 0.85
        },
        {
            "title": "arXiv最新论文：新型注意力机制突破Transformer瓶颈",
            "content": "最新发表在arXiv上的论文提出了一种新型注意力机制，能够突破Transformer的计算效率瓶颈。",
            "link": "https://example.com/new-attention",
            "source": "IT之家AI频道",
            "category": "论文研究",
            "score": 8.0,
            "published_at": "2024-07-23T08:00:00Z",
            "weight": 0.95
        },
        {
            "title": "Prompt工程技巧：如何写出高质量的提示词",
            "content": "本文分享了10个实用的Prompt工程技巧，帮助你更好地利用大语言模型。",
            "link": "https://example.com/prompt-tips",
            "source": "少数派",
            "category": "技巧观点",
            "score": 7.5,
            "published_at": "2024-07-23T07:00:00Z",
            "weight": 0.85
        },
        {
            "title": "AI监管政策新动向：欧盟AI法案正式通过",
            "content": "欧盟议会正式通过了AI法案，这是全球首个全面的AI监管框架。",
            "link": "https://example.com/eu-ai-act",
            "source": "36氪前沿科技",
            "category": "行业动态",
            "score": 7.8,
            "published_at": "2024-07-23T06:00:00Z",
            "weight": 0.9
        }
    ]
    
    # 初始化向量库
    print("\n[步骤1] 初始化向量库...")
    vdb = VectorDB()
    
    # 添加文章
    print("\n[步骤2] 添加文章到向量库...")
    vdb.add_articles(sample_articles)
    
    # 获取统计信息
    stats = vdb.get_collection_stats()
    print(f"  向量库类型: {stats['type']}")
    print(f"  文章数量: {stats['count']}")
    
    # 测试搜索
    print("\n[步骤3] 测试向量检索...")
    
    test_queries = ["大模型", "Transformer", "Prompt"]
    
    for query in test_queries:
        print(f"\n  查询: '{query}'")
        results = vdb.search_similar(query, top_k=3)
        for i, result in enumerate(results, 1):
            print(f"    {i}. {result['title']} (相似度: {result['similarity']})")
    
    print("\n" + "=" * 60)
    print("测试完成！")
