---
name: policy-search-china
description: "Search Chinese government policy documents from 7 ministries. Extract verbatim paragraphs with source links."
license: MIT
---

# Policy Search China

Search Chinese government policy documents (State Council, MIIT, NDRC, SASAC, NEA, CAC, NDA) and extract verbatim paragraphs for reports and planning. Commander plans, workers execute — five-stage pipeline with parallel search and extraction.

## Decision Guide

| 用户需求 | 执行链 | 命令 |
|----------|--------|------|
| 全面扫描（"近两年AI政策"） | **broad 链** | `chain_runner.py --chain broad --keywords "人工智能" --start 2024-01-01` |
| 交叉分析（"AI和能源结合"） | **cross 链** | `chain_runner.py --chain cross --keywords "人工智能" "能源" --start 2024-01-01` |
| 精准定位（"数据二十条确权"） | **locate 链** | `chain_runner.py --chain locate --keywords "确权"` |
| 溯源引用（"这句话出自哪"） | **trace 链** | `chain_runner.py --chain trace --keywords "原句..."` |
| 输出 HTML 汇编 | 生成脚本 | `rebuild_policy_html.py --topic "A" --topic "B" --mode and` |

## Core Pipeline

Commander (Agent) plans and reviews at each stage; workers (scripts) execute mechanically. Workers never decide — they return structured data for the Commander to evaluate.

### Stage 0：确认缓存新鲜度

```python
from atoms import check_cache_freshness

freshness = check_cache_freshness(cache_dir)
# → {"latest_date": "2026-07-28", "needs_web_update": False}
```

> **Commander** checks `needs_web_update` — if True, enable Web supplement search in Stage 1.

### Stage 1：并行搜索 — Commander 规划，工人执行

```python
from atoms import search_cache_title

# Commander decides keywords based on user intent
# Workers run each keyword in parallel (ThreadPoolExecutor)
hits_ai  = search_cache_title(cache_dir, "人工智能")  # → 32 results
hits_en  = search_cache_title(cache_dir, "能源")      # → 19 results
```

> **Commander** decomposes user intent into keywords. For broad scan, plan sub-domains first (e.g. "数字化" → AI, data, IoT, computing).  
> **Commander** evaluates: "32 AI results + 19 energy results — reasonable scale, proceed to filter."  
> If cache is stale: launch `web_search("site:gov.cn 人工智能 2025")` in parallel with cache search.

### Stage 2：过滤 + 去重 — Commander 定条件，工人链式执行

```python
from atoms import intersect_entries, filter_date_range, deduplicate_entries

# Commander decides: AND intersection + 2024+ time filter
result = intersect_entries(hits_ai, hits_en)           # 2.4 AND
result = filter_date_range(result, "2024-01-01", None) # 2.1 time
# Optional: filter_issuer / filter_doctype / exclude_entries
result = deduplicate_entries(result)                    # dedup at end
# → 3 entries (clean, ready for extraction)
```

> **Commander** decides filter criteria: date range, issuers, doc types, exclude keywords.  
> **Commander** reviews output: "3 entries after filtering — tight intersection. Proceed to extraction."

### Stage 3：工人并行提取段落

```python
from rebuild_policy_html import extract_paragraphs
from chain_runner import extract_all_paragraphs

# Workers extract in parallel, Commander receives aggregated results
groups = extract_all_paragraphs(result, ["人工智能", "能源"])
# → [(entry, [(para, chapter), ...]), ...]  — 2 groups, 71 paragraphs
```

> Workers handle all I/O: file reading, URL fallback (HTTPS→HTTP→browser→search→mirror), text extraction, keyword matching.  
> Commander does not need to worry about unreachable URLs or file format issues.

### Stage 4：输出 + 审核

```python
from rebuild_policy_html import build_html

html = build_html("AI与能源政策汇编", groups, ["人工智能", "能源"])
# Writes to output/ — includes source links, highlights, verification tags
```

> **Commander reviews** before delivery:
> - Coverage: 3 policies, 71 paragraphs — tight intersection, check if any key policy is missing
> - Links: verify 1-2 source_url fields are accessible
> - If coverage is insufficient, return to Stage 1 with broader keywords

## Setup

```bash
python3 scripts/init.py
```

## Source Coverage

| 缓存文件 | 部门 | site: 搜索前缀 |
|---------|------|---------------|
| `gov.json` | 国务院 | `site:gov.cn/zhengce/zhengceku/` |
| `miit.json` | 工信部 | `site:miit.gov.cn` |
| `nda.json` | 国家数据局 | `site:nda.gov.cn` |
| `sasac.json` | 国资委 | `site:gov.cn 国资委` |
| `nea.json` | 国家能源局 | `site:nea.gov.cn` |
| `ndrc.json` | 发改委 | `site:ndrc.gov.cn` |
| `cac.json` | 网信办 | `site:cac.gov.cn` |

跨部委联合发文优先 gov.cn。详见 `references/policy-sources.md`。

## Pitfalls

| 问题 | 解决方案 |
|------|---------|
| gov.cn 返回过时政策 | 搜索嵌入年份限定，引用前做时效性检查 |
| 同名政策多个版本 | 检查文号+发布日期+发文机关三重确认 |
| 单关键词带出不相关文件 | 用 `--mode and` 多关键词交集 |
| URL 不可达 | worker 内置五层降级，commander 无需干预 |
| 搜索结果过少 | commander 审查后回 Stage 1 放宽条件 |
| **禁止手工 HTML** | 必须通过 `rebuild_policy_html.py` 生成 |

## Verification Checklist

- [ ] Commander 正确识别意图：4 种链选对
- [ ] 搜索到政策与需求匹配：部门、领域、时间范围一致
- [ ] Commander 审核：结果数量、覆盖面、链接有效性
- [ ] 原文从官方源提取，引用逐字核对
- [ ] 输出含完整引用：文件名、文号、机关、日期、原文链接
