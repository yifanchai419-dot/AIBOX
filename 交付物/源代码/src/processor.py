import logging
import hashlib
import re
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(handler)


class DataProcessor:
    """
    数据处理类：负责文章去重、质量打分和自动分类
    
    Attributes:
        use_api: 是否使用大模型API进行分类和打分
        api_key: 大模型API密钥
        similarity_threshold: 相似度阈值（用于去重）
        min_score: 最低分数阈值（低于此分数的文章将被过滤）
    """
    
    def __init__(self, use_api: bool = False, api_key: str = None, 
                 similarity_threshold: float = 0.70, min_score: float = 4.0):
        self.use_api = use_api
        self.api_key = api_key
        self.similarity_threshold = similarity_threshold
        self.min_score = min_score
        
        # 分类关键词规则（用于无API时的保底分类）
        self.category_keywords = {
            "模型发布": ["模型", "发布", "开源", "LLM", "GPT", "Llama", "Qwen", "Gemini", 
                       "Falcon", "Mistral", "stable diffusion", "diffusion"],
            "产品更新": ["产品", "更新", "上线", "功能", "新特性", "ChatGPT", "Copilot", 
                       "Notion", "Midjourney", "DALL-E"],
            "行业动态": ["融资", "收购", "政策", "监管", "会议", "论坛", "报告", 
                       "市场", "趋势", "行业", "公司"],
            "论文研究": ["论文", "研究", "arXiv", "发表", "论文", "实验", "方法", 
                       "算法", "ICLR", "NeurIPS", "ICML", "ACL"],
            "技巧观点": ["技巧", "教程", "指南", "经验", "观点", "思考", "分析", 
                       "评测", "对比", "Prompt", "提示词"]
        }
        
        # AI相关关键词（用于判断文章是否与AI相关）
        self.ai_keywords = [
            "AI", "人工智能", "大模型", "LLM", "GPT", "Llama", "Qwen", "Gemini",
            "机器学习", "深度学习", "神经网络", "算法", "智能体", "Agent",
            "计算机视觉", "NLP", "自然语言处理", "生成式", "扩散模型", "Transformer",
            "开源", "论文", "arXiv", "研究", "技术", "产品", "工具", "应用",
            "ChatGPT", "Midjourney", "DALL-E", "Copilot", "Notion AI", "编程"
        ]
        
        # 高质量关键词（用于质量打分）
        self.quality_keywords = ["发布", "研究", "论文", "开源", "重要", "突破", "最新", "重磅"]
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度（基于Jaccard相似度）
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            相似度分数（0-1）
        """
        if not text1 or not text2:
            return 0.0
        
        # 使用分词（简单的按空格分词）
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # 计算Jaccard相似度
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """
        对文章列表进行去重
        
        Args:
            articles: 原始文章列表
            
        Returns:
            去重后的文章列表
        """
        if not articles:
            logger.info("去重：输入文章列表为空")
            return []
        
        logger.info(f"去重：开始处理 {len(articles)} 篇文章")
        
        unique_articles = []
        seen_titles = set()
        seen_contents = set()
        
        for article in articles:
            try:
                title = article.get("title", "")
                content = article.get("content", "")
                
                # 生成标题和内容的哈希值
                title_hash = hashlib.md5(title.encode()).hexdigest()
                content_hash = hashlib.md5(content[:500].encode()).hexdigest()
                
                # 检查标题是否重复
                if title_hash in seen_titles:
                    logger.debug(f"去重：跳过重复标题: {title}")
                    continue
                
                # 检查内容是否重复
                if content_hash in seen_contents:
                    logger.debug(f"去重：跳过重复内容: {title}")
                    continue
                
                # 检查与已添加文章的相似度
                is_duplicate = False
                for unique in unique_articles:
                    # 标题相似度检查
                    title_sim = self._calculate_text_similarity(title, unique.get("title", ""))
                    if title_sim >= self.similarity_threshold:
                        is_duplicate = True
                        break
                    
                    # 内容相似度检查
                    content_sim = self._calculate_text_similarity(content[:500], unique.get("content", "")[:500])
                    if content_sim >= self.similarity_threshold:
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    logger.debug(f"去重：跳过相似文章: {title}")
                    continue
                
                # 添加到去重列表
                unique_articles.append(article)
                seen_titles.add(title_hash)
                seen_contents.add(content_hash)
                
            except Exception as e:
                logger.warning(f"去重：处理文章时出错 - {str(e)}")
                continue
        
        logger.info(f"去重：完成，保留 {len(unique_articles)} 篇文章")
        return unique_articles
    
    def _is_ai_related(self, article: Dict) -> bool:
        """
        判断文章是否与AI相关
        
        Args:
            article: 文章字典
            
        Returns:
            是否与AI相关
        """
        title = article.get("title", "").lower()
        content = article.get("content", "").lower()
        full_text = title + " " + content
        
        # 首先检查精确匹配
        for keyword in self.ai_keywords:
            if keyword.lower() in full_text:
                return True
        
        # 检查常见缩写和变体
        ai_patterns = [
            r'\brag\b',  # RAG
            r'\bnlp\b',  # NLP
            r'\bllm\b',  # LLM
            r'\bgpt\b',  # GPT
            r'\bartificial\s+intelligence',  # artificial intelligence
            r'\bdeep\s+learning',  # deep learning
            r'\bmachine\s+learning',  # machine learning
            r'\bneural\s+network',  # neural network
            r'\btransformer\b',  # transformer
            r'\bdiffusion\b',  # diffusion
            r'\bopenai\b',  # OpenAI
            r'\bmeta\b',  # Meta
            r'\bgoogle\b',  # Google (often AI-related)
            r'\bmicrosoft\b',  # Microsoft (often AI-related)
            r'\bapple\b',  # Apple (often AI-related)
            r'\bdeepseek\b',  # DeepSeek
            r'\balibaba\b',  # Alibaba
            r'\bbaidu\b',  # Baidu
            r'\btencent\b',  # Tencent
            r'\bbytedance\b',  # ByteDance
            r'\bclaude\b',  # Claude
            r'\bmistral\b',  # Mistral
            r'\bxiaomi\b',  # Xiaomi
        ]
        
        for pattern in ai_patterns:
            if re.search(pattern, full_text):
                return True
        
        return False
    
    def score_article(self, article: Dict) -> float:
        """
        对单篇文章进行质量打分（0-10分）
        
        打分规则：
        1. AI相关性检查（一票否决）：非AI相关文章直接打低分
        2. 信源权重（权威性）- 权重30%
        3. 内容质量（长度、完整性）- 权重30%
        4. 时效性 - 权重20%
        5. 关键词匹配（AI相关关键词）- 权重20%
        
        Args:
            article: 文章字典
            
        Returns:
            质量分数（0-10）
        """
        try:
            score = 0.0
            
            # 0. AI相关性检查（一票否决）- 如果文章与AI无关，直接打低分
            if not self._is_ai_related(article):
                return round(2.5 + float(article.get("weight", 0.5)) * 0.5, 2)
            
            # 1. 信源权重（权威性）- 权重30%
            weight = article.get("weight", 0.5)
            authority_score = weight * 3.0
            score += authority_score
            
            # 2. 内容质量 - 权重30%
            content = article.get("content", "")
            content_length = len(content)
            
            # 正文长度评分：越长越好，但超过3000字后边际效益递减
            if content_length < 50:
                content_score = 0.0
            elif content_length < 100:
                content_score = 0.5
            elif content_length < 300:
                content_score = 1.0
            elif content_length < 500:
                content_score = 1.5 + (content_length - 300) / 200
            elif content_length < 1000:
                content_score = 2.0 + (content_length - 500) / 500
            else:
                content_score = 2.5 + (content_length - 1000) / 2000
            
            # 限制最大内容分数
            content_score = min(content_score, 3.0)
            score += content_score
            
            # 3. 时效性 - 权重20%
            published_at = article.get("published_at", "")
            time_score = 0.0
            
            if published_at:
                try:
                    pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    
                    # 计算发布时间与当前时间的差值（小时）
                    hours_diff = (now - pub_time).total_seconds() / 3600
                    
                    # 时效性评分：越新越高
                    if hours_diff < 6:
                        time_score = 2.0
                    elif hours_diff < 12:
                        time_score = 1.8
                    elif hours_diff < 24:
                        time_score = 1.5
                    elif hours_diff < 48:
                        time_score = 1.0
                    elif hours_diff < 72:
                        time_score = 0.5
                    elif hours_diff < 168:  # 7天
                        time_score = 0.2
                    else:
                        time_score = 0.05
                except Exception:
                    time_score = 0.8  # 时间解析失败，给低分
            
            score += time_score
            
            # 4. 关键词匹配 - 权重20%
            title = article.get("title", "")
            full_text = (title + " " + content).lower()
            
            keyword_score = 0.0
            ai_keyword_count = 0
            
            # 统计AI相关关键词出现次数
            for keyword in self.ai_keywords:
                if keyword.lower() in full_text:
                    ai_keyword_count += 1
                    keyword_score += 0.15
                    if keyword_score >= 1.5:
                        break
            
            # 高质量关键词额外加分
            for keyword in self.quality_keywords:
                if keyword.lower() in full_text:
                    keyword_score += 0.2
                    if keyword_score >= 2.0:
                        break
            
            score += min(keyword_score, 2.0)
            
            # 确保分数在0-10之间
            score = max(0.0, min(10.0, score))
            
            return round(score, 2)
        
        except Exception as e:
            logger.warning(f"打分：处理文章 '{article.get('title', '')}' 时出错 - {str(e)}")
            return 2.0  # 返回低分数
    
    def classify_article(self, article: Dict) -> str:
        """
        对单篇文章进行自动分类
        
        Args:
            article: 文章字典
            
        Returns:
            分类结果（模型发布、产品更新、行业动态、论文研究、技巧观点）
        """
        try:
            title = article.get("title", "").lower()
            content = article.get("content", "").lower()
            full_text = title + " " + content
            
            # 计算每个分类的匹配分数
            category_scores = {}
            
            for category, keywords in self.category_keywords.items():
                score = 0
                for keyword in keywords:
                    if keyword.lower() in full_text:
                        score += 1
                category_scores[category] = score
            
            # 找到分数最高的分类
            max_score = max(category_scores.values())
            
            if max_score == 0:
                # 无匹配关键词，默认归类为"技巧观点"
                return "技巧观点"
            
            # 返回分数最高的分类
            for category, score in category_scores.items():
                if score == max_score:
                    return category
        
        except Exception as e:
            logger.warning(f"分类：处理文章 '{article.get('title', '')}' 时出错 - {str(e)}")
            return "技巧观点"  # 返回默认分类
    
    def process_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        主处理函数：顺序调用去重、打分、分类逻辑
        
        Args:
            articles: 原始文章列表
            
        Returns:
            处理后的文章列表（已去重、已打分、已分类、按分数排序）
        """
        if not articles:
            logger.warning("主处理：输入文章列表为空")
            return []
        
        logger.info(f"主处理：开始处理 {len(articles)} 篇文章")
        
        # 1. 去重
        unique_articles = self.deduplicate(articles)
        
        # 2. 打分和分类
        processed_articles = []
        for article in unique_articles:
            try:
                # 打分
                score = self.score_article(article)
                article["score"] = score
                
                # 分类
                category = self.classify_article(article)
                article["category"] = category
                
                # 过滤低质量文章
                if score >= self.min_score:
                    processed_articles.append(article)
                else:
                    logger.debug(f"过滤：文章 '{article.get('title', '')}' 分数 {score} 低于阈值 {self.min_score}")
            
            except Exception as e:
                logger.warning(f"主处理：处理文章时出错 - {str(e)}")
                continue
        
        # 3. 按分数从高到低排序
        processed_articles.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        logger.info(f"主处理：完成，共 {len(processed_articles)} 篇高质量文章")
        
        return processed_articles    
    
    def process_articles_with_deepseek(self, articles: List[Dict], generator_client) -> List[Dict]:
        """
        使用 DeepSeek API 进行高精度批量打分与分类（带有规则保底）
        
        Args:
            articles: 原始文章列表
            generator_client: CourseGenerator实例，需包含_call_deepseek_api方法
            
        Returns:
            处理后的文章列表（已去重、已打分、已分类、按分数排序）
        """
        if not articles or not generator_client:
            logger.info("DeepSeek处理：输入为空或无客户端，使用规则匹配")
            return self.process_articles(articles)
        
        unique_articles = self.deduplicate(articles)
        total_articles = len(unique_articles)
        batch_size = 20
        eval_map = {}
        deepseek_count = 0
        rule_count = 0
        
        logger.info(f"DeepSeek处理：开始处理 {total_articles} 篇文章，批量大小: {batch_size}")
        
        # 批量处理所有文章（分批调用API）
        for start_idx in range(0, total_articles, batch_size):
            end_idx = min(start_idx + batch_size, total_articles)
            batch = unique_articles[start_idx:end_idx]
            
            batch_data = [
                {"id": start_idx + idx, "title": a.get("title", ""), "content": a.get("content", "")[:200]}
                for idx, a in enumerate(batch)
            ]
            
            prompt = f"""请对以下 AI 文章进行质量打分 (0.0 - 10.0) 和 分类归档。
可选分类：模型发布、产品更新、行业动态、论文研究、技巧观点。

文章列表：
{json.dumps(batch_data, ensure_ascii=False)}

请以 JSON 数组格式严格输出评估结果，格式如下：
[
  {{"id": 0, "score": 8.5, "category": "模型发布"}}, ...
]"""

            try:
                res = generator_client._call_deepseek_api(
                    prompt,
                    system_prompt="你是一个极度严谨的 AI 资讯分析专家，请严格只返回 JSON 数组，无任何解释文字。"
                )
                
                if not res:
                    logger.warning(f"DeepSeek处理：批量 {start_idx}-{end_idx} 返回为空，降级为规则匹配")
                    for article in batch:
                        article["score"] = self.score_article(article)
                        article["category"] = self.classify_article(article)
                        rule_count += 1
                    continue
                
                # 清理响应内容
                cleaned = res.replace("```json", "").replace("```", "").strip()
                
                # 验证响应格式
                try:
                    eval_list = json.loads(cleaned)
                    if not isinstance(eval_list, list):
                        raise ValueError("响应不是JSON数组")
                except json.JSONDecodeError:
                    logger.warning(f"DeepSeek处理：批量 {start_idx}-{end_idx} 响应解析失败，降级为规则匹配")
                    for article in batch:
                        article["score"] = self.score_article(article)
                        article["category"] = self.classify_article(article)
                        rule_count += 1
                    continue
                
                # 验证每个项目的结构
                for item in eval_list:
                    if isinstance(item, dict) and "id" in item and "score" in item and "category" in item:
                        try:
                            item["score"] = float(item["score"])
                            eval_map[item["id"]] = item
                        except (ValueError, TypeError):
                            logger.warning(f"DeepSeek处理：无效评分值，跳过id={item.get('id')}")
                    else:
                        logger.warning(f"DeepSeek处理：缺少必要字段，跳过item={item}")
                
                deepseek_count += len([item for item in eval_list if isinstance(item, dict) and "id" in item])
                
            except Exception as e:
                logger.warning(f"DeepSeek处理：批量 {start_idx}-{end_idx} 调用失败，降级为规则匹配: {str(e)}")
                for article in batch:
                    article["score"] = self.score_article(article)
                    article["category"] = self.classify_article(article)
                    rule_count += 1
                continue
        
        # 应用评估结果（带保底规则）
        for idx, article in enumerate(unique_articles):
            if idx in eval_map:
                # 获取DeepSeek评分，若分数过低则使用规则保底
                deepseek_score = eval_map[idx].get("score", 0)
                try:
                    deepseek_score = float(deepseek_score)
                except (ValueError, TypeError):
                    deepseek_score = 0.0
                
                # 如果DeepSeek评分过低（< 1.0），使用规则保底分数
                if deepseek_score < 1.0:
                    article["score"] = self.score_article(article)
                    rule_count += 1
                    deepseek_count -= 1 if deepseek_count > 0 else 0
                else:
                    article["score"] = deepseek_score
                
                # 使用DeepSeek分类，若无效则使用规则保底
                category = eval_map[idx].get("category", "")
                if category not in self.category_keywords:
                    article["category"] = self.classify_article(article)
                    rule_count += 1
                    deepseek_count -= 1 if deepseek_count > 0 else 0
                else:
                    article["category"] = category
            else:
                article["score"] = self.score_article(article)
                article["category"] = self.classify_article(article)
                rule_count += 1
                deepseek_count -= 1 if deepseek_count > 0 else 0
        
        # 确保deepseek_count统计正确
        deepseek_count = total_articles - rule_count
        
        logger.info(f"DeepSeek处理：完成。DeepSeek评分: {deepseek_count} 篇，规则保底: {rule_count} 篇")
        
        # 过滤并排序
        processed = [a for a in unique_articles if a.get("score", 0) >= self.min_score]
        processed.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return processed
        
    def get_category_statistics(self, articles: List[Dict]) -> Dict[str, int]:
        """
        获取分类统计信息
        
        Args:
            articles: 文章列表
            
        Returns:
            分类统计字典
        """
        stats = {}
        for article in articles:
            category = article.get("category", "未知")
            stats[category] = stats.get(category, 0) + 1
        return stats
    
    def evaluate_accuracy(self) -> float:
        """
        分类准确率自测评估
        
        使用标准标注测试集评估 classify_article 的分类准确率
        
        Returns:
            分类准确率（0-1）
        """
        # 标准标注测试集（涵盖5大板块，共18条）
        test_cases = [
            # 模型发布（4条）
            {"title": "Llama 3.4 发布：性能提升50%，支持中文", "content": "Meta今日发布了最新的Llama 3.4模型，采用了全新的架构设计，支持多语言", "expected": "模型发布"},
            {"title": "Qwen 2.5 开源：更强的中文理解能力", "content": "阿里云开源了Qwen 2.5模型，在中文任务上表现优异", "expected": "模型发布"},
            {"title": "GPT-5 即将发布：下一代大语言模型前瞻", "content": "OpenAI透露GPT-5正在开发中，预计将有重大突破", "expected": "模型发布"},
            {"title": "Mistral Large 2 发布：支持更长上下文", "content": "Mistral AI发布了Mistral Large 2，支持128k上下文窗口", "expected": "模型发布"},
            
            # 产品更新（4条）
            {"title": "ChatGPT 更新：新增图片理解功能", "content": "OpenAI宣布ChatGPT新增图片理解功能，用户可以上传图片并询问相关问题", "expected": "产品更新"},
            {"title": "Notion AI 新功能：自动总结文档", "content": "Notion推出了AI自动总结功能，可以快速生成文档摘要", "expected": "产品更新"},
            {"title": "GitHub Copilot 更新：支持代码解释", "content": "GitHub Copilot新增代码解释功能，帮助开发者理解复杂代码", "expected": "产品更新"},
            {"title": "Midjourney v6 上线：更逼真的图像生成", "content": "Midjourney发布v6版本，图像生成质量大幅提升", "expected": "产品更新"},
            
            # 行业动态（3条）
            {"title": "欧盟AI法案正式通过：全球首个全面AI监管框架", "content": "欧盟议会正式通过了AI法案，这是全球首个全面的AI监管框架", "expected": "行业动态"},
            {"title": "AI公司融资热潮：上半年融资额突破100亿美元", "content": "据统计，今年上半年AI领域融资额超过100亿美元", "expected": "行业动态"},
            {"title": "百度收购AI创业公司：加速布局AI生态", "content": "百度宣布收购一家AI创业公司，进一步完善AI生态布局", "expected": "行业动态"},
            
            # 论文研究（4条）
            {"title": "arXiv最新论文：新型注意力机制突破Transformer瓶颈", "content": "最新发表在arXiv上的论文提出了一种新型注意力机制", "expected": "论文研究"},
            {"title": "ICLR 2026论文解读：大模型效率优化新方法", "content": "本文解读了ICLR 2026上关于大模型效率优化的最新论文", "expected": "论文研究"},
            {"title": "NeurIPS研究：AI推理能力的边界探索", "content": "NeurIPS最新研究探讨了AI推理能力的极限和边界", "expected": "论文研究"},
            {"title": "新研究表明：大模型可以学习因果推理", "content": "最新研究发现，大语言模型在特定条件下可以学习因果推理", "expected": "论文研究"},
            
            # 技巧观点（3条）
            {"title": "Prompt工程技巧：如何写出高质量的提示词", "content": "本文分享了10个实用的Prompt工程技巧", "expected": "技巧观点"},
            {"title": "深度思考：AI对未来工作的影响", "content": "本文从多个角度分析了AI技术对未来工作的影响", "expected": "技巧观点"},
            {"title": "AI工具评测：10款AI写作助手对比", "content": "本文对比评测了10款主流的AI写作助手工具", "expected": "技巧观点"},
        ]
        
        correct_count = 0
        total_count = len(test_cases)
        results = []
        
        logger.info(f"开始分类准确率评估，测试样本数: {total_count}")
        
        for i, test_case in enumerate(test_cases, 1):
            try:
                # 调用分类方法
                predicted = self.classify_article({
                    "title": test_case["title"],
                    "content": test_case["content"]
                })
                
                # 判断是否正确
                is_correct = (predicted == test_case["expected"])
                if is_correct:
                    correct_count += 1
                
                # 记录结果
                results.append({
                    "index": i,
                    "title": test_case["title"],
                    "expected": test_case["expected"],
                    "predicted": predicted,
                    "correct": is_correct
                })
                
            except Exception as e:
                logger.warning(f"评估第{i}条测试样本时出错: {str(e)}")
                results.append({
                    "index": i,
                    "title": test_case["title"],
                    "expected": test_case["expected"],
                    "predicted": "错误",
                    "correct": False
                })
        
        # 计算准确率
        accuracy = correct_count / total_count if total_count > 0 else 0.0
        
        return accuracy, results


def process_articles(articles: List[Dict], **kwargs) -> List[Dict]:
    """
    便捷函数：创建DataProcessor实例并处理文章
    
    Args:
        articles: 原始文章列表
        **kwargs: DataProcessor初始化参数
        
    Returns:
        处理后的文章列表
    """
    processor = DataProcessor(**kwargs)
    return processor.process_articles(articles)


if __name__ == "__main__":
    """
    测试入口：使用fetcher模块抓取的数据进行完整流程测试
    """
    import sys
    import os
    
    # 添加项目根目录到Python路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("=" * 60)
    print("AI知识日报处理模块测试")
    print("=" * 60)
    
    # 尝试导入fetcher模块
    try:
        from src.fetcher import fetch_all_articles
        
        print("\n[步骤1] 抓取文章数据...")
        articles = fetch_all_articles(hours=48)
        print(f"  原始文章数量: {len(articles)}")
        
    except Exception as e:
        logger.warning(f"抓取真实数据失败，使用示例数据: {str(e)}")
        
        # 示例数据
        articles = [
            {
                "title": "Llama 3.4 发布：性能提升50%，支持中文",
                "content": "Meta今日发布了最新的Llama 3.4模型，相比上一代，性能提升了50%，并原生支持中文。该模型采用了全新的架构设计...",
                "link": "https://example.com/llama34",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "机器之心",
                "weight": 0.9
            },
            {
                "title": "ChatGPT 更新：新增图片理解功能",
                "content": "OpenAI宣布ChatGPT新增图片理解功能，用户现在可以上传图片并询问相关问题。这一功能基于GPT-4o模型...",
                "link": "https://example.com/chatgpt-update",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "AI前线",
                "weight": 0.85
            },
            {
                "title": "AI监管政策新动向：欧盟AI法案正式通过",
                "content": "欧盟议会正式通过了AI法案，这是全球首个全面的AI监管框架。法案将AI系统分为四个风险等级...",
                "link": "https://example.com/eu-ai-act",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "机器之心",
                "weight": 0.9
            },
            {
                "title": "arXiv最新论文：新型注意力机制突破Transformer瓶颈",
                "content": "最新发表在arXiv上的论文提出了一种新型注意力机制，能够突破Transformer的计算效率瓶颈...",
                "link": "https://example.com/new-attention",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "PaperWeekly",
                "weight": 0.95
            },
            {
                "title": "Prompt工程技巧：如何写出高质量的提示词",
                "content": "本文分享了10个实用的Prompt工程技巧，帮助你更好地利用大语言模型...",
                "link": "https://example.com/prompt-tips",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "AI前线",
                "weight": 0.85
            },
            # 重复文章（用于测试去重）
            {
                "title": "Llama 3.4 发布：性能提升50%，支持中文",
                "content": "Meta今日发布了最新的Llama 3.4模型，相比上一代，性能提升了50%...",
                "link": "https://example.com/llama34-duplicate",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "机器之心",
                "weight": 0.9
            }
        ]
        print(f"\n[步骤1] 使用示例数据")
        print(f"  示例文章数量: {len(articles)}")
    
    # 初始化处理器
    processor = DataProcessor(use_api=False, min_score=3.0)
    
    # 处理文章
    print("\n[步骤2] 处理文章（去重、打分、分类）...")
    processed_articles = processor.process_articles(articles)
    
    # 输出统计信息
    print("\n[步骤3] 处理结果统计")
    print(f"  去重后文章数量: {len(processed_articles)}")
    
    # 分类统计
    category_stats = processor.get_category_statistics(processed_articles)
    print(f"\n  分类统计:")
    for category, count in category_stats.items():
        print(f"    - {category}: {count} 篇")
    
    # 输出Top 3文章
    print("\n[步骤4] 打分最高的Top 3文章")
    top_3 = processed_articles[:3]
    for i, article in enumerate(top_3, 1):
        print(f"\n    【第 {i} 名】")
        print(f"      标题: {article['title']}")
        print(f"      分类: {article['category']}")
        print(f"      分数: {article['score']}")
        print(f"      信源: {article['source']}")
        print(f"      链接: {article['link']}")
    
    # [步骤5] 分类准确率自测评估
    print("\n" + "=" * 60)
    print("[步骤5] 分类准确率自测评估")
    print("=" * 60)
    
    accuracy, results = processor.evaluate_accuracy()
    
    # 打印详细对比清单
    print("\n详细对比清单：")
    print("-" * 80)
    print(f"{'序号':<4} {'预测结果':<8} {'期望结果':<8} {'是否正确':<6} {'标题'}")
    print("-" * 80)
    
    for result in results:
        status = "✅" if result["correct"] else "❌"
        print(f"{result['index']:<4} {result['predicted']:<8} {result['expected']:<8} {status:<6} {result['title']}")
    
    # 打印最终准确率
    print("\n" + "-" * 80)
    print(f"分类准确率: {accuracy * 100:.2f}% ({len([r for r in results if r['correct']])}/{len(results)})")
    
    # 断言确保准确率达到85%以上
    assert accuracy >= 0.85, f"分类准确率 {accuracy * 100:.2f}% 未达到85%以上的要求！"
    print("\n✅ 分类准确率达到85%以上要求，测试通过！")
    
    print("\n" + "=" * 60)
    print("测试完成！")