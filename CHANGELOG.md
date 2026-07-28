## v2.8.1 (2026-07-28)

### Added
- 每词独立颜色：Header 关键词标签与段落高亮使用统一的 12 色调色板
- `--highlight-keywords` CLI 参数：搜索词与展示词分离，不影响搜索精度
- Header 匹配关键词列表替换原静态文案

### Changed
- `build_html()` 全量关键词高亮（替换原单关键词高亮）
- 动态注入 per-keyword CSS 类（`.hl-0` ~ `.hl-N`）

# Changelog

## [v2.8.0] — 2026-07-28

### 重构
- **atoms.py 完全纯数据化**：`check_cache_freshness` 和 `search_cache_title` 不再接受 `cache_dir: Path` 参数，改为接收 `entries: list[dict]`。所有文件 I/O（`json.loads(jf.read_text())`）从 atoms 中移除，由调用方 `load_all_cache()` 统一负责后传入
- **chain 函数签名简化**：`chain_cross_analysis` / `chain_broad_scan` / `chain_precise_locate` / `chain_trace_source` 不再接收 `cache_dir` 参数，内部通过 `load_all_cache()` 自加载，调用更简洁

### 清理
- 删除 `references/output-format.md`（197 行 —— Commander 不需要了解 HTML 输出格式，Worker 内部实现无需暴露）
- 删除 `rebuild_policy_html.py` 中的死 `import`（`from atoms import search_cache_title` 在 `search_cache_fulltext` 中未实际调用）
- `atoms.py` header 从"18 个纯函数"更正为实际函数数量，去除过时注释
- `chain_runner.py` 去除所有 `cache_dir` 变量引用（剩余 0 处）

### 文档
- `SKILL.md` 阶段 1 补回 `references/search-strategies.md` 引用，确保 Commander 可见搜索策略参考

---

## [v2.7.1] — 2026-07-28

### 新增
- **政策概述一键复制按钮**：`summary-box` 标题右侧新增「📋 复制」按钮，使用 `navigator.clipboard.writeText()` 将全部概述段落复制到剪贴板。点击后按钮变为「✓ 已复制」1.5 秒自动还原

### 样式
- 新增 `.copy-btn` CSS 样式（金底白字，hove 加深，#d4ac0d → #b8960b）

---

## [v2.7.0] — 2026-07-28

### 新增
- **段落默认折叠**：每个政策 `.doc-section` 的段落区默认收起（`max-height: 0`），标题右侧显示「▶ 展开」按钮，点击切换展开/收起，箭头带 0.3s 旋转变换
- 折叠按钮支持展开/收起文本切换（「▼ 收起」↔「▶ 展开」），0.4s 高度过渡动画
- 验证标签（"N段 · 逐字引自原文"）始终可见，不受折叠影响

### 样式
- 新增 `.fold-toggle` / `.doc-body` / `.doc-body.collapsed` CSS 类，按钮深蓝底白色文字，hover 变浅蓝

---

## [v2.6.0] — 2026-07-28

### 新增
- **HTM 右侧悬浮返回顶部按钮**：滚动超过 300px 后显示圆形蓝色 `↑` 按钮，点击平滑滚动回顶部。使用 `position: fixed` + `opacity` 过渡动画
- **公文风格概括摘要**：`build_html()` 新增 `summary` 参数，Commander 撰写的概括文字以金底 `.summary-box` 展示在目录前面，分段落显示，可直接复制引用
- **Commander 段落级审查能力**：`scores.json` 新增 `paragraph_overrides` 字段，支持逐段标记 `drop` / `keep`，实现"政策级 + 段落级"两级过滤
- CLI 新增 `--summary` 参数，支持在默认路径（无相关性评分）下直接嵌入摘要

### 变更
- `build_html()` 函数签名从 `(title, groups, keywords)` 改为 `(title, groups, keywords, summary)`
- `scores.json` 格式扩展：新增 `summary` 字段和 `paragraph_overrides` 字段

---

## [v2.5.0] — 2026-07-28

### 新增
- **Stage 3.5 Commander 相关性评价流程**：政策提取后，Commander 读取候选 JSON，按政策级别标注"核心/高度相关/弱相关/无关"四级评分，生成 `scores.json` 后由 Worker 过滤生成精简 HTML
- `rebuild_policy_html.py` 新增 `--candidates-only` 模式：导出结构化候选段落 JSON（含 `matched_keywords` 标注），供 Commander 评价
- `rebuild_policy_html.py` 新增 `--relevance-scores` 模式：读取 Commander 评分后自动过滤段落并输出精简 HTML
- `export_candidates()` / `build_from_relevance_scores()` 两个新函数

### 过滤规则
- "核心" 政策 → 全部段落保留
- "高度相关" 政策 → 全部段落保留
- "弱相关" 政策 → 仅保留关键词出现 ≥3 次的段落
- "无关" 政策 → 全部移除

### 变更
- `search_and_build()` 返回类型从 `bool` 改为 `list`（返回 groups 列表供调用方重用）
- Stage 3→4 拆分为 Stage 3（候选导出）+ Stage 3.5（Commander 评分）+ Stage 4（评分后输出）

---

## [v2.4.0] — 2026-07-28

### 新增
- **SKILL.md 全面标注指挥官/工人边界**：每阶段明确标记谁规划（🤖）谁执行（🔧），去除内联 Python 代码块，改为 Commander 决策清单
- **指挥官审核协议**：Stage 0/1/3/4 各设 Commander review 检查点，确保执行路径可验证、不可跳过
- `chain_runner.py` CLI 补全 4 个缺失参数：`--issuer`、`--doctype`、`--exclude`、`--web`
- `_merge_search_results()` 函数预留（缓存 + Web 结果合并）

### 删除
- `verify_verbatim()` 死代码（已被 `build_html` 输出标签替代）
- `chain_runner.py` 中关于 `verify_verbatim` 的过时注释
- `search-strategies.md` 附录中与 `policy-sources.md` 重复的 15 行信源归属规则表（改为一行引用）

### 文档
- SKILL.md 从 192 行精简至 110 行，去除 Pipeline Planning 大段表格

---

## [v2.3.0] — 2026-07-28

### 新增
- **Stage 1 并行搜索**：多关键词使用 `ThreadPoolExecutor` 并行调用 `search_cache_title`，上限 8 线程
- **Stage 3 并行提取**：`extract_all_paragraphs()` 使用 `ThreadPoolExecutor` 并行调用 `extract_paragraphs`，内置收集排序
- `_merge_search_results()` 函数（缓存 + Web 补充搜索结果合并）

### 修复
- `deduplicate_entries` 从 Stage 4 前移至 Stage 2 末尾，避免对重复条目做冗余文件 I/O
- `extract_paragraphs` import 路径从 `atoms` 改为 `rebuild_policy_html`
- `search_cache_fulltext` import 路径同步修正

### 精简
- SKILL.md Pipeline Planning 大段并行度分析表格删除，判断逻辑下沉到 `chain_runner.py`

---

## [v2.2.0] — 2026-07-28

### 重构
- **职责边界分离**：
  - `atoms.py` → 纯数据操作（search/filter/intersect/dedup），不含文件 I/O
  - `rebuild_policy_html.py` → 文件 I/O + 输出（load_source/extract_paragraphs/build_html/URL 降级）
  - `chain_runner.py` → 编排层（单向引用：chain → rebuild → atoms）
- 删除 atoms.py 中的 `load_source()` / `extract_paragraphs()` / `fetch_url_with_fallback()` 重复实现（与 rebuild 版本功能分叉）
- 删除 `FALLBACK_DOMAINS` 常量（降级逻辑内嵌到 `_fetch_url_fallback`）

---

## [v2.1.1] — 2026-07-28

### 变更
- 五层降级策略从 SKILL.md 大段文档下沉到 `atoms.py`：`load_source()` 内置自动降级，Agent 无需手动判断
- SKILL.md 降级策略文档精简为一行 Pitfalls 条目

---

## [v2.1.0] — 2026-07-28

### 新增
- **URL 五层降级策略**：
  - L1: HTTPS (curl + 浏览器 UA)
  - L2: HTTP 降级
  - L3: 浏览器 (`browser_navigate`)
  - L4: 搜索引擎 (`web_search`)
  - L5: 替代源（`gov.cn` 转载）
- `_fetch_url_fallback()` 在 `atoms.py` 中实现（后移至 `rebuild_policy_html.py`）
- sasac.gov.cn L2 HTTP 降级可用，miit.gov.cn 加 UA 后 L1 可用

### 修复
- sasac.gov.cn 从"不可达"更正为"HTTPS 不可达但 HTTP 可达"
- `verify_verbatim` 死函数删除

---

## [v2.0.2] — 2026-07-28

### 修复
- **Wiki Changelog 同步断裂**：自 v1.9.8 起 Wiki 从未成功推送（远程有手动编辑导致 `git push` 被拒）。补全 v1.9.8 至 v2.0.2 缺失条目，此后发版前执行 `git pull --rebase` + push 后 `curl` 验证

---

## [v2.0.1] — 2026-07-28

### 修复
- 国家数据局域名从错误的 `ndrc.gov.cn` 修正为 `nda.gov.cn`
- 政策专栏 URL 路径补充 `zcfb` 段：`/sjj/zwgk/zcfb/list/`

---

## [v2.0.0] — 2026-07-28

### 新增
- **系统空间 / 用户空间双层架构**：更新不覆盖用户数据
- `scripts/init.py` 幂等初始化脚本
- `scripts/chain_runner.py` 编排层（4 条预设执行链）
- `scripts/atoms.py` 18 个原子操作函数
- `scripts/rebuild_policy_html.py` HTML 输出生成器
- `scripts/path_utils.py` 跨平台路径解析
- 7 个信源缓存 JSON（gov / miit / nda / sasac / nea / ndrc / cac）
- 逐字引用验证标签（`verify_verbatim` + build_html 输出标签）
- GitHub Release + Wiki 同步的 6 步发版流程
