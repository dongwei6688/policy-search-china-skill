#!/usr/bin/env python3
"""
Rebuild all policy HTML output files with STRICT verbatim extraction.
Every paragraph in the output must be 100% present in the source document.

Architecture:
  System space (read-only, replaced on update):
    ~/.hermes/skills/research/policy-search-china/
    ├── SKILL.md, scripts/, cache/ (50 pre-loaded entries)

  User space (read-write, NEVER overwritten on update):
    ~/.hermes/data/policy-search-china/
    ├── cache/ (user-added/modified entries)
    └── config/ (user preferences)

  Search priority: user space > system space
"""
import json, re, subprocess, configparser
from pathlib import Path

# ── Paths ───────────────────────────────────────────
SYSTEM_DIR = Path.home() / '.hermes' / 'skills' / 'research' / 'policy-search-china'
USER_DIR = Path.home() / '.hermes' / 'data' / 'policy-search-china'
OUTPUT_DIR = Path.home() / '.hermes' / 'output'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Ensure user space directories exist on first run
(USER_DIR / 'cache').mkdir(parents=True, exist_ok=True)
(USER_DIR / 'config').mkdir(parents=True, exist_ok=True)


# ── Dual-space path resolution ──────────────────────
def _resolve_local_path(local_path: str) -> Path:
    """Check user space first, then system space."""
    user_path = USER_DIR / local_path
    if user_path.exists():
        return user_path
    return SYSTEM_DIR / local_path


def _resolve_json_file(filename: str) -> list[dict]:
    """Load JSON cache: user space overrides system space by doc_number."""
    user_path = USER_DIR / 'cache' / filename
    system_path = SYSTEM_DIR / 'cache' / filename

    user_entries: list[dict] = []
    system_entries: list[dict] = []

    if user_path.exists():
        user_entries = json.loads(user_path.read_text(encoding='utf-8'))
    if system_path.exists():
        system_entries = json.loads(system_path.read_text(encoding='utf-8'))

    if not user_entries:
        return system_entries

    # Merge: user entries override system entries by doc_number
    user_by_key: dict[str, dict] = {}
    for e in user_entries:
        key = e.get('doc_number', '') or e.get('title', '')
        if key:
            user_by_key[key] = e

    merged = []
    seen_keys = set()
    for e in system_entries:
        key = e.get('doc_number', '') or e.get('title', '')
        if key in user_by_key:
            # User has a version → use user's version
            merged.append(user_by_key[key])
            seen_keys.add(key)
        else:
            merged.append(e)

    # Add user-only entries (added by user, not in system)
    for e in user_entries:
        key = e.get('doc_number', '') or e.get('title', '')
        if key not in seen_keys:
            merged.append(e)
            seen_keys.add(key)

    return merged


def load_all_cache() -> list[dict]:
    """Load all cache entries from all JSON files, user-first merge."""
    all_entries = []
    seen = set()

    # Collect all JSON filenames from both spaces
    json_names = set()
    for d in [USER_DIR / 'cache', SYSTEM_DIR / 'cache']:
        if d.exists():
            for jf in sorted(d.glob('*.json')):
                json_names.add(jf.name)

    for name in sorted(json_names):
        for e in _resolve_json_file(name):
            if e['title'] not in seen:
                seen.add(e['title'])
                all_entries.append(e)
    return all_entries


def load_source(entry: dict) -> str:
    """Return verbatim text from source file (checks user space first)."""
    lp = entry.get('local_path', '')
    fmt = entry.get('format', '')
    if not lp:
        return ''
    fp = _resolve_local_path(lp)
    if not fp.exists():
        return ''
    if fmt == 'pdf':
        txt_fp = fp.with_suffix('.txt')
        if txt_fp.exists():
            return txt_fp.read_text(encoding='utf-8')
        r = subprocess.run(['pdftotext', str(fp), '-'], capture_output=True, text=True, timeout=10)
        return r.stdout
    # HTML
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
    if body:
        text = re.sub(r'<[^>]+>', '', body)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    return ''


def extract_paragraphs(entry: dict, keyword: str) -> list[tuple[str, str]]:
    """Extract verbatim paragraphs containing keyword. Returns [(text, chapter_hint)]."""
    lp = entry.get('local_path', '')
    fmt = entry.get('format', '')
    if not lp:
        return []
    fp = _resolve_local_path(lp)
    if not fp.exists():
        return []

    paragraphs = []

    if fmt == 'pdf':
        txt_fp = fp.with_suffix('.txt')
        if not txt_fp.exists():
            return paragraphs
        text = txt_fp.read_text(encoding='utf-8')
        blocks = re.split(r'\n\s*\n', text)
        current_chapter = ''
        for block in blocks:
            block_stripped = block.strip()
            if not block_stripped:
                continue
            if len(block_stripped) < 60 and not block_stripped.endswith(('。','）','"','”')):
                current_chapter = block_stripped[:80]
            if keyword in block_stripped and len(block_stripped) > 30:
                cleaned = re.sub(r'\s+', ' ', block_stripped).strip()
                paragraphs.append((cleaned, current_chapter))
        return paragraphs

    # HTML
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
        return paragraphs

    metadata = re.search(r'<title>(.*?)</title>', html)
    doc_title = metadata.group(1)[:80] if metadata else ''

    chapter = ''
    for p_match in re.finditer(r'<p[^>]*>(.*?)</p>', body, re.DOTALL):
        raw = p_match.group(1)
        text = re.sub(r'<[^>]+>', '', raw).strip()
        if not text:
            continue
        if len(text) < 50 and not text.endswith(('。','）','"','”','！','？')):
            chapter = text
        if keyword in text and len(text) > 15:
            paragraphs.append((text, chapter if chapter else doc_title))

    return paragraphs


# ── HTML builder ─────────────────────────────────────
TOPICS = {
    '人工智能政策汇编': {'keywords': ['人工智能'], 'files_filter': lambda e: True},
    '工业互联网政策汇编': {'keywords': ['工业互联网'], 'files_filter': lambda e: True},
    '算力网络政策汇编': {'keywords': ['算力网络'], 'files_filter': lambda e: True},
    'AI与数据要素政策汇编': {'keywords': ['人工智能', '数据要素'], 'files_filter': lambda e: True},
    '智能矿山政策汇编': {'keywords': ['智能矿山', '煤矿智能化'], 'files_filter': lambda e: True},
}

# HTML template parts (CSS)
CSS = """\
body{font-family:'宋体',SimSun,serif;max-width:960px;margin:0 auto;padding:20px;background:#f9f9f9;color:#222;line-height:1.8}
.header{background:linear-gradient(135deg,#1a5276,#2e86c1);color:#fff;padding:30px;border-radius:10px;margin-bottom:30px}
.header h1{margin:0 0 10px 0;font-size:24px}.header p{margin:0;opacity:.85;font-size:14px}
.stats{display:flex;gap:15px;margin:20px 0;flex-wrap:wrap}
.stat-box{background:#fff;border-radius:8px;padding:15px 25px;box-shadow:0 2px 8px rgba(0,0,0,.08);flex:1;min-width:120px;text-align:center}
.stat-box .num{font-size:28px;font-weight:bold;color:#1a5276}.stat-box .label{font-size:12px;color:#666;margin-top:5px}
.toc{background:#fff;border-radius:8px;padding:20px 30px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:25px}
.toc h2{font-size:16px;color:#1a5276;margin:0 0 15px 0;border-bottom:2px solid #1a5276;padding-bottom:8px}
.toc a{display:inline-block;padding:2px 8px;margin:2px 0;color:#2e86c1;text-decoration:none;font-size:13px;background:#eef6fb;border-radius:3px}
.doc-section{background:#fff;border-radius:8px;padding:25px 30px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:25px;border-top:4px solid #1a5276}
.doc-header{margin-bottom:15px;padding-bottom:12px;border-bottom:1px solid #e0e0e0}
.doc-header h2{margin:0 0 8px 0;font-size:18px;color:#1a5276}
.doc-header .meta{font-size:13px;color:#666;margin-top:8px}
.doc-header .meta span{margin-right:15px}
.doc-header .meta .label{color:#999}
.doc-header .meta a{color:#2e86c1;text-decoration:none}
.doc-section p{text-indent:2em;margin:6px 0;font-size:14px;text-align:justify}
.hl{background:#fff3cd;padding:0 2px;font-weight:bold}
.verify{border:1px solid #27ae60;background:#eafaf1;padding:8px 15px;border-radius:5px;font-size:12px;color:#1e8449;margin:10px 0}
.footer{text-align:center;color:#999;font-size:12px;margin-top:30px;padding-top:20px;border-top:1px solid #ddd}
"""


def build_html(title: str, groups: list, config: dict) -> str:
    """Build final HTML with strict verbatim paragraphs."""
    keyword = config['keywords'][0]
    total_paras = sum(len(p) for _, p in groups)

    lines = []
    lines.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
    lines.append(f'<title>{title}</title>')
    lines.append(f'<style>{CSS}</style></head><body>')
    lines.append(f'<div class="header"><h1>{title}</h1><p>逐字引用 · 所有段落可在原文中验证</p></div>')

    lines.append('<div class="stats">')
    lines.append(f'<div class="stat-box"><div class="num">{len(groups)}</div><div class="label">涉及文件</div></div>')
    lines.append(f'<div class="stat-box"><div class="num">{total_paras}</div><div class="label">逐字段落</div></div>')
    lines.append('</div>')

    # TOC
    lines.append('<div class="toc"><h2>目录</h2>')
    for i, (entry, _) in enumerate(groups, 1):
        dn = entry.get('doc_number', '') or ''
        lines.append(f'<div>📄 {i}. {entry["title"][:40]} <span style="color:#999;font-size:12px">({dn})</span> <a href="#doc{i}">跳转</a></div>')
    lines.append('</div>')

    # Documents — ALL metadata from cache JSON, never hardcoded
    for i, (entry, paras) in enumerate(groups, 1):
        lines.append(f'<div class="doc-section" id="doc{i}">')
        lines.append('<div class="doc-header">')
        lines.append(f'<h2>{i}. {entry["title"]}</h2>')
        lines.append('<div class="meta">')
        if entry.get('doc_number'):
            lines.append(f'<span><span class="label">文号：</span>{entry["doc_number"]}</span>')
        lines.append(f'<span><span class="label">发文：</span>{entry["issuer"][:40]}</span>')
        lines.append(f'<span><span class="label">日期：</span>{entry["date"]}</span>')
        lines.append(f'<span><span class="label">原文：</span><a href="{entry["source_url"]}" target="_blank">gov.cn ↗</a></span>')
        lines.append('</div></div>')
        lines.append(f'<div class="verify">✅ {len(paras)} 段 · 全部逐字引自原文</div>')

        last_chapter = ''
        for para_text, chapter_hint in paras:
            if chapter_hint and chapter_hint != last_chapter and len(chapter_hint) > 5:
                lines.append(f'<p style="font-weight:bold;color:#2e86c1;margin-top:15px;text-indent:0">{chapter_hint}</p>')
                last_chapter = chapter_hint
            highlighted = para_text.replace(keyword, f'<span class="hl">{keyword}</span>')
            lines.append(f'<p>{highlighted}</p>')
        lines.append('</div>')

    lines.append(f'<div class="footer"><p>来源：policy-search-china · 逐字提取</p><p>用户空间：{USER_DIR}</p></div>')
    lines.append('</body></html>')
    return '\n'.join(lines)


# ── Main ────────────────────────────────────────────
if __name__ == '__main__':
    print(f'用户空间: {USER_DIR}')
    print(f'系统空间: {SYSTEM_DIR}')
    print(f'{"="*60}')

    for topic_name, config in TOPICS.items():
        print(f'\n  {topic_name}')
        all_entries = load_all_cache()
        groups = []

        for entry in all_entries:
            lp = entry.get('local_path', '')
            if not lp:
                continue

            combined_paras = []
            for kw in config['keywords']:
                paras = extract_paragraphs(entry, kw)
                combined_paras.extend(paras)

            seen_paras = set()
            unique_paras = []
            for pt, ch in combined_paras:
                key = re.sub(r'\s+', '', pt)
                if key not in seen_paras:
                    seen_paras.add(key)
                    unique_paras.append((pt, ch))

            if unique_paras:
                groups.append((entry, unique_paras))

        if not groups:
            print(f'  ⚠️ 无匹配结果')
            continue

        html = build_html(topic_name, groups, config)
        output_path = OUTPUT_DIR / f'{topic_name}.html'
        output_path.write_text(html, encoding='utf-8')
        print(f'  ✅ 输出: {output_path.name} ({len(html)}字, {sum(len(p) for _,p in groups)}段)')

    print(f'\n{"="*60}')
    print(f'完成。用户空间: {USER_DIR}')
    print(f'系统空间: {SYSTEM_DIR}')
