#!/usr/bin/env python3
"""
policy-search-china — 跨平台路径工具

让 skill 在任何 Agent 平台上都能使用，不再硬编码 ~/.hermes/ 路径。

解析规则（优先级从高到低）：
  1. 环境变量 POLICY_SEARCH_CHINA_DATA_DIR  用户数据目录
  2. 环境变量 POLICY_SEARCH_CHINA_OUTPUT_DIR 输出目录
  3. 传统 Hermes 路径 ~/.hermes/data/policy-search-china/（向后兼容）
  4. 兜底：SKILL_DIR/data/（skill 自带数据目录）

用法：
  from path_utils import SYSTEM_DIR, USER_DIR, OUTPUT_DIR, SYSTEM_CACHE, USER_CACHE
"""

import os
from pathlib import Path


# ── 技能根目录（从脚本位置推算，始终可靠） ────────────
# scripts/ 的上一级就是 skill 根目录
SKILL_DIR = Path(__file__).resolve().parent.parent


# ── 系统空间（只读，随 skill 分发） ──────────────────
SYSTEM_DIR = SKILL_DIR
SYSTEM_CACHE = SYSTEM_DIR / 'cache'


# ── 用户空间（读写，用户自己的数据和配置） ────────────
_ENV_DATA = os.environ.get('POLICY_SEARCH_CHINA_DATA_DIR')
if _ENV_DATA:
    USER_DIR = Path(_ENV_DATA).resolve()
else:
    # 向后兼容：检测是否在 Hermes 环境下运行
    _hermes_data = Path.home() / '.hermes' / 'data' / 'policy-search-china'
    if _hermes_data.exists():
        USER_DIR = _hermes_data
    else:
        # 兜底：用 skill 自带的 data 目录
        USER_DIR = SKILL_DIR / 'data'

USER_CACHE = USER_DIR / 'cache'
USER_CONFIG = USER_DIR / 'config'


# ── 输出目录 ──────────────────────────────────────────
_OUTPUT_ENV = os.environ.get('POLICY_SEARCH_CHINA_OUTPUT_DIR')
if _OUTPUT_ENV:
    OUTPUT_DIR = Path(_OUTPUT_ENV).resolve()
else:
    OUTPUT_DIR = USER_DIR / 'output'


def ensure_dirs():
    """确保所有必要目录存在（幂等）"""
    for d in [USER_CACHE, USER_CONFIG, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def resolve_local_path(local_path: str) -> Path:
    """
    查找本地原文文件，优先查用户空间（用户可覆盖系统文件）

    参数:
      local_path: 缓存条目中的 local_path 字段值（相对路径）

    返回:
      文件的绝对路径（用户空间优先）
    """
    user_path = USER_DIR / local_path
    if user_path.exists():
        return user_path
    return SYSTEM_DIR / local_path


def summary() -> str:
    """打印路径配置摘要"""
    lines = [
        '═' * 50,
        '  policy-search-china 路径配置',
        '═' * 50,
        f'  技能根目录 (SKILL_DIR):   {SKILL_DIR}',
        f'  系统缓存 (SYSTEM_CACHE):  {SYSTEM_CACHE}',
        f'  用户目录 (USER_DIR):      {USER_DIR}',
        f'  用户缓存 (USER_CACHE):    {USER_CACHE}',
        f'  输出目录 (OUTPUT_DIR):    {OUTPUT_DIR}',
    ]

    # 统计缓存文件数
    sys_count = len(list(SYSTEM_CACHE.glob('*.json'))) if SYSTEM_CACHE.exists() else 0
    usr_count = len(list(USER_CACHE.glob('*.json'))) if USER_CACHE.exists() else 0
    lines.append(f'  系统缓存索引:           {sys_count} 个 JSON')
    lines.append(f'  用户缓存索引:           {usr_count} 个 JSON')
    lines.append('═' * 50)
    return '\n'.join(lines)


if __name__ == '__main__':
    print(summary())
