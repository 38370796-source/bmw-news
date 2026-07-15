# BMW-News — Bloomberg Asia 双语新闻简报

> 自动抓取 Bloomberg Asia 首页新闻，通过 AI 生成中英双语标题 + 100-200 字中文摘要

## 功能

- 🔍 抓取 [Bloomberg Asia](https://www.bloomberg.com/asia) 首页全部新闻
- 🤖 AI 生成中文标题和摘要（支持 DeepSeek / OpenAI 兼容 API）
- 📝 输出 Markdown 双语简报 + JSON 数据
- 🐳 Docker 一键部署

## 快速开始

### 1. 配置

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM_API_KEY
```

### 2. 运行

```bash
# Docker Compose（推荐）
docker compose up --build

# 或直接用 Python（需 Python 3.13+）
pip install -r requirements.txt
LLM_API_KEY=your_key python bloomberg_crawler.py
```

### 3. 查看结果

简报输出在 `output/` 目录：
- `bloomberg_asia_brief_cn.md` — 双语 Markdown 简报
- `bloomberg_asia_brief_cn.json` — JSON 结构化数据

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_API_KEY` | ✅ | - | LLM API Key（DeepSeek / OpenAI 兼容） |
| `LLM_BASE_URL` | - | `https://api.deepseek.com` | LLM API 地址 |
| `LLM_MODEL` | - | `deepseek-chat` | 模型名称 |
| `HTTP_PROXY` | - | - | HTTP 代理（访问 Bloomberg 用） |
| `BLOOMBERG_URL` | - | `https://www.bloomberg.com/asia` | 目标 URL |
| `BATCH_SIZE` | - | `15` | 每批 LLM 处理数量 |

## 输出示例

```markdown
### 1. ASML Raises Outlook, Plans Capacity Hike as AI Boosts Demand
**ASML上调业绩展望并计划扩产，AI需求推动增长**
> ASML因人工智能需求强劲，上调销售预测并计划提高产能。此举显示半导体行业前景乐观，
AI技术正成为关键增长驱动力。摩根士丹利也受益于股市交易热潮，业绩表现亮眼。
🔗 https://www.bloomberg.com/news/articles/2026-07-15/asml-...
```

## 技术栈

- **爬虫**: crawl4ai (AsyncHTTPCrawlerStrategy)
- **LLM**: DeepSeek-chat (OpenAI 兼容)
- **容器化**: Docker + Docker Compose
- **语言**: Python 3.13+
