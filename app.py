import os
import sys
import json
import logging
import streamlit as st
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from scheduler import generate_daily_report, get_daily_cache_path, save_daily_report_to_cache
except ImportError:
    def get_daily_cache_path(date_str):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", f"report_{date_str}.json")

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AIBOX - AI日报智能体",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 还原你原本好看的 CSS，同时增强隔离性
st.markdown("""
<style>
    /* 全局样式重置 - 消除顶部空白 */
    html, body, [data-testid="stAppContainer"] {
        height: 100%; margin: 0; padding: 0;
    }
    
    /* 侧边栏样式 - 固定不可收缩 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important;
        padding-top: 0 !important;
        margin-top: 0 !important;
        min-width: 240px !important;
        max-width: 240px !important;
        width: 240px !important;
        flex-shrink: 0 !important;
        color: #f1f5f9 !important;
        z-index: 100 !important;
        transform: none !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }
    
    /* Logo标题样式 - AI部分蓝色高亮 */
    [data-testid="stSidebar"] h1 .logo-ai {
        color: #3b82f6 !important;
        text-shadow: 0 0 10px rgba(59,130,246,0.6) !important;
    }
    [data-testid="stSidebarNav"] { display: none !important; }
    
    /* 隐藏侧边栏折叠按钮 */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Close sidebar"],
    button[aria-label="Open sidebar"],
    button[aria-label="Collapse sidebar"],
    button[aria-label="Expand sidebar"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* 移除顶部空白 */
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stAppViewContainer"] { 
        padding-top: 0 !important; 
        margin-top: 0 !important;
    }
    [data-testid="stMain"] { 
        padding-top: 0 !important; 
        margin-top: 0 !important;
    }
    
    /* 隐藏教案生成页面中日期输入和关键词输入之间的分类按钮 */
    /* 这些按钮包含：产品更新、行业动态、论文研究、技巧观点 */
    section.main { 
        padding-top: 0 !important; 
        margin-top: 0 !important;
    }
    
    /* 侧边栏导航按钮 */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        gap: 8px;
    }
    [data-testid="stSidebar"] .stButton {
        margin: 0 !important;
    }
    
    /* 非活跃状态导航按钮 */
    [data-testid="stSidebar"] .stButton > button:not([class*="primary"]) {
        width: 100% !important;
        padding: 12px 16px !important;
        border-radius: 10px !important;
        text-align: left !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        transition: all 0.3s !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background: rgba(30, 41, 59, 0.8) !important;
        color: #f1f5f9 !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebar"] .stButton > button:not([class*="primary"]):hover {
        background: rgba(59, 130, 246, 0.3) !important;
        border-color: rgba(96, 165, 250, 0.5) !important;
        color: #ffffff !important;
    }
    
    /* 活跃状态导航按钮高亮 */
    [data-testid="stSidebar"] .stButton > button[class*="primary"] {
        width: 100% !important;
        padding: 12px 16px !important;
        border-radius: 10px !important;
        text-align: left !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
        border: 1px solid #60a5fa !important;
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4) !important;
    }
    [data-testid="stSidebar"] .stButton > button[class*="primary"]:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        border-color: #93c5fd !important;
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.5) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Radio导航组件样式 */
    [data-testid="stSidebar"] [data-testid="stRadio"] {
        margin: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        flex-direction: column !important;
        gap: 8px !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        width: 100% !important;
        padding: 12px 16px !important;
        border-radius: 10px !important;
        text-align: left !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        transition: all 0.3s !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background: rgba(30, 41, 59, 0.8) !important;
        color: #f1f5f9 !important;
        cursor: pointer !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(59, 130, 246, 0.3) !important;
        border-color: rgba(96, 165, 250, 0.5) !important;
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {
        background: rgba(30, 41, 59, 0.8) !important;
        color: #f1f5f9 !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background: rgba(59, 130, 246, 0.3) !important;
        color: #ffffff !important;
    }
    /* 选中状态的radio标签 */
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-state="checked"],
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        border-color: #60a5fa !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4) !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-state="checked"]:hover,
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked):hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.5) !important;
    }
    /* 隐藏radio圆点 */
    [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }

    /* 文章卡片 */
    .article-card {
        background: rgba(30,41,59,0.8); border-radius: 12px; padding: 16px; margin-bottom: 12px;
        cursor: pointer; border: 1px solid rgba(255,255,255,0.05); transition: all 0.3s ease;
    }
    .article-card:hover { background: rgba(51,65,85,0.9); border-color: rgba(96,165,250,0.3); }
    .article-title { font-size: 14px; font-weight: 600; color: #f1f5f9; margin-bottom: 8px; }
    .article-title a { color: inherit; text-decoration: none; }
    .article-title a:hover { color: #60a5fa; text-decoration: underline; }
    .article-meta { font-size: 12px; color: #6b7280; display: flex; gap: 12px; margin-bottom: 8px; }
    .article-summary { font-size: 13px; color: #9ca3af; line-height: 1.6; }
    
    /* 时间线 */
    .timeline-container { position: relative; padding-left: 24px; }
    .timeline-container::before {
        content: ''; position: absolute; left: 8px; top: 0; bottom: 0;
        width: 2px; background: linear-gradient(180deg, #3b82f6 0%, #6366f1 100%);
    }
    .timeline-item { position: relative; padding-bottom: 16px; }
    .timeline-item::before {
        content: ''; position: absolute; left: -20px; top: 6px;
        width: 10px; height: 10px; background: #3b82f6; border-radius: 50%;
        border: 2px solid #1e293b;
    }
    .timeline-time { font-size: 11px; color: #60a5fa; font-weight: 600; margin-bottom: 4px; }
    
    /* 分类标签 */
    .category-badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 0.75em; font-weight: 600; }
    .category-model { background: rgba(239,68,68,0.15); color: #f87171; }
    .category-product { background: rgba(16,185,129,0.15); color: #34d399; }
    .category-industry { background: rgba(245,158,11,0.15); color: #fbbf24; }
    .category-paper { background: rgba(59,130,246,0.15); color: #60a5fa; }
    .category-tips { background: rgba(148,163,184,0.15); color: #9ca3af; }
    .category-all { background: rgba(139,92,246,0.15); color: #a78bfa; }
    
    /* 评分标签 */
    .score-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold; color: white; }
    .score-high { background: #10b981; }
    .score-medium { background: #f59e0b; color: #1f2937; }
    .score-low { background: #ef4444; }
    
    /* 文件卡片 */
    .file-card { background: rgba(30,41,59,0.8); border-radius: 12px; padding: 16px; border: 1px solid rgba(255,255,255,0.05); }
    .file-icon { font-size: 32px; margin-bottom: 8px; }
    .file-name { font-size: 14px; font-weight: 600; color: #f1f5f9; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

CATEGORIES = ["全部讯息", "模型发布", "产品更新", "行业动态", "论文研究", "技巧观点"]
CATEGORY_COLORS = {
    "全部讯息": "category-all", "模型发布": "category-model",
    "产品更新": "category-product", "行业动态": "category-industry",
    "论文研究": "category-paper", "技巧观点": "category-tips"
}
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
ARTICLES_CACHE_FILE = os.path.join(CACHE_DIR, "articles_cache.json")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def init_session_state():
    if "current_page" not in st.session_state:
        st.session_state.current_page = "AI动态"
    if "articles" not in st.session_state:
        st.session_state.articles = []
    if "daily_report" not in st.session_state:
        st.session_state.daily_report = ""
    if "lesson_plans" not in st.session_state:
        st.session_state.lesson_plans = []
    if "selected_articles" not in st.session_state:
        st.session_state.selected_articles = []
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "全部讯息"

init_session_state()

from dotenv import load_dotenv
load_dotenv()

def load_daily_report_from_cache(date_str):
    cache_path = get_daily_cache_path(date_str)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_articles_cache(articles):
    """保存文章缓存，包含上次抓取时间"""
    try:
        with open(ARTICLES_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "articles": articles, 
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "last_fetch_time": datetime.now(timezone.utc).isoformat()
            }, f)
    except Exception as e:
        logger.warning(f"保存缓存失败: {e}")

def load_articles_cache():
    """加载文章缓存，返回(articles, last_fetch_time)"""
    if os.path.exists(ARTICLES_CACHE_FILE):
        try:
            with open(ARTICLES_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            articles = data.get("articles", [])
            last_fetch_time_str = data.get("last_fetch_time", "")
            last_fetch_time = datetime.fromisoformat(last_fetch_time_str) if last_fetch_time_str else None
            return articles, last_fetch_time
        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
    return [], None

def convert_to_beijing_time(published_at_str):
    try:
        if published_at_str.endswith("Z"):
            published_at_str = published_at_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(published_at_str)
        return dt.astimezone(timezone(timedelta(hours=8)))
    except Exception:
        return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

def format_time(dt):
    return dt.strftime("%m-%d %H:%M")

def get_articles_by_category(articles, category):
    if category == "全部讯息":
        return articles
    return [a for a in articles if a.get("category") == category]

def filter_articles_by_keyword(articles, keyword):
    if not keyword:
        return articles
    keyword = keyword.lower().strip()
    return [a for a in articles if keyword in a.get("title", "").lower() or keyword in a.get("content", "").lower()]

def generate_mock_articles():
    now = datetime.now(timezone.utc)
    return [
        {"title": "中国工程院外籍院士赫尔佐格：AI 下一个突破口是小型智能体协作", "content": "AI 下一个突破口是小型智能体协作，跨学科应用展现无限可能。", "link": "https://example.com/1", "published_at": (now - timedelta(hours=2)).isoformat(), "source": "IT之家AI频道", "category": "行业动态", "score": 8.21},
        {"title": "苹果 20 周年纪念版 iPhone 前瞻：微曲面显示屏、无实体按键，真全面屏仍存悬念", "content": "微曲面显示屏、无实体按键，真全面屏仍存悬念。", "link": "https://example.com/2", "published_at": (now - timedelta(hours=5)).isoformat(), "source": "IT之家AI频道", "category": "产品更新", "score": 8.13},
        {"title": "硬氪首发 | 复旦教授、前英特尔首席科学家做端侧具身大脑，「眸深智能」完成近亿元Pre-A轮追加融资", "content": "复旦教授做端侧具身大脑，完成近亿元融资。", "link": "https://example.com/3", "published_at": (now - timedelta(hours=8)).isoformat(), "source": "36氪前沿科技", "category": "模型发布", "score": 7.65},
    ]

def fetch_latest_articles():
    """获取最新文章，支持增量抓取"""
    # 读取缓存
    cached_articles, last_fetch_time = load_articles_cache()
    
    try:
        from src.fetcher import fetch_all_articles
        from src.processor import DataProcessor
        
        now = datetime.now(timezone.utc)
        processor = DataProcessor(use_api=False)
        
        if last_fetch_time:
            time_diff = now - last_fetch_time
            if time_diff.total_seconds() < 3600:  # 1小时内不重新抓取
                logger.info(f"快速缓存模式: 距离上次抓取仅 {time_diff.total_seconds():.0f} 秒，直接返回缓存")
                # 确保缓存数据都有category字段
                for article in cached_articles:
                    if "category" not in article:
                        article["category"] = processor.classify_article(article)
                    if "score" not in article:
                        article["score"] = processor.score_article(article)
                return cached_articles
            elif time_diff.days < 1:
                # 增量模式：只抓取上次抓取时间到现在的新文章
                logger.info(f"增量抓取模式: {last_fetch_time} 到 {now}")
                articles = fetch_all_articles(start_time=last_fetch_time, end_time=now)
            else:
                # 全量模式：超过1天，重新抓取最近7天的文章
                logger.info("全量抓取模式: 超过1天，重新抓取")
                end_date = now.date()
                start_date = end_date - timedelta(days=7)
                articles = fetch_all_articles(start_date=start_date, end_date=end_date)
        else:
            # 全量模式：首次抓取，抓取最近7天的文章
            logger.info("全量抓取模式: 首次抓取")
            end_date = now.date()
            start_date = end_date - timedelta(days=7)
            articles = fetch_all_articles(start_date=start_date, end_date=end_date)
        
        if articles:
            new_articles = processor.process_articles(articles)
            
            if cached_articles:
                # 确保缓存数据都有category字段
                for article in cached_articles:
                    if "category" not in article:
                        article["category"] = processor.classify_article(article)
                    if "score" not in article:
                        article["score"] = processor.score_article(article)
                # 合并并去重（按链接去重）
                existing_links = {a.get("link", "") for a in cached_articles}
                for article in new_articles:
                    if article.get("link", "") not in existing_links:
                        cached_articles.append(article)
                        existing_links.add(article.get("link", ""))
                # 按时间倒序重新排序
                cached_articles.sort(key=lambda a: convert_to_beijing_time(a.get("published_at", "")), reverse=True)
                result = cached_articles
            else:
                result = new_articles
            
            save_articles_cache(result)
            return result
        else:
            # 没有新文章，返回缓存数据
            if cached_articles:
                # 确保缓存数据都有category字段
                for article in cached_articles:
                    if "category" not in article:
                        article["category"] = processor.classify_article(article)
                    if "score" not in article:
                        article["score"] = processor.score_article(article)
                return cached_articles
    
    except Exception as e:
        logger.warning(f"抓取失败，使用缓存数据: {e}")
        if cached_articles:
            # 确保缓存数据都有category字段
            processor = DataProcessor(use_api=False)
            for article in cached_articles:
                if "category" not in article:
                    article["category"] = processor.classify_article(article)
                if "score" not in article:
                    article["score"] = processor.score_article(article)
            return cached_articles
    
    # 无缓存且抓取失败，返回模拟数据
    return generate_mock_articles()

def load_data():
    """每次刷新都加载数据，Streamlit缓存保证速度"""
    st.session_state.articles = fetch_latest_articles()

def get_icon(page_name):
    """根据页面名称获取图标"""
    icon_map = {
        "AI动态": "📰",
        "AI日报": "📊",
        "教案生成": "📚",
        "文件管理": "📁",
    }
    return icon_map.get(page_name, "📄")

def render_sidebar():
    """渲染侧边栏导航"""
    with st.sidebar:
        st.markdown("""
<div style="text-align:center; margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid rgba(255,255,255,0.1);">
    <h1 style="font-size:36px; font-weight:900; margin:0; letter-spacing:3px;">
        <span class="logo-ai">AI</span><span>BOX</span>
    </h1>
</div>
""", unsafe_allow_html=True)

        nav_items = [
            "📰 AI动态",
            "📊 AI日报",
            "📚 教案生成",
            "📁 文件管理",
        ]
        
        # 使用radio组件实现导航，原生支持选中状态高亮
        selected_nav = st.radio(
            "",
            nav_items,
            index=nav_items.index(f"{get_icon(st.session_state.current_page)} {st.session_state.current_page}"),
            key="nav_radio",
            horizontal=False,
            label_visibility="hidden",
        )
        
        # 获取选中的页面名称
        selected_page = selected_nav[2:] if len(selected_nav) > 2 else selected_nav
        
        # 如果选择了不同的页面，执行页面切换
        if selected_page != st.session_state.current_page:
            st.session_state.selected_category = "全部讯息"
            st.session_state.selected_articles = []
            st.session_state.lesson_plans = []
            if "view_file" in st.session_state:
                del st.session_state.view_file
            if "upload_file" in st.session_state:
                del st.session_state.upload_file
            if "delete_file" in st.session_state:
                del st.session_state.delete_file
            st.session_state.current_page = selected_page
            st.rerun()

        st.markdown("""
<div style="padding-top:20px; border-top:1px solid rgba(255,255,255,0.1); text-align:center; font-size:12px; color:#6b7280;">
    <p>📅 %s</p>
    <p>AI知识日报智能体</p>
</div>
""" % datetime.now().strftime("%Y年%m月%d日"), unsafe_allow_html=True)

def render_daily_dynamic():
    # 页面隔离检查：确保只在AI动态页面渲染
    if st.session_state.get("current_page") != "AI动态":
        return
    
    st.title("📰 AI动态")
    st.markdown("---")
    col_tabs = st.columns(len(CATEGORIES))
    for idx, cat in enumerate(CATEGORIES):
        with col_tabs[idx]:
            is_selected = st.session_state.selected_category == cat
            if st.button(cat, key=f"tab_{cat}", use_container_width=True, type="primary" if is_selected else "secondary"):
                st.session_state.selected_category = cat
                st.rerun()
    
    keyword = st.text_input("🔍 搜索关键词", placeholder=f"搜索{st.session_state.selected_category}相关资讯...", key="dd_search_input")
    cat_articles = get_articles_by_category(st.session_state.articles, st.session_state.selected_category)
    if keyword:
        cat_articles = filter_articles_by_keyword(cat_articles, keyword)
    
    # 按时间倒序排序，最新的在最上面
    cat_articles = sorted(cat_articles, key=lambda a: convert_to_beijing_time(a.get("published_at", "")), reverse=True)
    
    if cat_articles:
        timeline_html = ['<div class="timeline-container">']
        for article in cat_articles:
            dt = convert_to_beijing_time(article.get("published_at", ""))
            summary = article.get("content", "")[:100]
            if len(article.get("content", "")) > 100:
                summary += "..."
            timeline_html.append(f"""
<div class="timeline-item">
    <div class="timeline-time">{format_time(dt)}</div>
    <div class="article-card">
        <div class="article-title"><a href="{article.get('link','')}" target="_blank">{article.get('title','')}</a></div>
        <div class="article-meta">
            <span>📰 {article.get('source','')}</span>
            <span class="category-badge {CATEGORY_COLORS.get(article.get('category',''),'')}">{article.get('category','')}</span>
        </div>
        <div class="article-summary">{summary}</div>
    </div>
</div>
""")
        timeline_html.append("</div>")
        st.markdown("".join(timeline_html), unsafe_allow_html=True)

def render_daily_report():
    # 页面隔离检查：确保只在AI日报页面渲染
    if st.session_state.get("current_page") != "AI日报":
        return
    
    st.title("📊 AI日报")
    st.markdown("---")
    today = datetime.now()
    wd_map = {0:"一",1:"二",2:"三",3:"四",4:"五",5:"六",6:"日"}
    st.markdown(f"**AIBOX日报** - 二○二六年{today.month}月{today.day}日 · 星期{wd_map[today.weekday()]} · 每早六时")
    
    date_str = today.strftime("%Y%m%d")
    cached = load_daily_report_from_cache(date_str)
    
    if cached:
        st.session_state.daily_report = cached.get("report", "")
    
    if st.session_state.daily_report:
        st.download_button("📥 下载日报", st.session_state.daily_report, f"daily_report_{date_str}.md", mime="text/markdown")
        st.markdown(st.session_state.daily_report)
        
        # 自动保存到日报文件夹
        daily_reports_dir = os.path.join(OUTPUT_DIR, "daily_reports")
        os.makedirs(daily_reports_dir, exist_ok=True)
        output_path = os.path.join(daily_reports_dir, f"daily_report_{date_str}.md")
        if not os.path.exists(output_path):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(st.session_state.daily_report)
    else:
        st.info("日报将于每天早上6点自动生成")

def render_lesson_plan():
    # 页面隔离检查：确保只在教案生成页面渲染
    if st.session_state.get("current_page") != "教案生成":
        return
    
    st.title("📚 教案生成")
    st.markdown("---")
    
    # 限制只能选择近7天
    min_date = datetime.now().date() - timedelta(days=7)
    max_date = datetime.now().date()
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_date = st.date_input("开始日期", value=datetime.now().date() - timedelta(days=2), min_value=min_date, max_value=max_date, key="lp_start_date")
    with col2:
        end_date = st.date_input("结束日期", value=datetime.now().date(), min_value=min_date, max_value=max_date, key="lp_end_date")
    with col3:
        st.button("确认筛选", use_container_width=True, type="primary")
    
    keyword = st.text_input("🔍 关键词过滤", placeholder="输入关键词（如：智能体、大模型、AI等）", key="lp_keyword")
    cats = ["模型发布", "产品更新", "行业动态", "论文研究", "技巧观点"]
    tabs = st.tabs(cats, key="lp_tabs")
    
    # 日期范围筛选 - 使用session_state中存储的日期值
    filtered = []
    start_date_val = st.session_state.lp_start_date
    end_date_val = st.session_state.lp_end_date
    for a in st.session_state.articles:
        published_at = a.get("published_at", "")
        if not published_at:
            continue
        try:
            if published_at.endswith("Z"):
                published_at = published_at[:-1] + "+00:00"
            dt = datetime.fromisoformat(published_at)
            dt_beijing = dt.astimezone(timezone(timedelta(hours=8)))
            article_date = dt_beijing.date()
            if start_date_val <= article_date <= end_date_val:
                filtered.append(a)
        except Exception:
            continue
    
    filtered = filter_articles_by_keyword(filtered, keyword)
    filtered = sorted(filtered, key=lambda a: convert_to_beijing_time(a.get("published_at", "")), reverse=True)
    
    # 获取已选中文章的link集合用于快速查找
    selected_links = {a.get("link", "") for a in st.session_state.selected_articles}
    
    for idx, cat in enumerate(cats):
        with tabs[idx]:
            cat_articles = [a for a in filtered if a.get("category") == cat]
            if cat_articles:
                for i, article in enumerate(cat_articles):
                    article_link = article.get("link", "")
                    # 使用文章link作为复选框的key，避免index-based导致状态泄漏
                    checkbox_key = f"lp_chk_{article_link[:50].replace('/', '_').replace(':', '_')}"
                    
                    col_check, col_content = st.columns([1, 9])  # 调整列比例，增加复选框列宽度
                    with col_check:
                        checked = st.checkbox("", value=article_link in selected_links, key=checkbox_key)
                        if checked and article_link not in selected_links:
                            st.session_state.selected_articles.append(article)
                        elif not checked and article_link in selected_links:
                            # 找到并移除对应的文章
                            for idx, sel_article in enumerate(st.session_state.selected_articles):
                                if sel_article.get("link", "") == article_link:
                                    st.session_state.selected_articles.pop(idx)
                                    break
                    with col_content:
                        dt = convert_to_beijing_time(article.get("published_at", ""))
                        st.markdown(f"""
<div class="article-card">
    <div class="article-title"><a href="{article.get('link','')}" target="_blank">{article.get('title','')}</a></div>
    <div class="article-meta">
        <span>📰 {article.get('source','')}</span>
        <span>⏰ {format_time(dt)}</span>
        <span class="score-badge score-high">{article.get('score',0)}分</span>
    </div>
</div>
""", unsafe_allow_html=True)
    
    # 生成教案按钮
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
                generator = CourseGenerator(use_api=True)
                lesson_plans = []
                for article in st.session_state.selected_articles:
                    topic = article.get("title", "AI技术前沿")[:50]
                    plan = generator.generate_lesson_plan([article], topic)
                    lesson_plans.append({"article_title": article.get("title", ""), "content": plan, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                st.session_state.lesson_plans = lesson_plans
                st.success(f"🎉 成功生成 {len(lesson_plans)} 份教案！")
                os.makedirs(os.path.join(OUTPUT_DIR, "lesson_plans"), exist_ok=True)
                for plan in lesson_plans:
                    safe_title = plan["article_title"].replace("/", "-").replace("\\", "-")[:50]
                    filepath = os.path.join(OUTPUT_DIR, "lesson_plans", f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
                    generator.save_markdown(plan["content"], filepath)
            except Exception as e:
                st.error(f"生成教案失败: {str(e)}")
    
    # 教案预览
    if st.session_state.lesson_plans:
        st.subheader("📝 教案预览")
        for i, plan in enumerate(st.session_state.lesson_plans):
            with st.expander(f"教案 {i+1}: {plan['article_title'][:50]}..."):
                st.markdown(f'<div class="lesson-preview">{plan["content"]}</div>', unsafe_allow_html=True)
                st.download_button(label=f"📥 下载教案 {i+1}", data=plan["content"], file_name=f"lesson_plan_{i+1}_{datetime.now().strftime('%Y%m%d')}.md", mime="text/markdown", key=f"download_lesson_{i}")

def render_file_manager():
    # 页面隔离检查：确保只在文件管理页面渲染
    if st.session_state.get("current_page") != "文件管理":
        return
    
    st.title("📁 文件管理")
    st.markdown("---")
    
    # 确保目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    daily_reports_dir = os.path.join(OUTPUT_DIR, "daily_reports")
    lesson_plans_dir = os.path.join(OUTPUT_DIR, "lesson_plans")
    os.makedirs(daily_reports_dir, exist_ok=True)
    os.makedirs(lesson_plans_dir, exist_ok=True)
    
    # 处理删除请求
    if "delete_file" in st.session_state:
        delete_path = st.session_state.delete_file
        if os.path.exists(delete_path):
            os.remove(delete_path)
            st.success(f"已删除文件: {os.path.basename(delete_path)}")
        else:
            st.error("文件不存在")
        del st.session_state.delete_file
    
    # 处理上传请求
    if "upload_file" in st.session_state:
        file_info = st.session_state.upload_file
        target_dir = daily_reports_dir if file_info["folder"] == "daily" else lesson_plans_dir
        
        # 文件名冲突检测
        filename = file_info["filename"]
        filepath = os.path.join(target_dir, filename)
        if os.path.exists(filepath):
            # 添加时间戳后缀
            base_name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("_%Y%m%d_%H%M%S")
            filename = f"{base_name}{timestamp}{ext}"
            filepath = os.path.join(target_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(file_info["content"])
        st.success(f"文件上传成功: {filename}")
        del st.session_state.upload_file
    
    # 文件夹标签页导航
    tabs = st.tabs(["📋 日报文件夹", "📚 教案文件夹"], key="fm_tabs")
    
    # 日报文件夹
    with tabs[0]:
        st.markdown("""
<div style="background: rgba(30,41,59,0.6); border-radius: 12px; padding: 16px; margin-bottom: 16px;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 20px;">📁</span>
        <span style="font-weight: 600;">日报文件夹</span>
        <span style="font-size: 12px; color: #6b7280; margin-left: auto;">自动保存每日生成的AI日报</span>
    </div>
</div>
""", unsafe_allow_html=True)
        
        # 上传按钮
        uploaded_file = st.file_uploader("📤 上传日报文件 (.md)", type="md", key="upload_daily")
        if uploaded_file is not None:
            st.session_state.upload_file = {
                "folder": "daily",
                "filename": uploaded_file.name,
                "content": uploaded_file.read()
            }
            st.rerun()
        
        # 文件列表
        report_files = sorted([f for f in os.listdir(daily_reports_dir) if f.endswith(".md")], reverse=True)
        if report_files:
            st.markdown("### 文件列表")
            for filename in report_files:
                filepath = os.path.join(daily_reports_dir, filename)
                file_size = os.path.getsize(filepath) / 1024
                modified_time = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M")
                
                col_file, col_size, col_time, col_actions = st.columns([4, 1, 1, 2])
                with col_file:
                    st.markdown(f"""
<div class="file-card" style="padding: 12px;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span>📄</span>
        <span style="font-size: 14px; font-weight: 600; color: #f1f5f9;">{filename}</span>
    </div>
</div>
""", unsafe_allow_html=True)
                with col_size:
                    st.markdown(f'<div style="display: flex; align-items: center; height: 100%; font-size: 12px; color: #6b7280;">📦 {file_size:.2f} KB</div>', unsafe_allow_html=True)
                with col_time:
                    st.markdown(f'<div style="display: flex; align-items: center; height: 100%; font-size: 12px; color: #6b7280;">📅 {modified_time}</div>', unsafe_allow_html=True)
                with col_actions:
                    col_view, col_download, col_delete = st.columns(3)
                    with col_view:
                        if st.button("👁️", key=f"view_daily_{filename}"):
                            st.session_state.view_file = filepath
                    with col_download:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        st.download_button("📥", data=content, file_name=filename, mime="text/markdown", key=f"download_daily_{filename}")
                    with col_delete:
                        if st.button("🗑️", key=f"delete_daily_{filename}"):
                            st.session_state.delete_file = filepath
                            st.rerun()
        
            # 文件预览区域
            if "view_file" in st.session_state and st.session_state.view_file.startswith(daily_reports_dir):
                view_path = st.session_state.view_file
                with open(view_path, "r", encoding="utf-8") as f:
                    content = f.read()
                with st.expander(f"👁️ 查看文件: {os.path.basename(view_path)}", expanded=True):
                    st.markdown(content)
        else:
            st.markdown("""
<div style="text-align: center; padding: 40px; color: #6b7280;">
    <div style="font-size: 48px; margin-bottom: 12px;">📭</div>
    <div style="font-size: 14px;">暂无日报文件</div>
    <div style="font-size: 12px; margin-top: 4px;">日报将在每天6点自动生成并保存到此处</div>
</div>
""", unsafe_allow_html=True)
    
    # 教案文件夹
    with tabs[1]:
        st.markdown("""
<div style="background: rgba(30,41,59,0.6); border-radius: 12px; padding: 16px; margin-bottom: 16px;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 20px;">📁</span>
        <span style="font-weight: 600;">教案文件夹</span>
        <span style="font-size: 12px; color: #6b7280; margin-left: auto;">自动保存生成的课程教案</span>
    </div>
</div>
""", unsafe_allow_html=True)
        
        # 上传按钮
        uploaded_file = st.file_uploader("📤 上传教案文件 (.md)", type="md", key="upload_lesson")
        if uploaded_file is not None:
            st.session_state.upload_file = {
                "folder": "lesson",
                "filename": uploaded_file.name,
                "content": uploaded_file.read()
            }
            st.rerun()
        
        # 文件列表
        lesson_files = sorted([f for f in os.listdir(lesson_plans_dir) if f.endswith(".md")], reverse=True)
        if lesson_files:
            st.markdown("### 文件列表")
            for filename in lesson_files:
                filepath = os.path.join(lesson_plans_dir, filename)
                file_size = os.path.getsize(filepath) / 1024
                modified_time = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M")
                
                col_file, col_size, col_time, col_actions = st.columns([4, 1, 1, 2])
                with col_file:
                    st.markdown(f"""
<div class="file-card" style="padding: 12px;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span>📝</span>
        <span style="font-size: 14px; font-weight: 600; color: #f1f5f9;">{filename}</span>
    </div>
</div>
""", unsafe_allow_html=True)
                with col_size:
                    st.markdown(f'<div style="display: flex; align-items: center; height: 100%; font-size: 12px; color: #6b7280;">📦 {file_size:.2f} KB</div>', unsafe_allow_html=True)
                with col_time:
                    st.markdown(f'<div style="display: flex; align-items: center; height: 100%; font-size: 12px; color: #6b7280;">📅 {modified_time}</div>', unsafe_allow_html=True)
                with col_actions:
                    col_view, col_download, col_delete = st.columns(3)
                    with col_view:
                        if st.button("👁️", key=f"view_lesson_{filename}"):
                            st.session_state.view_file = filepath
                    with col_download:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        st.download_button("📥", data=content, file_name=filename, mime="text/markdown", key=f"download_lesson_{filename}")
                    with col_delete:
                        if st.button("🗑️", key=f"delete_lesson_{filename}"):
                            st.session_state.delete_file = filepath
                            st.rerun()
        
            # 文件预览区域
            if "view_file" in st.session_state and st.session_state.view_file.startswith(lesson_plans_dir):
                view_path = st.session_state.view_file
                with open(view_path, "r", encoding="utf-8") as f:
                    content = f.read()
                with st.expander(f"👁️ 查看文件: {os.path.basename(view_path)}", expanded=True):
                    st.markdown(content)
        else:
            st.markdown("""
<div style="text-align: center; padding: 40px; color: #6b7280;">
    <div style="font-size: 48px; margin-bottom: 12px;">📭</div>
    <div style="font-size: 14px;">暂无教案文件</div>
    <div style="font-size: 12px; margin-top: 4px;">生成教案后将自动保存到此处</div>
</div>
""", unsafe_allow_html=True)

def main():
    render_sidebar()

    page = st.session_state.current_page
    if page == "AI动态":
        load_data()
        render_daily_dynamic()
        return
    if page == "AI日报":
        load_data()
        render_daily_report()
        return
    if page == "教案生成":
        load_data()
        render_lesson_plan()
        return
    if page == "文件管理":
        render_file_manager()
        return

if __name__ == "__main__":
    main()