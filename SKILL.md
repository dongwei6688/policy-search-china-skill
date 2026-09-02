---
name: policy-search-china
description: "Search Chinese government policy documents from 16 ministries. Extract verbatim paragraphs with source links."
version: v2.38.0
license: MIT
---

# Policy Search China

搜索中国政府政策文件，覆盖 16 个部委/机构。指挥官（大模型）规划与审核，工人（脚本）机械执行。

## 决策指南

指挥官根据用户意图选择对应的工人脚本。

| 用户需求 | 工人 | 说明 |
|----------|------|------|
| 全面扫描（"近两年AI政策"） | `chain_runner.py --chain broad` | 单关键词广撒网，指挥官可先拆子领域 |
| 交叉分析（"AI和能源结合"） | `chain_runner.py --chain cross` | 多关键词 AND 交集，内置并行搜索 |
| 精准定位（"数据二十条确权"） | `chain_runner.py --chain locate` | 文号/段落精确查找 |
| 溯源引用（"这句话出自哪"） | `chain_runner.py --chain trace` | 原文句子反查出处 |
| **gov.cn 被 WAF 拦截 / 查缓存外新政策** | `gov_library_search.py --keywords ...` | 国务院政策文件库搜索接口（浏览器渲染） |
| **gov.cn 政策详情页 403（下载原文）** | `gov_library_search.py` 的 `fetch_gov_policy(url)` | playwright 渲染详情页提取全文（`.pages_content`） |
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

同时完成关键词扩展——列出与用户主题相关的衍生词、同义表达、子领域词（如用户说"制造业"扩展为"智能制造/智能工厂/数字化转型"等），后续通过 `--highlight-keywords` 传入用于展示高亮。

搜索策略参考：`references/search-strategies.md`。

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
④ rebuild_policy_html.py --topic "关键词1" --topic "关键词2" --mode and \
     --highlight-keywords "扩展词1" "扩展词2" \
     --relevance-scores scores.json
   → 生成精简 HTML，全量关键词（含扩展词）独立颜色高亮
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

16 个部委/机构（其中住建部/卫健委/自然资源部通过中央政策文件库托底搜索），详见 `references/policy-sources.md`。

| 缓存文件 | 部委 |
|:---------|:-----|
| `gov.json` | 国务院 |
| `miit.json` | 工信部 |
| `nda.json` | 国家数据局 |
| `sasac.json` | 国资委 |
| `nea.json` | 国家能源局 |
| `ndrc.json` | 发改委 |
| `cac.json` | 网信办 |
| `most.json` | 科技部 |
| `mof.json` | 财政部 |
| `mot.json` | 交通运输部 |
| `mee.json` | 生态环境部 |
| `moa.json` | 农业农村部 |
| `moe.json` | 教育部 |
| `mct.json` | 文旅部 |
| `mwr.json` | 水利部 |
| `mohrss.json` | 人社部 |

详见 `references/policy-sources.md`。

## 运维约定（工作区唯一性 + 路径架构）

> ⚠️ 本节为维护者内部约定，路径一律用相对/通用表述，勿写入具体机器路径（隐私安全）。

### 唯一工作区铁律

- **系统空间（skill 安装目录）是唯一工作区与发版源**（git 仓库，remote=GitHub）。所有修改/提交/发版只在这里进行。
- **发布仓库（`~/projects/` 下的同名独立 clone）只是镜像副本**。日常不提交；如误提交导致分叉，用 `git reset --hard origin/main` 对齐（内容已覆盖时安全）。
- **禁止在两个 clone 都手动提交**——会导致历史分叉（曾发生：发布仓库落后 30 个提交，v2.10.0 vs v2.25.0）。
- 三方一致性判定：系统空间 HEAD == 发布仓库 HEAD == GitHub origin/main。

### 路径架构（政策监控 cron 运行时）

- cron（每日 12:00）**无 workdir**，运行 cwd = Agent 网关的 cwd。所有脚本**绝对路径**（基于 skill 目录推算），不依赖 cwd，不会跑偏到其他项目目录。
- 缓存**双写**（设计如此，勿改）：
  - 系统空间 `cache/`（随包分发、发版时 git 提交）
  - 用户空间（`~/.hermes/data/policy-search-china/cache/` 或 `POLICY_SEARCH_CHINA_DATA_DIR` 指定，运行读写区，local_path 不悬空）
- 涉及脚本：`policy_daily_pipeline.py`（入库+发版）、`release_skill.py`（发版六步）、`dev-tools/policy_monitor.py`（发现），位于用户脚本目录。
- **教训（2026-08-15）**：.gitignore 防污染修复（排除 `.agents/` + `skills-lock.json`）必须提交到**系统空间**再 push，不能只提交在镜像仓库——否则 GitHub 缺失该防护。

## 常见问题

| 问题 | 处理 |
|------|------|
| 搜索结果过多 | 指挥官追加 `--end` / `--issuer` 过滤后重调 |
| 搜索结果为零 | 指挥官放宽关键词或移除时间限制后重调 |
| URL 不可达 | 工人自动降级（HTTPS→HTTP→政策库搜索接口），指挥官无需处理 |
| **gov.cn 政策页 403 / 静默空响应** | 走政策库搜索接口（`gov_library_search.py` / `--web`），无需换 IP |
| 覆盖率不够 | 指挥官在交付前审核阶段回阶段 1 补搜 |
| **禁止手工拼装 HTML** | 必须通过 `rebuild_policy_html.py` 生成 |

## 交付检查清单

指挥官每次交付前逐项确认：
- [ ] 意图 → 工人映射正确
- [ ] 阶段 1 返回数量合理
- [ ] 阶段 4 HTML 由脚本生成（非手动拼接）
- [ ] 抽查 1-2 条 source_url 可访问
- [ ] 覆盖面完整，无遗漏子领域

## 发版版本号同步

`release_skill.py` 发版时自动同步仓库内 4 个版本号位置（SKILL.md frontmatter、README.md 最新版本行、atoms.py/chain_runner.py docstring 首行），无需手工维护。若手动发版或修改版本号，请确保这 4 处一致。
