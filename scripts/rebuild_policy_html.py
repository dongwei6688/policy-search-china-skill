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

架构说明：
  系统空间（只读，更新替换）: ~/.hermes/skills/research/policy-search-china/
  用户空间（读写，永不覆盖）: ~/.hermes/data/policy-search-china/
  输出目录:                  ~/.hermes/output/

  搜索优先级：用户空间 > 系统空间
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

# ═══════════════════════════════════════════════════════════
#  路径配置
# ═══════════════════════════════════════════════════════════
SYSTEM_DIR = Path.home() / '.hermes' / 'skills' / 'research' / 'policy-search-china'
USER_DIR = Path.home() / '.hermes' / 'data' / 'policy-search-china'
OUTPUT_DIR = Path.home() / '.hermes' / 'output'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
#  CSS 样式（生成 HTML 时嵌入）
# ═══════════════════════════════════════════════════════════
CSS = """\
body{font-family:'宋体',SimSun,serif;max-width:960px;margin:0 auto;padding:20px;background:#f9f9f9;color:#222;line-height:1.8}
.header{background:linear-gradient(135deg,#1a5276,#2e86c1);color:#fff;padding:30px;border-radius:10px;margin-bottom:30px}
.header h1{margin:0 0 10px 0;font-size:24px}.header p{margin:0;opacity:.85;font-size:14px}
.stats{display:flex;gap:15px;margin:20px 0;flex-wrap:wrap}
.stat-box{background:#fff;border-radius:8px;padding:15px 25px;box-shadow:0 2px 8px rgba(0,0,0,.08);flex:1;min-width:120px;text-align:center}
.stat-box .num{font-size:28px;font-weight:bold;color:#1a5276}.stat-box .label{font-size:12px;color:#666;margin-top:5px}
.toc{background:#fff;border-radius:8px;padding:20px 30px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:25px}
.toc h2{font-size:16px;color:#1a5276;margin:0 0 15px 0;border-bottom:2px solid #1a5276;padding-bottom:8px}
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


# ═══════════════════════════════════════════════════════════
#  双空间缓存读取
#  核心逻辑：用户空间优先，系统空间兜底
# ═══════════════════════════════════════════════════════════

def _resolve_local_path(local_path: str) -> Path:
    """查找本地原文文件，优先查用户空间"""
    user_path = USER_DIR / local_path
    if user_path.exists():
        return user_path
    return SYSTEM_DIR / local_path


def load_all_cache() -> list[dict]:
    """
    加载所有缓存条目（用户空间优先合并）

    合并规则：
    - 用户空间和系统空间同时有同 doc_number 的条目 → 用用户的
    - 仅用户有的 → 保留
    - 仅系统有的 → 保留
    """
    json_names = set()
    for d in [USER_DIR / 'cache', SYSTEM_DIR / 'cache']:
        if d.exists():
            for jf in sorted(d.glob('*.json')):
                json_names.add(jf.name)

    def _load_merged(name: str) -> list[dict]:
        user_path = USER_DIR / 'cache' / name
        sys_path = SYSTEM_DIR / 'cache' / name

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
#  原文读取与段落提取
# ═══════════════════════════════════════════════════════════

def load_source(entry: dict) -> str:
    """读取原文全文（纯文本，去掉 HTML 标签）"""
    lp = entry.get('local_path', '')
    fmt = entry.get('format', '')
    if not lp:
        return ''
    fp = _resolve_local_path(lp)
    if not fp.exists():
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
    fp = _resolve_local_path(lp)
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
#  生成 HTML 输出
# ═══════════════════════════════════════════════════════════

def build_html(title: str, groups: list, keywords: list) -> str:
    """
    生成结构化 HTML 汇编文件

    参数:
      title:    输出文件标题（如"智慧城市政策汇编"）
      groups:   [(entry, [(para_text, chapter_hint), ...]), ...]
      keywords: 关键词列表（第一个用于高亮）
    """
    keyword = keywords[0]
    total_paras = sum(len(p) for _, p in groups)

    lines = []
    lines.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
    lines.append(f'<title>{title}</title>')
    lines.append(f'<style>{CSS}</style></head><body>')
    lines.append(f'<div class="header"><h1>{title}</h1><p>逐字引用 · 所有段落可在原文中验证</p></div>')

    # ── 统计概览卡片 ──
    lines.append('<div class="stats">')
    lines.append(f'<div class="stat-box"><div class="num">{len(groups)}</div><div class="label">涉及文件</div></div>')
    lines.append(f'<div class="stat-box"><div class="num">{total_paras}</div><div class="label">逐字段落</div></div>')
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

        # 逐段输出（含章节标题 + 关键词高亮）
        last_chapter = ''
        for para_text, chapter_hint in paras:
            if chapter_hint and chapter_hint != last_chapter and len(chapter_hint) > 5:
                lines.append(
                    f'<p style="font-weight:bold;color:#2e86c1;margin-top:15px;text-indent:0">'
                    f'{chapter_hint}</p>'
                )
                last_chapter = chapter_hint
            # 关键词高亮：仅更改展示，不改变原文文字
            highlighted = para_text.replace(keyword, f'<span class="hl">{keyword}</span>')
            lines.append(f'<p>{highlighted}</p>')
        lines.append('</div>')

    lines.append(f'<div class="footer"><p>来源：policy-search-china · 逐字提取</p></div>')
    lines.append('</body></html>')
    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
#  搜索与输出主逻辑
# ═══════════════════════════════════════════════════════════

def search_and_build(title: str, topic_keywords: list[str]) -> bool:
    """
    搜索关键词并生成 HTML

    返回: True=找到了内容，False=无匹配
    """
    all_entries = load_all_cache()
    groups = []

    for entry in all_entries:
        lp = entry.get('local_path', '')
        if not lp:
            continue

        # 可能有多关键词（如"人工智能"+"数据要素"），合并段落
        combined = []
        for kw in topic_keywords:
            combined.extend(extract_paragraphs(entry, kw))

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
        return False

    html = build_html(title, groups, topic_keywords)
    output_path = OUTPUT_DIR / f'{title}.html'
    output_path.write_text(html, encoding='utf-8')
    total_paras = sum(len(p) for _, p in groups)
    print(f'  ✅ {title}.html ({len(html)}字, {total_paras}段, {len(groups)}个文件)')
    return True


# ═══════════════════════════════════════════════════════════
#  命令行入口
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='政策汇编 HTML 生成器 — 逐字提取 + 关键词高亮',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 搜索单个主题
  python3 scripts/rebuild_policy_html.py --topic 智慧城市
  python3 scripts/rebuild_policy_html.py --topic "工业互联网"

  # 批量重建预设主题（人工智能、工业互联网等5个）
  python3 scripts/rebuild_policy_html.py --all

  # 搜索多关键词主题
  python3 scripts/rebuild_policy_html.py --topic "数据要素" --topic "人工智能"
        """,
    )
    parser.add_argument('--topic', action='append', dest='topics',
                        help='搜索主题关键词（可重复，如 --topic 智慧城市）')
    parser.add_argument('--all', action='store_true',
                        help='批量重建所有预设主题（PRESET_TOPICS）')
    args = parser.parse_args()

    print(f'  用户空间: {USER_DIR}')
    print(f'  系统空间: {SYSTEM_DIR}')
    print(f'  {"─" * 55}')

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
    if args.topics:
        # 多个 --topic 视为多关键词（如 "数据要素" + "人工智能"）
        keywords = args.topics
        # 生成标题时用关键词组合
        if len(keywords) == 1:
            title = f'{keywords[0]}政策汇编'
        else:
            title = f'{keywords[0]}与{keywords[1]}政策汇编'
        print(f'\n  单次模式："{title}"\n')
        search_and_build(title, keywords)
        return

    # ── 无参数：打印帮助 ──
    parser.print_help()


if __name__ == '__main__':
    main()
