---
name: policy-search-china
description: "Search Chinese government policy documents from 7 ministries. Extract verbatim paragraphs with source links."
license: MIT
---

# Policy Search China

Search Chinese government policy documents (State Council, MIIT, NDRC, SASAC, NEA, CAC, NDA). Commander plans — workers execute. All logic lives in compiled scripts, not in Agent-interpreted code blocks. This prevents step-skipping and execution drift.

## Decision Guide

Commander maps user intent to the correct worker. Each worker is a self-contained script — call it, review its output, decide next step.

| 用户需求 | Worker | 说明 |
|----------|--------|------|
| 全面扫描（"近两年AI政策"） | `chain_runner.py --chain broad` | 单关键词广撒网，commander 可先拆子领域 |
| 交叉分析（"AI和能源结合"） | `chain_runner.py --chain cross` | 多关键词 AND 交集，内置并行搜索 |
| 精准定位（"数据二十条确权"） | `chain_runner.py --chain locate` | 文号/段落精确查找 |
| 溯源引用（"这句话出自哪"） | `chain_runner.py --chain trace` | 原文句子反查出处 |
| 输出 HTML 汇编 | `rebuild_policy_html.py --topic ...` | 逐字段落 + 原文链接 + 验证标签 |

## Core Pipeline — Commander Execution Protocol

Commander follows this protocol strictly. Each line is a **Commander action** (call worker → review → decide). Override default params based on user intent.

### Stage 0：Setup

```
① python3 scripts/init.py              → 幂等创建工作区（首次运行）
② atoms.check_cache_freshness(cache_dir) → {"latest_date", "needs_web_update"}
```

Commander review: if `needs_web_update` is True, append `--web` flag to Stage 1 worker call.

### Stage 1：Search

```
③ chain_runner.py --chain {broad|cross} --keywords "..." --start YYYY-MM-DD [--web]
   → {"count": N, "entries": [...], "freshness": {...}}
```

Commander actions before calling:
- Decompose user intent into keyword list (cross: multiple; broad: plan sub-domains first)
- Decide date range from user's time context
- Add `--web` if cache is stale

Commander review after receiving output:
- Count > 0? → proceed. Count == 0? → try broader keywords or remove date filter.
- Count too high (>50)? → add `--end` or `--issuer` filters and re-run.

### Stage 2：Filter

Filters are applied **inside** the worker call in Stage 1. Commander specifies filter params upfront — workers don't ask for mid-stream decisions.

| Filter | How Commander activates it |
|--------|--------------------------|
| Time range | `--start YYYY-MM-DD --end YYYY-MM-DD` in Stage 1 call |
| Issuer | `--issuer 国家能源局` (if user wants specific department) |
| Doc type | `--doctype 意见` (if user wants specific document type) |
| AND intersection | `--keywords "A" "B"` triggers automatic intersection |
| Dedup | automatic — worker deduplicates before returning |

Commander review: count is reasonable? Any obvious false positives in titles? If yes, re-run with `--exclude`.

### Stage 3: 工人提取段落 → 导出候选

```
③ rebuild_policy_html.py --topic "A" --topic "B" --mode and --candidates-only
   → candidates.json: {policies: [{index, title, paragraphs: [{text, matched_keywords}]}]}
```

Commander review: scan policy titles. If candidate list is large (>10 policies), proceed to Stage 3.5 to reduce.

### Stage 3.5: Commander 相关性评价

```
Commander 读取 candidates.json → 按政策标题+样本段落逐项评分 → 输出 scores.json
```

评分等级：
| 等级 | 规则 | 过滤行为 |
|:-----|:-----|:---------|
| **核心** | 政策直接讨论用户主题 | 保留全部段落 |
| **高度相关** | 政策含重要相关内容，值得引用 | 保留全部段落 |
| **弱相关** | 政策边缘涉及但非主题 | 仅保留关键词密度高的段落（≥3次出现） |
| **无关** | 政策与用户主题无关 | 全部移除 |

Commander 逐项评审 19 项 → 标注 9 项核心/高度相关 → 输出 scores.json。

### Stage 4: 工人用评分生成精简 HTML

```
④ rebuild_policy_html.py --topic "A" --topic "B" --mode and --relevance-scores scores.json
   → 仅输出 核心+高度相关 段落的 HTML
```

### Stage 4：Review & Deliver

Commander reviews before sending to user:
1. **Coverage check** — did we catch the expected policies? Cross-check title list against known major documents in this domain.
2. **Link check** — spot-check 1-2 source URLs for accessibility.
3. **Gap detection** — if user mentioned a sub-domain with zero results, propose supplement search.

If gaps found: return to Stage 1 with adjusted keywords. Otherwise: deliver results.

## Setup

```bash
python3 scripts/init.py
```

## Workers Reference

| Worker | Input | Output | Responsible for |
|:-------|:------|:-------|:---------------|
| `chain_runner.py` | chain type, keywords, date range, filters | `{"count": N, "entries": [{...}]}` | Search + filter + dedup |
| `rebuild_policy_html.py` | topics, mode, --candidates-only, --relevance-scores | candidates.json or HTML file | Extract + score + filter + highlight + link |
| `atoms.py` | structured data | structured data | Pure data operations (imported by above) |

Commander never imports atoms.py directly — always goes through workers. Workers are the sole execution interface.

## Source Coverage

| 缓存 | 部门 | site: 前缀 |
|------|------|-----------|
| `gov.json` | 国务院 | `site:gov.cn/zhengce/zhengceku/` |
| `miit.json` | 工信部 | `site:miit.gov.cn` |
| `nda.json` | 国家数据局 | `site:nda.gov.cn` |
| `sasac.json` | 国资委 | `site:gov.cn 国资委` |
| `nea.json` | 国家能源局 | `site:nea.gov.cn` |
| `ndrc.json` | 发改委 | `site:ndrc.gov.cn` |
| `cac.json` | 网信办 | `site:cac.gov.cn` |

详见 `references/policy-sources.md`。

## Pitfalls

| 问题 | 处理 |
|------|------|
| 搜索结果过多 | Commander 添加 `--end` / `--issuer` 过滤后重调 |
| 搜索结果为零 | Commander 放宽关键词或移除时间限制后重调 |
| URL 不可达 | Worker 自动五层降级，Commander 无需处理 |
| 覆盖率不够 | Commander 审查 Stage 4 后回 Stage 1 补搜 |
| **禁止手工拼装 HTML** | 必须通过 `rebuild_policy_html.py` 生成 |

## Verification Checklist

Commander verifies before each delivery:
- [ ] 意图 → worker 映射正确
- [ ] Stage 1 输出 count 合理
- [ ] Stage 4 HTML 文件已生成（不是手动拼接）
- [ ] 抽查 1-2 条 source_url 可访问
- [ ] 覆盖面完整，无遗漏子领域
