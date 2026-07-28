# policy-search-china-skill

**国内政策文件搜索与引用** — 跨 Agent 平台通用 Skill（Hermes / OpenClaw / Workbuddy / Claude Code 等）

搜索国务院、工信部、国家数据局、国资委、国家能源局、发改委、网信办等权威信源的政策文件，提取逐字引文，生成结构化 HTML 汇编。

## 功能

- **缓存优先搜索**：50 条预装政策索引，命中跳过网络请求
- **逐字提取**：关键词命中段落原样输出，可回溯原文验证
- **PDF 支持**：支持 PDF 格式政策的文字提取
- **HTML 输出**：结构化格式，含统计概览、目录跳转、关键词高亮、验证标签
- **分层架构**：系统空间 + 用户空间，更新不覆盖用户数据

## 安装

确保系统已安装 Node.js（运行 `node --version` 确认，没有的话去 [nodejs.org](https://nodejs.org) 下载）。

**一条命令安装：**

```bash
npx skills add dongwei6688/policy-search-china-skill
```

装完后，对你的 AI 说一句：**"帮我搜索数据要素相关政策"** 即可。

> 高级用户也可手动安装：`git clone git@github.com:dongwei6688/policy-search-china-skill.git ~/.hermes/skills/policy-search-china && python3 ~/.hermes/skills/policy-search-china/scripts/init.py`

## 使用示例

```
用户: 帮我搜索"人工智能"相关政策
Agent: （加载 skill，扫描缓存，提取引文，输出 HTML 文件）
```

> 详细工作流见 SKILL.md 中的 `## How to Use` 节。

## 目录结构

```
policy-search-china/
├── SKILL.md                   ← 技能定义（含完整工作流说明）
├── scripts/
│   ├── init.py                ← 初始化脚本（幂等）
│   └── rebuild_policy_html.py ← 输出重建脚本
├── cache/                     ← 系统预装缓存（7 信源）
│   ├── nda.json               ← 国家数据局
│   ├── ndrc.json              ← 发改委
│   ├── gov.json               ← 国务院/中共中央
│   ├── miit.json              ← 工信部
│   ├── cac.json               ← 网信办
│   ├── nea.json               ← 国家能源局
│   ├── sasac.json             ← 国资委
│   ├── nda/                   ← 国家数据局 政策原文
│   ├── ndrc/                  ← 发改委 政策原文
│   ├── gov/                   ← 国务院/中共中央 政策原文
│   ├── miit/                  ← 工信部 政策原文
│   ├── nea/                   ← 国家能源局 政策原文
│   ├── cac/                   ← 网信办 政策原文
│   └── sasac/                 ← 国资委 政策原文
└── .gitignore
```

## 许可证

MIT License

---

> 本 Skill 采用跨平台设计（v1.5.0+），已上架 [skills.sh](https://www.skills.sh) 生态。推荐通过 `npx skills add` 安装以自动跨平台兼容。不硬编码路径，可通过环境变量 `POLICY_SEARCH_CHINA_DATA_DIR` 和 `POLICY_SEARCH_CHINA_OUTPUT_DIR` 适配任意 Agent 平台。开发维护以 Hermes Agent 为主，详见 SKILL.md 中"跨平台使用"节。
