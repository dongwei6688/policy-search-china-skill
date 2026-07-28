---
name: policy-search-china
description: "Search Chinese government policy documents and extract authoritative references for reports and planning documents. Covers State Council, MIIT, NDRC, SASAC, NEA, CAC and other key ministries."
license: MIT
---

# Policy Search China

Search Chinese government policy documents and extract authoritative references for reports and planning documents. Covers State Council, MIIT, NDRC, SASAC, NEA, CAC and other key ministries.

## Overview

撰写央国企数智化规划/报告时，需要引用权威政策原文作为依据。本 skill 提供从搜索定位 → 原文提取 → 引用标注的完整工作流，覆盖国务院、工信部、国家数据局、国资委、国家能源局、发改委、网信办七个核心信源。缓存机制支持离线查找与自动更新。

## When to Use

- 用户要求在规划/报告中引用政策原文
- 用户提到某个政策文号或文件名（如"数据二十条"、"十四五数字经济发展规划"）
- 用户需要确认某个政策条款的具体表述
- 用户需要快速查**一句话的具体政策出处**

**不要在以下场景使用：** 已确认无法公开获取的内部流通文件、非正式发布的地方政策征求意见稿。

## Decision Guide

| 用户需求 | 操作 | 详细参考 |
|----------|------|---------|
| 查找某条具体政策（已知文号/文件名） | 缓存搜索 → 文号搜索 → web 提取 → 输出 | `references/search-strategies.md` |
| 全面扫描某领域政策（如"近3年AI政策"） | 模型规划子领域 → 批量缓存检查 → web 逐条验证 → 输出 | `references/search-strategies.md` |
| 从政策中提取某主题按篇章输出 HTML | 缓存扫描 → 读取原文 → 章节归属 → HTML 生成 → 验证 | `references/output-format.md` |
| 确认信源/缓存映射 | 按域名匹配缓存文件 | `references/policy-sources.md` |

## Core Workflow — 可执行指引

```
pip install pypdf pdfplumber
```
```python
from pathlib import Path
import json, re, glob
```

### Phase 0: 缓存新鲜度检查
```python
# 检查最新缓存日期，高动态主题需联网预检
latest = ""
for jf in glob.glob("cache/*.json"):
    with open(jf) as f:
        for e in json.load(f):
            d = e.get("searched_at", "")
            if d > latest:
                latest = d
# 如果 latest < 今年，执行一次 web_search 确认有无新政策
```
对"人工智能""数据要素"等高频更新主题，用 `web_search("site:gov.cn/zhengce/zhengceku/ 人工智能 2026")` 确认缓存是否覆盖最新文件。

### Phase 1: 缓存搜索 — 遍历所有信源文件
```python
# skill_dir 通常指向 skill 根目录（系统空间）
for jf in Path(skill_dir).glob("cache/*.json"):
    for e in json.loads(jf.read_text()):
        if keyword in e["title"] + " ".join(e.get("tags", [])) + e.get("summary", ""):
            hits.append(e)
```
匹配优先级：文号 > 文件名 > 关键词。不同部委的缓存文件见信源表。

### Phase 2: 原文读取 — 按 format 字段分流
```python
if not hits:
    return  # 缓存未命中，需走 web_search
entry = hits[0]; lp = Path(entry["local_path"])
if entry.get("format") == "pdf":
    txt = lp.with_suffix(".txt")
    text = txt.read_text(encoding="utf-8") if txt.exists() else ""
elif entry.get("format") == "html":
    html = lp.read_text(encoding="utf-8")
    body = re.search(r'class="pages_content"[^>]*>(.*?)</?div>', html, re.DOTALL)
    text = body.group(1) if body else html
else:
    text = ""
```
gov.cn 用 `pages_content` 容器，ndrc.gov.cn 用 `article_con`。PDF 优先读配套 `.txt` 文件。

### Phase 3: 关键词段提取 — 逐段落匹配+章节归属
```python
paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', text, re.DOTALL)
for i, p in enumerate(paragraphs):
    if keyword in p:
        text_clean = re.sub(r'<[^>]+>', '', p).strip()
        chapter = re.findall(r'第[一二三四五六七八九十百零]+[篇章节]', text_clean)
        results.append((i, text_clean, chapter))
```

### Phase 4: 结构化 HTML 输出
```python
def highlight(text, keyword):
    return text.replace(keyword, f'<span class="hl">{keyword}</span>')
```
HTML 格式：逐字引用 + 关键词 `<span class="hl">` 高亮 + 每个文件区块的 `verification` 验证标签。不改变原文任何内容。

### Phase 5: 结果验证
- 每个引文段落回到原文逐字比对，确认无改述、无捏造
- 验证标签标注该文件引用的段落数量：`<div class="verification">✅ N段·逐字引用</div>`

## Setup

```bash
python3 scripts/init.py
```
脚本创建用户空间目录，检查运行依赖（python3、curl、pdftotext）。用户空间缓存数据在 skill 更新时不会被覆盖。

## Source Coverage

| 缓存文件 | 部门 | site: 搜索前缀 |
|---------|------|---------------|
| `gov.json` | 国务院 / 中国政府网 | `site:gov.cn/zhengce/zhengceku/` |
| `miit.json` | 工信部 | `site:miit.gov.cn` |
| `nda.json` | 国家数据局 | `site:nda.gov.cn` |
| `sasac.json` | 国资委 | `site:gov.cn 国资委`（国资委官网时效性差） |
| `nea.json` | 国家能源局 | `site:nea.gov.cn` |
| `ndrc.json` | 发改委 | `site:ndrc.gov.cn` |
| `cac.json` | 网信办 | `site:cac.gov.cn` |

跨部委联合发文优先在 gov.cn 检索。完整信源表含域名、专栏路径、归属规则等见 `references/policy-sources.md`。

## Two-Stage Workflow Principle

**不要从工具搜索开始。** 当用户说"查近3年能源领域数智化政策"，先做规划再做验证：

```python
# Stage 1: 🤖 大模型 API — 需求拆解与规划
# 调用 provider 模型，输出结构化搜索计划：
# [
#   {"子领域": "人工智能+能源", "预期文件": "关于推进人工智能+能源高质量发展的实施意见", "搜索词": "site:gov.cn 人工智能+能源 指导意见", "推测文号": "国能发科技〔2025〕73号"},
#   {"子领域": "智能煤矿", "预期文件": "智能化示范煤矿验收管理办法", "搜索词": "site:nea.gov.cn 智能煤矿 数字化"},
#   ...
# ]

# Stage 2: 🔧 本地工具 — 逐条验证
# 对每个预期文件：缓存搜索 → web_search 确认 → curl/browser 提取原文 → 缓存写入
```

这样覆盖面远高于"想到什么搜什么"，不容易遗漏细分领域文件。

## Common Pitfalls

| 问题 | 解决方案 |
|------|---------|
| gov.cn 返回过时政策 | 搜索嵌入年份限定 `2025` / `2026`，引用前做时效性检查 |
| web_extract 在 gov.cn 返回残缺 | 切到 `browser_navigate` + `browser_snapshot(full=true)` |
| 同名政策多个版本 | 检查文号+发布日期+发文机关三重确认 |
| web_extract 后端不支持 URL 提取 | 用 `curl` + Python 或 `browser` 代替 |
| 引号中英文混用 | 政策原文用中文弯引号 `“”`，文号括号用中文 `（）` |

更多已知限制（PDF 扫描件、缓存滞后性等）见 `references/output-format.md`。

## Verification Checklist

- [ ] 搜索到的政策与需求匹配：部门、领域、时间范围三项一致
- [ ] 政策原文已从官方源提取（优先 gov.cn / 部委官网）
- [ ] 引用条款逐字核对原文，无转述/概括
- [ ] 时效性确认：2022 年后的政策（或确认更早政策未被废止）
- [ ] 引用格式完整：文件名、文号、发布机关、发布日期、原文地址
- [ ] 原文地址可访问且为官方源（非转载）
- [ ] 缓存已写入：新提取的政策已追加到对应信源的缓存文件
