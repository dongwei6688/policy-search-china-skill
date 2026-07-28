---
name: policy-search-china
description: "Search Chinese government policy documents and extract authoritative references for reports and planning documents. Covers State Council, MIIT, NDRC, SASAC, NEA, CAC and other key ministries."
license: MIT
---

# Policy Search China

Search Chinese government policy documents and extract authoritative references for reports and planning documents. Covers State Council, MIIT, NDRC, SASAC, NEA, CAC and other key ministries.

## Overview

撰写央国企数智化规划/报告时，需要引用权威政策原文作为依据。本 skill 提供从**意图拆解 → 原子搜索 → 逐段提取 → 结构化输出**的完整流水线，覆盖七个核心部委信源。架构为 5 阶段 18 原子操作，可自由编排成不同执行链。

## When to Use

- 用户要求在规划/报告中引用政策原文
- 用户提到某个政策文号或文件名（如"数据二十条"、"十四五数字经济发展规划"）
- 用户需要确认某个政策条款的具体表述
- 用户需要快速查**一句话的具体政策出处**

**不要用：** 已确认无法公开获取的内部文件、非正式发布的地方征求意见稿。

## Decision Guide — 按意图路由

| 用户意图 | 执行链 | 命令 |
|----------|--------|------|
| 全面扫描（"近两年AI政策有哪些"） | **broad 链** | `chain_runner.py --chain broad --keywords "人工智能" --start 2024-01-01` |
| 交叉分析（"AI和能源结合的政策"） | **cross 链** | `chain_runner.py --chain cross --keywords "人工智能" "能源" --start 2024-01-01` |
| 精准定位（"数据二十条确权条款"） | **locate 链** | `chain_runner.py --chain locate --keywords "确权"` |
| 溯源引用（"这句话出自哪个政策"） | **trace 链** | `chain_runner.py --chain trace --keywords "原句内容"` |
| 输出 HTML 汇编 | `rebuild_policy_html.py` | `--topic "人工智能" --topic "能源" --mode and` |

## Core Pipeline — 5 阶段 18 原子操作

所有原子操作实现在 `scripts/atoms.py`，编排在 `scripts/chain_runner.py`。

### Stage 0: 环境准备

```python
from atoms import check_cache_freshness

freshness = check_cache_freshness(cache_dir)
# → {"latest_date": "2026-07-28", "needs_web_update": False}
```
- `0.1` **缓存新鲜度** — 无参数，返回最新日期 + 是否需要联网
- `0.2` **初始化工作区** — `python3 scripts/init.py`（幂等创建用户空间）

### Stage 1: 搜索与命中

```python
from atoms import search_cache_title, search_cache_fulltext

# 标题级（快）
hits = search_cache_title(cache_dir, "人工智能")
# → 遍历 title + summary + tags，返回条目列表

# 全文级（慢但全）
hits = search_cache_fulltext(cache_dir, "能源", hits)
# → 只在标题命中条目内扫原文段落，返回含 _body_hits 的条目
```

| # | 原子操作 | 说明 |
|:--|---------|------|
| `1.1` | `search_cache_title()` | 标题级关键词搜索 |
| `1.2` | `search_cache_fulltext()` | 全文级关键词搜索（性能更高时用） |
| `1.3` | Web 补充搜索 | `web_search("site:gov.cn 关键词 年份")` |
| `1.4` | 下载原文 | `curl` / `browser_navigate` → 写入缓存 |

### Stage 2: 过滤

```python
from atoms import (
    filter_date_range, filter_issuer, filter_doctype,
    intersect_entries, union_entries, exclude_entries
)

result = intersect_entries(hits_ai, hits_energy)      # 2.4 AND
result = filter_date_range(result, "2024-01-01", None) # 2.1 时间
result = filter_issuer(result, ["国家能源局"])           # 2.2 部门
result = exclude_entries(result, ["征求意见稿"])         # 2.6 NOT
```

| # | 原子操作 | 说明 |
|:--|---------|------|
| `2.1` | `filter_date_range()` | 时间范围过滤 |
| `2.2` | `filter_issuer()` | 发文机关过滤（子串匹配） |
| `2.3` | `filter_doctype()` | 文件类型过滤（意见/规划/通知…） |
| `2.4` | `intersect_entries()` | AND 交集（多关键词都命中） |
| `2.5` | `union_entries()` | OR 并集（任一命中，去重） |
| `2.6` | `exclude_entries()` | NOT 排除 |

### Stage 3: 提取

```python
from atoms import extract_metadata, extract_paragraphs, extract_chapters

meta = extract_metadata(entry)
# → {"title": "...", "doc_number": "国发〔2025〕11号", "issuer": "...", "source_url": "..."}

paras = extract_paragraphs(entry, "人工智能")
# → [("段落文本", "第三章"), ...]

chapters = extract_chapters(text)
# → [("第一章 总则", "一级"), ("第一条 ...", "二级"), ...]
```

| # | 原子操作 | 说明 |
|:--|---------|------|
| `3.1` | `extract_metadata()` | 提取标准化元信息（标题/文号/部门/日期/链接） |
| `3.2` | `extract_paragraphs()` | 逐段匹配关键词 + 章节归属 |
| `3.3` | `extract_chapters()` | 提取章/节/条的层级结构 |

### Stage 4: 验证

```python
from atoms import deduplicate_entries, verify_verbatim

entries = deduplicate_entries(entries)
# → 按 title + doc_number 去重

ok = verify_verbatim("段落文本", Path("cache/gov/xxx.htm"))
# → True/False，在原文中逐字匹配
```

| # | 原子操作 | 说明 |
|:--|---------|------|
| `4.1` | `deduplicate_entries()` | 按 title+doc_number 去重 |
| `4.2` | `verify_verbatim()` | 段落逐字验证原文 |

### Stage 5: 输出

```bash
# HTML 汇编（含原文链接、高亮、验证标签）
python3 scripts/rebuild_policy_html.py --topic "人工智能" --topic "能源" --mode and

# 摘要列表
python3 -c "from atoms import generate_summary_list; print(generate_summary_list(entries))"
```

| # | 原子操作 | 说明 |
|:--|---------|------|
| `5.1` | `build_html()` | 生成 HTML 汇编（重建脚本中） |
| `5.2` | `generate_summary_list()` | 生成 Markdown 摘要表格 |
| `5.3` | 注入原文链接 | HTML 输出中自动 `<a href="source_url">` |

## Setup

```bash
python3 scripts/init.py
```

## Source Coverage

| 缓存文件 | 部门 | site: 搜索前缀 | 政策专栏 |
|---------|------|---------------|---------|
| `gov.json` | 国务院 / 中国政府网 | `site:gov.cn/zhengce/zhengceku/` | gov.cn 政策文件库 |
| `miit.json` | 工信部 | `site:miit.gov.cn` | miit.gov.cn/zwgk/zcwj |
| `nda.json` | 国家数据局 | `site:nda.gov.cn` | nda.gov.cn/sjj/zwgk/zcfb/list |
| `sasac.json` | 国资委 | `site:gov.cn 国资委` | sasac.gov.cn（时效性差，建议 gov.cn 检索） |
| `nea.json` | 国家能源局 | `site:nea.gov.cn` | nea.gov.cn/policy/zxwj.htm |
| `ndrc.json` | 发改委 | `site:ndrc.gov.cn` | ndrc.gov.cn/xxgk/zcfb |
| `cac.json` | 网信办 | `site:cac.gov.cn` | cac.gov.cn/wxzw/zcfg |

> **说明：** `site:` 列为 web_search 搜索前缀，`site:` 不带路径（搜索引擎自动索引全站），政策专栏列为部委官网直接访问的政策列表页。sasac.gov.cn 时效性较差，国资委政策统一通过 `site:gov.cn 国资委` 检索。跨部委联合发文优先在 gov.cn 检索。

## Pitfalls & Hard Constraints

### 🚫 绝对禁止
| 规则 | 原因 |
|------|------|
| **禁止手工编写 HTML 报告** | 跳过脚本的 source_url 链接注入、逐字验证标签、元信息自动读取 |
| **所有 HTML 交付必须通过 `rebuild_policy_html.py` 生成** | 唯一保证链接完整性的路径 |

### 常见问题
| 问题 | 解决方案 |
|------|---------|
| gov.cn 返回过时政策 | 搜索嵌入年份限定 `2025` / `2026`，引用前做时效性检查 |
| web_extract 在 gov.cn 返回残缺 | 切到 `browser_navigate` + `browser_snapshot(full=true)` |
| 同名政策多个版本 | 检查文号+发布日期+发文机关三重确认 |
| 单关键词匹配带出不相关文件 | 用 `--mode and` 多关键词交集，或用 `exclude_entries()` 排除 |
| URL 不可达 | `load_source()` 内置五层自动降级（HTTPS→HTTP→浏览器→搜索引擎→替代源），无需手动处理 |

## Verification Checklist

- [ ] 意图正确识别：4 种链（broad/cross/locate/trace）选对
- [ ] 搜索到的政策与需求匹配：部门、领域、时间范围三项一致
- [ ] 政策原文已从官方源提取（优先 gov.cn / 部委官网）
- [ ] 引用条款逐字核对原文，无转述/概括
- [ ] 引用格式完整：文件名、文号、发布机关、发布日期、原文地址
- [ ] 原文地址可访问且为官方源（非转载）
