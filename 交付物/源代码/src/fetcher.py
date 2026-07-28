import os
import yaml
import logging
import time
import feedparser
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# 避免重复添加处理器
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(handler)


def clean_html(html_content: str, max_length: int = 1000) -> str:
    """
    清洗HTML标签，只保留纯文本内容
    
    Args:
        html_content: HTML格式的正文内容
        max_length: 截取的最大长度，默认为1000字
        
    Returns:
        清洗后的纯文本内容
    """
    if not html_content:
        return ""
    
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        # 获取所有文本内容
        text = soup.get_text(separator="\n", strip=True)
        # 移除多余的换行和空白
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        clean_text = "\n".join(lines)
        # 截取前max_length字
        return clean_text[:max_length]
    except Exception as e:
        logger.warning(f"HTML清洗失败: {str(e)}")
        return ""


def parse_published_time(published_str: str) -> datetime:
    """
    解析RSS发布时间字符串为datetime对象
    
    Args:
        published_str: RSS中的发布时间字符串
        
    Returns:
        解析后的datetime对象（UTC时间，带时区信息）
    """
    if not published_str:
        return datetime.now(timezone.utc)
    
    # 常见的时间格式（增加国内RSS常用格式）
    time_formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        # 国内RSS常用格式（如36氪）
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S %Z",
        "%Y-%m-%d  %H:%M:%S %z",  # 双空格情况
        "%Y-%m-%d  %H:%M:%S %Z",  # 双空格情况
        "%Y-%m-%d %H:%M:%S%z",    # 无时区空格
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    
    parsed_time = None
    for fmt in time_formats:
        try:
            parsed_time = datetime.strptime(published_str, fmt)
            break
        except ValueError:
            continue
    
    # 如果上面解析失败，尝试使用dateutil.parser.parse（如果已安装）
    if parsed_time is None:
        try:
            from dateutil import parser as dateutil_parser
            parsed_time = dateutil_parser.parse(published_str)
        except ImportError:
            # dateutil未安装，跳过
            pass
        except Exception:
            pass
    
    # 如果dateutil也失败，尝试使用feedparser的解析方法
    if parsed_time is None:
        try:
            parsed_time = feedparser.parse_date(published_str)
        except Exception:
            pass
    
    # 如果还是失败，返回当前时间
    if parsed_time is None:
        logger.warning(f"无法解析时间格式: {published_str}")
        return datetime.now(timezone.utc)
    
    # 确保返回的datetime对象带有时区信息（offset-aware）
    if parsed_time.tzinfo is None or parsed_time.tzinfo.utcoffset(parsed_time) is None:
        # 假设为UTC时间
        parsed_time = parsed_time.replace(tzinfo=timezone.utc)
    
    return parsed_time


def fetch_rss_articles(source: dict, hours: int = 48, start_date: datetime = None, end_date: datetime = None,
                       start_time: datetime = None, end_time: datetime = None) -> list:
    """
    从单个RSS源抓取文章
    
    Args:
        source: 信源配置字典，包含name, type, url, category_weight
        hours: 抓取过去多少小时内的文章，默认为48小时（仅当其他时间参数未指定时生效）
        start_date: 开始日期（datetime.date对象），用于历史日期回溯
        end_date: 结束日期（datetime.date对象），用于历史日期回溯
        start_time: 开始时间（datetime.datetime对象，带时区），用于精确时间范围抓取
        end_time: 结束时间（datetime.datetime对象，带时区），用于精确时间范围抓取
        
    Returns:
        文章列表，每条包含title, content, link, published_at, source, weight
    """
    articles = []
    source_name = source.get("name", "Unknown")
    source_url = source.get("url", "")
    weight = source.get("category_weight", 0.5)
    
    if not source_url:
        logger.warning(f"信源 {source_name} 缺少URL配置")
        return articles
    
    # 设置时间范围
    if start_time and end_time:
        # 精确时间范围模式（定时任务模式）
        start_datetime = start_time
        end_datetime = end_time
        # 增加时间容错范围（前后各1小时），确保不会因为时区问题漏掉文章
        tolerance_start = start_datetime - timedelta(hours=1)
        tolerance_end = end_datetime + timedelta(hours=1)
    elif start_date and end_date:
        # 历史日期回溯模式：转换为datetime并设置时区
        start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        
        # 历史日期回溯模式：不使用容错范围，严格按照用户指定的日期范围过滤
        tolerance_start = start_datetime
        tolerance_end = end_datetime
    else:
        # 实时模式：默认抓取过去hours小时内的文章
        end_datetime = datetime.now(timezone.utc)
        start_datetime = end_datetime - timedelta(hours=hours)
        tolerance_start = start_datetime
        tolerance_end = end_datetime
    
    try:
        logger.info(f"正在抓取信源: {source_name}")
        
        # 解析RSS feed
        feed = feedparser.parse(source_url)
        
        if feed.get("bozo", 0) != 0:
            logger.warning(f"信源 {source_name} 解析异常: {feed.get('bozo_exception', 'Unknown error')}")
            return articles
        
        if not feed.entries:
            logger.info(f"信源 {source_name} 没有找到文章")
            return articles
        
        # 先尝试按时间范围过滤
        time_filtered_articles = []
        
        for entry in feed.entries:
            # 解析发布时间（统一转换为UTC）
            published_at = parse_published_time(entry.get("published", ""))
            
            # 过滤超出时间范围的文章（使用容错范围）
            if not (tolerance_start <= published_at <= tolerance_end):
                continue
            
            # 获取标题
            title = entry.get("title", "").strip()
            
            # 获取链接
            link = entry.get("link", "")
            
            # 获取并清洗正文
            # 尝试从多个字段获取正文内容
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")
            elif hasattr(entry, "summary"):
                content = entry.summary
            elif hasattr(entry, "description"):
                content = entry.description
            
            clean_content = clean_html(content)
            
            # 跳过内容过短的文章（放宽门槛，确保短摘要也能被抓取）
            if len(clean_content) < 10:
                continue
            
            time_filtered_articles.append({
                "title": title,
                "content": clean_content,
                "link": link,
                "published_at": published_at.isoformat(),
                "source": source_name,
                "weight": weight,
            })
        
        # 历史日期模式下，如果按时间范围没找到文章，返回空列表（RSS源具有时效性，无法获取历史数据）
        # 只有arXiv和GitHub API支持真正的历史数据查询
        if start_date and end_date and len(time_filtered_articles) == 0 and not (start_time and end_time):
            logger.info(f"信源 {source_name} 在指定日期范围内没有找到文章（RSS源具有时效性），跳过该信源")
            articles = []
        else:
            articles = time_filtered_articles
        
        logger.info(f"信源 {source_name} 抓取完成，共 {len(articles)} 篇文章")
        
    except Exception as e:
        logger.warning(f"信源 {source_name} 抓取失败: {str(e)}")
    
    return articles


def load_sources(config_path: str = "config/sources.yaml") -> list:
    """
    从配置文件加载信源列表
    
    Args:
        config_path: 配置文件路径，默认为config/sources.yaml
        
    Returns:
        信源配置列表
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config.get("sources", [])
    except FileNotFoundError:
        logger.error(f"配置文件未找到: {config_path}")
        return []
    except Exception as e:
        logger.error(f"配置文件读取失败: {str(e)}")
        return []


def _fetch_arxiv_with_retry(url, headers, max_retries=3, retry_delay=5):
    """
    带重试机制的 arXiv API 请求
    
    Args:
        url: 请求URL
        headers: 请求头
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
        
    Returns:
        请求响应
    """
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                logger.warning(f"arXiv API 请求超限 (429)，第 {attempt+1}/{max_retries} 次尝试")
                time.sleep(retry_delay * (attempt + 1))
            else:
                raise
        except urllib.error.URLError as e:
            logger.warning(f"arXiv API 连接错误，第 {attempt+1}/{max_retries} 次尝试: {str(e)}")
            time.sleep(retry_delay * (attempt + 1))
        except Exception as e:
            logger.warning(f"arXiv API 请求异常，第 {attempt+1}/{max_retries} 次尝试: {str(e)}")
            time.sleep(retry_delay * (attempt + 1))
    
    raise Exception(f"arXiv API 请求失败，已重试 {max_retries} 次")


def fetch_arxiv_papers(start_date: datetime, end_date: datetime, max_results: int = 100, allow_fallback: bool = True, strict_time_filter: bool = False) -> list:
    """
    通过 arXiv 官方 API 根据日期范围抓取历史论文
    
    Args:
        start_date: 开始日期（datetime.date或datetime.datetime对象）
        end_date: 结束日期（datetime.date或datetime.datetime对象）
        max_results: 最大返回结果数，默认为100（增加数量确保有足够数据）
        allow_fallback: 是否允许兜底方案（获取最近提交的论文）
        strict_time_filter: 是否严格按照日期范围过滤（不使用容错范围）
        
    Returns:
        论文文章列表，每条包含title, content, link, published_at, source, weight
    """
    articles = []
    
    try:
        logger.info(f"正在通过 arXiv API 抓取论文: {start_date} 到 {end_date}")
        
        # arXiv API 要求请求间隔至少3秒，增加到5秒以避免429错误
        time.sleep(5)
        
        # 判断是否为datetime对象（带时间）
        if hasattr(start_date, 'hour'):
            # 带时间的datetime对象，使用精确时间
            start_str = start_date.strftime("%Y%m%d%H%M")
        else:
            # 只有date对象，使用当天0点
            start_str = start_date.strftime("%Y%m%d") + "0000"
            
        if hasattr(end_date, 'hour'):
            # 带时间的datetime对象，使用精确时间
            end_str = end_date.strftime("%Y%m%d%H%M")
        else:
            # 只有date对象，使用当天23:59
            end_str = end_date.strftime("%Y%m%d") + "2359"
        
        # 构建 arXiv API 查询
        # 查询 AI 相关领域的论文，使用 OR 连接多个分类
        # 注意：arXiv API的OR语法需要用空格分隔，不能用+号
        categories = [
            "cat:cs.AI",
            "cat:stat.ML",
            "cat:cs.LG",
            "cat:cs.CL",
            "cat:cs.CV",
            "cat:cs.NE"
        ]
        category_query = " OR ".join(categories)
        
        # 添加日期范围过滤
        date_query = f"+AND+submittedDate:[{start_str}+TO+{end_str}]"
        
        # 完整查询字符串
        search_query = f"({category_query}){date_query}"
        
        # arXiv API 查询参数
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        
        # 构建请求 URL（使用https）
        url = f"https://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"
        logger.info(f"arXiv API 请求URL: {url}")
        
        # 请求头
        headers = {
            "User-Agent": "AI-Knowledge-Daily-Bot/1.0 (https://github.com/example/ai-course-agent; contact@example.com)"
        }
        
        # 发送请求（带重试）
        response_data = _fetch_arxiv_with_retry(url, headers)
        xml_content = response_data.decode("utf-8")
        
        # 解析 XML
        feed = feedparser.parse(xml_content)
        
        if feed.get("bozo", 0) != 0:
            logger.warning(f"arXiv API 解析异常: {feed.get('bozo_exception', 'Unknown error')}")
            # 如果首次查询失败，尝试不带日期限制的查询作为兜底（历史日期回溯模式下不兜底）
            if allow_fallback:
                logger.info("尝试不带日期限制的查询作为兜底...")
                return _fetch_arxiv_papers_fallback(max_results)
            else:
                logger.info("历史日期回溯模式下不使用兜底方案")
                return articles
        
        if not feed.entries:
            logger.info("arXiv API 指定日期范围没有找到论文")
            # 如果指定日期没有结果，尝试扩展日期范围（历史日期回溯模式下不兜底）
            if allow_fallback:
                logger.info("尝试扩展日期范围...")
                return _fetch_arxiv_papers_fallback(max_results)
            else:
                logger.info("历史日期回溯模式下不使用兜底方案")
                return articles
        
        # 计算时间范围边界（统一转换为UTC）
        entry_start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        entry_end = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        
        # 根据模式决定是否使用容错范围
        if strict_time_filter:
            # 严格模式：不使用容错范围
            tolerance_start = entry_start
            tolerance_end = entry_end
        else:
            # 普通模式：允许的时间容错范围（前后各1天）
            tolerance_days = 1
            tolerance_start = entry_start - timedelta(days=tolerance_days)
            tolerance_end = entry_end + timedelta(days=tolerance_days)
        
        for entry in feed.entries:
            # 获取标题
            title = entry.get("title", "").strip()
            
            # 获取链接
            link = entry.get("link", "")
            
            # 获取摘要（作为内容）
            summary = entry.get("summary", "")
            clean_content = clean_html(summary)
            
            # 跳过内容过短的论文（放宽门槛，确保短摘要也能被抓取）
            if len(clean_content) < 10:
                continue
            
            # 获取发布时间（统一转换为UTC）
            published_at = parse_published_time(entry.get("published", ""))
            
            # 时间过滤（使用容错范围）
            if not (tolerance_start <= published_at <= tolerance_end):
                continue
            
            # 获取作者信息
            authors = []
            if hasattr(entry, "authors"):
                authors = [author.get("name", "") for author in entry.authors]
            authors_str = ", ".join(authors)
            
            # 构建文章对象
            articles.append({
                "title": title,
                "content": clean_content,
                "link": link,
                "published_at": published_at.isoformat(),
                "source": f"arXiv ({authors_str})",
                "weight": 1.0,  # 论文权重最高
            })
        
        # 如果结果过少，尝试扩展日期范围获取更多论文（历史日期回溯模式下不扩展）
        if len(articles) < 10 and allow_fallback:
            logger.info(f"当前日期范围仅获取到 {len(articles)} 篇论文，尝试扩展日期范围...")
            fallback_articles = _fetch_arxiv_papers_fallback(max_results)
            # 合并并去重
            existing_links = {a["link"] for a in articles}
            for article in fallback_articles:
                if article["link"] not in existing_links:
                    articles.append(article)
                    existing_links.add(article["link"])
        
        logger.info(f"arXiv API 抓取完成，共 {len(articles)} 篇论文")
        
    except Exception as e:
        logger.warning(f"arXiv API 抓取失败: {str(e)}")
        # 失败时尝试兜底方案（历史日期回溯模式下不兜底）
        if allow_fallback:
            return _fetch_arxiv_papers_fallback(max_results)
        else:
            logger.info("历史日期回溯模式下不使用兜底方案")
            return articles
    
    return articles


def _fetch_arxiv_papers_fallback(max_results: int = 100) -> list:
    """
    arXiv API 查询失败时的兜底方案：不带日期限制，获取最近提交的论文
    
    Args:
        max_results: 最大返回结果数
        
    Returns:
        论文文章列表
    """
    articles = []
    
    try:
        logger.info("使用 arXiv API 兜底方案：获取最近提交的论文")
        
        # 构建查询（不带日期限制，只按分类查询）
        categories = [
            "cat:cs.AI",
            "cat:stat.ML",
            "cat:cs.LG",
            "cat:cs.CL",
            "cat:cs.CV",
            "cat:cs.NE"
        ]
        category_query = "+OR+".join(categories)
        
        params = {
            "search_query": f"({category_query})",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        
        url = f"http://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"
        
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AI-Knowledge-Daily-Bot/1.0 (https://github.com/example/ai-course-agent; contact@example.com)"
            }
        )
        
        response = urllib.request.urlopen(req, timeout=30)
        xml_content = response.read().decode("utf-8")
        
        feed = feedparser.parse(xml_content)
        
        if feed.get("bozo", 0) != 0 or not feed.entries:
            logger.info("arXiv API 兜底方案也没有找到论文")
            return articles
        
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            clean_content = clean_html(summary)
            
            if len(clean_content) < 10:
                continue
            
            published_at = parse_published_time(entry.get("published", ""))
            
            authors = []
            if hasattr(entry, "authors"):
                authors = [author.get("name", "") for author in entry.authors]
            authors_str = ", ".join(authors)
            
            articles.append({
                "title": title,
                "content": clean_content,
                "link": link,
                "published_at": published_at.isoformat(),
                "source": f"arXiv ({authors_str})",
                "weight": 1.0,
            })
        
        logger.info(f"arXiv API 兜底方案完成，共 {len(articles)} 篇论文")
        
    except Exception as e:
        logger.warning(f"arXiv API 兜底方案失败: {str(e)}")
    
    return articles


def fetch_github_trending(start_date: datetime, end_date: datetime, max_results: int = 30) -> list:
    """
    通过 GitHub Search API 根据日期范围抓取热门 AI 相关仓库
    
    Args:
        start_date: 开始日期（datetime.date或datetime.datetime对象）
        end_date: 结束日期（datetime.date或datetime.datetime对象）
        max_results: 最大返回结果数，默认为30
        
    Returns:
        GitHub仓库文章列表，每条包含title, content, link, published_at, source, weight
    """
    articles = []
    
    try:
        logger.info(f"正在通过 GitHub API 抓取热门仓库: {start_date} 到 {end_date}")
        
        # 等待3秒避免限流
        time.sleep(3)
        
        # 判断是否为datetime对象（带时间）
        if hasattr(start_date, 'hour'):
            # 带时间的datetime对象，使用精确时间格式
            start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            # 只有date对象，使用日期格式
            start_str = start_date.strftime("%Y-%m-%d")
            
        if hasattr(end_date, 'hour'):
            # 带时间的datetime对象，使用精确时间格式
            end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            # 只有date对象，使用日期格式
            end_str = end_date.strftime("%Y-%m-%d")
        
        # GitHub Search API 查询参数
        # 搜索 AI 相关的热门仓库
        keywords = ["AI", "LLM", "machine-learning", "deep-learning", "neural-network", "chatbot", "agent"]
        keyword_query = "+OR+".join([f"topic:{kw}" for kw in keywords])
        
        # 日期范围过滤
        date_query = f"+created:{start_str}..{end_str}"
        
        # 完整查询（放宽星标门槛，确保能抓取到最新新建的AI开源项目）
        search_query = f"({keyword_query}){date_query}+stars:>5"
        
        # 构建请求 URL
        params = {
            "q": search_query,
            "sort": "stars",
            "order": "desc",
            "per_page": max_results
        }
        
        url = f"https://api.github.com/search/repositories?{urllib.parse.urlencode(params)}"
        
        # 创建请求对象，添加 User-Agent 头
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AI-Knowledge-Daily-Bot/1.0 (https://github.com/example/ai-course-agent; contact@example.com)"
            }
        )
        
        # 发送请求
        response = urllib.request.urlopen(req, timeout=30)
        json_content = response.read().decode("utf-8")
        
        # 解析 JSON
        import json
        data = json.loads(json_content)
        
        if "items" not in data or not data["items"]:
            logger.info("GitHub API 没有找到仓库")
            return articles
        
        for item in data["items"]:
            # 获取仓库名称
            name = item.get("full_name", "")
            title = f"GitHub: {name}"
            
            # 获取描述
            description = item.get("description", "")
            clean_content = clean_html(description)
            
            # 跳过内容过短的仓库（放宽门槛，确保简短描述也能被抓取）
            if len(clean_content) < 10:
                continue
            
            # 获取链接
            link = item.get("html_url", "")
            
            # 获取创建时间
            created_at = item.get("created_at", "")
            published_at = parse_published_time(created_at)
            
            # 获取星标数和作者
            stars = item.get("stargazers_count", 0)
            owner = item.get("owner", {}).get("login", "")
            
            # 获取语言信息
            language = item.get("language", "")
            
            # 构建文章对象
            articles.append({
                "title": title,
                "content": f"{clean_content}\n\n语言: {language}\n星标数: {stars}",
                "link": link,
                "published_at": published_at.isoformat(),
                "source": f"GitHub ({owner})",
                "weight": 0.9,  # GitHub 仓库权重较高
            })
        
        logger.info(f"GitHub API 抓取完成，共 {len(articles)} 个仓库")
        
    except Exception as e:
        logger.warning(f"GitHub API 抓取失败: {str(e)}")
    
    return articles


def fetch_all_articles(hours: int = 48, start_date: datetime = None, end_date: datetime = None, 
                      start_time: datetime = None, end_time: datetime = None, target_count: int = 80) -> list:
    """
    从所有配置的信源抓取文章
    
    Args:
        hours: 抓取过去多少小时内的文章，默认为48小时（仅当其他时间参数未指定时生效）
        start_date: 开始日期（datetime.date对象），用于历史日期回溯
        end_date: 结束日期（datetime.date对象），用于历史日期回溯
        start_time: 开始时间（datetime.datetime对象，带时区），用于精确时间范围抓取
        end_time: 结束时间（datetime.datetime对象，带时区），用于精确时间范围抓取
        target_count: 目标抓取数量，默认为80篇，不足时会自动扩展日期范围
        
    Returns:
        所有信源的文章合并列表
    """
    articles = []
    sources = load_sources()
    
    # 确定时间范围
    if start_time and end_time:
        # 使用精确的datetime时间范围（定时任务模式）
        logger.info(f"定时任务模式: {start_time} 到 {end_time}")
        current_start = start_time
        current_end = end_time
        start_date_obj = start_time.date()
        end_date_obj = end_time.date()
    elif start_date and end_date:
        # 使用日期范围（历史日期回溯模式）
        logger.info(f"历史日期回溯模式: {start_date} 到 {end_date}")
        current_start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        current_end = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        start_date_obj = start_date
        end_date_obj = end_date
    else:
        # 实时模式
        current_end = datetime.now(timezone.utc)
        current_start = current_end - timedelta(hours=hours)
        start_date_obj = current_start.date()
        end_date_obj = current_end.date()
    
    # 使用 arXiv 和 GitHub 官方 API 抓取（定时任务模式传递精确时间）
    if start_date_obj and end_date_obj:
        # 调用 arXiv API 抓取论文（定时任务模式传递精确时间，历史日期回溯模式不使用兜底且严格过滤）
        if start_time and end_time:
            arxiv_articles = fetch_arxiv_papers(start_time, end_time, allow_fallback=True, strict_time_filter=False)
        else:
            arxiv_articles = fetch_arxiv_papers(start_date_obj, end_date_obj, allow_fallback=False, strict_time_filter=True)
        articles.extend(arxiv_articles)
        
        # 调用 GitHub API 抓取热门仓库（定时任务模式传递精确时间）
        if start_time and end_time:
            github_articles = fetch_github_trending(start_time, end_time)
        else:
            github_articles = fetch_github_trending(start_date_obj, end_date_obj)
        articles.extend(github_articles)
    
    # 抓取 RSS 源文章（所有模式都会抓取）
    if not sources:
        logger.warning("未找到任何信源配置")
        return articles
    
    logger.info(f"开始抓取 {len(sources)} 个信源的文章...")
    
    for source in sources:
        if source.get("type") != "rss":
            logger.warning(f"不支持的信源类型: {source.get('type')}")
            continue
        
        # 根据模式调用不同的参数
        if start_time and end_time:
            # 定时任务模式：传递精确时间
            source_articles = fetch_rss_articles(source, hours, start_time=current_start, end_time=current_end)
        elif start_date_obj and end_date_obj:
            # 历史日期回溯模式：只传递日期（RSS源具有时效性，无法获取历史数据）
            source_articles = fetch_rss_articles(source, hours, start_date=start_date_obj, end_date=end_date_obj)
        else:
            # 实时模式
            source_articles = fetch_rss_articles(source, hours)
        articles.extend(source_articles)
    
    # 如果结果过少，尝试扩展日期范围获取更多文章（定时任务模式和历史日期回溯模式下不扩展）
    # 定时任务模式：保持精确时间范围
    # 历史日期回溯模式：用户指定了明确的日期范围，不应扩展
    if not (start_time and end_time) and not (start_date_obj and end_date_obj) and len(articles) < target_count:
        logger.info(f"当前仅获取到 {len(articles)} 篇文章，目标 {target_count} 篇，尝试扩展日期范围...")
        
        # 计算需要扩展的天数（每次扩展1天，最多扩展5天）
        current_days = (end_date_obj - start_date_obj).days
        extend_days = min(5, max(1, (target_count - len(articles)) // 10))
        
        extended_start = start_date_obj - timedelta(days=extend_days)
        extended_end = end_date_obj + timedelta(days=extend_days)
        
        logger.info(f"扩展日期范围: {extended_start} 到 {extended_end}")
        
        # 再次调用 arXiv API
        extended_arxiv = fetch_arxiv_papers(extended_start, extended_end, max_results=100)
        # 再次调用 GitHub API
        extended_github = fetch_github_trending(extended_start, extended_end, max_results=50)
        
        # 再次抓取 RSS
        extended_rss = []
        for source in sources:
            if source.get("type") != "rss":
                continue
            extended_rss.extend(fetch_rss_articles(source, hours, extended_start, extended_end))
        
        # 合并并去重（基于链接）
        existing_links = {a["link"] for a in articles}
        for article in extended_arxiv + extended_github + extended_rss:
            if article["link"] not in existing_links:
                articles.append(article)
                existing_links.add(article["link"])
    
    # 按发布时间倒序排列
    articles.sort(key=lambda x: x["published_at"], reverse=True)
    
    logger.info(f"抓取完成，共获取 {len(articles)} 篇文章")
    
    return articles


if __name__ == "__main__":
    """
    测试入口：测试实时模式和历史日期回溯模式
    """
    
    print("=" * 60)
    print("AI知识日报采集模块测试")
    print("=" * 60)
    
    # 测试1：实时模式（过去24小时）
    print("\n[测试1] 实时模式 - 抓取过去24小时文章")
    print("-" * 60)
    articles = fetch_all_articles(hours=24)
    
    print(f"共抓取到 {len(articles)} 篇文章")
    print("-" * 60)
    
    # 打印前3条资讯
    for i, article in enumerate(articles[:3], 1):
        print(f"\n【第 {i} 条】")
        print(f"标题: {article['title']}")
        print(f"信源: {article['source']}")
        print(f"权重: {article['weight']}")
        print(f"链接: {article['link']}")
        print(f"发布时间: {article['published_at']}")
        print(f"正文: {article['content'][:200]}...")  # 只显示前200字
        print("-" * 60)
    
    # 设置测试日期范围（最近7天，确保有足够的数据）
    test_end_date = datetime.now(timezone.utc).date()
    test_start_date = test_end_date - timedelta(days=7)
    
    # 测试2：历史日期回溯模式（arXiv API）
    print("\n[测试2] 历史日期回溯模式 - 通过 arXiv API 抓取论文")
    print("-" * 60)
    
    print(f"日期范围: {test_start_date} 到 {test_end_date}")
    
    arxiv_articles = fetch_arxiv_papers(test_start_date, test_end_date, max_results=10)
    
    print(f"arXiv API 共抓取到 {len(arxiv_articles)} 篇论文")
    print("-" * 60)
    
    # 打印前3条论文
    for i, article in enumerate(arxiv_articles[:3], 1):
        print(f"\n【第 {i} 篇论文】")
        print(f"标题: {article['title']}")
        print(f"信源: {article['source']}")
        print(f"权重: {article['weight']}")
        print(f"链接: {article['link']}")
        print(f"发布时间: {article['published_at']}")
        print(f"摘要: {article['content'][:200]}...")  # 只显示前200字
        print("-" * 60)
    
    # 测试3：历史日期回溯模式（GitHub API）
    print("\n[测试3] 历史日期回溯模式 - 通过 GitHub API 抓取热门仓库")
    print("-" * 60)
    
    print(f"日期范围: {test_start_date} 到 {test_end_date}")
    
    github_articles = fetch_github_trending(test_start_date, test_end_date, max_results=10)
    
    print(f"GitHub API 共抓取到 {len(github_articles)} 个仓库")
    print("-" * 60)
    
    # 打印前3个仓库
    for i, article in enumerate(github_articles[:3], 1):
        print(f"\n【第 {i} 个仓库】")
        print(f"标题: {article['title']}")
        print(f"信源: {article['source']}")
        print(f"权重: {article['weight']}")
        print(f"链接: {article['link']}")
        print(f"发布时间: {article['published_at']}")
        print(f"描述: {article['content'][:200]}...")  # 只显示前200字
        print("-" * 60)
    
    # 测试4：完整历史回溯模式（同时调用 arXiv + GitHub + RSS）
    print("\n[测试4] 完整历史回溯模式 - arXiv + GitHub + RSS")
    print("-" * 60)
    
    all_articles = fetch_all_articles(start_date=test_start_date, end_date=test_end_date)
    
    print(f"完整历史回溯共抓取到 {len(all_articles)} 篇文章")
    print("-" * 60)
    
    # 打印前3条综合结果
    for i, article in enumerate(all_articles[:3], 1):
        print(f"\n【第 {i} 条】")
        print(f"标题: {article['title']}")
        print(f"信源: {article['source']}")
        print(f"权重: {article['weight']}")
        print(f"链接: {article['link']}")
        print(f"发布时间: {article['published_at']}")
        print(f"正文: {article['content'][:200]}...")  # 只显示前200字
        print("-" * 60)
    
    print("\n测试完成！")