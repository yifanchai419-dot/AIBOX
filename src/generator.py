import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(handler)

# 尝试加载.env文件
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("成功加载.env文件")
except ImportError:
    logger.warning("python-dotenv未安装，将直接读取系统环境变量")

# 尝试导入OpenAI SDK
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK未安装，将使用Mock模式")


class CourseGenerator:
    """
    课程生成类：负责生成每日总结简报和1小时课程教案
    
    Attributes:
        use_api: 是否使用大模型API生成内容
        client: OpenAI客户端实例
        model: 使用的模型名称
    """
    
    def __init__(self, use_api: bool = True, model: str = "deepseek-chat"):
        self.use_api = use_api
        self.model = model
        self.client = None
        
        # 尝试读取环境变量（优先DEEPSEEK_API_KEY，兼容OPENAI_API_KEY）
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        # 读取base_url，确保有https://前缀
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        
        # 初始化OpenAI客户端
        if use_api and api_key and OPENAI_AVAILABLE:
            try:
                self.client = OpenAI(api_key=api_key, base_url=base_url)
                logger.info(f"成功初始化OpenAI客户端，模型: {model}")
            except Exception as e:
                logger.warning(f"初始化OpenAI客户端失败: {str(e)}")
                self.use_api = False
        else:
            if not api_key:
                logger.warning("未配置DEEPSEEK_API_KEY或OPENAI_API_KEY，将使用Mock模式")
            self.use_api = False
    
    def _call_openai_api(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        调用OpenAI API生成内容
        
        Args:
            prompt: 提示词
            max_tokens: 最大输出token数
            
        Returns:
            生成的内容
        """
        if not self.client or not self.use_api:
            return ""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的AI教育内容创作者，擅长将复杂的AI技术知识转化为通俗易懂的课程内容。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"调用OpenAI API失败: {str(e)}")
            return ""
    
    def _call_deepseek_api(self, prompt: str, system_prompt: str = "") -> str:
        """
        调用DeepSeek API进行高精度分析（支持自定义system prompt）
        
        Args:
            prompt: 提示词
            system_prompt: 系统提示词（可选）
            
        Returns:
            生成的内容
        """
        if not self.client or not self.use_api:
            return ""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt if system_prompt else "你是一位专业的AI资讯分析专家。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"调用DeepSeek API失败: {str(e)}")
            return ""
    
    def _clean_report_output(self, content: str) -> str:
        """
        清理API返回的日报内容，确保格式正确：
        1. 移除开头寒暄语（如"好的，这是..."）
        2. 移除一级标题（#）
        3. 找到并保留从## 🎯 今日 AI 焦点 TOP 5开始的内容
        
        Args:
            content: API返回的原始内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return content
            
        # 找到"今日 AI 焦点 TOP 5"的位置，从那里开始截取
        start_markers = [
            "## 🎯 今日 AI 焦点 TOP 5",
            "## 今日AI焦点TOP 5",
            "## 今日 AI 焦点 TOP 5"
        ]
        
        for marker in start_markers:
            idx = content.find(marker)
            if idx != -1:
                content = content[idx:]
                break
        
        # 如果没有找到任何标记，尝试找到第一个二级标题
        if not any(m in content for m in start_markers):
            import re
            match = re.search(r'^##\s', content, re.MULTILINE)
            if match:
                content = content[match.start():]
        
        # 移除一级标题行
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # 移除以#开头的行（一级标题）
            if line.strip().startswith('# ') and not line.strip().startswith('##'):
                continue
            cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # 移除开头的空行
        content = content.strip()
        
        return content
    
    def _generate_daily_report_mock(self, articles: List[Dict]) -> str:
        """
        Mock模式：使用模板生成每日总结简报
        
        Args:
            articles: 处理后的文章列表
            
        Returns:
            Markdown格式的每日简报
        """
        today = datetime.now().strftime("%Y年%m月%d日")
        
        # 按分类分组
        categories = ["模型发布", "产品更新", "行业动态", "论文研究", "技巧观点"]
        category_groups = {cat: [] for cat in categories}
        
        for article in articles[:20]:  # 取前20篇
            category = article.get("category", "技巧观点")
            if category in category_groups:
                category_groups[category].append(article)
        
        # 生成TOP 5
        top_5 = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)[:5]
        
        def fmt_time(article):
            """格式化发布时间"""
            dt_str = article.get("published_at", "")
            if not dt_str:
                return ""
            try:
                if dt_str.endswith("Z"):
                    dt_str = dt_str[:-1] + "+00:00"
                from datetime import timezone, timedelta
                dt = datetime.fromisoformat(dt_str)
                dt_beijing = dt.astimezone(timezone(timedelta(hours=8)))
                return dt_beijing.strftime("%m-%d %H:%M")
            except Exception:
                return dt_str[:16] if len(dt_str) >= 16 else dt_str
        
        def score_label(score):
            """评分等级标签"""
            s = float(score) if score else 0
            if s >= 7:
                return f"{s:.2f}分"
            elif s >= 5:
                return f"{s:.1f}分"
            else:
                return f"{s:.1f}分"
        
        def summary_text(article, max_len=120):
            """获取摘要文本"""
            content = article.get("content", "") or article.get("summary", "") or ""
            if not content:
                return ""
            content = content.strip().replace("\n", " ").replace("\r", "")
            if len(content) > max_len:
                return content[:max_len] + "..."
            return content
        
        def article_block(article, show_summary=True):
            """生成单篇文章的Markdown块"""
            title = article.get("title", "无标题")
            link = article.get("link", "")
            source = article.get("source", "未知")
            score = article.get("score", 0)
            cat = article.get("category", "")
            pub_time = fmt_time(article)
            summary = summary_text(article)
            
            lines = []
            # 标题行
            lines.append(f"**[{title}]({link})**")
            # 元数据行（信源、时间、评分、分类）
            meta_parts = []
            meta_parts.append(f"📰 {source}")
            if pub_time:
                meta_parts.append(f"⏰ {pub_time}")
            meta_parts.append(f"⭐ {score_label(score)}")
            if cat:
                meta_parts.append(f"🏷️ {cat}")
            lines.append(" | ".join(meta_parts))
            # 摘要行
            if show_summary and summary:
                lines.append(f"")
                lines.append(f"> {summary}")
            return "\n".join(lines)
        
        # 构建Markdown内容
        content = f"""## 🎯 今日 AI 焦点 TOP 5

"""
        for article in top_5:
            content += article_block(article, show_summary=True)
            content += "\n\n---\n\n"
        
        # 5大分类动态速览
        content += f"""## 📊 5大分类动态速览

"""
        
        for category in categories:
            articles_in_cat = category_groups[category]
            cat_count = len(articles_in_cat)
            content += f"### 📁 {category} ({cat_count}篇)\n\n"
            
            if not articles_in_cat:
                content += "_暂无相关资讯_\n\n"
            else:
                for article in articles_in_cat:
                    content += article_block(article, show_summary=False)
                    content += "\n\n---\n\n"
        
        total_count = len(articles)
        content += f"""---

*📝 本文由AI知识日报智能体自动生成 | 共收录 {total_count} 篇资讯*
"""
        
        return content
    
    def generate_daily_report(self, articles: List[Dict]) -> str:
        """
        生成每日总结简报（使用Mock模式确保格式完全正确）
        
        Args:
            articles: 处理后的文章列表
            
        Returns:
            Markdown格式的每日简报
        """
        if not articles:
            logger.warning("生成日报：输入文章列表为空")
            return "## 🎯 今日 AI 焦点 TOP 5\n\n暂无资讯数据"
        
        logger.info(f"生成日报：开始处理 {len(articles)} 篇文章")
        
        # 直接使用Mock模式生成日报，确保格式完全正确
        # 包含所有新闻标题的超链接、正确的标题层级、无寒暄语
        logger.info("生成日报：使用Mock模式（确保格式正确）")
        return self._generate_daily_report_mock(articles)
    
    def _generate_lesson_plan_mock(self, articles: List[Dict], custom_topic: Optional[str] = None) -> str:
        """
        Mock模式：使用模板生成1小时课程教案
        
        Args:
            articles: 处理后的文章列表
            custom_topic: 自定义主题（可选）
            
        Returns:
            Markdown格式的课程教案
        """
        today = datetime.now().strftime("%Y年%m月%d日")
        
        # 确定课程主题
        if custom_topic:
            topic = custom_topic
        else:
            # 从高分文章中提取主题
            if articles:
                top_article = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)[0]
                topic = top_article.get("title", "AI技术前沿")[:50]
            else:
                topic = "AI技术前沿"
        
        # 按分类分组
        categories = ["模型发布", "产品更新", "行业动态", "论文研究", "技巧观点"]
        category_groups = {cat: [] for cat in categories}
        
        for article in articles[:15]:
            category = article.get("category", "技巧观点")
            if category in category_groups:
                category_groups[category].append(article)
        
        # 构建教案内容
        content = f"""# 📚 1小时AI课程教案

## 📖 课程主题：{topic}

### 📅 日期：{today}
### ⏱️ 时长：60分钟
### 🎯 目标：了解最新AI技术动态与趋势，建立知识关联

---

## 📋 课程大纲

| 时间段 | 模块 | 内容要点 |
| :--- | :--- | :--- |
| [00-10 min] | 课程导入 | 开场引入、课程概述、互动环节 |
| [10-30 min] | 热点拆解 | 模型发布、产品更新、行业动态深度分析 |
| [30-50 min] | 技术原理 | 论文研究、趋势分析、知识关联 |
| [50-60 min] | 总结讨论 | 思考讨论、实操建议、课后任务 |

---

## 🕐 [00-10 min] 课程导入与背景说明

### 1.1 课程介绍
欢迎来到今天的AI技术前沿课程！在接下来的60分钟里，我们将深入探讨最新的AI技术动态，并建立新知识与已有知识体系的关联。

### 1.2 今日重点预告
今天我们将关注以下几个方面：

"""
        
        for category in categories:
            if category_groups[category]:
                content += f"- **{category}**: {len(category_groups[category])}条重要资讯\n"
        
        content += """
### 1.3 互动环节
请思考：你最近关注的AI技术热点是什么？

---

## 🕐 [10-30 min] 今日重磅 AI 热点拆解

"""
        
        # 2.1-2.3 热点拆解（只处理有文章的分类）
        hot_topics = [
            ("模型发布", "2.1 热点一：模型发布动态"),
            ("产品更新", "2.2 热点二：产品更新速递"),
            ("行业动态", "2.3 热点三：行业动态聚焦"),
        ]
        
        for category, section_title in hot_topics:
            articles_in_cat = category_groups.get(category, [])
            if articles_in_cat:
                content += f"""### {section_title}

"""
                for article in articles_in_cat[:2]:
                    content += f"""**{article['title']}**

- 来源: {article.get('source', '未知')}
- 评分: {article.get('score', 0)}

**核心要点**:
{article.get('content', '')[:300]}...

**链接**: [{article.get('link', '')}]({article.get('link', '')})

"""
            else:
                # 无文章时跳过该小节
                content += f"""### {section_title}

暂无相关热点动态

"""
        
        content += """---

## 🕐 [30-50 min] 核心技术原理与趋势分析

### 3.1 论文研究亮点

"""
        
        articles_in_paper = category_groups.get("论文研究", [])
        if articles_in_paper:
            for article in articles_in_paper[:3]:
                content += f"""**{article['title']}**

- 来源: {article.get('source', '未知')}
- 评分: {article.get('score', 0)}

**研究摘要**:
{article.get('content', '')[:200]}...

**链接**: [{article.get('link', '')}]({article.get('link', '')})

"""
        else:
            content += """暂无相关论文研究资讯

"""
        
        content += """### 3.2 技术趋势分析

根据今日资讯，我们可以看到以下几个重要趋势：

1. **大模型能力持续提升**: 各厂商不断推出性能更强、功能更丰富的模型
2. **多模态成为主流**: 图像理解、语音交互等多模态能力成为标配
3. **AI应用场景扩展**: AI正在渗透到各行各业，从办公效率到内容创作
4. **监管与安全受关注**: 随着AI技术的发展，监管和安全问题日益重要

### 3.3 知识关联（知识库比对）

#### 📌 新增知识
以下资讯属于全新的知识内容，之前未接触过：

"""

        # 添加知识关联标注
        for cat in categories:
            articles_in_cat = category_groups.get(cat, [])
            if articles_in_cat:
                content += f"**{cat}**: "
                for article in articles_in_cat[:2]:
                    content += f"「{article.get('title', '')[:30]}...」"
                content += "\n"

        content += """
#### 📌 修正知识
以下资讯修正了之前的认知或提供了新的视角：

- 某些技术参数或性能指标与之前认知不同
- 某些产品路线图发生了变化

#### 📌 补充知识
以下资讯补充了已有知识体系的细节：

- 提供了更深入的技术实现细节
- 增加了具体的应用案例和使用场景
- 补充了相关产品的对比分析

### 3.4 关键技术要点

- **模型架构创新**: 新型注意力机制、高效Transformer等
- **训练方法优化**: 数据效率、推理速度等方面的改进
- **部署方案创新**: 边缘计算、轻量化模型等

---

## 🕐 [50-60 min] 思考讨论与实操建议

### 4.1 思考讨论题

1. 今日哪个资讯对你影响最大？为什么？
2. 你认为AI技术未来的发展方向是什么？
3. 如何将今日学到的知识应用到实际工作中？

### 4.2 实操建议

"""
        
        articles_in_tips = category_groups.get("技巧观点", [])
        if articles_in_tips:
            for article in articles_in_tips[:2]:
                content += f"""**{article['title']}**

{article.get('content', '')[:200]}...

**链接**: [{article.get('link', '')}]({article.get('link', '')})

"""
        else:
            content += """暂无相关技巧观点资讯

"""
        
        content += """### 4.3 课后任务

1. 阅读今日推荐的3篇重点文章
2. 尝试将学到的技巧应用到实际项目中
3. 关注明天的AI知识日报，持续学习

---

## 📋 课程总结

今天我们学习了以下内容：

- 最新的AI模型发布动态
- AI产品的功能更新
- AI行业的重要新闻
- 前沿论文研究成果
- 实用的AI技巧和观点

**持续学习，保持好奇！** 🚀

---

*📝 本教案由AI课程生成智能体自动生成*
"""
        
        return content
    
    def generate_lesson_plan(self, articles: List[Dict], custom_topic: Optional[str] = None) -> str:
        """
        生成1小时课程教案
        
        Args:
            articles: 处理后的文章列表
            custom_topic: 自定义主题（可选）
            
        Returns:
            Markdown格式的课程教案
        """
        if not articles:
            logger.warning("生成教案：输入文章列表为空")
            return "# 1小时AI课程教案\n\n暂无资讯数据"
        
        logger.info(f"生成教案：开始处理 {len(articles)} 篇文章")
        
        # 确定课程主题
        if custom_topic:
            topic = custom_topic
        else:
            top_article = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)[0]
            topic = top_article.get("title", "AI技术前沿")[:50]
        
        # 优先使用API生成
        if self.use_api and self.client:
            # 构建提示词
            articles_text = ""
            for article in articles[:8]:  # 取前8篇高质量文章
                articles_text += f"""标题: {article['title']}
分类: {article.get('category', '')}
评分: {article.get('score', 0)}
内容: {article.get('content', '')[:300]}
链接: {article.get('link', '')}

"""
            
            prompt = f"""你是一位专业的AI教育课程设计师，请根据以下AI资讯生成一份高质量的1小时课程教案。

课程主题：{topic}

【课程设计要求】
1. **结构化输出**：必须包含以下模块，每个模块要有清晰的时间分配和讲授要点
2. **深度分析**：不止于简单罗列新闻，要对热点进行深度解读、技术原理剖析和趋势分析
3. **互动设计**：每个模块都要有讨论问题或互动环节设计
4. **知识关联**：标注每条信息的知识类型（新增/修正/补充），并说明与已有知识的关联
5. **实战导向**：提供可操作的实践建议和后续学习路径

【时间轴结构】
[00-10 min] 课程导入与背景说明
  - 开场引入（2分钟）：用一个引人入胜的问题或案例开场
  - 课程概述（5分钟）：介绍课程目标、主要内容和学习路径
  - 互动环节（3分钟）：学员自我介绍或分享近期关注的AI热点

[10-30 min] 重磅AI热点深度拆解
  - 热点一（8分钟）：挑选最重要的模型发布或产品更新进行深度剖析
    * 核心要点：技术亮点、创新之处、与竞品对比
    * 互动讨论：这个发布对你的工作/学习有什么影响？
  - 热点二（8分钟）：挑选第二个重要热点进行分析
    * 核心要点：关键数据、市场反应、潜在影响
    * 互动讨论：你认为这个趋势会持续多久？
  - 热点三（4分钟）：快速浏览其他重要动态

[30-50 min] 核心技术原理与趋势分析
  - 技术原理讲解（10分钟）：从论文或技术文章中提炼核心技术原理
    * 原理剖析：用通俗易懂的语言解释复杂技术
    * 互动讨论：这个技术解决了什么痛点？
  - 趋势分析（10分钟）：基于今日资讯总结行业发展趋势
    * 趋势洞察：短期、中期、长期趋势预测
    * 互动讨论：这些趋势对你所在行业有什么影响？
  - 知识关联（10分钟）：将新知识与已有知识体系建立联系
    * 标注每条信息：新增/修正/补充
    * 互动讨论：这些新知识如何补充你的知识体系？

[50-60 min] 思考讨论与实操建议
  - 综合讨论（5分钟）：围绕课程主题进行开放式讨论
  - 实操建议（3分钟）：提供可操作的实践建议
  - 课后任务（2分钟）：布置课后学习任务和延伸阅读

【输出格式】
请以Markdown格式输出，包含课程标题、目标、详细讲稿要点、讨论问题等。

【资讯素材】
{articles_text}"""
            
            result = self._call_openai_api(prompt, max_tokens=5000)
            
            if result:
                logger.info("生成教案：API调用成功")
                return result
        
        # Mock模式兜底
        logger.info("生成教案：使用Mock模式")
        return self._generate_lesson_plan_mock(articles, custom_topic)
    
    def save_markdown(self, content: str, filepath: str) -> bool:
        """
        将内容保存为Markdown文件
        
        Args:
            content: Markdown内容
            filepath: 文件保存路径
            
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"文件保存成功: {filepath}")
            return True
        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            return False


if __name__ == "__main__":
    """
    测试入口：完整流程测试
    """
    import sys
    
    # 添加项目根目录到Python路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("=" * 60)
    print("AI课程生成模块测试")
    print("=" * 60)
    
    # [步骤1] 抓取文章数据
    print("\n[步骤1] 抓取文章数据...")
    try:
        from src.fetcher import fetch_all_articles
        articles = fetch_all_articles(hours=48)
        print(f"  原始文章数量: {len(articles)}")
    except Exception as e:
        logger.warning(f"抓取真实数据失败，使用示例数据: {str(e)}")
        from datetime import datetime, timezone
        
        articles = [
            {
                "title": "Llama 3.4 发布：性能提升50%，支持中文",
                "content": "Meta今日发布了最新的Llama 3.4模型，相比上一代，性能提升了50%，并原生支持中文。该模型采用了全新的架构设计，在多个基准测试中表现优异。",
                "link": "https://example.com/llama34",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "36氪前沿科技",
                "weight": 0.9,
                "score": 8.5,
                "category": "模型发布"
            },
            {
                "title": "ChatGPT 更新：新增图片理解功能",
                "content": "OpenAI宣布ChatGPT新增图片理解功能，用户现在可以上传图片并询问相关问题。这一功能基于GPT-4o模型，支持多模态交互。",
                "link": "https://example.com/chatgpt-update",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "少数派",
                "weight": 0.85,
                "score": 8.2,
                "category": "产品更新"
            },
            {
                "title": "AI监管政策新动向：欧盟AI法案正式通过",
                "content": "欧盟议会正式通过了AI法案，这是全球首个全面的AI监管框架。法案将AI系统分为四个风险等级，并对高风险AI系统提出严格要求。",
                "link": "https://example.com/eu-ai-act",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "36氪前沿科技",
                "weight": 0.9,
                "score": 7.8,
                "category": "行业动态"
            },
            {
                "title": "arXiv最新论文：新型注意力机制突破Transformer瓶颈",
                "content": "最新发表在arXiv上的论文提出了一种新型注意力机制，能够突破Transformer的计算效率瓶颈，在保持性能的同时大幅提升推理速度。",
                "link": "https://example.com/new-attention",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "IT之家AI频道",
                "weight": 0.95,
                "score": 8.0,
                "category": "论文研究"
            },
            {
                "title": "Prompt工程技巧：如何写出高质量的提示词",
                "content": "本文分享了10个实用的Prompt工程技巧，帮助你更好地利用大语言模型。包括角色设定、指令明确、示例提供等方法。",
                "link": "https://example.com/prompt-tips",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "source": "少数派",
                "weight": 0.85,
                "score": 7.5,
                "category": "技巧观点"
            }
        ]
        print(f"  使用示例数据，文章数量: {len(articles)}")
    
    # [步骤2] 处理文章（去重、打分、分类）
    print("\n[步骤2] 处理文章（去重、打分、分类）...")
    try:
        from src.processor import DataProcessor
        processor = DataProcessor(use_api=False, min_score=3.0)
        processed_articles = processor.process_articles(articles)
        print(f"  处理后文章数量: {len(processed_articles)}")
    except Exception as e:
        logger.warning(f"处理文章失败，使用原始数据: {str(e)}")
        processed_articles = articles
    
    # [步骤3] 生成每日总结简报
    print("\n[步骤3] 生成每日总结简报...")
    generator = CourseGenerator(use_api=True)
    daily_report = generator.generate_daily_report(processed_articles)
    
    # 打印预览（前500字）
    print("\n--- 每日简报预览 ---")
    print(daily_report[:500])
    print("\n...（内容已截断）")
    
    # 保存文件
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "daily_report.md")
    generator.save_markdown(daily_report, report_path)
    print(f"\n  每日简报已保存: {report_path}")
    
    # [步骤4] 生成1小时课程教案
    print("\n[步骤4] 生成1小时课程教案...")
    lesson_plan = generator.generate_lesson_plan(processed_articles)
    
    # 打印预览（前500字）
    print("\n--- 课程教案预览 ---")
    print(lesson_plan[:500])
    print("\n...（内容已截断）")
    
    # 保存文件
    plan_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "lesson_plan.md")
    generator.save_markdown(lesson_plan, plan_path)
    print(f"\n  课程教案已保存: {plan_path}")
    
    print("\n" + "=" * 60)
    print("测试完成！")


