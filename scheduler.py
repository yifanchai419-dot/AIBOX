#!/usr/bin/env python3
"""
日报定时任务调度器

功能：每天早上6点自动生成日报，保存到缓存目录
日报内容为前一天00:00-24:00的新闻汇总

使用方式：
1. 直接运行: python scheduler.py
2. 作为模块导入: from scheduler import start_scheduler
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'scheduler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def get_daily_cache_path(date_str):
    """获取指定日期的日报缓存文件路径"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"report_{date_str}.json")


def save_daily_report_to_cache(date_str, report, articles):
    """保存日报数据到缓存"""
    cache_path = get_daily_cache_path(date_str)
    try:
        # 计算时间范围：前一天00:00-24:00
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        start_time = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
        end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, 999999)
        
        data = {
            "report": report,
            "articles": articles,
            "generated_at": datetime.now().isoformat(),
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


def generate_daily_report():
    """
    生成日报主函数
    
    时间范围：前一天00:00-24:00
    例如：7月24日6点运行时，抓取7月23日00:00到7月23日24:00的数据
    """
    logger.info("=" * 60)
    logger.info("开始执行定时任务：生成每日AI日报")
    logger.info("=" * 60)
    
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    
    # 计算时间范围：前一天00:00到前一天24:00（UTC时区）
    yesterday = today - timedelta(days=1)
    start_time = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    
    logger.info(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} 到 {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    try:
        # 导入模块
        from src.fetcher import fetch_all_articles
        from src.processor import DataProcessor
        from src.generator import CourseGenerator
        
        # 抓取指定时间范围的文章
        logger.info("开始抓取文章数据...")
        articles = fetch_all_articles(
            start_time=start_time,
            end_time=end_time
        )
        logger.info(f"抓取完成，共获取 {len(articles)} 篇文章")
        
        if not articles:
            logger.warning("未抓取到任何文章，跳过本次生成")
            return
        
        # 处理文章（使用Mock模式，不调用API）
        logger.info("开始处理文章（去重、打分、分类）...")
        processor = DataProcessor(use_api=False)
        processed_articles = processor.process_articles(articles)
        logger.info(f"处理完成，保留 {len(processed_articles)} 篇高质量文章")
        
        # 生成日报（使用Mock模式）
        logger.info("开始生成日报...")
        generator = CourseGenerator(use_api=False)
        report = generator.generate_daily_report(processed_articles)
        
        # 保存到缓存
        save_daily_report_to_cache(date_str, report, processed_articles)
        
        logger.info("=" * 60)
        logger.info("定时任务执行完成")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"定时任务执行失败: {str(e)}", exc_info=True)


def generate_initial_report():
    """
    生成初始日报（首次启动时执行）
    
    如果当天6点已过，生成当天的日报
    如果当天6点未到，生成昨天的日报
    """
    logger.info("检查是否需要生成初始日报...")
    
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    cache_path = get_daily_cache_path(date_str)
    
    # 如果当天缓存已存在，跳过
    if os.path.exists(cache_path):
        logger.info(f"当天日报缓存已存在: {cache_path}")
        return
    
    # 判断当前时间是否已过6点
    if now.hour >= 6:
        # 已过6点，生成当天日报
        logger.info("当前时间已过6点，生成当天日报...")
        generate_daily_report()
    else:
        # 未过6点，生成昨天的日报
        logger.info("当前时间未过6点，生成昨天的日报...")
        yesterday = now - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")
        cache_path = get_daily_cache_path(date_str)
        
        if os.path.exists(cache_path):
            logger.info(f"昨天日报缓存已存在: {cache_path}")
            return
        
        # 生成昨天的日报（时间范围：前天00:00到昨天24:00，UTC时区）
        two_days_ago = yesterday - timedelta(days=1)
        start_time = datetime(two_days_ago.year, two_days_ago.month, two_days_ago.day, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        
        try:
            from src.fetcher import fetch_all_articles
            from src.processor import DataProcessor
            from src.generator import CourseGenerator
            
            articles = fetch_all_articles(start_time=start_time, end_time=end_time)
            if articles:
                processor = DataProcessor(use_api=False)
                processed_articles = processor.process_articles(articles)
                generator = CourseGenerator(use_api=False)
                report = generator.generate_daily_report(processed_articles)
                save_daily_report_to_cache(date_str, report, processed_articles)
                logger.info(f"昨天日报生成完成: {date_str}")
            else:
                logger.warning("未抓取到昨天的文章")
        except Exception as e:
            logger.error(f"生成初始日报失败: {str(e)}")


def start_scheduler():
    """启动定时任务调度器"""
    logger.info("启动日报定时任务调度器...")
    
    # 创建后台调度器
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    
    # 添加每天6点的定时任务
    scheduler.add_job(
        generate_daily_report,
        trigger=CronTrigger(hour=6, minute=0),
        id="daily_report_generator",
        name="每日AI日报生成",
        replace_existing=True
    )
    
    # 添加每分钟检查任务（用于测试）
    # scheduler.add_job(
    #     generate_daily_report,
    #     trigger=CronTrigger(minute='*/1'),
    #     id="daily_report_generator_test",
    #     name="每日AI日报生成测试",
    #     replace_existing=True
    # )
    
    # 启动调度器
    scheduler.start()
    
    # 生成初始日报
    generate_initial_report()
    
    logger.info("定时任务调度器已启动")
    logger.info("每天早上6点自动生成日报")
    logger.info("按 Ctrl+C 停止")
    
    return scheduler


if __name__ == "__main__":
    """独立运行定时任务调度器"""
    scheduler = start_scheduler()
    
    # 保持进程运行
    try:
        while True:
            # 每秒检查一次
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭调度器...")
        scheduler.shutdown()
        logger.info("调度器已关闭")
