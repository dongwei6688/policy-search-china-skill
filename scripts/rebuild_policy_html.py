#!/usr/bin/env python3
"""
政策汇编 HTML 生成器 — 逐字提取 + 关键词高亮

功能：
  从本地缓存中搜索指定关键词，提取含关键词的政策原文段落，
  生成结构化的 HTML 汇编文件（含目录、统计、高亮、验证标签）。

用法：
  # 搜索单个主题（推荐）
  python3 scripts/rebuild_policy_html.py --topic 智慧城市

  # 批量重建所有预设主题
  python3 scripts/rebuild_policy_html.py --all

  # 查看帮助
  python3 scripts/rebuild_policy_html.py --help

跨平台路径支持：
  本脚本不再硬编码 ~/.hermes/ 路径，通过 path_utils.py 自动解析。
  通过环境变量可覆盖：
    POLICY_SEARCH_CHINA_DATA_DIR    用户数据目录（默认: ~/.hermes/data/policy-search-china/ 或 SKILL_DIR/data/）
    POLICY_SEARCH_CHINA_OUTPUT_DIR  输出目录（默认: USER_DIR/output/）

架构说明：
  系统空间（只读，随 skill 分发）: SKILL_DIR/cache/
  用户空间（读写，永不覆盖）:     USER_DIR/cache/
  输出目录:                        OUTPUT_DIR/

  搜索优先级：用户空间 > 系统空间
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ── 使用跨平台路径工具 ─────────────────────────────
_SELF_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SELF_DIR))
from path_utils import (
    SYSTEM_DIR, USER_DIR, OUTPUT_DIR,
    SYSTEM_CACHE, USER_CACHE,
    resolve_local_path, ensure_dirs, summary,
)

ensure_dirs()

# ═══════════════════════════════════════════════════════════
#  预设主题（仅 --all 模式使用）
#  说明：这些是开发时常用的 5 个主题，方便批量重建。
#  用户可根据自己的偏好增删改，不会影响 --topic 单次搜索。
# ═══════════════════════════════════════════════════════════
PRESET_TOPICS = {
    '人工智能政策汇编':        {'keywords': ['人工智能']},
    '工业互联网政策汇编':      {'keywords': ['工业互联网']},
    '算力网络政策汇编':        {'keywords': ['算力网络']},
    'AI与数据要素政策汇编':    {'keywords': ['人工智能', '数据要素']},
    '智能矿山政策汇编':        {'keywords': ['智能矿山', '煤矿智能化']},
}

# ═══════════════════════════════════════════════════════════
#  CSS 样式（生成 HTML 时嵌入，无外部依赖）
# ═══════════════════════════════════════════════════════════
CSS = """\
body{font-family:system-ui,-apple-system,"PingFang SC","Hiragino Sans GB","HarmonyOS Sans SC","Microsoft YaHei",sans-serif;max-width:900px;margin:0 auto;padding:0 32px;background:#f0f2f5;color:#2c3e50;line-height:1.9}
.header{background:linear-gradient(135deg,#0f1f3d 0%,#1a3a6b 40%,#1e5a8a 100%);color:#fff;padding:40px 28px;margin:0 0 28px 0;border-radius:8px}
.header h1{font-size:26px;font-weight:700;color:#fff;margin:0 0 8px 0}
.header p{margin:0;font-size:13px;color:rgba(255,255,255,.65)}
.stats{display:flex;gap:12px;margin:24px 0;flex-wrap:wrap}
.stat-box{background:#fff;border-radius:8px;padding:16px 24px;box-shadow:0 2px 8px rgba(0,0,0,.06);flex:1;min-width:110px;text-align:center}
.stat-box .num{font-size:30px;font-weight:700;color:#1a3a6b}.stat-box .label{font-size:12px;color:#8899aa;margin-top:4px;text-transform:uppercase;letter-spacing:.5px}
.summary-box{background:#fff;border-left:3px solid #2d6aa0;border-radius:0 8px 8px 0;padding:24px 28px;margin:0 0 24px 0;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.summary-box h2{font-size:15px;color:#2d6aa0;font-weight:600;margin:0 0 12px 0;padding-bottom:8px;border-bottom:1px solid #eef2f6}
.summary-box .copy-btn{float:right;padding:3px 12px;background:#2d6aa0;color:#fff;border:none;border-radius:4px;font-size:12px;cursor:pointer;transition:all .2s}
.summary-box .copy-btn:hover{background:#1a3a6b}
.summary-box p{text-indent:2em;font-size:14px;color:#4a5568;margin:8px 0;text-align:justify;line-height:2}
.toc{background:#fff;border-radius:8px;padding:20px 28px;margin:0 0 20px 0;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.toc h2{font-size:15px;font-weight:600;color:#1a3a6b;margin:0 0 12px 0;padding-bottom:8px;border-bottom:1px solid #eef2f6}
.toc a{color:#3b6cb4;text-decoration:none}
.doc-section{background:#fff;border-radius:8px;padding:28px 32px;margin:0 0 20px 0;box-shadow:0 2px 8px rgba(0,0,0,.05);border-top:3px solid #2d6aa0}
.doc-header{margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #eef2f6}
.doc-header h2{font-size:17px;font-weight:600;color:#1a202c;margin:0 0 6px 0}
.doc-header .meta{font-size:12px;color:#8899aa;margin-top:6px}
.doc-header .meta span{margin-right:14px}
.doc-header .meta .label{color:#aab5c0}
.doc-header .meta a{color:#3b6cb4;text-decoration:none}
.doc-section p{text-indent:2em;margin:7px 0;font-size:14px;color:#4a5568;text-align:justify;line-height:1.95}
.hl{background:#dbeafe;color:#1e40af;padding:0 3px;font-weight:600;border-radius:3px}
.verify{font-size:11px;color:#a0aec0;margin:10px 0}
.fold-toggle{float:right;padding:3px 10px;background:#2d6aa0;color:#fff;border:none;border-radius:4px;font-size:12px;cursor:pointer;transition:all .2s}
.fold-toggle:hover{background:#1a3a6b}
.fold-toggle .arrow{display:inline-block;transition:transform .25s;margin-right:3px}
.fold-toggle.expanded .arrow{transform:rotate(90deg)}
.doc-body{overflow:hidden;transition:max-height .35s ease}
.doc-body.collapsed{max-height:0}
.footer{text-align:center;color:#aab5c0;font-size:12px;margin:0;padding-top:20px;border-top:1px solid #e0e4e8;padding-bottom:32px}
#back-to-top{position:fixed;right:28px;bottom:36px;width:40px;height:40px;background:#2d6aa0;color:#fff;border:none;border-radius:50%;font-size:18px;cursor:pointer;opacity:0;transition:all .25s;box-shadow:0 2px 10px rgba(45,106,160,.3);z-index:9999}
#back-to-top.visible{opacity:.9}#back-to-top:hover{opacity:1;transform:translateY(-2px);box-shadow:0 4px 16px rgba(45,106,160,.4)}
"""


# ═══════════════════════════════════════════════════════════
#  双空间缓存读取
#  核心逻辑：用户空间优先，系统空间兜底
# ═══════════════════════════════════════════════════════════

def load_all_cache() -> list[dict]:
    """
    加载所有缓存条目（用户空间优先合并）

    合并规则：
    - 用户空间和系统空间同时有同 doc_number 的条目 → 用用户的
    - 仅用户有的 → 保留
    - 仅系统有的 → 保留
    """
    json_names = set()
    for d in [USER_CACHE, SYSTEM_CACHE]:
        if d.exists():
            for jf in sorted(d.glob('*.json')):
                json_names.add(jf.name)

    def _load_merged(name: str) -> list[dict]:
        user_path = USER_CACHE / name
        sys_path = SYSTEM_CACHE / name

        user_entries = json.loads(user_path.read_text(encoding='utf-8')) if user_path.exists() else []
        sys_entries = json.loads(sys_path.read_text(encoding='utf-8')) if sys_path.exists() else []

        if not user_entries:
            return sys_entries

        # 用户条目按 doc_number 建立索引
        user_by_key = {}
        for e in user_entries:
            key = e.get('doc_number', '') or e.get('title', '')
            if key:
                user_by_key[key] = e

        merged = []
        seen_keys = set()
        for e in sys_entries:
            key = e.get('doc_number', '') or e.get('title', '')
            if key in user_by_key:
                merged.append(user_by_key[key])  # 用户版本优先
                seen_keys.add(key)
            else:
                merged.append(e)

        # 追加用户独有的条目
        for e in user_entries:
            key = e.get('doc_number', '') or e.get('title', '')
            if key not in seen_keys:
                merged.append(e)
                seen_keys.add(key)

        return merged

    all_entries = []
    seen = set()
    for name in sorted(json_names):
        for e in _load_merged(name):
            if e['title'] not in seen:
                seen.add(e['title'])
                all_entries.append(e)
    return all_entries


# ═══════════════════════════════════════════════════════════
#  URL 降级策略 — 本地工具，不依赖 Agent
# ═══════════════════════════════════════════════════════════

def _fetch_url_fallback(url: str, timeout: int = 5) -> dict:
    """
    URL 五层降级访问 — 自动尝试 HTTPS→HTTP

    Layer 1: HTTPS (curl + 浏览器 UA)
    Layer 2: HTTP 降级
    Layer 3-5: 提示 Agent 环境工具（browser_navigate / web_search / 替代源）
    """
    # Layer 1: HTTPS
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         "-m", str(timeout), "-H", "User-Agent: Mozilla/5.0", url],
        capture_output=True, text=True
    )
    if r.stdout.strip() == "200":
        r2 = subprocess.run(
            ["curl", "-s", "-m", str(timeout), "-H", "User-Agent: Mozilla/5.0", url],
            capture_output=True, text=True
        )
        return {"success": True, "content": r2.stdout, "layer": 1, "method": "HTTPS"}

    # Layer 2: HTTP 降级
    http_url = url.replace("https://", "http://")
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         "-m", str(timeout), http_url],
        capture_output=True, text=True
    )
    if r.stdout.strip() == "200":
        r2 = subprocess.run(
            ["curl", "-s", "-m", str(timeout), http_url],
            capture_output=True, text=True
        )
        return {"success": True, "content": r2.stdout, "layer": 2, "method": "HTTP 降级"}

    return {"success": False, "content": "", "layer": 2, "method": "失败",
            "suggestion": "L3: browser_navigate | L4: web_search | L5: gov.cn 替代源"}


# ═══════════════════════════════════════════════════════════
#  原文读取与段落提取
# ═══════════════════════════════════════════════════════════

def load_source(entry: dict) -> str:
    """读取原文全文（纯文本，去掉 HTML 标签）

    内置五层 URL 降级：本地文件丢失时自动从 source_url L1(HTTPS)→L2(HTTP)→... 获取。
    """
    lp = entry.get('local_path', '')
    fmt = entry.get('format', '')
    if not lp:
        return ''

    fp = resolve_local_path(lp)

    # ── 本地文件不存在 → 尝试 URL 降级获取 ──
    if not fp.exists():
        url = entry.get('source_url', '')
        if url:
            r = _fetch_url_fallback(url)
            if r['success']:
                return re.sub(r'<[^>]+>', '', r['content'])
        return ''

    # PDF：读配套 TXT 或实时 pdftotext
    if fmt == 'pdf':
        txt_fp = fp.with_suffix('.txt')
        if txt_fp.exists():
            return txt_fp.read_text(encoding='utf-8')
        r = subprocess.run(['pdftotext', str(fp), '-'], capture_output=True, text=True, timeout=10)
        return r.stdout

    # HTML：尝试多种容器模式提取正文
    html = fp.read_text(errors='ignore')
    body = ''
    for pat in [
        r'class="border-table noneBorder pages_content"[^>]*>(.*?)</table>',
        r'class="pages_content"[^>]*>(.*?)</div>',
        r'<body[^>]*>(.*?)</body>',
    ]:
        m = re.search(pat, html, re.DOTALL)
        if m:
            body = re.sub(r'<script[^>]*>.*?</script>', '', m.group(1), flags=re.DOTALL)
            body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL)
            break
    if not body:
        return ''
    text = re.sub(r'<[^>]+>', '', body)
    return re.sub(r'\s+', ' ', text).strip()


def extract_paragraphs(entry: dict, keyword: str) -> list[tuple[str, str]]:
    """
    从原文中提取所有包含 keyword 的段落

    返回: [(段落文本, 章节提示), ...]
    规则: 段落必须逐字来自原文，不做改述
    """
    lp = entry.get('local_path', '')
    fmt = entry.get('format', '')
    if not lp:
        return []
    fp = resolve_local_path(lp)
    if not fp.exists():
        return []

    # ── PDF 处理 ──
    if fmt == 'pdf':
        txt_fp = fp.with_suffix('.txt')
        if not txt_fp.exists():
            return []
        text = txt_fp.read_text(encoding='utf-8')
        blocks = re.split(r'\n\s*\n', text)
        results = []
        current_chapter = ''
        for block in blocks:
            s = block.strip()
            if not s:
                continue
            # 短文本且不以句号结尾 → 可能是章节标题
            if len(s) < 60 and not s.endswith(('。', '）', '"', '”')):
                current_chapter = s[:80]
            if keyword in s and len(s) > 30:
                results.append((re.sub(r'\s+', ' ', s).strip(), current_chapter))
        return results

    # ── HTML 处理 ──
    html = fp.read_text(errors='ignore')
    body = ''
    for pat in [
        r'class="border-table noneBorder pages_content"[^>]*>(.*?)</table>',
        r'class="pages_content"[^>]*>(.*?)</div>',
        r'<body[^>]*>(.*?)</body>',
    ]:
        m = re.search(pat, html, re.DOTALL)
        if m:
            body = m.group(1)
            break
    if not body:
        return []

    # 从 <title> 获取文档名作为章节兜底
    doc_title = ''
    tm = re.search(r'<title>(.*?)</title>', html)
    if tm:
        doc_title = tm.group(1)[:80]

    results = []
    chapter = ''
    for pm in re.finditer(r'<p[^>]*>(.*?)</p>', body, re.DOTALL):
        raw = pm.group(1)
        text = re.sub(r'<[^>]+>', '', raw).strip()
        if not text:
            continue
        # 短文本可能是章节标题
        if len(text) < 50 and not text.endswith(('。', '）', '"', '”', '！', '？')):
            chapter = text
        if keyword in text and len(text) > 15:
            results.append((text, chapter if chapter else doc_title))

    return results


# ═══════════════════════════════════════════════════════════
#  全文搜索（依赖 extract_paragraphs，属于文件 I/O 层）
# ═══════════════════════════════════════════════════════════

def search_cache_fulltext(
    cache_dir: Path, keyword: str, hit_entries: list[dict]
) -> list[dict]:
    """全文级关键词搜索 — 仅在标题命中条目中扫描原文"""

    result = []
    for e in hit_entries:
        lp = e.get("local_path", "")
        if not lp or not Path(lp).exists():
            continue
        paras = extract_paragraphs(e, keyword)
        if paras:
            e["_body_hits"] = len(paras)
            result.append(e)
    return result


# ═══════════════════════════════════════════════════════════
#  生成 HTML 输出
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
#  关键词颜色调色板（每词一色，Header标签与段落高亮统一）
# ═══════════════════════════════════════════════════════════

KEYWORD_COLORS = [
    ("#dbeafe", "#1e40af"),  # 蓝
    ("#d1fae5", "#065f46"),  # 绿
    ("#ffedd5", "#9a3412"),  # 橙
    ("#ede9fe", "#5b21b6"),  # 紫
    ("#fce7f3", "#9d174d"),  # 粉
    ("#ccfbf1", "#115e59"),  # 青
    ("#fef3c7", "#92400e"),  # 金
    ("#fee2e2", "#991b1b"),  # 红
    ("#e0e7ff", "#3730a3"),  # 靛蓝
    ("#f3e8ff", "#6b21a8"),  # 深紫
    ("#ecfccb", "#3f6212"),  # 黄绿
    ("#fce4d6", "#9c3a00"),  # 深橙
]


def _kw_color_css(keywords: list[str]) -> str:
    """为每个关键词生成独立的 CSS 高亮类"""
    rules = []
    for i, (bg, fg) in enumerate(zip(
        [c[0] for c in KEYWORD_COLORS] * ((len(keywords) // 12) + 1),
        [c[1] for c in KEYWORD_COLORS] * ((len(keywords) // 12) + 1),
    )):
        if i >= len(keywords):
            break
        rules.append(f".hl-{i}{{background:{bg};color:{fg};padding:0 2px;font-weight:600;border-radius:2px}}")
        rules.append(f".kw-tag-{i}{{background:{bg};color:{fg}}}")
    return "\n".join(rules)


def build_html(title: str, groups: list, keywords: list, summary: str = "") -> str:
    """
    生成结构化 HTML 汇编文件

    参数:
      title:    输出文件标题（如"智慧城市政策汇编"）
      groups:   [(entry, [(para_text, chapter_hint), ...]), ...]
      keywords: 全量关键词列表（全部用于高亮和 Header 展示）
      summary:  公文风格概括摘要（Commander 撰写，为空则跳过摘要区）
    """
    # 去重并保持顺序
    from atoms import deduplicate_entries  # 仅用于数据去重，非文件 I/O
    seen, unique_kws = set(), []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_kws.append(kw)
    keywords = unique_kws
    total_paras = sum(len(p) for _, p in groups)

    # JS: 返回顶部按钮（滚动超过 300px 显示）
    back_to_top_js = """<button id="back-to-top" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button>
<script>window.addEventListener('scroll',function(){document.getElementById('back-to-top').classList.toggle('visible',window.scrollY>300)})</script>"""

    lines = []
    lines.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
    lines.append(f'<title>{title}</title>')
    # 动态注入关键词颜色 CSS
    kw_css = _kw_color_css(keywords)
    lines.append(f'<style>{CSS}\n{kw_css}</style></head><body>')
    lines.append(back_to_top_js)
    # Header：每词不同颜色标签
    kw_tags = ' · '.join(
        f'<span class="kw-tag-{i}" style="padding:2px 8px;border-radius:3px;margin:0 4px">{kw}</span>'
        for i, kw in enumerate(keywords)
    )
    lines.append(f'<div class="header"><h1>{title}</h1><p>匹配关键词：{kw_tags}</p></div>')

    # ── 统计概览卡片 ──
    lines.append('<div class="stats">')
    lines.append(f'<div class="stat-box"><div class="num">{len(groups)}</div><div class="label">涉及文件</div></div>')
    lines.append(f'<div class="stat-box"><div class="num">{total_paras}</div><div class="label">逐字段落</div></div>')
    lines.append('</div>')

    # ── Commander 概括摘要（公文风格，直接可复制）──
    if summary:
        lines.append('<div class="summary-box">')
        lines.append(
            '<h2>📋 政策概述（可直接引用）'
            '<button class="copy-btn" onclick="var p=this.parentNode.parentNode.querySelectorAll(\'p\');'
            'var t=Array.from(p).map(e=>e.innerText).join(\'\\n\\n\');'
            'navigator.clipboard.writeText(t).then(()=>{'
            'this.textContent=\'✓ 已复制\';setTimeout(()=>{this.textContent=\'📋 复制\'},1500)'
            '})" title="复制全部概述内容">📋 复制</button></h2>'
        )
        for para in summary.strip().split('\n'):
            para = para.strip()
            if para:
                lines.append(f'<p>{para}</p>')
        lines.append('</div>')

    # ── 目录（带锚点跳转） ──
    lines.append('<div class="toc"><h2>目录</h2>')
    for i, (entry, _) in enumerate(groups, 1):
        dn = entry.get('doc_number', '') or ''
        lines.append(
            f'<div>📄 {i}. {entry["title"][:40]} '
            f'<span style="color:#999;font-size:12px">({dn})</span> '
            f'<a href="#doc{i}">跳转</a></div>'
        )
    lines.append('</div>')

    # ── 正文 ──
    for i, (entry, paras) in enumerate(groups, 1):
        lines.append(f'<div class="doc-section" id="doc{i}">')
        lines.append('<div class="doc-header">')
        # 折叠按钮（默认折叠，点击展开/收起）
        lines.append(
            f'<button class="fold-toggle" onclick="var b=this.parentNode.parentNode;'
            f'var body=b.querySelector(\'.doc-body\');'
            f'var collapsed=body.classList.toggle(\'collapsed\');'
            f'this.classList.toggle(\'expanded\',!collapsed);'
            f'this.innerHTML=(collapsed?\'▶ 展开\':\'▼ 收起\')">▶ 展开</button>'
        )
        lines.append(f'<h2>{i}. {entry["title"]}</h2>')
        lines.append('<div class="meta">')

        # 所有元信息从缓存 JSON 读取，不硬编码
        if entry.get('doc_number'):
            lines.append(f'<span><span class="label">文号：</span>{entry["doc_number"]}</span>')
        lines.append(f'<span><span class="label">发文：</span>{entry.get("issuer", "")[:40]}</span>')
        lines.append(f'<span><span class="label">日期：</span>{entry.get("date", "")}</span>')
        src_url = entry.get('source_url', '#')
        lines.append(f'<span><span class="label">原文：</span><a href="{src_url}" target="_blank">gov.cn ↗</a></span>')
        lines.append('</div></div>')

        # 验证标签
        lines.append(f'<div class="verify">✅ {len(paras)} 段 · 全部逐字引自原文</div>')

        # 段落区（默认折叠）
        lines.append('<div class="doc-body collapsed">')

        # 逐段输出（含章节标题 + 关键词高亮）
        last_chapter = ''
        for para_text, chapter_hint in paras:
            if chapter_hint and chapter_hint != last_chapter and len(chapter_hint) > 5:
                lines.append(
                    f'<p style="font-weight:bold;color:#2e86c1;margin-top:15px;text-indent:0">'
                    f'{chapter_hint}</p>'
                )
                last_chapter = chapter_hint
            # 全量关键词高亮：每个关键词使用独立颜色（hl-0, hl-1, ...）
            highlighted = para_text
            for i, kw in enumerate(keywords):
                highlighted = highlighted.replace(kw, f'<span class="hl-{i}">{kw}</span>')
            lines.append(f'<p>{highlighted}</p>')
        lines.append('</div>')  # doc-body
        lines.append('</div>')  # doc-section

    lines.append(f'<div class="footer"><p>来源：policy-search-china · 逐字提取</p></div>')
    lines.append('</body></html>')
    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
#  搜索与输出主逻辑
# ═══════════════════════════════════════════════════════════

def search_and_build(title: str, topic_keywords: list[str], mode: str = "or") -> list:
    """
    搜索关键词并提取段落，返回 groups 列表。

    返回: [(entry, [(para_text, chapter_hint), ...]), ...]
    若调用方传入 HTML 生成逻辑则同时写文件。
    """
    all_entries = load_all_cache()
    groups = []

    for entry in all_entries:
        lp = entry.get('local_path', '')
        if not lp:
            continue

        # 逐关键词提取段落
        kw_paras = {}
        for kw in topic_keywords:
            kw_paras[kw] = extract_paragraphs(entry, kw)

        # AND 模式：所有关键词都命中才算
        if mode == "and":
            if not all(kw_paras[kw] for kw in topic_keywords):
                continue

        # 合并段落
        combined = []
        for kw in topic_keywords:
            combined.extend(kw_paras[kw])

        # 按段落去重
        seen = set()
        unique = []
        for pt, ch in combined:
            key = re.sub(r'\s+', '', pt)
            if key not in seen:
                seen.add(key)
                unique.append((pt, ch))

        if unique:
            groups.append((entry, unique))

    if not groups:
        print(f'  ⚠️ "{title}": 无匹配结果')
        return []

    return groups


# ═══════════════════════════════════════════════════════════
#  Stage 3.5: 相关性评价 — Commander 接口
# ═══════════════════════════════════════════════════════════

def export_candidates(
    title: str, groups: list, topic_keywords: list[str]
) -> Path:
    """
    导出候选段落 JSON，供 Commander 进行相关性评价。

    JSON 结构：
      {"title": "...", "keywords": [...],
       "policies": [{"index": 0, "title": "...", "doc_number": "...",
                     "issuer": "...", "date": "...", "source_url": "...",
                     "paragraph_count": N,
                     "paragraphs": [{"p_index": 0, "text": "...",
                                     "chapter": "...", "matched_keywords": [...]}]}]}
    """
    candidates = {
        "title": title,
        "keywords": topic_keywords,
        "policies": [],
    }
    for i, (entry, paras) in enumerate(groups):
        policy = {
            "index": i,
            "title": entry.get("title", ""),
            "doc_number": entry.get("doc_number", ""),
            "issuer": entry.get("issuer", ""),
            "date": entry.get("date", ""),
            "source_url": entry.get("source_url", ""),
            "paragraph_count": len(paras),
            "paragraphs": [],
        }
        for pi, (pt, ch) in enumerate(paras):
            # 记录该段落命中了哪些关键词
            matched = [kw for kw in topic_keywords if kw in pt]
            policy["paragraphs"].append({
                "p_index": pi,
                "text": pt[:300],  # 截断，Commander 不需要全文
                "chapter": ch or "",
                "matched_keywords": matched,
            })
        candidates["policies"].append(policy)

    path = OUTPUT_DIR / f"{title}_candidates.json"
    path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2),
                    encoding='utf-8')
    print(f'  📋 候选清单: {path.name} ({len(groups)} 项政策, '
          f'{sum(p["paragraph_count"] for p in candidates["policies"])} 段)')
    return path


def build_from_relevance_scores(
    scores_path: str, groups: list, topic_keywords: list[str],
    highlight_keywords: list[str] = None
) -> Path:
    """
    根据 Commander 的评分 JSON 过滤段落，生成精简 HTML。

    scores.json 格式：
      {"title": "...",
       "policy_scores": {"0": "核心", "1": "弱相关", "2": "无关", ...},
       "paragraph_overrides": {"0_15": "drop", "1_3": "keep", ...}}

    评分语义：
      "核心"     → 全部保留
      "高度相关" → 全部保留
      "弱相关"   → 仅保留 matched_keywords ≥ 2 的段落（或 overrides 中的 "keep"）
      "无关"     → 全部移除（或 overrides 中的 "keep"）
    """
    with open(scores_path, encoding='utf-8') as f:
        scores = json.load(f)

    title = scores.get("title", "政策汇编")
    policy_scores = scores.get("policy_scores", {})
    overrides = scores.get("paragraph_overrides", {})
    filtered_groups = []

    for i, (entry, paras) in enumerate(groups):
        idx = str(i)
        tier = policy_scores.get(idx, "核心")  # 默认核心

        if tier == "无关":
            # 检查段落级 override
            kept = []
            for pi, (pt, ch) in enumerate(paras):
                ov = overrides.get(f"{idx}_{pi}", "")
                if ov == "keep":
                    kept.append((pt, ch))
            if kept:
                filtered_groups.append((entry, kept))
            continue

        if tier == "弱相关":
            # 仅保留关键词密度高的段落（任一关键词出现 ≥3 次），或 override 为 keep 的
            kept = []
            for pi, (pt, ch) in enumerate(paras):
                ov = overrides.get(f"{idx}_{pi}", "")
                if ov == "drop":
                    continue
                if ov == "keep":
                    kept.append((pt, ch))
                    continue
                # 任一关键词在段落中出现 ≥3 次 → 保留（说明该段确实在讨论此主题）
                if any(pt.count(kw) >= 3 for kw in topic_keywords):
                    kept.append((pt, ch))
            if kept:
                filtered_groups.append((entry, kept))
            continue

        # "核心" / "高度相关" → 全部保留，只处理 drop overrides
        kept = []
        for pi, (pt, ch) in enumerate(paras):
            ov = overrides.get(f"{idx}_{pi}", "")
            if ov == "drop":
                continue
            kept.append((pt, ch))
        if kept:
            filtered_groups.append((entry, kept))

    if not filtered_groups:
        print(f'  ⚠️ 评分过滤后无内容可输出')
        return None

    # 重新统计
    total_paras = sum(len(p) for _, p in filtered_groups)
    before_paras = sum(len(p) for _, p in groups)
    reduction = int((1 - total_paras / before_paras) * 100) if before_paras else 0

    html = build_html(title, filtered_groups, highlight_keywords,
                     summary=scores.get("summary", ""))
    output_path = OUTPUT_DIR / f'{title}.html'
    output_path.write_text(html, encoding='utf-8')
    print(f'  ✅ {title}.html ({len(html)}字, {total_paras}段/{before_paras}原始段,'
          f' -{reduction}%, {len(filtered_groups)}个文件)')
    return output_path

def main():
    parser = argparse.ArgumentParser(
        description='政策汇编 HTML 生成器 — 逐字提取 + 关键词高亮',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
使用示例:
  # 搜索单个主题
  python3 scripts/rebuild_policy_html.py --topic 智慧城市
  python3 scripts/rebuild_policy_html.py --topic "工业互联网"

  # 批量重建预设主题（人工智能、工业互联网等5个）
  python3 scripts/rebuild_policy_html.py --all

  # 搜索多关键词主题
  python3 scripts/rebuild_policy_html.py --topic "数据要素" --topic "人工智能"

  # 交集模式（AND）：只返回同时包含所有关键词的政策
  python3 scripts/rebuild_policy_html.py --topic "人工智能" --topic "能源" --mode and

跨平台:
  设置环境变量 POLICY_SEARCH_CHINA_DATA_DIR 和 POLICY_SEARCH_CHINA_OUTPUT_DIR
  可在任何 Agent 平台上使用本 skill
        """,
    )
    parser.add_argument('--topic', action='append', dest='topics',
                        help='搜索主题关键词（可重复，如 --topic 智慧城市）')
    parser.add_argument('--mode', choices=['or', 'and'], default='or',
                        help='多关键词匹配模式：or=任一命中，and=全部命中（默认 or）')
    parser.add_argument('--all', action='store_true',
                        help='批量重建所有预设主题（PRESET_TOPICS）')
    parser.add_argument('--candidates-only', action='store_true',
                        help='仅导出候选段落 JSON（供 Commander 评价相关性）')
    parser.add_argument('--relevance-scores',
                        help='Commander 评分 JSON 路径（与 --candidates-only 互斥）')
    parser.add_argument('--summary',
                        help='公文风格概括摘要文本（直接嵌入 HTML 目录前）')
    parser.add_argument('--highlight-keywords', nargs='+',
                        help='额外高亮关键词（仅用于展示高亮，不影响搜索过滤）')
    args = parser.parse_args()

    # 打印路径信息
    print(summary())
    print(f'  {"─" * 50}')

    # ── --all 模式：走预设主题列表 ──
    if args.all:
        print(f'\n  批量模式：{len(PRESET_TOPICS)} 个预设主题\n')
        success = 0
        failed = 0
        for title, cfg in PRESET_TOPICS.items():
            if search_and_build(title, cfg['keywords']):
                success += 1
            else:
                failed += 1
        print(f'\n  完成: {success} 成功, {failed} 跳过')
        return

    # ── --topic 模式：用户自定义搜索 ──
    if not args.all and args.topics:
        keywords = args.topics
        # 高亮关键词仅用于展示，不影响搜索
        highlight_kws = keywords + (list(args.highlight_keywords) if args.highlight_keywords else [])
        if len(keywords) == 1:
            title = f'{keywords[0]}政策汇编'
        else:
            title = f'{keywords[0]}与{keywords[1]}政策汇编'
        print(f'\n  单次模式："{title}"\n')

        groups = search_and_build(title, keywords, mode=args.mode)
        if not groups:
            return

        # --candidates-only：导出 JSON，供 Commander 进行 Stage 3.5 评价
        if args.candidates_only:
            path = export_candidates(title, groups, keywords)
            print(f'\n  Commander 请评价此文件中的政策相关性 → 生成 scores.json')
            print(f'  📋 {path}')
            return

        # --relevance-scores：读 Commander 评分后生成精简 HTML
        if args.relevance_scores:
            build_from_relevance_scores(args.relevance_scores, groups, keywords, highlight_kws)
            return

        # 默认：直接生成 HTML（无相关性过滤）
        total_paras = sum(len(p) for _, p in groups)
        html = build_html(title, groups, highlight_kws, summary=args.summary or "")
        output_path = OUTPUT_DIR / f'{title}.html'
        output_path.write_text(html, encoding='utf-8')
        print(f'  ✅ {title}.html ({len(html)}字, {total_paras}段,'
              f' {len(groups)}个文件)')
        return

    # ── 无参数：打印帮助 ──
    parser.print_help()


if __name__ == '__main__':
    main()
