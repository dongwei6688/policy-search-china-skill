# policy-search-china-skill

**国内政策文件搜索与引用** — Hermes Agent Skill

搜索国务院、工信部、国家数据局、国资委、国家能源局、发改委、网信办等权威信源的政策文件，提取逐字引文，生成结构化 HTML 汇编。

## 功能

- **缓存优先搜索**：50 条预装政策索引，命中跳过网络请求
- **逐字提取**：关键词命中段落原样输出，可回溯原文验证
- **PDF 支持**：支持 PDF 格式政策的文字提取
- **HTML 输出**：结构化格式，含统计概览、目录跳转、关键词高亮、验证标签
- **分层架构**：系统空间 + 用户空间，更新不覆盖用户数据

## 安装

```bash
# 1. 下载 skill 到本地
git clone git@github.com:dongwei6688/policy-search-china-skill.git \
  ~/.hermes/skills/research/policy-search-china

# 2. 运行初始化
python3 ~/.hermes/skills/research/policy-search-china/scripts/init.py

# 3. 在 Hermes 中使用
# 加载 skill → 搜索关键词 → 生成 HTML 汇编
```

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
├── cache/                     ← 系统预装缓存
│   ├── cac.json
│   ├── gov.json
│   ├── miit.json
│   ├── ndrc.json
│   ├── nea.json
│   ├── sasac.json
│   └── cac/ gov/ miit/ ndrc/ nea/ sasac/   ← HTML 原文
└── .gitignore
```

## 许可证

MIT License

---

*Built for Hermes Agent. Part of the [awesome-hermes-agent](https://github.com/0xNyk/awesome-hermes-agent) ecosystem.*
