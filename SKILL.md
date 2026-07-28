---
name: policy-search-china
description: "Search Chinese government policy documents from 7 ministries. Extract verbatim paragraphs with source links."
license: MIT
---

# Policy Search China

搜索中国政府政策文件，覆盖七大信源。指挥官（大模型）规划与审核，工人（脚本）机械执行。所有逻辑封装在编译脚本中，不依赖 Agent 解释执行代码块。

## 决策指南

指挥官根据用户意图选择对应的工人脚本。

| 用户需求 | 工人 | 说明 |
|----------|------|------|
| 全面扫描（"近两年AI政策"） | `chain_runner.py --chain broad` | 单关键词广撒网，指挥官可先拆子领域 |
| 交叉分析（"AI和能源结合"） | `chain_runner.py --chain cross` | 多关键词 AND 交集，内置并行搜索 |
| 精准定位（"数据二十条确权"） | `chain_runner.py --chain locate` | 文号/段落精确查找 |
| 溯源引用（"这句话出自哪"） | `chain_runner.py --chain trace` | 原文句子反查出处 |
| 输出 HTML 汇编 | `rebuild_policy_html.py --topic ...` | 逐字段落 + 原文链接 + 验证标签 |

## 执行流程（5 阶段 + 指挥官审核）

指挥官严格按以下步骤执行：调工人 → 审结果 → 决定下一步。

### 阶段 0：环境准备

```
① python3 scripts/init.py              → 幂等创建工作区（首次运行）
② atoms.check_cache_freshness(cache_dir) → {"latest_date", "needs_web_update"}
```

指挥官审核：若 `needs_web_update` 为 True，在阶段 1 的工人调用中追加 `--web` 参数。

### 阶段 1：搜索

```
③ chain_runner.py --chain {broad|cross} --keywords "..." --start YYYY-MM-DD [--web]
   → {"count": N, "entries": [...], "freshness": {...}}
```

**调用前：** 指挥官将用户意图分解为关键词列表（cross 链：多关键词；broad 链：先规划子领域再搜索），根据用户的时间语境决定日期范围，缓存陈旧时追加 `--web`。

**调用后：** 指挥官审核结果数量。count > 0 → 继续；count == 0 → 放宽关键词或移除时间过滤重试；count > 50 → 追加 `--end` 或 `--issuer` 过滤。

### 阶段 2：过滤

过滤条件在阶段 1 的工人调用中一次性传入，工人不在中途询问决策。

| 过滤条件 | 指挥官如何启用 |
|----------|---------------|
| 时间范围 | `--start YYYY-MM-DD --end YYYY-MM-DD` |
| 发文机关 | `--issuer 国家能源局` |
| 文件类型 | `--doctype 意见` |
| AND 交集 | `--keywords "A" "B"` 自动触发交集 |
| 去重 | 工人自动执行 |

指挥官审核：数量是否合理？标题中是否有明显的误匹配？如有，追加 `--exclude` 重跑。

### 阶段 3：提取候选段落

```
③ rebuild_policy_html.py --topic "A" --topic "B" --mode and --candidates-only
   → candidates.json: {policies: [{index, title, paragraphs: [{text, matched_keywords}]}]}
```

指挥官审核：候选政策数 > 10 项时，进入阶段 3.5 做相关性评价缩减。

### 阶段 3.5：指挥官相关性评价

指挥官读取 `candidates.json`，完成三项工作：

**① 政策级评分：**
| 等级 | 规则 | 过滤行为 |
|:-----|:-----|:---------|
| **核心** | 政策直接讨论用户主题 | 保留全部段落 |
| **高度相关** | 政策含重要相关内容 | 保留全部段落 |
| **弱相关** | 政策边缘涉及但非主题 | 仅保留关键词密度高的段落（任一关键词出现 ≥3 次） |
| **无关** | 与用户主题无关 | 全部移除 |

**② 段落级审查（可选）：** 对"弱相关"政策的段落抽样检查，标记明显不相关的段落为 `drop`（如开头背景描述、宏观政策引言等与主题关联弱的段落）。

**③ 公文风格概括摘要：** 撰写一段可直接引用的政策概述（3-5段），格式要求：
- 公文正式语言，避免口语化
- 按主题分条说明（如"一是…二是…三是…"）
- 每条含文件名称、文号、核心要点

以上三项汇总为 `scores.json`，格式：
```json
{"title": "...",
 "policy_scores": {"0": "核心", "1": "无关", ...},
 "paragraph_overrides": {"0_0": "drop", ...},
 "summary": "一是...\n\n二是...\n\n三是..."}
```

```
④ rebuild_policy_html.py --topic "A" --topic "B" --mode and --relevance-scores scores.json
   → 仅输出核心 + 高度相关段落的 HTML
```

### 交付前审核

指挥官在交付用户前逐项检查：
1. **覆盖面** — 是否捕获了预期的核心政策？对照该领域的已知重要文件
2. **链接** — 抽查 1-2 条 source_url 是否可访问
3. **缺口** — 用户提到的子领域是否有零结果的？如有，返回阶段 1 补搜

有缺口则回阶段 1 调整关键词重搜，否则交付结果。

## 环境初始化

```bash
python3 scripts/init.py
```

## 工人接口参考

| 工人 | 输入 | 输出 | 职责 |
|:-------|:------|:-----|:-----|
| `chain_runner.py` | 链类型、关键词、日期范围、过滤条件 | `{"count": N, "entries": [...]}` | 搜索 + 过滤 + 去重 |
| `rebuild_policy_html.py` | 主题、模式、相关性评分 | candidates.json 或 HTML 文件 | 提取 + 评分 + 过滤 + 高亮 + 链接 |
| `atoms.py` | 结构化数据 | 结构化数据 | 纯数据操作（被以上两个工人引用） |

指挥官不直接 import `atoms.py`——始终通过工人间接调用。

## 信源覆盖

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

## 常见问题

| 问题 | 处理 |
|------|------|
| 搜索结果过多 | 指挥官追加 `--end` / `--issuer` 过滤后重调 |
| 搜索结果为零 | 指挥官放宽关键词或移除时间限制后重调 |
| URL 不可达 | 工人自动五层降级，指挥官无需处理 |
| 覆盖率不够 | 指挥官在交付前审核阶段回阶段 1 补搜 |
| **禁止手工拼装 HTML** | 必须通过 `rebuild_policy_html.py` 生成 |

## 交付检查清单

指挥官每次交付前逐项确认：
- [ ] 意图 → 工人映射正确
- [ ] 阶段 1 返回数量合理
- [ ] 阶段 4 HTML 由脚本生成（非手动拼接）
- [ ] 抽查 1-2 条 source_url 可访问
- [ ] 覆盖面完整，无遗漏子领域
