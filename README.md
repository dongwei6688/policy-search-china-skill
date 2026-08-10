# Policy Search China

[![skills.sh](https://skills.sh/b/dongwei6688/policy-search-china-skill)](https://skills.sh/dongwei6688/policy-search-china-skill)
[![GitHub release](https://img.shields.io/github/v/release/dongwei6688/policy-search-china-skill)](https://github.com/dongwei6688/policy-search-china-skill/releases)

**国内政策文件搜索与引用** — 跨 Agent 平台通用 Skill（Hermes / npx skills / Claude Code 等）

搜索国务院、工信部、国家数据局、国资委、国家能源局等 16 个部委/机构的政策文件，通过 Commander/Worker 架构实现智能搜索、逐字引文提取和结构化 HTML 汇编。支持 4 种决策链覆盖从广撒网到精准溯源的全部场景。

**最新版本：v2.22.0**

---

## ✨ Highlights

- **16 个部委信源覆盖** — 缓存 70+ 条政策索引，覆盖国务院、工信部、发改委、科技部、财政部等全部核心部委
- **Commander/Worker 架构** — 大模型（Commander）负责意图分解、结果审核与关联评价；脚本（Worker）负责机械执行，各司其职
- **逐字精确提取** — 关键词命中段落原样输出，保留原文格式与编号，可回溯官方原文验证
- **结构化 HTML 输出** — 含统计概览、目录跳转、12 色关键词高亮、一键复制、折叠段落、原文验证标签

---

## Quick Start

### 推荐安装（跨平台自动兼容）

```bash
npx skills add https://github.com/dongwei6688/policy-search-china-skill --skill policy-search-china
```

安装后，对 AI 说一句 **"帮我搜索数据要素相关政策"** 即可。

### 手动安装（Hermes Agent）

```bash
git clone git@github.com:dongwei6688/policy-search-china-skill.git ~/.hermes/skills/research/policy-search-china/
python3 ~/.hermes/skills/research/policy-search-china/scripts/init.py
```

> 可通过环境变量 `POLICY_SEARCH_CHINA_DATA_DIR` 和 `POLICY_SEARCH_CHINA_OUTPUT_DIR` 自定义数据与输出目录。

---

## Features

### Commander/Worker 架构

- **Commander**（大模型）：分解用户意图、选择决策链、分配合适的关键词、审核搜索结果、做相关性评分、决定下一步
- **Worker**（Python 脚本）：机械执行搜索、缓存检索、全文提取、HTML 构建

### 4 种决策链

| 链类型 | 场景 | 说明 |
|--------|------|------|
| **broad**（广撒网） | "近两年人工智能政策" | 单关键词多领域扫描，Commander 拆分子领域 |
| **cross**（交叉分析） | "AI 与能源结合" | 多关键词 AND 交集，内置并行搜索 |
| **locate**（精准定位） | "数据二十条确权" | 文号/标题/段落精确查找 |
| **trace**（溯源引用） | "这句话出自哪个文件" | 原文句子反查出处 |

### 5 阶段执行流程

1. **环境准备** — `init.py` 幂等工作区初始化 + 缓存新鲜度检查
2. **搜索** — 缓存优先，过期时自动降级到网络搜索，支持并行（`ThreadPoolExecutor`）
3. **过滤** — 时间范围、发文机关、文件类型、AND 交集、去重
4. **Commander 评分** — 读取候选段落做政策级相关性评分和段落级评分
5. **HTML 构建** — 输出含统计概览、目录跳转、12 色调色板关键词高亮、一键复制按钮、折叠段落、回到顶部

### 输出特性

- **12 色调色板**：每个搜索词独立颜色，Header 标签与段落高亮一致
- **一键复制**：每个段落旁有复制按钮，支持单段复制
- **折叠段落**：按政策文件折叠，可展开/收起
- **回到顶部**：长页面浮动导航按钮
- **验证标签**：每段标注来源文件、发文机关、文号和段落序号

### 搜索可靠性

- **URL 5 层降级**：HTTPS → HTTP → Browser Fallback → 站内搜索 → 备用信源
- **64 条域名匹配规则**：按部委专业搜索入口定向
- **PDF 支持**：自动提取 PDF 格式政策文字
- **并行搜索**：多关键词通过 `ThreadPoolExecutor` 并发查询

---

## Decision Guide

| 用户需求 | 决策链 | 对应脚本 |
|----------|--------|----------|
| "帮我搜一下近两年 AI 相关政策" | broad（广撒网） | `chain_runner.py --chain broad` |
| "找同时提到 AI 和能源的政策" | cross（交叉分析） | `chain_runner.py --chain cross` |
| "查数据二十条关于确权的规定" | locate（精准定位） | `chain_runner.py --chain locate` |
| "这句话出自哪个文件？" | trace（溯源引用） | `chain_runner.py --chain trace` |
| "把搜索结果生成 HTML 报告" | — | `rebuild_policy_html.py --topic ...` |

---

## Directory Structure

```
policy-search-china/
├── SKILL.md                       ← 技能定义（含完整工作流说明）
├── README.md                      ← 本文件
├── CHANGELOG.md                   ← 版本变更日志
├── LICENSE                        ← MIT License
├── scripts/
│   ├── init.py                    ← 初始化脚本（幂等）
│   ├── atoms.py                   ← 原子操作（缓存检索、新鲜度检查）
│   ├── chain_runner.py            ← 决策链执行引擎（broad/cross/locate/trace）
│   ├── rebuild_policy_html.py     ← HTML 汇编输出生成器
│   ├── path_utils.py              ← 路径工具函数
│   └── pre-push.sh                ← 提交前检查脚本
├── references/
│   ├── policy-sources.md          ← 16 部委信源清单与搜索入口
│   └── search-strategies.md       ← 搜索策略与关键词扩展指南
├── cache/                         ← 缓存数据（16 信源，70+ 条政策索引）
│   ├── gov.json / gov/            ← 国务院／中共中央
│   ├── miit.json / miit/          ← 工信部
│   ├── nda.json / nda/            ← 国家数据局
│   ├── sasac.json / sasac/        ← 国资委
│   ├── nea.json / nea/            ← 国家能源局
│   ├── ndrc.json / ndrc/          ← 发改委
│   ├── cac.json / cac/            ← 网信办
│   ├── most.json / most/          ← 科技部
│   ├── mof.json                   ← 财政部（仅索引）
│   ├── mot.json / mot/            ← 交通运输部
│   ├── mee.json / mee/            ← 生态环境部
│   ├── moa.json / moa/            ← 农业农村部
│   ├── moe.json / moe/            ← 教育部
│   ├── mct.json / mct/            ← 文旅部
│   ├── mwr.json / mwr/            ← 水利部
│   └── mohrss.json / mohrss/      ← 人社部
└── .gitignore
```

---

## Cache Sources

| 缓存文件 | 对应部委/机构 | 英文缩写 |
|----------|--------------|----------|
| `gov` | 国务院／中共中央 | State Council / CPC Central Committee |
| `miit` | 工信部 | Ministry of Industry and Information Technology |
| `nda` | 国家数据局 | National Data Administration |
| `sasac` | 国资委 | State-owned Assets Supervision and Administration Commission |
| `nea` | 国家能源局 | National Energy Administration |
| `ndrc` | 发改委 | National Development and Reform Commission |
| `cac` | 网信办 | Cyberspace Administration of China |
| `most` | 科技部 | Ministry of Science and Technology |
| `mof` | 财政部 | Ministry of Finance |
| `mot` | 交通运输部 | Ministry of Transport |
| `mee` | 生态环境部 | Ministry of Ecology and Environment |
| `moa` | 农业农村部 | Ministry of Agriculture and Rural Affairs |
| `moe` | 教育部 | Ministry of Education |
| `mct` | 文旅部 | Ministry of Culture and Tourism |
| `mwr` | 水利部 | Ministry of Water Resources |
| `mohrss` | 人社部 | Ministry of Human Resources and Social Security |

> 住建部、卫健委、自然资源部等通过中央政策文件库 （sousuo.www.gov.cn） 托底搜索。

---

## License

MIT License

---

> 本 Skill 已上架 [skills.sh](https://www.skills.sh) 生态，推荐通过 `npx skills add` 安装以自动兼容多 Agent 平台。不硬编码路径，可通过环境变量适配任意部署环境。
