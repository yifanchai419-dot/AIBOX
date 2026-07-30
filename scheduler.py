#!/usr/bin/env python3
"""
日报定时任务调度器

功能：每天早上6点自动生成日报，保存到缓存目录
日报内容为前一天00:00-24:00的新闻汇总（北京时间）

使用方式：
1. 作为模块导入: from scheduler import start_scheduler, ensure_daily_report_ready
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 北京时间
BJT = timezone(timedelta(hours=8))

# 配置日志
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'scheduler.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

# 全局调度器引用，确保单例
_scheduler_instance = None


def get_daily_cache_path(date_str):
    """获取指定日期的日报缓存文件路径"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"report_{date_str}.json")


def get_daily_report_md_path(date_str):
    """获取指定日期的日报 Markdown 文件路径"""
    daily_reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "daily_reports")
    os.makedirs(daily_reports_dir, exist_ok=True)
    return os.path.join(daily_reports_dir, f"daily_report_{date_str}.md")


def save_daily_report_to_cache(date_str, report, articles):
    """保存日报数据到缓存"""
    cache_path = get_daily_cache_path(date_str)
    try:
        # 时间范围使用北京时间：date_str 对应那天的 00:00 - 24:00
        report_date = datetime.strptime(date_str, "%Y%m%d")
        start_time = datetime(report_date.year, report_date.month, report_date.day, 0, 0, 0, tzinfo=BJT)
        end_time = datetime(report_date.year, report_date.month, report_date.day, 23, 59, 59, 999999, tzinfo=BJT)

        data = {
            "report": report,
            "articles": articles,
            "generated_at": datetime.now(BJT).isoformat(),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"日报缓存已保存: {cache_path}")
        return True
    except Exception as e:
        logger.error(f"保存缓存失败: {str(e)}")
        return False


def generate_daily_report_for_date(target_date: datetime.date, force: bool = False):
    """
    为指定日期生成日报。

    参数：
        target_date: 日报对应的数据日期（北京时间）
        force: 是否强制重新生成（默认 False，已存在则跳过）
    """
    date_str = target_date.strftime("%Y%m%d")
    output_path = get_daily_report_md_path(date_str)
    cache_path = get_daily_cache_path(date_str)

    if not force and os.path.exists(output_path):
        logger.info(f"日报已存在，跳过生成: {output_path}")
        return "exists"

    logger.info("=" * 60)
    logger.info(f"开始生成 {date_str} 的 AI 日报")
    logger.info("=" * 60)

    # 时间范围：当天 00:00:00 到 23:59:59（北京时间）
    start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=BJT)
    end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tzinfo=BJT)

    # 对应 UTC 时间范围（用于对比数据库中的 UTC 时间戳）
    utc_start = start_time.astimezone(timezone.utc)
    utc_end = end_time.astimezone(timezone.utc)

    logger.info(f"北京时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} 到 {end_time.strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"UTC 时间范围: {utc_start.strftime('%Y-%m-%d %H:%M')} 到 {utc_end.strftime('%Y-%m-%d %H:%M')}")

    try:
        # 导入处理模块
        from src.database import get_all_articles
        from src.processor import DataProcessor
        from src.generator import CourseGenerator

        # 读取数据库中的所有文章
        logger.info("从持久化数据库中读取文章...")
        all_articles = get_all_articles()
        logger.info(f"数据库中共有 {len(all_articles)} 篇文章")

        # 过滤指定时间范围内的文章
        def in_time_range(article):
            published_at = article.get("published_at", "")
            if not published_at:
                return False
            try:
                if published_at.endswith("Z"):
                    published_at = published_at[:-1] + "+00:00"
                dt = datetime.fromisoformat(published_at)
                # 转为 UTC 进行统一对比
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return utc_start <= dt <= utc_end
            except Exception:
                return False

        filtered_articles = [a for a in all_articles if in_time_range(a)]
        logger.info(f"筛选出 {len(filtered_articles)} 篇指定时间范围内的文章")

        if not filtered_articles:
            logger.warning("未找到指定时间范围内的文章，尝试增量抓取补充数据...")
            try:
                from src.fetcher import fetch_all_articles
                articles = fetch_all_articles(start_time=start_time, end_time=end_time)
                if articles:
                    processor = DataProcessor(use_api=False)
                    filtered_articles = processor.process_articles(articles)
                    from src.database import add_new_articles
                    add_new_articles(filtered_articles)
                    logger.info(f"增量抓取完成，共获取 {len(filtered_articles)} 篇文章")
                else:
                    logger.warning("增量抓取也未成功，跳过本次生成")
                    return "no_data"
            except Exception as e:
                logger.error(f"增量抓取失败: {str(e)}")
                return "no_data"

        # 确保文章都有 category 和 score 字段
        processor = DataProcessor(use_api=False)
        for article in filtered_articles:
            if "category" not in article:
                article["category"] = processor.classify_article(article)
            if "score" not in article:
                article["score"] = processor.score_article(article)

        # 生成日报（使用 Mock 模式保证格式稳定）
        logger.info("开始生成日报内容...")
        generator = CourseGenerator(use_api=False)
        report = generator.generate_daily_report(filtered_articles)

        # 保存到缓存
        save_daily_report_to_cache(date_str, report, filtered_articles)

        # 保存到文件管理的日报板块
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"日报已保存: {output_path}")

        logger.info("=" * 60)
        logger.info(f"{date_str} 日报生成完成")
        logger.info("=" * 60)
        return "ok"

    except Exception as e:
        logger.error(f"生成日报失败: {str(e)}", exc_info=True)
        return "error"


def generate_daily_report():
    """
    定时任务入口：生成"昨天"的日报（前一天 00:00-24:00 北京时间）。
    """
    now_bjt = datetime.now(BJT)
    today = now_bjt.date()
    yesterday = today - timedelta(days=1)

    result = generate_daily_report_for_date(yesterday)
    return result


def ensure_daily_reports_ready():
    """
    启动时检查并补齐缺失的日报：
    - 检查最近 7 天的日报，逐个补齐缺失的
    - 确保调度器长期未运行后的数据完整性
    """
    now_bjt = datetime.now(BJT)
    today = now_bjt.date()

    logger.info(f"启动时日报检查：当前北京时间 {now_bjt.strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查最近 7 天的日报，逐个补齐
    days_to_check = [today - timedelta(days=i) for i in range(1, 8)]
    for target_date in days_to_check:
        if target_date >= today:
            continue
        date_str = target_date.strftime("%Y%m%d")
        output_path = get_daily_report_md_path(date_str)
        if not os.path.exists(output_path):
            logger.info(f"发现 {date_str} 的日报缺失，正在生成...")
            try:
                result = generate_daily_report_for_date(target_date)
                logger.info(f"{date_str} 日报生成结果: {result}")
            except Exception as e:
                logger.error(f"生成 {date_str} 日报时发生异常: {str(e)}", exc_info=True)
        else:
            logger.info(f"{date_str} 的日报已存在，无需生成")

    return True


def start_scheduler():
    """启动定时任务调度器（单例）"""
    global _scheduler_instance
    if _scheduler_instance is not None and _scheduler_instance.running:
        logger.info("调度器已在运行，跳过重复启动")
        return _scheduler_instance

    logger.info("启动日报定时任务调度器...")
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

    # 每天早上 6:00 执行（北京时间）
    scheduler.add_job(
        generate_daily_report,
        trigger=CronTrigger(hour=6, minute=0),
        id="daily_report_generator",
        name="每日AI日报生成",
        replace_existing=True,
        misfire_grace_time=3600,   # 允许 1 小时的补偿窗口，防止进程重启导致错过任务
        coalesce=True              # 合并积压的任务
    )

    scheduler.start()
    _scheduler_instance = scheduler

    logger.info("定时任务调度器已启动")
    logger.info("每天早上 6:00（北京时间）自动生成前一天的日报")

    # 启动时立即检查并补齐缺失的日报
    try:
        ensure_daily_reports_ready()
    except Exception as e:
        logger.error(f"启动时日报检查失败: {str(e)}", exc_info=True)

    return scheduler


def stop_scheduler():
    """停止定时任务调度器"""
    global _scheduler_instance
    if _scheduler_instance is not None and _scheduler_instance.running:
        try:
            _scheduler_instance.shutdown(wait=False)
            logger.info("定时任务调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {str(e)}")
    _scheduler_instance = None


if __name__ == "__main__":
    scheduler = start_scheduler()
    try:
        import time
        while True:
            time.sleep(60)
            # 每分钟输出一次当前状态
            jobs = scheduler.get_jobs()
            if jobs:
                next_run = jobs[0].next_run_time
                if next_run:
                    logger.info(f"调度器运行中，下次触发时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭调度器...")
        stop_scheduler()
