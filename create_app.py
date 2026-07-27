import os

content = '''import os
import sys
import json
import logging
import streamlit as st
from datetime import datetime, timedelta, timezone

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入日报生成函数
from scheduler import generate_daily_report, get_daily_cache_path, save_daily_report_to_cache

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title="AIBOX - AI日报智能体",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS - 全局样式
st.markdown("""
<style>
    /* 全局样式重置 */
    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }
    
    /* 字体统一 */
    html, body, [class*="st-"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* 隐藏Streamlit默认侧边栏 */
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* 自定义侧边栏样式 */
    .sidebar-container {
        position: fixed;
        left: 0;
        top: 0;
        width: 220px;
        height: 100vh;
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        color: #ffffff;
        padding: 24px 16px;
        display: flex;
        flex-direction: column;
        z-index: 1000;
        overflow-y: auto;
    }
    
    .sidebar-logo {
        text-align: center;
        margin-bottom: 32px;
        padding-bottom: 20px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .sidebar-logo h1 {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: 2px;
        margin: 0;
    }
    
    .sidebar-logo .logo-highlight {
        color: #60a5fa;
    }
    
    .sidebar-nav {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .nav-item {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 15px;
        font-weight: 500;
        color: #9ca3af;
        text-decoration: none;
        background: transparent;
        border: none;
        width: 100%;
        text-align: left;
    }
    
    .nav-item:hover {
        background: rgba(59, 130, 246, 0.15);
        color: #ffffff;
    }
    
    .nav-item.active {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(96, 165, 250, 0.2));
        color: #ffffff;
        border-left: 3px solid #60a5fa;
    }
    
    .nav-item-icon {
        margin-right: 10px;
        font-size: 18px;
    }
    
    .sidebar-footer {
        padding-top: 20px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        font-size: 12px;
        color: #6b7280;
    }
    
    /* 主内容区域 */
    .main-content {
        margin-left: 220px;
        min-height: 100vh;
        background: #0f172a;
        padding: 24px;
        position: relative;
        z-index: 1;
    }
    
    /* 卡片样式 */
    .article-card {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
        cursor: pointer;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .article-card:hover {
        background: rgba(51, 65, 85, 0.9);
        border-color: rgba(96, 165, 250, 0.3);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .article-title {
        font-size: 14px;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 8px;
        line-height: 1.5;
    }
    
    .article-title a {
        color: inherit;
        text-decoration: none;
    }
    
    .article-title a:hover {
        color: #60a5fa;
        text-decoration: underline;
    }
    
    .article-meta {
        font-size: 12px;
        color: #6b7280;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    
    .article-summary {
        font-size: 13px;
        color: #9ca3af;
        line-height: 1.6;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    /* 时间轴样式 */
    .timeline-container {
        position: relative;
        padding-left: 24px;
    }
    
    .timeline-container::before {
        content: '';
        position: absolute;
        left: 8px;
        top: 0;
        bottom: 0;
        width: 2px;
        background: linear-gradient(180deg, #3b82f6 0%, #6366f1 100%);
        border-radius: 1px;
    }
    
    .timeline-item {
        position: relative;
        padding-bottom: 16px;
    }
    
    .timeline-item::before {
        content: '';
        position: absolute;
        left: -20px;
        top: 6px;
        width: 10px;
        height: 10px;
        background: #3b82f6;
        border-radius: 50%;
        border: 2px solid #1e293b;
    }
    
    .timeline-time {
        font-size: 11px;
        color: #60a5fa;
        font-weight: 600;
        margin-bottom: 4px;
    }
    
    /* 搜索框样式 */
    .search-box {
        width: 100%;
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(30, 41, 59, 0.5);
        color: #ffffff;
        font-size: 13px;
        outline: none;
        transition: all 0.3s ease;
    }
    
    .search-box:focus {
        border-color: #3b82f6;
        background: rgba(30, 41, 59, 0.8);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* 分数标签 */
    .score-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
        color: white;
    }
    .score-high { background-color: #10b981; }
    .score-medium { background-color: #f59e0b; color: #1f2937; }
    .score-low { background-color: #ef4444; }
    
    /* 分类标签 */
    .category-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 0.75em;
        font-weight: 600;
    }
    .category-model { background-color: rgba(239, 68, 68, 0.15); color: #f87171; }
    .category-product { background-color: rgba(16, 185, 129, 0.15); color: #34d399; }
    .category-industry { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; }
    .category-paper { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; }
    .category-tips { background-color: rgba(148, 163, 184, 0.15); color: #9ca3af; }
    .category-all { background-color: rgba(139, 92, 246, 0.15); color: #a78bfa; }
    
    /* 教案预览区字体样式 */
    .lesson-preview h1 { font-size: 22px !important; font-weight: bold; margin-bottom: 12px; }
    .lesson-preview h2 { font-size: 18px !important; font-weight: 600; margin-bottom: 10px; }
    .lesson-preview h3 { font-size: 15px !important; font-weight: 600; margin-bottom: 8px; }
    .lesson-preview p, .lesson-preview li, .lesson-preview span, .lesson-preview strong, .lesson-preview em { font-size: 14px !important; line-height: 1.6; }
    .lesson-preview ul, .lesson-preview ol { padding-left: 24px; margin-bottom: 12px; }
    .lesson-preview li { margin-bottom: 6px; }
    .lesson-preview hr { margin: 16px 0; border-color: rgba(255, 255, 255, 0.1); }
    
    /* 日报内容区 */
    .daily-report-content a { color: inherit; text-decoration: none; }
    .daily-report-content a:hover { color: #3b82f6; text-decoration: underline; }
    .daily-report-content h2 { font-size: 28px !important; font-weight: 700; margin-bottom: 20px; color: #ffffff; }
    
    /* 文件卡片样式 */
    .file-card {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 12px;
        padding: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: all 0.3s ease;
    }
    
    .file-card:hover { border-color: rgba(96, 165, 250, 0.3); }
    
    .file-icon { font-size: 32px; margin-bottom: 8px; }
    .file-name { font-size: 14px; font-weight: 600; color: #f1f5f9; margin-bottom: 4px; }
    .file-meta { font-size: 12px; color: #6b7280; margin-bottom: 12px; }
    
    .file-actions { display: flex; gap: 8px; }
    
    .btn {
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .btn-primary { background: #3b82f6; color: white; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: rgba(255, 255, 255, 0.1); color: #e5e7eb; }
    .btn-secondary:hover { background: rgba(255, 255, 255, 0.15); }
    .btn-danger { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
    .btn-danger:hover { background: rgba(239, 68, 68, 0.3); }
    
    /* 滚动条样式 */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(30, 41, 59, 0.5); border-radius: 3px; }
    ::-webkit-scrollbar-thumb { background: rgba(100, 116, 139, 0.5); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(148, 163, 184, 0.6); }
    
    /* 响应式布局 */
    @media (max-width: 768px) {
        .sidebar-container { width: 180px; }
        .main-content { margin-left: 180px; }
    }
</style>
""", unsafe_allow_html=True)

# 常量定义
CATEGORIES = ["全部讯息", "模型发布", "产品更新", "行业动态", "论文研究", "技巧观点"]
CATEGORY_COLORS = {
    "全部讯息": "category-all",
    "模型发布": "category-model",
    "产品更新": "category-product",
    "行业动态": "category-industry",
    "论文研究": "category-paper",
    "技巧观点": "category-tips"
}
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# 初始化session_state
def init_session_state():
    if "current_page" not in st.session_state:
        st.session_state.current_page = "每日动态"
    if "articles" not in st.session_state:
        st.session_state.articles = []
    if "daily_report" not in st.session_state:
        st.session_state.daily_report = ""
    if "lesson_plans" not in st.session_state:
        st.session_state.lesson_plans = []
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    if "selected_articles" not in st.session_state:
        st.session_state.selected_articles = []
    if "api_mode" not in st.session_state:
        st.session_state.api_mode = False
    if "preloading" not in st.session_state:
        st.session_state.preloading = False
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "全部讯息"

init_session_state()

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
if api_key:
    st.session_state.api_mode = True

def load_daily_report_from_cache(date_str):
    cache_path = get_daily_cache_path(date_str)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.warning(f"加载缓存失败: {str(e)}")
    return None

def convert_to_beijing_time(published_at_str):
    try:
        if published_at_str.endswith("Z"):
            published_at_str = published_at_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(published_at_str)
        beijing_tz = timezone(timedelta(hours=8))
        return dt.astimezone(beijing_tz)
    except Exception as e:
        logger.warning(f"时间转换失败: {str(e)}")
        return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

def format_time(dt):
    return dt.strftime("%m-%d %H:%M")

def get_articles_by_category(articles, category):
    if category == "全部讯息":
        return articles
    return [a for a in articles if a.get("category") == category]

def filter_articles_by_keyword(articles, keyword):
    if not keyword or keyword.strip() == "":
        return articles
    keyword = keyword.lower().strip()
    return [a for a in articles if keyword in a.get("title", "").lower() or keyword in a.get("content", "").lower()]

def prefetch_all_data():
    if st.session_state.data_loaded or st.session_state.preloading:
        return
    st.session_state.preloading = True
    try:
        from src.fetcher import fetch_all_articles
        from src.processor import DataProcessor
        logger.info("开始预抓取历史数据...")
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=7)
        articles = fetch_all_articles(start_date=start_date, end_date=end_date)
        if articles:
            processor = DataProcessor(use_api=False)
            processed_articles = processor.process_articles(articles)
            st.session_state.articles = processed_articles
            st.session_state.data_loaded = True
            try:
                from src.vector_db import VectorDB
                vdb = VectorDB()
                vdb.add_articles(processed_articles)
                st.session_state.vector_db = vdb
            except Exception as e:
                logger.warning(f"更新向量库失败: {str(e)}")
            logger.info(f"预抓取完成，共 {len(processed_articles)} 篇文章")
        else:
            logger.warning("预抓取未获取到任何文章")
    except Exception as e:
        logger.error(f"预抓取失败: {str(e)}")
        st.session_state.articles = generate_mock_articles()
        st.session_state.data_loaded = True
    st.session_state.preloading = False

def generate_mock_articles():
    now = datetime.now(timezone.utc)
    return [
        {"title": "Llama 3.4 发布：性能提升50%，支持中文", "content": "Meta今日发布了最新的Llama 3.4模型，相比上一代，性能提升了50%，并原生支持中文。", "link": "https://example.com/llama34", "published_at": (now - timedelta(hours=2)).isoformat(), "source": "机器之心", "category": "模型发布", "score": 9.2},
        {"title": "ChatGPT 更新：新增图片理解功能", "content": "OpenAI宣布ChatGPT新增图片理解功能，用户现在可以上传图片并询问相关问题。", "link": "https://example.com/chatgpt-update", "published_at": (now - timedelta(hours=5)).isoformat(), "source": "AI前线", "category": "产品更新", "score": 8.8},
        {"title": "AI监管政策新动向：欧盟AI法案正式通过", "content": "欧盟议会正式通过了AI法案，这是全球首个全面的AI监管框架。", "link": "https://example.com/eu-ai-act", "published_at": (now - timedelta(hours=8)).isoformat(), "source": "36氪前沿科技", "category": "行业动态", "score": 8.5},
        {"title": "arXiv最新论文：新型注意力机制突破Transformer瓶颈", "content": "最新发表在arXiv上的论文提出了一种新型注意力机制。", "link": "https://example.com/new-attention", "published_at": (now - timedelta(hours=12)).isoformat(), "source": "PaperWeekly", "category": "论文研究", "score": 8.9},
        {"title": "Prompt工程技巧：如何写出高质量的提示词", "content": "本文分享了10个实用的Prompt工程技巧。", "link": "https://example.com/prompt-tips", "published_at": (now - timedelta(hours=15)).isoformat(), "source": "少数派", "category": "技巧观点", "score": 7.8},
        {"title": "Qwen 2.5 开源：更强的中文理解能力", "content": "阿里云开源了Qwen 2.5模型，在中文任务上表现优异。", "link": "https://example.com/qwen25", "published_at": (now - timedelta(hours=20)).isoformat(), "source": "开源中国", "category": "模型发布", "score": 8.6},
        {"title": "Midjourney v6 上线：更逼真的图像生成", "content": "Midjourney发布v6版本，图像生成质量大幅提升。", "link": "https://example.com/midjourney-v6", "published_at": (now - timedelta(hours=22)).isoformat(), "source": "IT之家AI频道", "category": "产品更新", "score": 8.3},
        {"title": "AI公司融资热潮：上半年融资额突破100亿美元", "content": "据统计，今年上半年AI领域融资额超过100亿美元。", "link": "https://example.com/ai-funding", "published_at": (now - timedelta(hours=26)).isoformat(), "source": "TechCrunch", "category": "行业动态", "score": 8.0},
        {"title": "新研究表明：大模型可以学习因果推理", "content": "最新研究发现，大语言模型在特定条件下可以学习因果推理。", "link": "https://example.com/causal-reasoning", "published_at": (now - timedelta(hours=30)).isoformat(), "source": "MIT Technology Review", "category": "论文研究", "score": 9.1},
        {"title": "AI工具评测：10款AI写作助手对比", "content": "本文对比评测了10款主流的AI写作助手工具。", "link": "https://example.com/ai-writing-review", "published_at": (now - timedelta(hours=35)).isoformat(), "source": "Engadget", "category": "技巧观点", "score": 7.5},
        {"title": "Gemini 1.5 Flash 发布：更快更经济的推理", "content": "Google发布了Gemini 1.5 Flash模型。", "link": "https://example.com/gemini-flash", "published_at": (now - timedelta(hours=40)).isoformat(), "source": "The Verge", "category": "模型发布", "score": 8.4},
        {"title": "GitHub Copilot 更新：支持代码解释", "content": "GitHub Copilot新增代码解释功能。", "link": "https://example.com/copilot-update", "published_at": (now - timedelta(hours=45)).isoformat(), "source": "Hacker News", "category": "产品更新", "score": 8.1}
    ]

def render_sidebar():
    st.markdown("""
<div class="sidebar-container">
    <div class="sidebar-logo">
        <h1><span class="logo-highlight">AI</span>BOX</h1>
    </div>
    <div class="sidebar-nav">
""", unsafe_allow_html=True)
    
    nav_items = [
        ("每日动态", "📰"),
        ("AI日报", "📊"),
        ("教案生成", "📚"),
        ("文件管理", "📁")
    ]
    
    for page_name, icon in nav_items:
        is_active = st.session_state.current_page == page_name
        btn_key = f"nav_btn_{page_name}"
        
        if st.button(f"{icon} {page_name}", key=btn_key, use_container_width=True, type="primary" if is_active else "secondary"):
            if not is_active:
                st.session_state.current_page = page_name
                st.session_state.selected_articles = []
                st.rerun()
    
    st.markdown("""
    </div>
    <div class="sidebar-footer">
        <p>📅 {current_date}</p>
        <p>AI知识日报智能体</p>
    </div>
</div>
""".format(current_date=datetime.now().strftime("%Y年%m月%d日")), unsafe_allow_html=True)

def render_daily_dynamic():
    st.title("📰 每日动态")
    st.markdown("---")
    
    # 标签栏切换
    col_tabs = st.columns(len(CATEGORIES))
    for idx, category in enumerate(CATEGORIES):
        with col_tabs[idx]:
            btn_key = f"tab_{category}"
            if st.button(category, key=btn_key, use_container_width=True):
                st.session_state.selected_category = category
    
    # 当前选中分类的内容
    current_category = st.session_state.selected_category
    keyword = st.text_input("🔍 搜索关键词", placeholder=f"搜索{current_category}相关资讯...", key=f"search_{current_category}")
    
    # 获取当前分类的文章
    category_articles = get_articles_by_category(st.session_state.articles, current_category)
    
    # 过滤今日文章
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_articles = [a for a in category_articles if datetime.fromisoformat(a.get("published_at", "").replace("Z", "+00:00")) >= today_start]
    
    # 按关键词过滤
    if keyword:
        today_articles = filter_articles_by_keyword(today_articles, keyword)
    
    # 按时间倒序排列
    today_articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    
    # 显示内容
    if today_articles:
        timeline_html = ['<div class="timeline-container">']
        for article in today_articles[:20]:
            dt_beijing = convert_to_beijing_time(article.get("published_at", ""))
            time_str = format_time(dt_beijing)
            title = article.get("title", "")
            content = article.get("content", "")[:100] + "..." if len(article.get("content", "")) > 100 else article.get("content", "")
            source = article.get("source", "")
            link = article.get("link", "")
            timeline_html.append(f"""
<div class="timeline-item">
    <div class="timeline-time">{time_str}</div>
    <div class="article-card" onclick="window.open('{link}', '_blank')">
        <div class="article-title"><a href="{link}" target="_blank">{title}</a></div>
        <div class="article-meta">
            <span>📰 {source}</span>
            <span class="category-badge {CATEGORY_COLORS.get(article.get('category', ''), '')}">{article.get('category', '')}</span>
        </div>
        <div class="article-summary">{content}</div>
    </div>
</div>
""")
        timeline_html.append("</div>")
        st.markdown("".join(timeline_html), unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="text-align: center; padding: 40px; color: #6b7280;">
    <div style="font-size: 48px; margin-bottom: 12px;">📭</div>
    <div style="font-size: 14px;">暂无相关资讯</div>
</div>
""", unsafe_allow_html=True)

def render_daily_report():
    st.title("📊 AI日报")
    st.markdown("---")
    today = datetime.now()
    weekday_map = {0: "星期一", 1: "星期二", 2: "星期三", 3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日"}
    st.markdown(f"""
<div class="daily-report-header">
    <div class="daily-report-title">
        <span class="logo-part">AIBOX</span>
        <span class="highlight-part"> 日报</span>
    </div>
    <div class="daily-report-subtitle">
        二○二六年{today.month}月{today.day}日 · {weekday_map[today.weekday()]} · DAILY · 每早六时
    </div>
</div>
""", unsafe_allow_html=True)
    date_str = today.strftime("%Y%m%d")
    cached_data = load_daily_report_from_cache(date_str)
    if cached_data:
        st.session_state.daily_report = cached_data["report"]
        if not st.session_state.data_loaded:
            st.session_state.articles = cached_data["articles"]
            st.session_state.data_loaded = True
    else:
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y%m%d")
        yesterday_cache = load_daily_report_from_cache(yesterday_str)
        if yesterday_cache:
            st.session_state.daily_report = yesterday_cache["report"]
            if not st.session_state.data_loaded:
                st.session_state.articles = yesterday_cache["articles"]
                st.session_state.data_loaded = True
            st.warning("⚠️ 今日日报尚未生成（定时任务每天6点自动生成），当前显示昨日日报")
    if st.session_state.daily_report:
        st.download_button(label="📥 下载日报", data=st.session_state.daily_report, file_name=f"daily_report_{date_str}.md", mime="text/markdown", use_container_width=True)
        st.markdown(st.session_state.daily_report)
    else:
        st.markdown("""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px; text-align: center;">
    <div style="font-size: 64px; margin-bottom: 20px;">⏰</div>
    <h3 style="margin-bottom: 10px;">今日日报尚未生成</h3>
    <p style="color: #666; font-size: 14px;">日报将于每天早上6点自动生成，内容为前一天00:00-24:00的新闻汇总</p>
</div>
""", unsafe_allow_html=True)

def render_lesson_plan():
    st.title("📚 教案生成")
    st.markdown("---")
    if not st.session_state.data_loaded:
        st.warning("⚠️ 数据正在加载中，请稍候...")
        return
    st.subheader("时间筛选")
    col_date_start, col_date_end = st.columns(2)
    with col_date_start:
        start_date = st.date_input("开始日期", value=datetime.now().date() - timedelta(days=2), help="支持近7天任意时段筛选资讯")
    with col_date_end:
        end_date = st.date_input("结束日期", value=datetime.now().date())
    keyword_filter = st.text_input("🔍 关键词过滤", placeholder="输入关键词（如：智能体、大模型、AI等）")
    now = datetime.now(timezone.utc)
    start_time = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_time = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
    filtered_articles = [a for a in st.session_state.articles if start_time <= datetime.fromisoformat(a.get("published_at", "").replace("Z", "+00:00")) <= end_time]
    if keyword_filter:
        filtered_articles = filter_articles_by_keyword(filtered_articles, keyword_filter)
    st.subheader("文章列表")
    categories = ["模型发布", "产品更新", "行业动态", "论文研究", "技巧观点"]
    tabs = st.tabs(categories)
    for idx, category in enumerate(categories):
        with tabs[idx]:
            category_articles = [a for a in filtered_articles if a.get("category") == category]
            category_articles.sort(key=lambda x: x.get("score", 0), reverse=True)
            if category_articles:
                for i, article in enumerate(category_articles):
                    with st.container():
                        col_check, col_content = st.columns([1, 11])
                        with col_check:
                            checked = st.checkbox("", value=article in st.session_state.selected_articles, key=f"lesson_check_{i}")
                            if checked and article not in st.session_state.selected_articles:
                                st.session_state.selected_articles.append(article)
                            elif not checked and article in st.session_state.selected_articles:
                                st.session_state.selected_articles.remove(article)
                        with col_content:
                            st.markdown(f"""
<div class="article-card" style="cursor: default;">
    <div class="article-title"><a href="{article.get('link', '')}" target="_blank">{article.get('title', '')}</a></div>
    <div class="article-meta">
        <span>📰 {article.get('source', '')}</span>
        <span class="category-badge {CATEGORY_COLORS.get(article.get('category', ''), '')}">{article.get('category', '')}</span>
        <span class="score-badge {'score-high' if article.get('score', 0) >= 7 else 'score-medium' if article.get('score', 0) >= 5 else 'score-low'}">{article.get('score', 0)}分</span>
    </div>
    <div class="article-summary">{article.get('content', '')[:100]}...</div>
</div>
""", unsafe_allow_html=True)
            else:
                st.info(f"暂无{category}相关文章")
    st.markdown("---")
    col_selected, col_generate = st.columns([2, 3])
    with col_selected:
        st.markdown(f'<div style="display: flex; align-items: center; height: 100%;"><span style="font-size: 16px; font-weight: 600;">✅ 已选中 <b>{len(st.session_state.selected_articles)}</b> 篇文章</span></div>', unsafe_allow_html=True)
    with col_generate:
        generate_btn = st.button("🚀 生成教案（每篇文章独立生成）", type="primary", use_container_width=True, disabled=len(st.session_state.selected_articles) == 0)
    if generate_btn:
        with st.spinner("正在生成教案..."):
            try:
                from src.generator import CourseGenerator
                generator = CourseGenerator(use_api=False)
                lesson_plans = []
                for article in st.session_state.selected_articles:
                    topic = article.get("title", "AI技术前沿")[:50]
                    plan = generator.generate_lesson_plan([article], topic)
                    lesson_plans.append({"article_title": article.get("title", ""), "content": plan, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                st.session_state.lesson_plans = lesson_plans
                st.success(f"🎉 成功生成 {len(lesson_plans)} 份教案！")
                os.makedirs(os.path.join(OUTPUT_DIR, "lesson_plans"), exist_ok=True)
                for plan in lesson_plans:
                    safe_title = plan["article_title"].replace("/", "-").replace("\\\\", "-")[:50]
                    filepath = os.path.join(OUTPUT_DIR, "lesson_plans", f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
                    generator.save_markdown(plan["content"], filepath)
            except Exception as e:
                st.error(f"生成教案失败: {str(e)}")
    if st.session_state.lesson_plans:
        st.subheader("📝 教案预览")
        for i, plan in enumerate(st.session_state.lesson_plans):
            with st.expander(f"教案 {i+1}: {plan['article_title'][:50]}..."):
                st.markdown(f'<div class="lesson-preview">{plan["content"]}</div>', unsafe_allow_html=True)
                st.download_button(label=f"📥 下载教案 {i+1}", data=plan["content"], file_name=f"lesson_plan_{i+1}_{datetime.now().strftime('%Y%m%d')}.md", mime="text/markdown", key=f"download_lesson_{i}")

def render_file_manager():
    st.title("📁 文件管理")
    st.markdown("---")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "daily_reports"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "lesson_plans"), exist_ok=True)
    
    # 处理删除请求
    if "delete_file" in st.session_state:
        delete_path = st.session_state.delete_file
        if os.path.exists(delete_path):
            os.remove(delete_path)
            st.success(f"已删除文件: {os.path.basename(delete_path)}")
        else:
            st.error("文件不存在")
        del st.session_state.delete_file
    
    col_report, col_lesson = st.columns(2)
    with col_report:
        st.subheader("📋 日报存储区")
        report_dir = os.path.join(OUTPUT_DIR, "daily_reports")
        for filename in os.listdir(CACHE_DIR):
            if filename.startswith("report_") and filename.endswith(".json"):
                date_str = filename.replace("report_", "").replace(".json", "")
                cached_data = load_daily_report_from_cache(date_str)
                if cached_data and "report" in cached_data:
                    output_path = os.path.join(report_dir, f"daily_report_{date_str}.md")
                    if not os.path.exists(output_path):
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(cached_data["report"])
        report_files = sorted([f for f in os.listdir(report_dir) if f.endswith(".md")], reverse=True)
        if report_files:
            for filename in report_files[:20]:
                filepath = os.path.join(report_dir, filename)
                file_size = os.path.getsize(filepath) / 1024
                modified_time = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M")
                col_file, col_actions = st.columns([3, 2])
                with col_file:
                    st.markdown(f"""
<div class="file-card">
    <div class="file-icon">📄</div>
    <div class="file-name">{filename}</div>
    <div class="file-meta"><span>📅 {modified_time}</span><span>📦 {file_size:.2f} KB</span></div>
</div>
""", unsafe_allow_html=True)
                with col_actions:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    st.download_button(label="📥 下载", data=content, file_name=filename, mime="text/markdown", key=f"report_download_{filename}")
        else:
            st.markdown("""
<div style="text-align: center; padding: 40px; color: #6b7280;">
    <div style="font-size: 48px; margin-bottom: 12px;">📭</div>
    <div style="font-size: 14px;">暂无日报文件</div>
    <div style="font-size: 12px; margin-top: 4px;">日报将在每天6点自动生成并保存</div>
</div>
""", unsafe_allow_html=True)
    with col_lesson:
        st.subheader("📚 教案存储区")
        lesson_dir = os.path.join(OUTPUT_DIR, "lesson_plans")
        lesson_files = sorted([f for f in os.listdir(lesson_dir) if f.endswith(".md")], reverse=True)
        if lesson_files:
            for filename in lesson_files[:20]:
                filepath = os.path.join(lesson_dir, filename)
                file_size = os.path.getsize(filepath) / 1024
                modified_time = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M")
                col_file, col_actions = st.columns([3, 2])
                with col_file:
                    st.markdown(f"""
<div class="file-card">
    <div class="file-icon">📝</div>
    <div class="file-name">{filename}</div>
    <div class="file-meta"><span>📅 {modified_time}</span><span>📦 {file_size:.2f} KB</span></div>
</div>
""", unsafe_allow_html=True)
                with col_actions:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    st.download_button(label="📥 下载", data=content, file_name=filename, mime="text/markdown", key=f"lesson_download_{filename}")
                    if st.button("🗑️ 删除", key=f"lesson_delete_{filename}"):
                        st.session_state.delete_file = filepath
                        st.rerun()
        else:
            st.markdown("""
<div style="text-align: center; padding: 40px; color: #6b7280;">
    <div style="font-size: 48px; margin-bottom: 12px;">📭</div>
    <div style="font-size: 14px;">暂无教案文件</div>
    <div style="font-size: 12px; margin-top: 4px;">生成教案后将自动保存到此处</div>
</div>
""", unsafe_allow_html=True)

def main():
    prefetch_all_data()
    render_sidebar()
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    if st.session_state.preloading:
        st.markdown("""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh;">
    <div style="font-size: 48px; margin-bottom: 16px;">🔄</div>
    <div style="font-size: 18px; font-weight: 600; color: #60a5fa;">正在加载数据，请稍候...</div>
    <div style="width: 200px; height: 4px; background: rgba(59, 130, 246, 0.2); border-radius: 2px; margin-top: 16px; overflow: hidden;">
        <div style="width: 50%; height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa); animation: loading 1.5s infinite;"></div>
    </div>
</div>
<style>@keyframes loading { 0% { transform: translateX(-100%); } 100% { transform: translateX(200%); } }</style>
""", unsafe_allow_html=True)
    else:
        if st.session_state.current_page == "每日动态":
            render_daily_dynamic()
        elif st.session_state.current_page == "AI日报":
            render_daily_report()
        elif st.session_state.current_page == "教案生成":
            render_lesson_plan()
        elif st.session_state.current_page == "文件管理":
            render_file_manager()
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
'''

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("app.py created successfully")
