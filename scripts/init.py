#!/usr/bin/env python3
"""
policy-search-china 初始化脚本
在首次安装或首次加载时执行，确保必要目录结构就绪。

运行方式：
  1. 自动：Agent 加载 skill 时检测 setup_needed=true 自动提示执行
  2. 手动：python3 scripts/init.py
  3. 幂等：可重复运行，不会覆盖已有内容

跨平台支持：
  设置环境变量 POLICY_SEARCH_CHINA_DATA_DIR 自定义用户数据目录
  设置环境变量 POLICY_SEARCH_CHINA_OUTPUT_DIR 自定义输出目录
"""

import json
import os
import shutil
from pathlib import Path

# ── 使用跨平台路径工具 ─────────────────────────────
# 在任何 Agent 平台（Hermes / OpenClaw / Workbuddy / Claude Code）上都能运行
_SELF_DIR = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(_SELF_DIR))
from path_utils import (
    SKILL_DIR, SYSTEM_DIR, SYSTEM_CACHE,
    USER_DIR, USER_CACHE, USER_CONFIG, OUTPUT_DIR,
    ensure_dirs,
)

CONFIG_FILE = USER_CONFIG / 'user_config.ini'

# ── 系统空间完整性检查清单 ────────────────────────
# 注意：不是所有缓存文件都必选，但核心索引 JSON 必须存在
REQUIRED_FILES = {
    'SKILL.md': SKILL_DIR / 'SKILL.md',
    'scripts/rebuild_policy_html.py': SKILL_DIR / 'scripts' / 'rebuild_policy_html.py',
}

# 推荐的缓存索引（缺失时仅给出警告，不阻止运行）
RECOMMENDED_CACHE = {
    'cache/cac.json': SYSTEM_CACHE / 'cac.json',
    'cache/gov.json': SYSTEM_CACHE / 'gov.json',
    'cache/miit.json': SYSTEM_CACHE / 'miit.json',
    'cache/ndrc.json': SYSTEM_CACHE / 'ndrc.json',
    'cache/nda.json': SYSTEM_CACHE / 'nda.json',
    'cache/nea.json': SYSTEM_CACHE / 'nea.json',
    'cache/sasac.json': SYSTEM_CACHE / 'sasac.json',
    'cache/most.json': SYSTEM_CACHE / 'most.json',
    'cache/mof.json': SYSTEM_CACHE / 'mof.json',
    'cache/mot.json': SYSTEM_CACHE / 'mot.json',
    'cache/mee.json': SYSTEM_CACHE / 'mee.json',
    'cache/moa.json': SYSTEM_CACHE / 'moa.json',
    'cache/moe.json': SYSTEM_CACHE / 'moe.json',
    'cache/mct.json': SYSTEM_CACHE / 'mct.json',
    'cache/mwr.json': SYSTEM_CACHE / 'mwr.json',
    'cache/mohrss.json': SYSTEM_CACHE / 'mohrss.json',
}


def step_1_create_dirs():
    print('\n[1/5] 创建用户空间目录...')
    ensure_dirs()
    print(f'  ✅ 用户缓存: {USER_CACHE}')
    print(f'  ✅ 用户配置: {USER_CONFIG}')
    print(f'  ✅ 输出目录: {OUTPUT_DIR}')


def step_2_check_system():
    print('\n[2/5] 检查系统空间完整性...')
    all_ok = True
    for label, fpath in REQUIRED_FILES.items():
        exists = fpath.exists()
        if not exists:
            print(f'  ❌ {label}: 文件缺失')
            all_ok = False
        else:
            size = fpath.stat().st_size
            print(f'  ✅ {label}: {size/1024:.0f}KB')

    if not all_ok:
        print('\n  ⚠️ 系统空间不完整，请重新安装 skill')
        return False

    # 检查推荐缓存（非必须）
    for label, fpath in RECOMMENDED_CACHE.items():
        if fpath.exists():
            size = fpath.stat().st_size
            print(f'  ✅ {label}: {size/1024:.0f}KB')
        else:
            print(f'  ⚠️ {label}: 未找到（部分搜索可能受限）')

    print('  ✅ 系统空间完整')
    return True


def step_3_create_config():
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


def step_4_check_deps():
    print('\n[4/5] 依赖验证...')
    deps = ['python3', 'curl', 'pdftotext']
    for cmd in deps:
        if shutil.which(cmd):
            print(f'  ✅ {cmd}')
        else:
            print(f'  ⚠️ {cmd}: 未安装（PDF 处理可能受限）')


def step_5_summary():
    print(f'\n[5/5] 系统状态')
    print(f'  技能根目录: {SKILL_DIR}')
    print(f'  用户空间:   {USER_DIR}')
    sys_count = len(list(SYSTEM_CACHE.glob('*.json')))
    print(f'  预装缓存:   {sys_count} 个 JSON 索引文件')
    usr_count = len(list(USER_CACHE.glob('*.json')))
    if usr_count:
        print(f'  用户缓存:   {usr_count} 个文件')

    # 跨平台提示
    print()
    print('  📌 跨平台使用:')
    print(f'     设置 POLICY_SEARCH_CHINA_DATA_DIR={USER_DIR}')
    print(f'     设置 POLICY_SEARCH_CHINA_OUTPUT_DIR={OUTPUT_DIR}')
    print(f'     即可在其他 Agent 平台上使用本技能')


def main():
    print('=' * 55)
    print('  policy-search-china — 初始化')
    print('=' * 55)

    step_1_create_dirs()
    ok = step_2_check_system()
    if ok:
        step_3_create_config()
    step_4_check_deps()
    step_5_summary()

    print('\n' + '=' * 55)
    print('  初始化完成')
    print('=' * 55)


if __name__ == '__main__':
    main()
