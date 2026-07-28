---
name: policy-search-china
description: "Search Chinese government policy documents and extract authoritative references for reports and planning documents. Covers State Council, MIIT, NDRC, SASAC, NEA, CAC and other key ministries."
license: MIT
---

# Policy Search China

Search Chinese government policy documents and extract authoritative references for reports and planning documents. Covers State Council, MIIT, NDRC, SASAC, NEA, CAC and other key ministries.

## Overview

撰写央国企数智化规划/报告时，引用权威政策原文作为依据。覆盖国务院、工信部、国家数据局、国资委、国家能源局、发改委、网信办七个信源。

## 角色分工：指挥官 + 工人

整个 Pipeline 由两个角色协作完成：

| 角色 | 对应 | 职责 |
|:----|:-----|:-----|
| **指挥官** | 大模型（Agent） | 统筹调度 + 审核衔接：什么时候用什么工人，工人干完活后审查结果，决定下一步 |
| **工人/模块** | 脚本与代码 | 机械执行：搜索缓存、过滤去重、提取段落、生成 HTML。不判断、不决策 |

**指挥官的三项核心工作：**
1. **统筹调度** — 拆解用户意图，选择执行链，规划搜索关键词和过滤条件
2. **审核衔接** — 工人返回结果后，审查覆盖面是否足够、是否需要补搜、各阶段结果是否正确衔接
3. **最终解读** — 把结构化数据翻译成用户能理解的回答

**每个工人模块做什么：**

| 模块 | 能力 |
|:-----|:-----|
| `atoms.py` | 纯数据操作：缓存搜索、过滤、交集、去重、元信息提取 |
| `rebuild_policy_html.py` | 文件 I/O：原文读取（含 URL 五层降级）、段落提取、HTML 生成 |
| `chain_runner.py` | 编排调度：多线程并行执行、结果聚合、执行链串联 |

## When to Use

- 用户要求在规划/报告中引用政策原文
- 用户提到某个政策文号或文件名
- 用户需要确认某个政策条款的具体表述
- 用户需要查一句话的具体政策出处

**不要用：** 已确认无法公开获取的内部文件、非正式发布的地方征求意见稿。

## Decision Guide — 指挥官用

指挥官分析用户意图后，调度对应的执行链。每条链由 5 个阶段组成。

| 用户意图 | 执行链 |
|----------|--------|
| 全面扫描（"近两年AI政策"） | **broad 链** — 单关键词广撒网，指挥官需拆分子领域 |
| 交叉分析（"AI和能源结合"） | **cross 链** — 多关键词 AND 交集 |
| 精准定位（"数据二十条确权条款"） | **locate 链** — 文号/段落精确查找 |
| 溯源引用（"这句话出自哪"） | **trace 链** — 原文句子反查出处 |
| 输出 HTML 汇编 | `rebuild_policy_html.py` — 逐字段落 + 原文链接 |

## Core Pipeline — 指挥官调度流程

以下每个阶段标注 **指挥官**（决策与审核）和 **工人**（机械执行）的分工。

### Stage 0：指挥官判断 → 工人执行

> **指挥官** 判断："用户要搜近两年政策，缓存可能不够新，需要确认新鲜度。"  
> **工人** 调用 `check_cache_freshness(cache_dir)`，返回最新日期和是否需要 Web 更新。

### Stage 1：指挥官规划 → 工人并行执行

> **指挥官** 将用户需求分解为搜索关键词列表。交叉分析场景下规划多关键词，全面扫描场景下规划子领域拆分（如"数字化 → AI+数据要素+工业互联网+算力+…"）。  
> **指挥官** 判断是否需要启用 Web 补充搜索（缓存不够新时）。  
> **工人** 每个关键词独立调用 `search_cache_title()`，多线程并行。Web 搜索并行发起。  
> 
> *搜索策略参考：`references/search-strategies.md`*

### Stage 2：指挥官决定过滤条件 → 工人串行过滤

> **指挥官** 根据用户意图决定：时间范围、发文机关、文件类型、排除词。  
> **工人** 串行执行 `intersect(AND) → filter_date → filter_issuer(可选) → filter_doctype(可选) → exclude(可选) → dedup`。  
> 去重放在过滤末尾，节约后续文件 I/O。

### Stage 3：工人并行提取 → 聚合

> **工人** 对过滤后的每个条目独立读取原文 + 提取含关键词段落。多线程并行，URL 不可达时五层自动降级（指挥官无需干预）。  
> 提取完成后自动按条目聚合，准备送入输出。

### Stage 4：工人输出 → 指挥官审核衔接

> **工人** `build_html()` 生成结构化 HTML：逐字段落原文、关键词高亮、原文链接、验证标签。  
> **指挥官审核**：
> 1. 结果数量是否合理？3 条太少 → 放宽关键词或时间范围补搜
> 2. 覆盖面是否完整？缺了某个子领域 → 追加关键词回 Stage 1
> 3. 链接是否可访问？抽查 source_url 有效性
> 
> **指挥官解读**：告诉用户搜到多少条、核心文件是什么、覆盖了哪些子领域。

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

- [ ] 指挥官正确识别意图：4 种链选对
- [ ] 搜索到的政策与需求匹配：部门、领域、时间范围一致
- [ ] 政策原文从官方源提取（优先 gov.cn / 部委官网）
- [ ] 引用条款逐字核对原文，无转述/概括
- [ ] 引用格式完整：文件名、文号、发布机关、发布日期、原文地址
- [ ] 原文地址可访问且为官方源
- [ ] 指挥官完成审核：结果数量、覆盖面、链接有效性均已审查
