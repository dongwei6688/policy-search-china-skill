## v2.3.0 (2026-07-28)

### Added
- Stage 1 并行：多关键词搜索使用 ThreadPoolExecutor 多线程
- Stage 3 并行：extract_all_paragraphs() 多线程提取 + 收集聚合
- merge_search_results() 合并缓存+Web搜索结果

### Changed
- SKILL.md 精简至 ~110 行：删除 Pipeline Planning 详细逻辑，只保留步骤描述
- 详细实现逻辑下沉到 chain_runner.py 和 rebuild_policy_html.py

### Fixed
- deduplicate_entries 从 Stage 4 移到 Stage 2 末尾（节省 Stage 3 文件 I/O）
- Stage 4 验证逻辑不再独立为一个 Stage（逐字验证已嵌入 build_html 输出标签）

## v2.2.0 (2026-07-28)

### Changed
- **职责边界重构**：atoms.py 只保留纯数据操作，文件I/O+URL降级全部归 rebuild_policy_html.py
- 删除 atoms.py 中重复的 load_source()/extract_paragraphs()/fetch_url_with_fallback()
- search_cache_fulltext() 移至 rebuild_policy_html.py（依赖文件I/O）
- chain_runner.py trace链改用 rebuild_load_source()，不再手动读文件

### Fixed
- 修复 trace 链中 re/clean 变量引用错误
- 消除 atoms.py 与 rebuild 间的功能分叉（atoms弱版 vs rebuild完整版）

## v2.1.1 (2026-07-28)

### Changed
- 五层降级策略从 SKILL.md 下沉到 atoms.py：load_source() 内置自动降级，Agent 无需手动判断
- SKILL.md 降级策略大段文档精简为一行 Pitfalls 条目

## v2.1.0 (2026-07-28)

### Added
- URL 五层降级策略：L1 HTTPS → L2 HTTP降级 → L3 浏览器 → L4 搜索引擎 → L5 替代源
- atoms.py 新增 fetch_url_with_fallback() 函数，L1-L2 自动降级
- Source Coverage 增加各信源实测结果（L1/L2/L3 标注）

### Fixed
- sasac.gov.cn 原来误判为「不可达」，实际是 HTTPS 不通但 HTTP 可通
- miit.gov.cn curl 403 → 加浏览器 UA 后直通

## v2.0.2 (2026-07-28)

### Fixed
- 回滚 v2.0.1 的错误：sasac.gov.cn 和 pkulaw.com 是真实网站，服务器不可达是网络限制而非网站问题
- 恢复北大法宝到 policy-sources.md
- 国资委描述改为"时效性较差"而非"不可达"

## v2.0.1 (2026-07-28)

### Fixed
- 国家数据局政策专栏路径：sjj/zwgk/list → sjj/zwgk/zcfb/list
- 移除北大法宝（pkulaw.com 不可达）
- 国资委标注：sasac.gov.cn 服务器不可达
- Source Coverage 新增「政策专栏」列，区分 site: 搜索前缀与直访路径

## v2.0.0 (2026-07-28)

### Added
- **18 原子操作库** `scripts/atoms.py`：5 阶段标准化（环境准备/搜索/过滤/提取/验证/输出），每个函数只做一件事
- **执行链编排器** `scripts/chain_runner.py`：4 条预设链（broad/cross/locate/trace），命令行为 `--chain` 路由
- **AND 交集模式**：`rebuild_policy_html.py --mode and` 多关键词同时命中

### Changed
- **SKILL.md 全面重构**：Decision Guide 改为意图路由表，Core Workflow 改为 5 阶段 18 原子操作
- 搜索逻辑从单体脚本拆分为可组合的原子函数，每次新增意图只需编排新链

### Fixed
- trace 链：添加 GBK 编码回退处理非 UTF-8 文件

## v1.9.10 (2026-07-28)
## v1.9.10 (2026-07-28)

### Added
- Pitfalls 节改名「Pitfalls  Hard Constraints」，增加绝对禁止规则：禁止手工编写 HTML 报告，所有 HTML 最终交付必须通过 rebuild_policy_html.py 生成

## v1.9.9 (2026-07-28)

### Changed
- YAML 精简至 3 字段（name+description+license），对齐 anthropics 标准
- 标题改为纯英文 `# Policy Search China`
- 新增 `## Overview` 概览节

# 更新日志

## v1.9.8 (2026-07-28)

### Fixed
- **SKILL.md Core Workflow 代码修复**：4 处问题
  - 新增统一 import 块（`Path`, `json`, `re`, `glob`），代码可直接执行
  - Phase 0 空缓存不抛 ValueError（`max()` → 显式循环）
  - Phase 0/2 文件句柄泄漏修复（`open()` → `with`/`read_text()`）
  - Phase 2 hits 空守卫（`if not hits: return`，防 IndexError）
- **ndrc.json 数据修复**：3 条格式标签修正（`format: pdf` → `html`，实际为 .txt 纯文本文件）

## v1.9.7 (2026-07-28)

### Changed
- 每位 Phase 加可执行代码示例（Python 缓存扫描、段落提取、HTML 高亮输出）
- Two-Stage Principle 改为具体搜索计划示例
- 去除 Overview 冗余描述，合并到 H1 摘要
- 去除 Phase 描述的 reference 文件依赖（Agent 读完主文件可直接执行）

## v1.9.6 (2026-07-28)

### Changed
- 移除 SKILL.md 中 mermaid 流程图（Agent 不渲染），保留文字说明
- 精简 Setup 节双空间架构描述，详细信息收敛到 reference 文件

## v1.9.5 (2026-07-28)

### Changed
- 重构 SKILL.md：按 anthropics 官方规范精简至 124 行（此前 726 行），新增 Decision Guide 决策表
- 新增 references/ 目录，拆分出 3 个 reference 文件：policy-sources.md、search-strategies.md、output-format.md

## v1.9.4 (2026-07-28)

### Fixed

- **data_elements_scenarios_guide.pdf OCR 文本提取**：457 页扫描件完成 OCR，配套 .txt 文件可用，补齐此前缺失的 PDF 全文搜索能力

## v1.9.3 (2026-07-28)

### Added

- **pre-push hook 变更类型自动检测**：扫描本次 push 的文件变更，按发版判断矩阵自动判定是否需要发版，杜绝"该发没发"或"不该发卡住"的概率问题
- pre-push 检查项 0：变更类型自动归类，纯文档变更跳过版本检查直接放行
- SKILL.md：补充推前检查钩子文档（特性说明 + 分类规则表）

### Changed

- pre-push 检查项编号重排：版本检查移至 3-5 号（仅需发版时执行），通用检查为 1-2 号

## v1.9.2 (2026-07-28)

### Fixed

- **条目归属清理**：nda.json 中移除发改数据〔2024〕660号（按文号单位原则，发改类归 ndrc.json），仅保留国数文号条目
  - nda.json: 5 条 → 4 条，与 cache/nda/ 目录文件数一致

## v1.9.1 (2026-07-28)

### Changed

- **缓存文件命名规范化**：统一为英文描述性命名，废除中文文号命名
  - nda/: `国数综科基2025-114号.txt` → `data_infrastructure_scenarios.html`
  - nda/: `国数综政策2025-106号.pdf` → `data_elements_scenarios_guide.pdf`
  - nda/: `国数综政策2026-35号.txt` → `data_property_rights_guide.html`
  - nda/: `industry_high_quality_dataset.html`（新增，补全国数科基〔2026〕25号全文）
  - ndrc/: `发改数据2025-1154号.txt` → `digital_economy_enterprises.txt`
  - ndrc/: `发改能源2026-622号.txt` → `non_fossil_energy_guide.txt`
- **format 字段清理**：确保 format 与实际文件后缀一致（html → .html/.htm，pdf → .pdf/.txt）

## v1.9.0 (2026-07-28)

### Added

- **新政策入库**：3 条重点政策（含 2 条全文 + 1 条 PDF 缓存）
  - 《关于加强数字经济创新型企业培育的若干措施》（发改数据〔2025〕1154号），六部门联合发文
  - 《关于在国家数据基础设施建设先行先试中加强场景应用的实施方案》（国数综科基〔2025〕114号），国家数据局综合司
  - 《工业制造、现代农业等九个领域"数据要素×"典型场景指引》（国数综政策〔2025〕106号），国家数据局综合司
- **新缓存条目**：nda.json 新增 2 条，ndrc.json 新增 1 条

## v1.8.0 (2026-07-28)

### Added

- **新政策入库**：《非化石能源电力消费核算指南（试行）》（发改能源〔2026〕622号），发改委/能源局/生态环境部/统计局/数据局五部门联合发文，含全文txt缓存
- **新缓存条目**：ndrc.json 新增 1 条能源核算政策

## v1.7.0 (2026-07-28)

### Added

- **新政策入库**：《关于推进行业高质量数据集建设行动的实施方案》（国数科基〔2026〕25号），国家数据局，含六大专项行动、20条措施
- **新缓存条目**：nda.json 新增 1 条行业数据集政策

## v1.6.0 (2026-07-28)

### Added

- **新政策入库**：《数据产权登记工作指引（试行）》（国数综政策〔2026〕35号），国家数据局综合司，全文缓存
- **新缓存条目**：nda.json 新增 1 条数据产权政策

### Changed

- 国家数据局域名统一为 `www.nda.gov.cn`

### Fixed

- SKILL.md 中多处 nda.gov.cn 缺 www 前缀

## v1.5.1 (2026-07-28)

### Added

- **冲突处理原则**：用户空间属于用户，同文号不一致时输出对比报告+推荐理由，等待用户决定后再操作

### Changed

- 搜索逻辑从"用户空间优先"改为"同文号实时一致性对比"

### Removed

- 清理 SKILL.md 中无意义的时间戳标注

## v1.5.0 (2026-07-27)

### Added

- **跨平台重构**：不再硬编码 `~/.hermes/` 路径，支持 Hermes / OpenClaw / Workbuddy / Claude Code 等任意 Agent
- **开源发布**：MIT 协议，GitHub 公开发布
- **预装缓存**：约 50 条全文缓存（7 个信源）

## v1.4.0 (2026-07-22)

### Added

- **分层架构**：系统空间 + 用户空间，更新不覆盖用户数据
- **初始化脚本**：`scripts/init.py`，幂等创建目录
- **脚本重构**：`rebuild_policy_html.py` 改为 `--topic` / `--all` 模式

### Changed

- 全脚本增加中文分区注释
- 输出路径改为 `~/` 相对路径

### Fixed

- 信源 URL 修正（网信办、能源局、数据局）

## v1.3.0 (2026-07-22)

### Added

- HTML 输出逐字验证机制
- 关键词高亮标记
- 6 个 Phase 工作流定义

## v1.2.0 (2026-07-21)

### Added

- PDF 政策处理（pdftotext 提取）
- 缓存搜索优化（动态 glob）

## v1.1.0 (2026-07-20)

### Added

- 6 个信源完整覆盖
- HTML 输出结构化（统计、目录、正文）
- 双段式工作流（大模型 API 规划 → 本地工具验证）

## v1.0.0 (2026-07-19)

### Added

- 初始版本
- 基础搜索 + 缓存机制
- 5 个搜索主题预置
