import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, timezone
from src.fetcher import fetch_all_articles, parse_published_time, load_sources, fetch_rss_articles

# 设置测试日期（7月22日）
test_date = datetime(2026, 7, 22).date()

print("=" * 80)
print("测试历史日期数据抓取")
print(f"测试日期: {test_date}")
print("=" * 80)

# 测试1: 直接测试fetch_all_articles
print("\n[测试1] 调用fetch_all_articles获取历史日期数据")
print("-" * 80)
articles = fetch_all_articles(start_date=test_date, end_date=test_date)
print(f"共抓取到 {len(articles)} 篇文章")

# 打印每篇文章的详细信息
print("\n[测试2] 打印所有文章的发布时间和来源")
print("-" * 80)
print(f"{'序号':<4} {'发布时间':<35} {'来源':<20} {'标题'}")
print("-" * 80)

for i, article in enumerate(articles, 1):
    pub_time = article.get("published_at", "")
    source = article.get("source", "")
    title = article.get("title", "")[:60]
    print(f"{i:<4} {pub_time:<35} {source:<20} {title}")

# 测试3: 检查时间解析是否正确
print("\n[测试3] 验证时间解析")
print("-" * 80)

# 测试时间范围
start_datetime = datetime.combine(test_date, datetime.min.time(), tzinfo=timezone.utc)
end_datetime = datetime.combine(test_date, datetime.max.time(), tzinfo=timezone.utc)

print(f"期望时间范围 (UTC): {start_datetime} 到 {end_datetime}")

# 检查每篇文章的时间是否在范围内
out_of_range = []
for article in articles:
    pub_time_str = article.get("published_at", "")
    try:
        pub_time = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
        if not (start_datetime <= pub_time <= end_datetime):
            out_of_range.append((article, pub_time))
    except Exception as e:
        print(f"解析时间失败: {pub_time_str} - {e}")

if out_of_range:
    print(f"\n⚠️ 发现 {len(out_of_range)} 篇文章不在期望时间范围内:")
    for article, pub_time in out_of_range:
        print(f"  - {pub_time} | {article.get('source', '')} | {article.get('title', '')[:50]}")
else:
    print("\n✅ 所有文章都在期望时间范围内")

# 测试4: 单独测试各个RSS源
print("\n[测试4] 单独测试各个RSS源的时间过滤")
print("-" * 80)

sources = load_sources()
for source in sources:
    if source.get("type") != "rss":
        continue
    
    source_name = source.get("name", "Unknown")
    print(f"\n测试信源: {source_name}")
    
    source_articles = fetch_rss_articles(source, hours=24, start_date=test_date, end_date=test_date)
    
    print(f"  返回文章数: {len(source_articles)}")
    
    # 打印前3篇文章的时间
    for j, article in enumerate(source_articles[:3], 1):
        print(f"  {j}. {article.get('published_at', '')} | {article.get('title', '')[:50]}")
