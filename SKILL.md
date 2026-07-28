---
name: policy-search-china
description: "Search Chinese government policy documents and extract authoritative references for reports and planning documents. Covers State Council, MIIT, NDRC, SASAC, NEA, CAC and other key ministries."
license: MIT
---

# Policy Search China

Search Chinese government policy documents and extract authoritative references for reports and planning documents. Covers State Council, MIIT, NDRC, SASAC, NEA, CAC and other key ministries.

## Overview

撰写央国企数智化规划/报告时，引用权威政策原文作为依据。覆盖国务院、工信部、国家数据局、国资委、国家能源局、发改委、网信办七个信源。执行链为 **意图拆解 → 并行搜索 → 过滤去重 → 段落提取 → 逐字输出**。

## When to Use

- 用户要求在规划/报告中引用政策原文
- 用户提到某个政策文号或文件名
- 用户需要确认某个政策条款的具体表述
- 用户需要查一句话的具体政策出处

**不要用：** 已确认无法公开获取的内部文件、非正式发布的地方征求意见稿。

## Decision Guide — 按意图路由

Agent 分析用户意图后选择对应的执行链。每条链由 5 个阶段组成，每个阶段标注 🤖（大模型负责）或 🔧（脚本自动执行）。

| 用户意图 | 执行链 |
|----------|--------|
| 全面扫描（"近两年AI政策"） | **broad 链** — 单关键词广撒网 |
| 交叉分析（"AI和能源结合"） | **cross 链** — 多关键词 AND 交集 |
| 精准定位（"数据二十条确权条款"） | **locate 链** — 文号/段落精确查找 |
| 溯源引用（"这句话出自哪"） | **trace 链** — 原文句子反查出处 |
| 输出 HTML 汇编 | `rebuild_policy_html.py` — 逐字段落 + 原文链接 |

## Core Pipeline — 🤖/🔧 边界

以下按阶段定义 🤖（大模型理解/规划/解读）和 🔧（脚本机械执行）的分工。

### Stage 0: 🤖 判断 → 🔧 执行

> **🤖 Agent** 判断："用户要搜近两年政策，缓存可能不够新，需要确认新鲜度。"  
> **🔧** 调用 `check_cache_freshness(cache_dir)` 返回最新日期和是否需要 Web 更新。

### Stage 1: 🤖 规划搜索 → 🔧 并行执行

> **🤖 Agent** 将用户需求分解为搜索关键词列表。交叉分析场景下规划多关键词，全面扫描场景下规划子领域拆分（如"数字化 → AI+数据要素+工业互联网+算力+…"）。  
> **🤖 Agent** 判断是否需要启用 Web 补充搜索（缓存不够新时）。  
> **🔧** 每个关键词独立调用 `search_cache_title()`，多线程并行。Web 搜索并行发起。结果自动合并去重。  
> 
> *搜索策略参考：`references/search-strategies.md`*

### Stage 2: 🤖 决定过滤条件 → 🔧 串行过滤

> **🤖 Agent** 根据用户意图决定：时间范围、发文机关、文件类型、排除词。  
> **🔧** 串行执行 `intersect(AND) → filter_date → filter_issuer(可选) → filter_doctype(可选) → exclude(可选) → dedup`。  
> 去重放在过滤末尾，节约后续文件 I/O。

### Stage 3: 🔧 并行提取 → 聚合

> **🔧** 对过滤后的每个条目独立读取原文 + 提取含关键词段落。多线程并行执行 `extract_paragraphs()`，自动按条目聚合结果。  
> URL 不可达时自动走五层降级（HTTPS→HTTP→浏览器→搜索→替代源），Agent 无需干预。

### Stage 4: 🔧 输出 → 🤖 解读

> **🔧** `build_html()` 生成结构化 HTML 汇编：逐字段落原文、关键词高亮、原文链接、验证标签。  
> **🤖 Agent** 解读结果：告诉用户搜到几条政策、核心文件是什么、是否覆盖了所需的子领域。如需补充搜索，返回 Stage 1 追加关键词。

## Setup

```bash
python3 scripts/init.py
```

## Source Coverage

| 缓存文件 | 部门 | site: 搜索前缀 |
|---------|------|---------------|
| `gov.json` | 国务院 / 中国政府网 | `site:gov.cn/zhengce/zhengceku/` |
| `miit.json` | 工信部 | `site:miit.gov.cn` |
| `nda.json` | 国家数据局 | `site:nda.gov.cn` |
| `sasac.json` | 国资委 | `site:gov.cn 国资委`（官网时效性差） |
| `nea.json` | 国家能源局 | `site:nea.gov.cn` |
| `ndrc.json` | 发改委 | `site:ndrc.gov.cn` |
| `cac.json` | 网信办 | `site:cac.gov.cn` |

跨部委联合发文优先在 gov.cn 检索。详见 `references/policy-sources.md`。

## Pitfalls & Hard Constraints

### 🚫 绝对禁止
| 规则 | 原因 |
|------|------|
| **禁止手工编写 HTML 报告** | 跳过脚本的 source_url 链接注入、逐字验证标签 |
| **所有 HTML 交付必须通过 `rebuild_policy_html.py` 生成** | 唯一保证链接完整性的路径 |

### 常见问题
| 问题 | 解决方案 |
|------|---------|
| gov.cn 返回过时政策 | 搜索嵌入年份限定，引用前做时效性检查 |
| 同名政策多个版本 | 检查文号+发布日期+发文机关三重确认 |
| 单关键词匹配带出不相关文件 | 用 `--mode and` 多关键词交集 |
| URL 不可达 | `load_source()` 内置五层降级（HTTPS→HTTP→浏览器→搜索→替代源） |

## Verification Checklist

- [ ] 意图正确识别：4 种链选对
- [ ] 搜索到的政策与需求匹配：部门、领域、时间范围一致
- [ ] 政策原文从官方源提取（优先 gov.cn / 部委官网）
- [ ] 引用条款逐字核对原文，无转述/概括
- [ ] 引用格式完整：文件名、文号、发布机关、发布日期、原文地址
- [ ] 原文地址可访问且为官方源
