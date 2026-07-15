---
name: bloomberg-news-brief
description: >
  自动抓取 Bloomberg Asia 首页新闻，通过 AI 生成中英双语新闻简报。
  触发词：Bloomberg新闻摘要、Bloomberg简报、彭博新闻、bloomberg brief、bmw-news。
  当用户要求获取 Bloomberg 新闻、生成新闻摘要、抓取 Bloomberg 头条时使用此技能。
agent_created: true
---

# Bloomberg 新闻摘要

抓取 [Bloomberg Asia](https://www.bloomberg.com/asia) 首页所有新闻，通过 DeepSeek-chat 大模型生成中英双语标题（英文原标题 + 中文翻译）+ 100-200 字中文摘要，输出 Markdown 简报和 JSON 数据。

## 触发条件

当用户提出以下需求时触发此技能：
- "Bloomberg新闻摘要" / "彭博新闻简报" / "抓取Bloomberg头条"
- "bloomberg brief" / "bmw-news" / "彭博社新闻"
- 任何要求获取 Bloomberg 最新新闻的请求

## 工作流程

### 1. 确认环境

检查 Python 虚拟环境和依赖是否就绪：

```bash
# 确认 venv 存在且有 crawl4ai
ls .venv/bin/python3 && .venv/bin/pip list | grep -q crawl4ai
```

如果环境未就绪，按以下顺序搭建：
```bash
/Users/lw/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m venv .venv
export HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890
/Users/lw/.local/bin/uv pip install --python .venv/bin/python3 -r .workbuddy/skills/bloomberg-news-brief/scripts/requirements.txt
```

### 2. 运行爬虫

```bash
HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 .venv/bin/python3 .workbuddy/skills/bloomberg-news-brief/scripts/crawler.py
```

### 3. 展示结果

读取 `output/bloomberg_asia_brief_cn.md` 并展示摘要给用户。同时列出输出文件路径：
- `output/bloomberg_asia_brief_cn.md` — 双语 Markdown 简报
- `output/bloomberg_asia_brief_cn.json` — JSON 结构化数据

### 4. 注意事项

- 如未设置 `LLM_API_KEY` 环境变量，脚本会自动使用内置的 DeepSeek API Key，但建议提醒用户去 https://platform.deepseek.com 注册免费获取
- 如果代理无法连接，尝试检查 7890 端口是否可用：`curl -x http://127.0.0.1:7890 -s -o /dev/null -w "%{http_code}" https://www.bloomberg.com/asia`
- 抓取约需 2 秒，LLM 翻译约需 100 秒（89 条新闻），总计约 100 秒

## 输出格式

每条新闻包含：
- **英文原标题**（### 标题）
- **中文翻译标题**（加粗）
- **100-200 字中文摘要**（引用块）
- **原文 Bloomberg 链接**

## 技术栈

- **爬虫**: crawl4ai 0.9.2 (AsyncHTTPCrawlerStrategy)
- **LLM**: DeepSeek-chat (兼容 OpenAI API)
- **代理**: HTTP 代理 127.0.0.1:7890
