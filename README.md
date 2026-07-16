# BMW-News — Bloomberg Asia 双语新闻简报

> 自动抓取 Bloomberg Asia 首页新闻，通过 AI 生成中英双语标题 + 100-200 字中文摘要

## 功能

- 🔍 抓取 [Bloomberg Asia](https://www.bloomberg.com/asia) 首页全部新闻
- 🤖 AI 生成中文标题和摘要（支持 DeepSeek / OpenAI 兼容 API）
- 📝 输出 Markdown 双语简报 + JSON 数据
- 🐳 Docker 一键部署

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/38370796-source/bmw-news.git
cd bmw-news

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 LLM_API_KEY（去 https://platform.deepseek.com 免费注册获取）
# 如果在国内无需代理访问 Bloomberg，删掉 HTTP_PROXY 那行即可

# 3. 启动
docker compose up --build
```

### 非 Docker 方式

```bash
pip install -r requirements.txt
LLM_API_KEY=your_key python bloomberg_crawler.py
```
> 需要 Python 3.13+

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_API_KEY` | ✅ | - | LLM API Key（DeepSeek / OpenAI 兼容） |
| `LLM_BASE_URL` | - | `https://api.deepseek.com` | LLM API 地址 |
| `LLM_MODEL` | - | `deepseek-chat` | 模型名称 |
| `HTTP_PROXY` | - | - | HTTP 代理（访问 Bloomberg 用） |
| `BLOOMBERG_URL` | - | `https://www.bloomberg.com/asia` | 目标 URL |
| `BATCH_SIZE` | - | `15` | 每批 LLM 处理数量 |


## 使用方式

根据你执行的 docker compose up --build 命令，输出内容会以两种方式呈现，你可以按以下步骤查看：

方式一：直接查看终端实时输出（最快）

当你运行 docker compose up --build 后，终端会实时打印爬虫和AI生成的进度及结果。
最终生成的Markdown格式双语简报会直接显示在终端日志里，你可以直接翻阅终端内容查看。

方式二：查看生成的文件（持久化保存）

程序运行结束后，会在你当前的 bmw-news 目录下生成两个输出文件：
1. Markdown简报（方便阅读）：output_YYYY-MM-DD_HH-MM-SS.md
   （文件名带时间戳，例如 output_2026-07-16_10-30-25.md）
2. JSON数据（方便程序处理）：output_YYYY-MM-DD_HH-MM-SS.json

👉 查看方法：
在 bmw-news 目录下直接列出文件：
ls -l output_*.md output_*.json

用编辑器打开查看（以VS Code为例）：
code output_2026-07-16_*.md  # 替换为实际文件名

或用命令行查看：
cat output_2026-07-16_*.md


💡 补充说明

1. 为什么找不到文件？
   • 如果终端最后没有显示 Generating report... 之类的日志，可能是爬虫失败（如网络问题、Bloomberg反爬）。请检查终端是否有报错（红色错误日志）。

   • 如果使用了代理，请确保 .env 中的 HTTP_PROXY 填写正确。

2. 想重新运行？
   停止当前容器（Ctrl+C），然后再次运行：
   docker compose up
   
   （不需要再加 --build，除非你修改了代码）

3. 非Docker方式输出位置相同
   如果你后来尝试了非Docker方式（python bloomberg_crawler.py），文件同样生成在当前目录。


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
