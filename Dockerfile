FROM python:3.13-slim

LABEL org.opencontainers.image.title="Bloomberg Asia News Crawler"
LABEL org.opencontainers.image.description="Crawl Bloomberg Asia headlines, generate bilingual (EN/CN) news briefs with AI summaries"
LABEL org.opencontainers.image.source="https://github.com/38370796-source/bmw-news"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建 crawl4ai 数据目录
RUN mkdir -p /app/.crawl4ai/cache /app/output

# 复制源码
COPY bloomberg_crawler.py .

# 环境变量默认值
ENV CRAWL4_AI_BASE_DIRECTORY=/app/.crawl4ai
ENV OUTPUT_DIR=/app/output
ENV BLOOMBERG_URL=https://www.bloomberg.com/asia
ENV LLM_MODEL=deepseek-chat
ENV LLM_BASE_URL=https://api.deepseek.com
ENV BATCH_SIZE=15

# 入口
ENTRYPOINT ["python", "bloomberg_crawler.py"]
