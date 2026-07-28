# 输出格式规范 — 结构化 HTML 生成与验证

> 本文档定义从政策原文中提取特定主题内容（如"人工智能"、"算力"、"数据要素"）并按篇章结构输出结构化 HTML 的完整工作流。涵盖缓存新鲜度检查、目标文件定位、原文读取、章节归属识别、HTML 输出、结果验证、PDF 处理、代码模板及已知限制。

---

## Phase 0：缓存新鲜度检查（高动态主题预检）

> ⚠️ **核心风险**：本地缓存是静态快照，存在滞后性。如果目标主题有新政策发布而缓存未收录，纯本地查询会产生"漏报"。

1. **检查缓存新鲜度** — 扫描缓存 JSON 中所有条目的 `searched_at` 字段，取最新日期作为缓存时间戳
2. **关键主题预检** — 如果目标主题属于高动态领域（如"人工智能"每月有新政策），执行一次快速 web 搜索确认是否有缓存未覆盖的最新文件：
   - 搜索词示例：`site:gov.cn/zhengce/zhengceku/ 人工智能 2025` 或 `site:gov.cn/zhengce/zhengceku/ 人工智能 2026`
   - 比较搜索结果日期与缓存最新日期：如果搜索结果中有晚于缓存时间戳的新政策，先下载入库再继续
3. **决策路径**：
   - 缓存覆盖充分 → 纯本地执行（Phase 1-5）
   - 缓存有缺口 → 先执行"搜索与缓存补充"流程，补充完成后回到 Phase 1

---

## Phase 1：定位目标文件（缓存扫描）

1. **确定搜索关键词** — 如"人工智能"、"算力"、"数据要素"
2. **扫描缓存 JSON** — 遍历 `{skill_dir}/cache/*.json`，用关键词匹配 `title` + `tags` + `summary`，筛选符合条件的政策文件
3. **确定日期范围** — 如需近 2 年等时间过滤，在 JSON 的 `date` 字段上做条件判断

---

## Phase 2：读取原文与内容提取（按 format 字段选择读取方式）

1. **读本地文件** — 通过缓存条目的 `local_path` 读取对应原文文件
2. **按 format 字段分流**：
   - `format: "html"` — 解析 `pages_content` 或类似的内容容器 div，用 `<p>` 标签分割全文段落
   - `format: "pdf"` — 优先读取同目录下同名 `.txt` 配套文件；无则用 `pdftotext` 实时提取；扫描件则标记跳过
   - `format: "link"` — 仅有链接，跳过内容提取
3. **关键词匹配** — 遍历所有段落，标记包含关键词的段落及其段落编号
4. **统计元信息** — 统计关键词在全文的出现次数、涉及段落数、涉及章节数

---

## Phase 3：识别章节归属（篇→章→节层级）

1. **提取章节标题** — 扫描原文中所有 `<p>` 标签，识别 `第X篇`、`第X章`、`第X节` 等层级结构
2. **建立段落-章节映射** — 按段落编号确定每个关键词段落归属的 篇→章→节 层级
3. **整理层级关系** — 对同一章节下的多个段落合并去重

章节标题识别策略：
- HTML 格式：使用正则 `第[一二三四五六七八九十百零]+[篇章节]` 匹配
- PDF 格式：使用正则 `^[一二三四五六七八九十]+[、.][^\n]{2,}` 匹配

---

## Phase 4：结构化 HTML 输出（卡片式统计、目录、正文区块、高亮标记、验证标签）

### 输出结构

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

### 样式规范

| 规范项 | 要求 |
|--------|------|
| 统计概览 | 使用卡片式布局（`stats` 容器），每项含数字和标签 |
| 目录 | 使用带锚点跳转的链接列表 |
| 正文区块 | 每个文件一个独立区块，文件头部显示标题、文号、发文机关、日期 |
| 原文链接 | `<a href="source_url" target="_blank">原文链接</a>`，点击在新标签页打开政策原文网页 |
| 篇/章导航 | 每个区块顶部有篇/章导航标签 |
| 关键词高亮 | 使用 `<span class="hl">关键词</span>` 仅改变展示，不改变原文内容 |
| 引文缩进 | 使用 `text-indent: 2em` |
| 验证标签 | 每个文件区块头部添加绿色验证标签 `<div class="verification">✅ N个段落 · 全部逐字引自原文</div>` |
| 元信息来源 | **所有元信息（文号、发文机关、日期、原文链接）必须从缓存 JSON 的对应字段读取，不得手动硬编码** |
| 原文链接精确性 | **原文链接（source_url）必须使用缓存条目中的精确值，不得自行拼接或推测** |

---

## Phase 5：结果验证检查清单

- [ ] **统计**：关键词落地提及次数与搜索结果一致
- [ ] **章节**：每个提取段落均归属到正确的 篇→章→节 层级
- [ ] **完整性**：未遗漏任何含关键词的有效段落
- [ ] **格式**：HTML 可直接在浏览器中打开阅读
- [ ] **来源**：页脚标注原文链接与缓存技能标识
- [ ] **高亮**：每个引文段落中关键词已标记 `<span class="hl">`，且替换后原文内容不变（可再次通过逐字比对验证）
- [ ] **验证标签**：每个文件区块头部有 `verification` 标签，标注段落数量
- [ ] **元信息正确性**：文号、发文机关、日期、原文链接从缓存 JSON 字段精确读取，无硬编码

---

## PDF 文件搜索说明

当缓存条目的 `format` 为 `pdf` 时，`local_path` 指向 PDF 文件，搜索时按以下步骤处理：

1. **检查同目录下是否存在同名的 `.txt` 文件** — 如有，直接读取 `.txt` 作为内容来源进行关键词搜索和段落提取
2. **如无 `.txt` 文件** — 用 `pdftotext <pdf_path> -` 实时提取文本，边提取边搜索
3. **如 PDF 为图片扫描件（pdftotext 返回空）** — 标记为"仅存证，无法提取文字"，跳过内容搜索
4. **写入 summary 时只使用在文本中可验证的原句** — 不得自行概括或拼接未经原文验证的指标

---

## 关键代码模板（Python：缓存扫描→原文读取→段落提取→HTML输出）

```python
# Phase 1: 扫描缓存
import json, re
from pathlib import Path

skill_dir = Path.home() / '.hermes' / 'skills' / 'policy-search-china'
keyword = "算力"
cutoff = "2024-01-01"
hits = []

for jf in sorted((skill_dir / 'cache').glob('*.json')):
    for e in json.loads(jf.read_text()):
        if e.get('date', '') >= cutoff and keyword in (
            e['title'] + ' '.join(e.get('tags', [])) + e.get('summary', '')
        ):
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
    chapter_finder = lambda t: re.findall(
        r'^[一二三四五六七八九十]+[、.][^\n]{2,}', t, re.MULTILINE
    )

elif fmt == 'html':
    # HTML格式：解析 pages_content 容器
    html = lp.read_text(encoding='utf-8')
    body = re.search(
        r'class="(?:border-table noneBorder )?pages_content"[^>]*>(.*?)</?(?:table|div)>',
        html, re.DOTALL
    )
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
        if text:
            results.append((i, text))

# Phase 4: 输出 HTML — 逐字引用 + 关键词高亮
def highlight(text, keyword):
    """仅对关键词添加高亮标记，不改变原文内容"""
    return text.replace(keyword, f'<span class="hl">{keyword}</span>')

output = ''
for i, text in results:
    highlighted = highlight(text, keyword)
    output += f'<p>{highlighted}</p>\n'
```

---

## 已知限制（5个）

1. **HTML 结构差异** — 不同来源的网站（gov.cn / cac.gov.cn / sasac.gov.cn）使用不同的页面模板，`pages_content` 类名可能不同。需要根据 URL 域名选择对应的提取规则。

2. **多文件输出去重** — 当跨文件提取时，需注意去重（同一文件在多个 JSON 缓存中重复引用的情况，如 `gov.json` 和 `nea.json` 同时指向同一文件）。

3. **标题识别** — 部分网站的章节标题使用 `<strong>` 而非独立 `<p>` 标签，需增加备用提取模式。

4. **段落编号漂移** — `read_file` 的 offset/limit 分页读取可能导致段落编号不连续，建议全文件读入后在内存中处理。

5. **缓存滞后性** — 缓存是静态快照，新发布政策在缓存重建前不可见。对于高动态主题（如人工智能、数据要素），纯本地查询可能漏报最新文件。**解决方案**：执行 Phase 0 新鲜度检查，发现缺口时先补充缓存。
