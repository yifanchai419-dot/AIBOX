import json
import os
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_FILE = os.path.join(DATA_DIR, "articles_db.json")

os.makedirs(DATA_DIR, exist_ok=True)

def load_articles_db():
    """加载文章数据库"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("articles", [])
        except Exception as e:
            print(f"加载数据库失败: {e}")
    return []

def save_articles_db(articles):
    """保存文章数据库"""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "articles": articles,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存数据库失败: {e}")
        return False

def add_new_articles(new_articles):
    """添加新文章，按URL去重，返回新增数量"""
    if not new_articles:
        return 0
    
    # 加载现有数据
    existing_articles = load_articles_db()
    
    # 获取现有链接集合
    existing_links = {article.get("link", "") for article in existing_articles if article.get("link")}
    
    # 过滤重复文章
    added_count = 0
    for article in new_articles:
        link = article.get("link", "")
        if link and link not in existing_links:
            existing_articles.append(article)
            existing_links.add(link)
            added_count += 1
    
    # 保存
    save_articles_db(existing_articles)
    return added_count

def cleanup_old_articles(days_to_keep=7):
    """清理超过指定天数的旧文章，返回删除数量"""
    articles = load_articles_db()
    if not articles:
        return 0
    
    # 计算截止时间（北京时区）
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    
    def is_recent(article):
        """判断文章是否在保留期内"""
        published_at = article.get("published_at", "")
        if not published_at:
            return True  # 没有时间戳的保留
        
        try:
            if published_at.endswith("Z"):
                published_at = published_at[:-1] + "+00:00"
            dt = datetime.fromisoformat(published_at)
            return dt >= cutoff_time
        except Exception:
            return True  # 解析失败的保留
    
    # 过滤保留文章
    filtered = [a for a in articles if is_recent(a)]
    deleted_count = len(articles) - len(filtered)
    
    if deleted_count > 0:
        save_articles_db(filtered)
    
    return deleted_count

def get_recent_articles(days=7):
    """获取最近指定天数的文章"""
    articles = load_articles_db()
    
    # 计算截止时间
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
    
    def is_recent(article):
        published_at = article.get("published_at", "")
        if not published_at:
            return True
        
        try:
            if published_at.endswith("Z"):
                published_at = published_at[:-1] + "+00:00"
            dt = datetime.fromisoformat(published_at)
            return dt >= cutoff_time
        except Exception:
            return True
    
    return [a for a in articles if is_recent(a)]

def get_all_articles():
    """获取所有文章"""
    return load_articles_db()

def get_articles_count():
    """获取文章总数"""
    return len(load_articles_db())

if __name__ == "__main__":
    # 测试
    print("数据库测试:")
    print(f"文章总数: {get_articles_count()}")
    
    # 测试清理
    deleted = cleanup_old_articles(7)
    print(f"清理旧文章数量: {deleted}")
    
    # 测试获取最近7天
    recent = get_recent_articles(7)
    print(f"最近7天文章数: {len(recent)}")
