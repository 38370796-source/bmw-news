#!/usr/bin/env python3
"""
Bloomberg Asia News Crawler v3 — 中英双语简报
使用 crawl4ai 抓取 Bloomberg Asia 首页新闻，OpenAI LLM 生成中英双语标题和摘要。
代理：http://127.0.0.1:7890
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

# 设置 crawl4ai 数据目录
CRAWL4AI_DIR = Path(__file__).parent / ".crawl4ai"
CRAWL4AI_DIR.mkdir(parents=True, exist_ok=True)
(CRAWL4AI_DIR / "cache").mkdir(exist_ok=True)
os.environ["CRAWL4_AI_BASE_DIRECTORY"] = str(CRAWL4AI_DIR)

from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.async_configs import CrawlerRunConfig, ProxyConfig
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy
from openai import OpenAI

# ========== 配置 ==========
PROXY = os.environ.get("HTTP_PROXY", os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890"))
TARGET_URL = os.environ.get("BLOOMBERG_URL", "https://www.bloomberg.com/asia")
BASE_URL = "https://www.bloomberg.com"
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(Path(__file__).parent / "output")))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# LLM 配置（通过环境变量传入，支持 OpenAI 兼容 API）
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "15"))

# ========== Bloomber 爬取 ==========


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    if not url.startswith("http"):
        return urljoin(BASE_URL + "/", url)
    return url


def parse_bloomberg_markdown(markdown: str) -> list[dict]:
    """从 crawl4ai 的 Markdown 输出中提取新闻条目"""
    items = []
    seen_urls = set()
    lines = markdown.split("\n")

    link_pattern = re.compile(r'\[([^\]]*?)\]\((https?://[^\s)]+)\)')

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        matches = link_pattern.findall(line)
        for text, url in matches:
            if "assets.bwbx.io" in url:
                continue
            if "/news/" not in url:
                continue
            if text.strip().isdigit() or re.match(r'^\d+:\d+$', text.strip()):
                continue
            if len(text.strip()) < 5:
                continue

            normalized = normalize_url(url)
            if normalized in seen_urls:
                continue
            seen_urls.add(normalized)

            article_type = "video" if "/news/videos/" in url else "article"

            headline = text.strip()
            headline = re.sub(r'!\[.*?\]\(.*?\)', '', headline).strip()
            headline = re.sub(r'^(Video|Opinion|Analysis|Exclusive|Watch|Listen)\s*[:\-]?\s*', '', headline)
            headline = re.sub(r'^\d+:\d+\s*', '', headline)
            headline = re.sub(r'^Newsletter:\s*', '', headline)
            headline = ' '.join(headline.split())

            if len(headline) < 10:
                continue

            # 查找摘要
            summary = ""
            for offset in [-1, 1]:
                idx = i + offset
                if 0 <= idx < len(lines):
                    ctx = lines[idx].strip()
                    if ctx and "assets.bwbx.io" not in ctx and "bloomberg.com" not in ctx:
                        ctx = re.sub(r'!\[.*?\]\(.*?\)', '', ctx).strip()
                        ctx = re.sub(r'\[.*?\]\(.*?\)', '', ctx).strip()
                        if len(ctx) > 20 and not ctx.startswith("###"):
                            summary = ctx
                            break

            items.append({
                "headline": headline,
                "url": normalized,
                "type": article_type,
                "summary": summary[:300],
                "raw_line": line[:200],
            })

    return items


# ========== LLM 处理 ==========

def build_translate_prompt(items: list[dict]) -> str:
    """构建 LLM 翻译和摘要的 prompt"""
    items_text = []
    for idx, item in enumerate(items):
        snippet = item.get("summary", "") or item.get("raw_line", "")
        items_text.append(
            f"[{idx}]\n"
            f"Title: {item['headline']}\n"
            f"Context: {snippet[:200]}\n"
        )

    joined = "\n".join(items_text)
    return f"""You are a professional financial news editor. Process the following Bloomberg Asia news items.

For EACH item, provide:
1. **Chinese title**: Accurate, concise Chinese translation of the English title (use financial/economic terminology properly)
2. **Chinese summary**: 100-200 Chinese characters that capture the key information. Include key data points (numbers, percentages, amounts) when present.

Format each result EXACTLY as:
---
[ID]: <item_index>
CN_TITLE: <Chinese title>
CN_SUMMARY: <100-200 char Chinese summary>
---

Here are the news items:

{joined}

Output all results in the specified format. Do not skip any item."""


def parse_llm_response(response: str, item_count: int) -> list[dict]:
    """解析 LLM 返回的结构化结果"""
    results = []
    blocks = re.split(r'\n---\n|^---\n|\n---$', response.strip())

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # 匹配多种 ID 格式: [ID]: 0, [0]:, [ID]:0
        idx_match = re.search(r'\[(?:ID\]|[0-9]+)\]:\s*(\d+)', block)
        if not idx_match:
            # Fallback: just look for [N]: pattern
            idx_match = re.search(r'\[(\d+)\]:', block)
        
        cn_title_match = re.search(r'CN_TITLE:\s*(.+?)(?:\n|$)', block)
        cn_summary_match = re.search(r'CN_SUMMARY:\s*(.+?)(?:\n|$)', block)

        if idx_match:
            idx = int(idx_match.group(1))
            results.append({
                "idx": idx,
                "cn_title": (cn_title_match.group(1).strip() if cn_title_match else ""),
                "cn_summary": (cn_summary_match.group(1).strip() if cn_summary_match else ""),
            })

    return results


async def llm_process_batch(client: OpenAI, items: list[dict], batch_id: int) -> list[dict]:
    """使用 LLM 处理一批新闻"""
    print(f"  🤖 LLM 处理第 {batch_id} 批 ({len(items)} 条)...", end=" ", flush=True)

    prompt = build_translate_prompt(items)

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional bilingual financial news editor. Always respond in the exact format specified."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        content = response.choices[0].message.content
        parsed = parse_llm_response(content, len(items))

        # 合并结果
        results = []
        for i, item in enumerate(items):
            llm_data = next((p for p in parsed if p["idx"] == i), {})
            results.append({
                **item,
                "cn_title": llm_data.get("cn_title", ""),
                "cn_summary": llm_data.get("cn_summary", ""),
            })

        print(f"✅")
        return results

    except Exception as e:
        print(f"❌ {e}")
        # 返回原文，不翻译
        return [{**item, "cn_title": "", "cn_summary": f"[LLM 处理失败: {e}]"} for item in items]


# ========== 格式化输出 ==========

def format_bilingual_brief(all_items: list[dict], crawl_time: str) -> str:
    """格式化为中英双语简报"""
    articles = [i for i in all_items if i["type"] == "article"]
    videos = [i for i in all_items if i["type"] == "video"]

    lines = [
        "# 📰 Bloomberg Asia 双语新闻简报",
        f"**抓取时间**: {crawl_time}",
        f"**来源**: {TARGET_URL}",
        f"**共 {len(all_items)} 条**（文章 {len(articles)} 篇 + 视频 {len(videos)} 个）",
        "",
        "---",
        "",
        "## 📝 新闻文章",
        "",
    ]

    for i, item in enumerate(articles, 1):
        en_title = item["headline"]
        cn_title = item.get("cn_title", "")
        cn_summary = item.get("cn_summary", "")
        url = item["url"]

        lines.append(f"### {i}. {en_title}")
        if cn_title:
            lines.append(f"**{cn_title}**")
        if cn_summary:
            lines.append(f"> {cn_summary}")
        lines.append(f"🔗 {url}")
        lines.append("")

    if videos:
        lines.append("## 🎬 视频报道")
        lines.append("")
        for i, item in enumerate(videos, 1):
            en_title = item["headline"]
            cn_title = item.get("cn_title", "")
            url = item["url"]
            lines.append(f"{i}. 🎥 **{en_title}**")
            if cn_title:
                lines.append(f"   *{cn_title}*")
            lines.append(f"   🔗 {url}")
            lines.append("")

    lines.extend(["---", "", f"*使用 crawl4ai + {LLM_MODEL} 自动生成 — Proxy: 127.0.0.1:7890*"])
    return "\n".join(lines)


# ========== 主流程 ==========

async def main():
    start_time = time.time()

    print("=" * 60)
    print("  Bloomberg Asia 双语新闻简报生成器 v3")
    print(f"  目标: {TARGET_URL}")
    print(f"  代理: {PROXY}")
    print(f"  LLM:  {LLM_MODEL}")
    print("=" * 60)
    print()

    # Phase 1: 爬取
    print("🔄 Phase 1: 爬取 Bloomberg Asia 首页...")
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        proxy_config=ProxyConfig(server=PROXY),
    )

    async with AsyncWebCrawler(
        verbose=True,
        crawler_strategy=AsyncHTTPCrawlerStrategy(),
    ) as crawler:
        result = await crawler.arun(url=TARGET_URL, config=run_config)

    if not result.success:
        print(f"❌ 请求失败: {result.error_message}")
        return

    print(f"✅ 爬取成功 (HTML: {len(result.html or '')} 字符, MD: {len(result.markdown or '')} 字符)")
    print()

    # Phase 2: 解析
    print("🔍 Phase 2: 解析 Markdown 提取新闻...")
    items = parse_bloomberg_markdown(result.markdown or "")

    # 去重
    unique = {item["url"]: item for item in items}
    items = list(unique.values())

    articles = [i for i in items if i["type"] == "article"]
    videos = [i for i in items if i["type"] == "video"]

    print(f"📊 提取: {len(items)} 条（文章 {len(articles)} + 视频 {len(videos)}）")
    print()

    # Phase 3: LLM 翻译生成
    if not LLM_API_KEY:
        print("⚠️ 未设置 OPENAI_API_KEY / DEEPSEEK_API_KEY，跳过 LLM 翻译，仅输出英文标题")
        all_processed = items
    else:
        print("🤖 Phase 3: LLM 双语翻译 + 摘要生成...")
        client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
        )

        all_processed = []

        # 分批处理
        for batch_idx in range(0, len(items), BATCH_SIZE):
            batch = items[batch_idx:batch_idx + BATCH_SIZE]
            batch_id = batch_idx // BATCH_SIZE + 1

            processed_batch = await llm_process_batch(client, batch, batch_id)
            all_processed.extend(processed_batch)

            # 请求间短暂延迟
            if batch_idx + BATCH_SIZE < len(items):
                await asyncio.sleep(1)

        print(f"✅ LLM 处理完成 ({len(all_processed)} 条)")
        print()

    # Phase 4: 输出
    crawl_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    brief_md = format_bilingual_brief(all_processed, crawl_time)

    md_path = OUTPUT_DIR / "bloomberg_asia_brief_cn.md"
    md_path.write_text(brief_md, encoding="utf-8")
    print(f"✅ 双语简报: {md_path}")

    json_path = OUTPUT_DIR / "bloomberg_asia_brief_cn.json"
    json_path.write_text(
        json.dumps(all_processed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ JSON 数据: {json_path}")

    elapsed = time.time() - start_time
    print(f"\n⏱ 总耗时: {elapsed:.1f}s")
    print(f"📄 简报文件在 output/ 目录下")


if __name__ == "__main__":
    asyncio.run(main())
