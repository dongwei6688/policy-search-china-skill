#!/usr/bin/env python3
"""
policy-search-china 初始化脚本
在首次安装或首次加载时执行，确保必要目录结构就绪。

运行方式（三种）：
  1. 自动：Hermes 加载 skill 时检测 setup_needed=true 自动提示执行
  2. 手动：python3 scripts/init.py
  3. 幂等：可重复运行，不会覆盖已有内容
"""
import json, os, shutil
from pathlib import Path

# ── 路径 ───────────────────────────────────────────
SKILL_DIR = Path(__file__).resolve().parent.parent
USER_DIR = Path.home() / '.hermes' / 'data' / 'policy-search-china'
SYSTEM_CACHE = SKILL_DIR / 'cache'
USER_CACHE = USER_DIR / 'cache'
USER_CONFIG = USER_DIR / 'config'
OUTPUT_DIR = Path.home() / '.hermes' / 'output'
CONFIG_FILE = USER_CONFIG / 'user_config.ini'

print('=' * 55)
print('  policy-search-china — 初始化')
print('=' * 55)

# ── Step 1: 创建用户空间目录 ──────────────────────
print('\n[1/5] 创建用户空间目录...')
USER_CACHE.mkdir(parents=True, exist_ok=True)
USER_CONFIG.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f'  ✅ 用户缓存: {USER_CACHE}')
print(f'  ✅ 用户配置: {USER_CONFIG}')
print(f'  ✅ 输出目录: {OUTPUT_DIR}')

# ── Step 2: 检查系统空间完整性 ─────────────────────
print('\n[2/5] 检查系统空间完整性...')
checks = {
    'SKILL.md': SKILL_DIR / 'SKILL.md',
    'scripts/rebuild_policy_html.py': SKILL_DIR / 'scripts' / 'rebuild_policy_html.py',
    'cache/cac.json': SYSTEM_CACHE / 'cac.json',
    'cache/gov.json': SYSTEM_CACHE / 'gov.json',
    'cache/miit.json': SYSTEM_CACHE / 'miit.json',
    'cache/ndrc.json': SYSTEM_CACHE / 'ndrc.json',
    'cache/nda.json': SYSTEM_CACHE / 'nda.json',
    'cache/nea.json': SYSTEM_CACHE / 'nea.json',
    'cache/sasac.json': SYSTEM_CACHE / 'sasac.json',
}
all_ok = True
for label, fpath in checks.items():
    exists = fpath.exists()
    if not exists:
        print(f'  ❌ {label}: 文件缺失')
        all_ok = False
    else:
        size = fpath.stat().st_size
        print(f'  ✅ {label}: {size/1024:.0f}KB')

if not all_ok:
    print('\n  ⚠️ 系统空间不完整，请重新安装 skill')
else:
    print('  ✅ 系统空间完整')

# ── Step 3: 创建默认配置文件 ──────────────────────
print('\n[3/5] 配置文件...')
if not CONFIG_FILE.exists():
    config_content = f"""# policy-search-china 用户空间配置文件
# 首次运行时自动生成，可安全修改

[paths]
user_data_dir = {USER_DIR}
system_skill_dir = {SKILL_DIR}

[search]
# 缓存搜索优先级: user_first | system_first
priority = user_first
"""
    CONFIG_FILE.write_text(config_content)
    print(f'  ✅ 已创建: {CONFIG_FILE}')
else:
    print(f'  🔄 已存在, 未覆盖: {CONFIG_FILE}')

# ── Step 4: 验证可执行依赖 ────────────────────────
print('\n[4/5] 依赖验证...')
deps = ['python3', 'curl', 'pdftotext']
for cmd in deps:
    if shutil.which(cmd):
        print(f'  ✅ {cmd}')
    else:
        print(f'  ⚠️ {cmd}: 未安装（PDF 处理可能受限）')

# ── Step 5: 打印系统状态 ──────────────────────────
print(f'\n[5/5] 系统状态')
print(f'  系统空间: {SKILL_DIR}')
print(f'  用户空间: {USER_DIR}')
cache_count = len(list(SYSTEM_CACHE.glob('*.json')))
print(f'  预装缓存: {cache_count} 个 JSON 索引文件')

user_cache_count = len(list(USER_CACHE.glob('*.json')))
if user_cache_count:
    print(f'  用户缓存: {user_cache_count} 个文件')

print('\n' + '=' * 55)
print('  初始化完成')
print('=' * 55)
