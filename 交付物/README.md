# AIBOX — AI 知识日报与课程生成智能体

> 云体验地址：[https://aibox-daily.streamlit.app/](https://aibox-daily.streamlit.app/)

---

## 一、项目简介

**AIBOX** 是一个自动化的 AI 知识聚合与课程生成智能体。它能够每日自动从多个信源（RSS 订阅、arXiv API、GitHub API）采集 AI 领域的最新动态，经过去重、打分、分类后，自动生成结构化的 AI 日报；用户可基于筛选后的资讯，勾选文章一键生成 1 课时课程教案，帮助团队高效追踪 AI 前沿进展。

### 核心亮点

- **日报自动生成**：每日 6:00（北京时间）自动采集、处理、生成 AI 日报
- **智能筛选**：多级去重策略 + 四维质量评分模型（0~10 分）
- **5 大分类**：模型发布、产品更新、行业动态、论文研究、技巧观点
- **LLM 驱动生成**：接入大语言模型，生成结构化课程教案
- **Mock 兜底**：无 API Key 时自动降级为模板生成，保证系统可用性
- **历史回溯**：支持指定日期范围回溯生成历史日报与教案

---

## 二、功能介绍

### 2.1 AI 动态

按 5 大分类浏览实时资讯，支持关键词搜索与时间线卡片展示。

### 2.2 AI 日报

查看每日生成的 AI 领域动态汇总，包含"今日 AI 焦点 TOP 5"和"5 大分类动态速览"两大板块，支持下载 Markdown 文件。

### 2.3 教案生成

基于筛选结果生成 1 课时结构化课程教案（60 分钟时间线），用户选择日期范围、勾选文章后一键生成。输出包含课程导入、热点拆解、原理讲解、互动讨论、课后任务等完整环节。

### 2.4 文件管理

管理已生成的日报与教案，支持预览、下载、删除及一键清空。

### 2.5 回收站

恢复或永久删除已移除的文件，保留最近 7 天内删除的项目，过期自动清理。

---

## 三、技术架构

### 系统架构图

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  外部信源    │    │  AIBOX 系统  │    │  输出交付    │
├─────────────┤    ├─────────────┤    ├─────────────┤
│ RSS 订阅源  │───▶│ 采集层      │───▶│ 文件系统    │
│ arXiv API   │    │ 处理层      │    │ Streamlit UI│
│ GitHub API  │    │ 生成层      │    │             │
└─────────────┘    │ 存储层      │    └─────────────┘
                   │ 调度层      │
                   └─────────────┘
```

### 技术栈

| 类别 | 选型 | 用途 |
| :--- | :--- | :--- |
| 语言 | Python 3.9+ | 核心开发语言 |
| 框架 | Streamlit ≥ 1.30.0 | Web 应用框架 |
| 调度 | APScheduler | 定时任务（每日 6:00 自动生成日报） |
| 采集 | feedparser + requests | RSS/API 数据抓取 |
| 解析 | beautifulsoup4 | HTML 清洗与文本提取 |
| 存储 | JSON 文件 + ChromaDB | 业务数据持久化 + 向量检索 |
| LLM | DeepSeek API | 课程生成引擎（支持 Mock 兜底） |

---

## 四、目录结构

```
ai_course_agent/
├── src/                    # 核心模块
│   ├── fetcher.py          # 采集层：多源数据抓取
│   ├── processor.py        # 处理层：去重、打分、分类
│   ├── generator.py        # 生成层：日报与教案生成
│   ├── database.py         # 存储层：文章数据持久化
│   └── vector_db.py        # 检索层：向量数据库与相似度搜索
├── config/
│   └── sources.yaml        # RSS 信源配置（10 个 RSS + 2 个 API）
├── data/
│   ├── articles_db.json    # 文章数据库
│   └── chromadb/           # ChromaDB 向量库
├── output/
│   ├── daily_reports/      # 日报 Markdown 文件
│   ├── lesson_plans/       # 教案 Markdown 文件
│   └── recycle_bin/        # 回收站（含 _meta.json 元数据）
├── cache/                  # 采集缓存 + 日报缓存
├── logs/                   # 运行日志
├── docs/                   # 项目文档
│   ├── 需求分析文档.md
│   └── 技术选型说明.md
├── 交付物/                 # 交付物汇总
│   ├── 源代码/             # 核心代码副本
│   ├── 技术文档.md         # 完整技术文档
│   └── README.md           # 本文件
├── app.py                  # Streamlit 主应用
├── scheduler.py            # 定时调度器
└── requirements.txt        # 依赖清单
```

---

## 五、安装指南

### 环境要求

- Python ≥ 3.9（推荐 3.10+）
- pip ≥ 21.0
- 现代浏览器（Chrome / Edge / Firefox）

### 安装步骤

```bash
# 1. 进入项目目录
cd ai_course_agent

# 2. 创建并激活虚拟环境
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

### API Key 配置（可选）

无 API Key 时系统使用 Mock 模式运行，可正常浏览资讯和生成日报。如需使用 LLM 生成高质量教案，需配置 API Key：

```bash
# 创建 .env 文件
# Windows PowerShell
@"
DEEPSEEK_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.deepseek.com/v1
"@ | Out-File -Encoding utf8 .env

# macOS/Linux
cat > .env << 'EOF'
DEEPSEEK_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.deepseek.com/v1
EOF
```

---

## 六、使用说明

### 启动应用

```bash
streamlit run app.py
```

启动后浏览器访问 `http://localhost:8501` 即可使用。

### 操作流程

#### 1. 浏览 AI 动态
- 默认进入「AI 动态」页面
- 点击顶部分类标签切换浏览（模型发布 / 产品更新 / 行业动态 / 论文研究 / 技巧观点）
- 使用搜索框按关键词过滤资讯

#### 2. 查看 AI 日报
- 切换到「AI 日报」页面
- 系统自动加载最近日报，可选择日期查看历史
- 点击「📥 下载日报」导出 Markdown 文件

#### 3. 生成课程教案
- 切换到「教案生成」页面
- 设置日期范围（近 7 天内）
- 在各分类 Tab 中勾选感兴趣的文章
- 点击「🚀 生成教案」按钮
- 在预览区查看、下载生成的教案

#### 4. 文件管理
- 切换到「文件管理」页面
- 切换日报/教案标签页进行预览、下载、删除
- 删除的文件暂存于回收站（保留 7 天）

#### 5. 回收站操作
- 切换到「回收站」页面
- 过期文件自动清理
- 支持恢复（回到原路径）和永久删除

---

## 七、注意事项

| 项目 | 说明 |
|------|------|
| API 密钥安全 | 切勿将 `.env` 文件提交到版本控制系统 |
| 首次启动 | 首次访问会自动抓取最近 7 天文章，可能需要数分钟 |
| 定时任务 | 调度器在后台线程中运行，需保持应用在线 |
| 时区处理 | 所有时间统一使用 UTC 存储，展示时转换为北京时间 |
| 磁盘空间 | 文章数据库和向量库会持续增长，建议定期清理 |
| 日志查看 | 调度器日志存储于 `logs/scheduler.log` |
| 端口冲突 | 默认端口 8501 被占用时，使用 `--server.port` 指定其他端口 |
| 教案生成 | 教案需用户主动选择文章后触发，非自动生成 |

---

## 八、风险与局限

| 风险 | 等级 | 应对措施 |
| :--- | :--- | :--- |
| LLM API 成本 | 中 | 内置 Mock 模式，可离线演示 |
| RSS 源不稳定 | 低 | 异常隔离，单源不影响全局 |
| 定时任务丢失 | 低 | APScheduler 补偿执行机制 |
| ChromaDB 依赖 | 低 | 降级为 TF-IDF / Jaccard 相似度 |