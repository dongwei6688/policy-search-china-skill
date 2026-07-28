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

| 用户意图 | 执行链 | 命令 |
|----------|--------|------|
| 全面扫描 | **broad 链** | `chain_runner.py --chain broad --keywords "..." --start YYYY-MM-DD` |
| 交叉分析（多关键词 AND） | **cross 链** | `chain_runner.py --chain cross --keywords "A" "B" --start YYYY-MM-DD` |
| 精准定位（文号/条款） | **locate 链** | `chain_runner.py --chain locate --keywords "..."` |
| 溯源引用（句子→出处） | **trace 链** | `chain_runner.py --chain trace --keywords "原文句子"` |
| 输出 HTML 汇编 | `rebuild_policy_html.py` | `--topic "A" --topic "B" --mode and` |

## Core Pipeline — 5 阶段

详细实现见脚本注释，SKILL.md 只描述各阶段做什么。

### Stage 0: 环境准备

`check_cache_freshness()` → 判断缓存是否需要联网更新；`init.py` 幂等创建工作区。

### Stage 1: 搜索 — 并行

- **缓存搜索**：每个关键词独立遍历缓存 JSON，多关键词可并行
- **Web 补充**（可选）：与缓存搜索并行发起 `web_search`，结果自动合并去重

### Stage 2: 过滤 + 去重

过滤链：AND 交集 → 时间范围 → 部门/文种(可选) → NOT 排除 → 去重。
同一关键词的缓存+Web 结果先合并，再进入过滤。

### Stage 3: 段落提取 — 并行

每个条目独立读取原文 + 提取含关键词段落，可多线程并行。
提取完成后按条目收集聚合，准备送入输出。

### Stage 4: 输出 — 逐字引用

生成 HTML 汇编文件，自动注入原文链接、关键词高亮、逐字段落验证标签。
格式见 `references/output-format.md`。

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
