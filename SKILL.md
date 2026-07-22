---
name: policy-search-china
description: "Search Chinese government policy documents and extract authoritative references for reports and planning documents. Covers State Council, MIIT, NDRC, SASAC, NEA, CAC and other key ministries."
version: 1.4.0
author: Hermes Agent
license: MIT
setup_needed: true
metadata:
  hermes:
    tags: [policy, china, government, research, citation, chinese]
    related_skills: [soe-digital-plan-writing, enterprise-plan-drafting, tech-news-briefing]
---

# 国内政策文件搜索与引用

## Overview

撰写央国企数智化规划/报告时，需要引用权威政策原文作为依据。本 Skill 提供从搜索定位 → 原文提取 → 引用标注的完整工作流，覆盖国务院、工信部、国家数据局、国资委、国家能源局、发改委、网信办等信源。

## When to Use

- 用户要求在规划/报告中引用政策原文
- 用户提到某个政策文号或文件名（如"数据二十条"、"十四五数字经济发展规划"）
- 用户需要确认某个政策条款的具体表述
- 用户需要核对政策文件的发布机构、发布日期、文号

**不要在以下场景使用：** 已确认无法公开获取的内部流通文件、非正式发布的地方政策征求意见稿。

## How to Use

本 Skill 的核心工作流按六个 Phase 顺序执行：

**Phase 0：缓存新鲜度检查** — 扫描本地缓存最新 `searched_at` 日期，对高动态主题联网核查有无新政策

**Phase 1：缓存搜索** — 遍历 `cache/` 目录下所有 `*.json` 信源文件，先匹配 keyword 在 title/summary/tags 中的命中，再匹配全文

**Phase 2：原文读取** — 按条目的 `format` 字段选择读取方式：`html` 解析 pages_content 容器提取段落，`pdf` 读取配套 `.txt` 文件

**Phase 3：关键词段提取** — 对每个段落做关键词逐段判定，记录段落编号、所属章节、原文引用

**Phase 4：结构化输出** — 生成含逐字引文的 HTML 文件，关键词高亮标记，每文件区块含验证标签

**Phase 5：结果验证** — 逐字比对输出引文与原文，确保无改述、无捏造

具体操作步骤见各 Phase 章节。输出的 HTML 文件保存在 `~/.hermes/output/` 目录，脚本工具在 `scripts/` 目录下。

## Setup

首次安装或加载本 Skill 时，运行初始化脚本确保目录结构就绪：

```bash
python3 {skill_dir}/scripts/init.py
```

脚本执行以下操作（幂等，可重复运行）：
- 创建用户空间目录 `~/.hermes/data/policy-search-china/{cache, config}`
- 创建输出目录 `~/.hermes/output/`
- 检查系统空间完整性（SKILL.md、scripts/、缓存索引文件）
- 生成默认配置文件 `~/.hermes/data/policy-search-china/config/user_config.ini`
- 检查运行依赖（python3、curl、pdftotext）

**说明：** Hermes Agent 首次加载此 Skill 时会自动提示运行初始化。
用户空间目录 `~/.hermes/data/policy-search-china/` 的数据在 skill 更新时**不会被覆盖**。

## 信源体系

### 权威政策发布渠道

| 部门 | 主域名 | 政策专栏路径 | site: 搜索前缀 |
|------|--------|-------------|---------------|
| 国务院 | gov.cn | www.gov.cn/zhengce/ | `site:gov.cn 政策` |
| 工信部 | miit.gov.cn | www.miit.gov.cn/zwgk/zcwj/ | `site:miit.gov.cn` |
| 国家数据局 | nda.gov.cn | www.nda.gov.cn/sjj/zwgk/list/ | `site:nda.gov.cn` |
| 国资委 | sasac.gov.cn | www.sasac.gov.cn/n2588035/ | `site:sasac.gov.cn` |
| 国家能源局 | nea.gov.cn | www.nea.gov.cn/policy/zxwj.htm | `site:nea.gov.cn` |
| 发改委 | ndrc.gov.cn | www.ndrc.gov.cn/xxgk/zcfb/ | `site:ndrc.gov.cn 政策` |
| 网信办 | cac.gov.cn | www.cac.gov.cn/wxzw/zcfg/A093703index_1.htm | `site:cac.gov.cn` |

### 综合政策文件库（补充信源）

| 平台 | 用途 | site: 语法 |
|------|------|-----------|
| 中国政府网政策文件库 | 国务院全部公开发文的统一入口 | `site:gov.cn/zhengce/zhengceku/` |
| 北大法宝/北大法意 | 法律/行政法规数据库（公开版） | `site:pkulaw.com` |
| 国研网 | 政策研究与解读 | `site:drcnet.com.cn` |

## 核心原则：两段式工作流——大模型 API 规划，本地工具验证

> **🤖 大模型 API = 调用 provider 模型能力（比如当前 provider 为 DeepSeek，调用时需根据 provider 进行具体适配）完成**：需求理解、领域拆解、搜索规划、结果整合
> **🔧 本地工具 = Hermes Agent 执行**：`web_search` / `curl` / `browser_navigate` / `read_file` / `write_file` 等

**关键教训（2026-07 实战验证）：** 当需要全面扫描某领域的政策（如"近3年能源数智化政策"），纯工具搜索的"想到什么搜什么"方式覆盖面窄，容易遗漏细分领域文件。先调用大模型 API 生成搜索规划，可以一次性拆解出 10+ 个子查询，覆盖更全面。

**正确做法：两段式工作流——模型规划，工具验证**

> **第一段：🤖 大模型 API 生成搜索规划**（拆子领域、列预期文件、规划验证路径）
> **→ 第二段：🔧 本地工具逐条验证**（`web_search` 确认文件存在、`curl`/`browser` 提取原文）

## 搜索分组策略

### 按领域的关键词组合

以下每组按优先级排列，优先用高精度关键词，结果不足时降级到宽泛关键词：

**1. 数字化/数智化转型**
```
高精度：数字化转型 政策 site:gov.cn OR site:miit.gov.cn
高精度：数智化转型 政策 site:gov.cn OR site:sasac.gov.cn
中精度：两化融合 指导意见 site:miit.gov.cn
宽泛：信息化 工业化 深度融合 政策
```

**2. 数据要素/数据治理**
```
高精度：数据二十条 site:gov.cn
高精度：数据要素 ×市场 政策
高精度：数据资产 入表 财政部 site:gov.cn
中精度：数据治理 管理办法 site:cac.gov.cn
中精度：公共数据 授权 运营 指导意见
```

**3. AI / 人工智能**
```
高精度：人工智能 发展规划 site:gov.cn
高精度：生成式人工智能 管理办法 site:cac.gov.cn
高精度：人工智能+ 行动 方案 site:gov.cn
中精度：AI+ 产业 指导意见 site:miit.gov.cn
宽泛：新一代人工智能 发展 政策
```

**4. 智能制造**
```
高精度：智能制造 示范 行动 site:miit.gov.cn
高精度：智能工厂 评价 site:miit.gov.cn
中精度：制造业 数字化转型 实施 指南 site:gov.cn
中精度：人工智能+制造 专项行动 site:miit.gov.cn
```

**5. 网络安全/信创**
```
高精度：网络安全法 site:gov.cn
高精度：数据安全法 site:gov.cn
高精度：关键信息基础设施 安全 保护 site:gov.cn
中精度：信息技术应用创新 政策 site:miit.gov.cn
中精度：信创 产业 发展 意见 site:gov.cn
```

**6. 绿色低碳**
```
高精度：碳达峰 碳中和 意见 site:gov.cn
高精度：能源 绿色 转型 方案 site:gov.cn
中精度：节能 降碳 改造 行动 site:ndrc.gov.cn
中精度：新能源 发展 规划 site:nea.gov.cn
```

**7. 网络化/新基建**
```
高精度：新基建 政策 site:gov.cn
高精度：5G 工业互联网 指导意见 site:gov.cn OR site:miit.gov.cn
中精度：算力 基础设施 发展 规划 site:gov.cn
中精度：东数西算 工程 site:ndrc.gov.cn
```

**8. 能源专项（新增——上次实战遗漏的细分领域）**
```
高精度：智能煤矿 数字化 site:nea.gov.cn OR site:gov.cn
高精度：虚拟电厂 指导意见 site:gov.cn OR site:ndrc.gov.cn
高精度：绿色微电网 site:miit.gov.cn OR site:gov.cn
高精度：配电网 智能化 site:nea.gov.cn
中精度：能源装备 数字化 site:nea.gov.cn
中精度：新型电力系统 行动方案 site:gov.cn
中精度：人工智能+ 能源 场景 site:nea.gov.cn
```

### 按年份筛选

搜索词中嵌入年份可以精确限定政策时效：
```
高精度：数据要素 ×2026 site:gov.cn
中精度：2025 人工智能 政策 site:gov.cn
宽泛：数字化转型 2025 2026 政策
```

**优先引用 2022 年以来的政策**（十五五规划周期内的基础文件）。

## 本地缓存机制

政策文件发布后内容固定、长期有效，适合永久缓存。缓存在本地，每次政策搜索前
先查缓存，命中则跳过网络请求，直接从本地读取。

### 分层架构：系统空间 + 用户空间

本 Skill 采用**分层叠加**架构，将"技能本体"与"用户数据"分离：

| 空间 | 路径 | 特性 |
|------|------|------|
| **系统空间** | `{skill_dir}/` | 只读，更新时整体替换。包含 SKILL.md、scripts/、预装缓存(50条) |
| **用户空间** | `~/.hermes/data/policy-search-china/` | 读写，永不覆盖。包含用户新增/修改的缓存、配置 |

**搜索优先级：用户空间 > 系统空间**

```
搜索缓存时：
  1. 先查用户空间 cache/*.json
  2. 没命中 → 查系统空间 cache/*.json
  3. 还没命中 → 联网搜索，结果写入用户空间
```

**合并规则（按 doc_number 去重）：**
- 用户空间中的条目**优先于**系统空间中同 doc_number 的条目
- 仅存在于用户空间的条目（用户新增的）保留
- 仅存在于系统空间的条目（预装但用户没改过的）保留
- 系统空间更新时新增的预装条目会被用户看到（除非用户有同名条目）

### 缓存文件结构

**按来源分割**：每个部委/信源一个独立的 JSON 文件，便于分类管理和直接定位。

**系统空间索引目录：** `{skill_dir}/cache/`（Skill 安装目录下的 cache 子目录，随 Skill 一同分发）
**用户空间索引目录：** `~/.hermes/data/policy-search-china/cache/`（用户首次使用时自动创建，不被更新覆盖）

| 缓存文件 | 覆盖范围 |
|---------|---------|
| `nea.json` | 国家能源局（nea.gov.cn） |
| `miit.json` | 工信部（miit.gov.cn） |
| `gov.json` | 国务院、中国政府网（gov.cn） |
| `ndrc.json` | 发改委（ndrc.gov.cn） |
| `nda.json` | 国家数据局（nda.gov.cn） |
| `sasac.json` | 国资委（sasac.gov.cn） |
| `cac.json` | 网信办（cac.gov.cn） |

**每条记录格式：**

```json
{
  "doc_number": "国能发科技〔2025〕73号",
  "title": "《关于推进「人工智能+」能源高质量发展的实施意见》",
  "issuer": "国家发展改革委 国家能源局",
  "date": "2025-09-04",
  "source_url": "https://www.gov.cn/zhengce/zhengceku/202509/content_7040253.htm",
  "summary": "（从官方页面提取的原文摘要，或关键条款摘录）",
  "tags": ["能源", "人工智能", "数智化"],
  "searched_at": "2026-07-22",
  "format": "html",                          // html(可提取段落) / pdf(PDF附件) / link(仅链接)
  "local_path": "cache/gov/content_7040253.htm"
}
```

**排序规则：** 每个文件内的记录按 `date` 字段**升序排列**（日期早的在前、
新追加的在后），便于按时间线浏览政策沿革。

**PDF附件处理：** 当 `format` 为 `pdf` 时，`local_path` 指向 PDF 文件，
同时会在同目录下生成一个与 PDF 同名的 `.txt` 文本提取文件（用 `pdftotext` 转出），
用于关键词搜索和段落提取。搜索时优先以 `.txt` 文件作为内容来源。

### 缓存键规则

使用 **文号** 作为主键（`doc_number`），**文件名** 作为辅助键（`title`）。
查缓存时优先匹配文号，次选文件名模糊匹配。

### 缓存查找流程 — 🔧 本地工具

在每个 Phase 2 搜索步骤之前，先执行以下缓存查找（**用户空间优先于系统空间**）：

1. **确定主缓存文件** — 根据待查文件所属部门，确定对应的缓存文件名
   （部委→对应文件，跨部委联合发文→`gov.json`；国家数据局→`nda.json`）
2. **先查用户空间** — 读取 `~/.hermes/data/policy-search-china/cache/{文件名}`，如存在则用文号或文件名匹配
3. **未命中 → 查系统空间** — 读取 `{skill_dir}/cache/{文件名}`，做二次匹配
4. **命中** → 直接从缓存读取 `summary` 和元信息，跳过 `web_search` 和 `curl`
5. **未命中 → 兜底查找** — 有些政策在原部委网站查不到，但被同步收录在
   `gov.cn`（国务院政策文件库），因此当主缓存文件不是 `gov.json` 时，再读一次
   `gov.json` 做二次匹配（同样先查用户空间再查系统空间）。命中则跳过搜索，未命中才执行正常搜索流程
6. **未命中 → 写入用户空间** — 联网搜索结果写入用户空间对应缓存文件，不修改系统空间

### 缓存写入 — 🔧 本地工具

每次成功提取一篇政策的原文摘要后，写入**用户空间**对应信源的缓存文件（`~/.hermes/data/policy-search-china/cache/`），不修改系统空间。

**信源归属判断规则（按优先级依次匹配）：**

| 优先级 | 判断依据 | 命中则写入 |
|-------|---------|-----------|
| 1 | `source_url` 包含 `nea.gov.cn` | → `nea.json` |
| 2 | `source_url` 包含 `nda.gov.cn` | → `nda.json` |
| 3 | `source_url` 包含 `miit.gov.cn` | → `miit.json` |
| 4 | `source_url` 包含 `sasac.gov.cn` | → `sasac.json` |
| 5 | `source_url` 包含 `cac.gov.cn` | → `cac.json` |
| 6 | `source_url` 包含 `ndrc.gov.cn` | → `ndrc.json` |
| 7 | `source_url` 包含 `gov.cn` | → `gov.json` |
| 8 | 以上都不匹配，按 `doc_number` 前缀判断：`国能发`→`nea`、`国数`→`nda`、`工信部`→`miit`、`发改`→`ndrc`、`国资`→`sasac` | 对应文件 |
| 9 | 以上均无法判断 | → `gov.json`（兜底） |

写入步骤：

1. 按上述规则确定目标缓存文件名
2. 读取现有内容（如不存在则创建空数组）
3. 检查该文号是否已在缓存中（避免重复）
4. 追加新记录
5. 按 `date` 字段重新排序（升序）
6. 用 `write_file` 写回

### 缓存维护说明

- **永久有效**：政策内容稳定不变，无需设置过期策略
- **只增不删**：仅当明确发现政策被废止时才手动删除对应条目
- **无容量限制**：每个信源的政策数量有限，JSON 文件大小可控，无需 LRU 淘汰
- **新增信源**：如需覆盖新的部委/信源，在系统空间缓存目录下新建 `xxx.json`，同时在"信源归属判断规则"表中增加对应条目
- **路径发现**：运行时通过 `skill_view(name="policy-search-china")` 获取 `skill_dir`；系统缓存路径为 `{skill_dir}/cache/`，用户缓存路径为 `~/.hermes/data/policy-search-china/cache/`

### 自我进化机制

本 Skill 具备**随使用而进化**的能力。核心逻辑：

```
第一次使用：  手头只有 50 条预装缓存
搜索"工业互联网" → 缓存命中 → 直接输出

搜索"虚拟电厂" → 缓存未命中 → 联网搜索
              → 下载原文到用户空间
              → 下次再搜，直接命中

半年后：      用户空间积累了 200+ 条政策
搜索效率：    首次搜索命中率从 30% → 90%
```

**进化路径：**

| 使用次数 | 缓存规模 | 联网依赖 |
|---------|---------|---------|
| 第一次 | 50 条（预装） | 高（多数需联网） |
| 10 次后 | ~80 条 | 中 |
| 50 次后 | ~150 条 | 低 |
| 持续使用 | 持续增长 | 仅在全新领域需要联网 |

**关键设计：**
- 搜索命中 → 零延迟，直接读本地
- 搜索未命中 → 联网下载，自动写入用户空间
- 用户空间永不覆盖 → 积累的缓存不会因版本更新丢失
- 每个用户积累的缓存路径不同 → 多人使用不冲突

## 搜索工作流

### 模式一：精确查找（已知文号/文件名）

用户有明确目标（"帮我查数据二十条原文"、"找到国资委数字化转型的通知"）。

#### Step 1: 识别需求 — 🤖 大模型 API

大模型 API 解析用户需求，提取：部门、领域、时间范围、文号（如有）。

#### Step 2: 执行搜索 — 🔧 本地工具

**前置：缓存检查** — 先读对应信源的缓存文件（如 `nea.json` / `gov.json` 等），用文号或文件名匹配。命中则跳过
搜索，直接进入 Step 3 从缓存读原文。

如未命中，按优先级使用以下搜索策略：

**策略 A — 精确文号/文件名（最高优先级）**
```
"文件全名" site:gov.cn
"文号 [2023] 第X号"
```

**策略 B — 部委 + 关键词**
```
site:[部委域名] [领域关键词] [年份]
```

**策略 C — 跨部委宽搜（A/B 无结果时）**
```
[政策主题] 通知 办法 意见 规划 site:gov.cn
```

**策略 D — 标题精确匹配（关键政策）**
```
intitle:[政策关键词] site:gov.cn
```

每次搜索取 **前 3-5 个结果** 判断是否为目标政策。

**执行方式：** 调用 `web_search` 工具，按上述语法构造搜索词。

#### Step 3: 内容提取 — 🔧 本地工具

找到目标政策页面后，使用以下工具按优先级尝试：

1. **`web_extract`** — 提取 HTML 页面正文
2. **`curl` + Python** — 当 `web_extract` 不可用（DDGS 后端不支持）时，用 `terminal` 执行 `curl` 提取
3. **`browser_navigate` + `browser_snapshot`** — 动态加载页面或 curl 失败时的 fallback
4. **PDF 处理** — 政策为 PDF 时，`web_extract` 直链提取或 `browser` 打开 PDF

**关键条款定位：** 对提取的文本用 Python `re` 或字符串搜索定位目标条款，截取上下段落。

**写入缓存：** 提取完成后，将文号、文件名、机关、日期、原文地址、原文摘要写入
`{skill_dir}/cache/` 下对应信源的缓存文件。

---

### 模式二：全面扫描（探索某领域政策全景）

当需要全面扫描某领域的政策时，**不要从工具搜索开始**。先调用大模型 API 做规划。

#### Phase 1：模型知识规划 — 🤖 大模型 API

调用大模型 API 对要搜索的领域形成搜索规划。例如用户需求"近3年能源领域数智化政策"：

1. **拆分子领域** — 调用大模型 API：将"能源数智化"拆解为人工智能+能源、数字化智能化、智能电网、虚拟电厂、智能煤矿、绿色微电网、能源装备数字化、新型电力系统等子领域
2. **列出预期文件清单** — 调用大模型 API：对每个子领域，列出该领域近3年应当存在的核心政策文件（文件名、推测文号、推测年份）
3. **规划验证路径** — 调用大模型 API：对每个文件，规划验证路径——用什么关键词、到哪个部委网站搜

输出格式：
```
预期清单：
1. 《XX文件》— 推测文号/年份 — 验证：site:gov.cn [关键词]
2. 《XX文件》— 推测文号/年份 — 验证：site:nea.gov.cn [关键词]
...
```

#### Phase 2：批量交叉验证 — 🔧 本地工具

对 Phase 1 给出的预期清单，先执行**缓存批量检查**：

1. **读取缓存** — 用 `read_file` 读取对应信源的缓存文件（如 `nea.json` / `gov.json` 等）
2. **批量匹配** — 对预期清单中的每个文件，用文号/文件名匹配缓存
3. **分流处理**：
   - **缓存命中** → 跳过 `web_search` 和 `curl`，直接从缓存读取 `summary`
   - **缓存未命中** → 执行以下验证流程，结果写入缓存

对未命中的文件，逐条（或并行）用本地工具执行验证：

1. **`web_search`** — 用预期关键词组合搜索，确认文件是否存在
2. **`curl` / `browser`** — 提取官方页面，补充文号、精确发布日期、原文地址
3. **遗漏补搜** — 对 Phase 1 没有覆盖的子领域，使用"搜索分组策略"中的关键词
   补充搜索
#### Phase 3：原文提取与引用输出 — 🔧 本地工具 + 🤖 大模型 API

1. **🔧 内容提取** — 用 `curl` / `browser` / `web_extract` 提取每条政策的原文
2. **🤖 整合输出** — 调用大模型 API，将提取的原文按标准引用格式（文件名、文号、机关、日期、链接、条款）结构化输出

### Step 4: 引用输出 — 🤖 大模型 API

调用大模型 API，将提取的原文按标准格式输出：

```
- **文件名称**：《关于……的通知》（文号 [年份] X号）
- **发布机关**：国务院/工信部/……
- **发布日期**：YYYY年MM月DD日
- **原文地址**：[政策名称](https://www.gov.cn/……)
- **引用条款**：（逐条缩进）
  - 第X条：……
  - 第X条：……
```

引用条款的措辞需 **直接引用原文**，不得转述或概括；如有解读需求，在原文后以括号注明解读。

### Step 5: 上下文标注 — 🤖 大模型 API

在规划文档中使用政策引用时，调用大模型 API 生成标注语法：
```
【来源：国务院《数据二十条》，2022年12月，第X条，https://www.gov.cn/……】
```

## PDF 政策文件处理

大量政策以 PDF 形式发布（尤其工信部、发改委的文件）。处理策略：

1. **直接提取**：`web_extract(url)` 传入 PDF 直链，返回正文文本
2. **web_extract 失败时**：`browser_navigate` 打开 PDF 页面，结合 `browser_snapshot(full=true)` 提取
3. **结构化提取**：对 PDF 正文用 Python `re` 做"章/节/条/款"的结构化分割，便于逐条引用

**PDF 政策的识别：** 在搜索结果的 URL 或链接文本中识别 `.pdf` 后缀，优先选择。

## 政策时效性检查

每次引用前必须确认政策是否仍有效：

**方法一：搜索发布日期**
- 查看页面顶部/底部的发布日期
- 确认发布日期在 **2022年以后的优先引用**；确需引用更早的政策需确认未被废止

**方法二：检查修订/废止记录**
- 在政策文件末尾或文号标注处搜索"废止"、"修订"、"替代"等关键词
- 搜索 `[文号] 废止 site:gov.cn` 确认当前状态

**方法三：版本确认**
- 同一主题可能有多个版本（如"三年行动计划"的 2023-2025 版和 2026-2028 版）
- 确认引用的版本与规划周期一致（十五五规划引用 2026 年及之后发布的政策）

## 常见坑

1. **gov.cn 搜索返回过时政策。** 2020 年以前的文件仍可通过 `site:gov.cn` 搜索到，但可能已被废止或已被新政策替代。解决方案：搜索时嵌入年份限定；引用前做时效性检查。

2. **web_extract 在 gov.cn 上返回残缺内容。** 部分 gov.cn 政策页面有动态加载组件，`web_extract` 可能只取到页面头部。解决方案：切换到 `browser_navigate` + `browser_snapshot(full=true)`。

3. **同名政策多个版本。** 例如"《关于加快推进国有企业数字化转型工作的通知》"可能有多个配套文件。解决方案：检查文号、发布日期、发文机关三重确认版本。

4. **政策 PDF 无法直接提取。** 部分 PDF 是图片扫描件，`web_extract` 返回空。解决方案：如果 PDF 是纯图片扫描件，说明当前无 OCR 环境可用，需告知用户无法直接提取文字内容，可建议通过官方政策解读页面获取文字版。

5. **国资委网站搜索结果时效性差。** `site:sasac.gov.cn` 的搜索结果返回大量 2018-2020 年的内容，2023 年后的政策较少。解决方案：国资委的新政策经常被 gov.cn 同步收录，改用 `site:gov.cn 国资委 数字化转型`。

6. **国家数据局官网原文不易获取。** 国家数据局 2023 年成立，官网 nda.gov.cn 以新闻资讯为主，政策文件多通过国务院、发改委渠道发布。解决方案：搜索以 `site:gov.cn 数据要素` 为主，辅以 `site:nda.gov.cn`。

7. **网信办文件适用性。** CAC 的文件多以"办法""规定"形式发布（如生成式人工智能管理办法），通常为监管性而非鼓励性政策。引用时注意区分"政策依据"与"合规要求"的引用意图。

8. **引号配对与中英文混用。** 政策原文使用中文弯引号 `“”`，引用时不要误用英文直引号 `""`。政策文号中的括号使用中文括号 `（）`。

9. **`web_extract` 后端不支持 URL 提取。** 当前 web 后端为 DDGS，只支持搜索不支持页面抓取。`web_extract(url)` 会返回 `DuckDuckGo (ddgs) is a search-only backend`。解决方案：用 `curl` + Python 提取 HTML 页面，或用 `browser_navigate` 获取动态渲染内容。

10. **gov.cn 和部委网站响应慢，curl 超时。** 部分部委网站（如 nea.gov.cn）从境外访问可能超时。解决方案：优先使用 gov.cn 转载链接（www.gov.cn/zhengce/zhengceku/），响应更快；设置 curl 超时参数 `--max-time 20`。

## 主题内容提取与结构化输出

当需要从一篇或多篇政策原文中提取特定主题内容（如"人工智能"、"算力"、"数据要素"）并按篇章结构输出时，使用以下工作流。

### 适用场景

- 从单一政策文件中提取某主题的全部内容（如 十五五规划中的"算力"相关内容）
- 从多篇政策文件中交叉提取某主题（如 多个AI相关政策中的"人工智能"内容）
- 输出格式为结构化的 HTML 文件，便于查阅和引用

### 工作流 — 🔧 本地工具 + 🤖 大模型 API

#### Phase 0：缓存新鲜度检查 — 🔧 本地工具（可选）

> ⚠️ **核心风险**：本地缓存是静态快照，存在滞后性。如果目标主题有新政策发布而缓存未收录，纯本地查询会产生"漏报"。

1. **检查缓存新鲜度** — 扫描缓存 JSON 中所有条目的 `searched_at` 字段，取最新日期作为缓存时间戳
2. **关键主题预检** — 如果目标主题属于高动态领域（如"人工智能"每月有新政策），执行一次快速 web 搜索确认是否有缓存未覆盖的最新文件：
   - 搜索词示例：`site:gov.cn/zhengce/zhengceku/ 人工智能 2025` 或 `site:gov.cn/zhengce/zhengceku/ 人工智能 2026`
   - 比较搜索结果日期与缓存最新日期：如果搜索结果中有晚于缓存时间戳的新政策，先下载入库再继续
3. **决策路径**：
   - 缓存覆盖充分 → 纯本地执行（Phase 1-5）
   - 缓存有缺口 → 先执行"搜索与缓存补充"流程（见主流程 Phase 2），补充完成后回到 Phase 1

#### Phase 1：定位目标文件 — 🔧 本地工具

1. **确定搜索关键词** — 如"人工智能"、"算力"、"数据要素"
2. **扫描缓存 JSON** — 遍历 `{skill_dir}/cache/*.json`，用关键词匹配 `title` + `tags` + `summary`，筛选符合条件的政策文件
3. **确定日期范围** — 如需近2年等时间过滤，在 JSON 的 `date` 字段上做条件判断

#### Phase 2：读取原文与内容提取 — 🔧 本地工具

1. **读本地 HTML** — 通过缓存条目的 `local_path` 读取对应原文文件
2. **提取正文区域** — 用正则定位 `pages_content` 或类似的内容容器 div
3. **按段落分割** — 用 `<p>` 标签分割全文段落
4. **关键词匹配** — 遍历所有段落，标记包含关键词的段落及其段落编号
5. **统计元信息** — 统计关键词在全文的出现次数、涉及段落数、涉及章节数

#### Phase 3：识别章节归属 — 🤖 大模型 API + 🔧 本地工具

1. **提取章节标题** — 扫描原文中所有 `<p>` 标签，识别 `第X篇`、`第X章`、`第X节` 等层级结构
2. **建立段落-章节映射** — 按段落编号确定每个关键词段落归属的 篇→章→节 层级
3. **整理层级关系** — 对同一章节下的多个段落合并去重

#### Phase 4：生成结构化 HTML 输出 — 🤖 大模型 API

输出格式要求如下（以跨文件查询为例）：

```
├── 统计概览（关键词出现次数、涉及文件数、章节数、段落数）
├── 目录（按政策文件分组）
│   ├── 文件A：涉及的章节列表
│   ├── 文件B：涉及的章节列表
│   └── ...
├── 正文（按政策文件分组，文件内按篇章结构排列）
│   ├── 📄 文件A — 标题 / 文号 / 发文机关 / 日期
│   │   ├── 第X篇 篇名
│   │   │   ├── 第X章 章名
│   │   │   │   ├── 第X节 节名 → 段落原文（关键词高亮）
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── ...
│   ├── 📄 文件B — ...
│   └── ...
└── 页脚（来源声明 + 原文链接）
```

**样式规范：**
- 统计概览使用卡片式布局（`stats` 容器），每项含数字和标签
- 目录使用带锚点跳转的链接列表
- 正文每个文件一个独立区块，文件头部显示标题、文号、发文机关、日期，以及一个可点击跳转原文的链接（`<a href="source_url" target="_blank">原文链接</a>`），点击在新标签页打开政策原文网页
- 每个区块顶部有 篇/章 导航标签
- 关键词在正文中使用高亮标记（`<span class="hl">`）
- 引文使用 `text-indent: 2em` 缩进
- 每个引文段落的搜索关键词使用 `<span class="hl">关键词</span>` 高亮，仅改变展示不改变原文内容
- 每个文件区块头部添加绿色验证标签（`<div class="verification">✅ N个段落 · 全部逐字引自原文</div>`），明确标注该文件的段落数量
- **所有元信息（文号、发文机关、日期、原文链接）必须从缓存 JSON 的对应字段读取，不得手动硬编码**
- **原文链接（source_url）必须使用缓存条目中的精确值，不得自行拼接或推测**

#### Phase 5：结果验证 — 🔧 本地工具

- [ ] 统计：关键词落地方提及次数与搜索结果一致
- [ ] 章节：每个提取段落均归属到正确的 篇→章→节 层级
- [ ] 完整性：未遗漏任何含关键词的有效段落
- [ ] 格式：HTML 可直接在浏览器中打开阅读
- [ ] 来源：页脚标注原文链接与缓存技能标识
- [ ] 高亮：每个引文段落中关键词已标记 `<span class="hl">`，且替换后原文内容不变（可再次通过逐字比对验证）
- [ ] 验证标签：每个文件区块头部有 `verification` 标签，标注段落数量
- [ ] 元信息正确性：文号、发文机关、日期、原文链接从缓存 JSON 字段精确读取，无硬编码

### PDF 文件搜索说明

当缓存条目的 `format` 为 `pdf` 时，`local_path` 指向 PDF 文件，搜索时按以下步骤处理：

1. **检查同目录下是否存在同名的 `.txt` 文件** — 如有，直接读取 `.txt` 作为内容来源进行关键词搜索和段落提取
2. **如无 `.txt` 文件** — 用 `pdftotext <pdf_path> -` 实时提取文本，边提取边搜索
3. **如 PDF 为图片扫描件（pdftotext 返回空）** — 标记为"仅存证，无法提取文字"，跳过内容搜索
4. **写入 summary 时只使用在文本中可验证的原句** — 不得自行概括或拼接未经原文验证的指标

### 关键代码模板

```python
# Phase 1: 扫描缓存
import json, re
from pathlib import Path

skill_dir = Path.home() / '.hermes' / 'skills' / 'research' / 'policy-search-china'
keyword = "算力"
cutoff = "2024-01-01"
hits = []

for jf in sorted((skill_dir / 'cache').glob('*.json')):
    for e in json.loads(jf.read_text()):
        if e.get('date', '') >= cutoff and keyword in (e['title'] + ' '.join(e.get('tags',[])) + e.get('summary','')):
            hits.append(e)

# Phase 2: 读取原文 — 按 format 字段选择读取方式
entry = hits[0]
lp = skill_dir / entry['local_path']
fmt = entry.get('format', 'html')

if fmt == 'pdf':
    # PDF格式：读配套 .txt 文件
    txt_path = lp.with_suffix('.txt')
    text = txt_path.read_text(encoding='utf-8') if txt_path.exists() else ''
    paragraphs = text.split('\n\n')  # 用空行分割段落
    chapter_finder = lambda t: re.findall(r'^[一二三四五六七八九十]+[、.][^\n]{2,}', t, re.MULTILINE)

elif fmt == 'html':
    # HTML格式：解析 pages_content 容器
    html = lp.read_text(encoding='utf-8')
    body = re.search(r'class="(?:border-table noneBorder )?pages_content"[^>]*>(.*?)</?(?:table|div)>', html, re.DOTALL)
    body_content = body.group(1) if body else html
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', body_content, re.DOTALL)
    chapter_finder = lambda t: re.findall(r'第[一二三四五六七八九十百零]+[篇章节]', t)

else:
    # 仅链接：跳过
    paragraphs = []
    chapter_finder = lambda t: []

# Phase 3: 提取关键词段落与章节
results = []
for i, p in enumerate(paragraphs):
    if keyword in p:
        text = re.sub(r'<[^>]+>', '', p).strip()
        if text: results.append((i, text))

# Phase 4: 输出 HTML — 逐字引用 + 关键词高亮
def highlight(text, keyword):
    """仅对关键词添加高亮标记，不改变原文内容"""
    return text.replace(keyword, f'<span class="hl">{keyword}</span>')

for i, text in results:
    highlighted = highlight(text, keyword)
    output += f'<p>{highlighted}</p>\n'
```

### 已知限制

1. **HTML 结构差异** — 不同来源的网站（gov.cn / cac.gov.cn / sasac.gov.cn）使用不同的页面模板，`pages_content` 类名可能不同。需要根据 URL 域名选择对应的提取规则。
2. **多文件输出** — 当跨文件提取时，需注意去重（同一文件在多个 JSON 缓存中重复引用的情况，如 `gov.json` 和 `nea.json` 同时指向同一文件）。
3. **标题识别** — 部分网站的章节标题使用 `<strong>` 而非独立 `<p>` 标签，需增加备用提取模式。
4. **段落编号漂移** — `read_file` 的 offset/limit 分页读取可能导致段落编号不连续，建议全文件读入后在内存中处理。
5. **缓存滞后性** — 缓存是静态快照，新发布政策在缓存重建前不可见。对于高动态主题（如人工智能、数据要素），纯本地查询可能漏报最新文件。解决方案：执行 Phase 0 新鲜度检查，发现缺口时先补充缓存。

## Verification Checklist

- [ ] 搜索到的政策与需求匹配：部门、领域、时间范围三项一致
- [ ] 政策原文已从官方源提取（优先 gov.cn / 部委官网）
- [ ] 引用条款逐字核对原文，无转述/概括
- [ ] 时效性确认：2022 年后的政策（或确认更早政策未被废止）
- [ ] 引用格式完整：文件名、文号、发布机关、发布日期、原文地址
- [ ] 原文地址可访问且为官方源（非转载）
- [ ] 缓存已写入：新提取的政策已追加到对应信源的缓存文件（`{skill_dir}/cache/*.json`）
