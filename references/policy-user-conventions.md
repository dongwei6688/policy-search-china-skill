# 用户政策约定（董伟，2026-08-29 从 USER.md 迁移落位）

> 本文件是 policy-search-china 项目（董伟）的用户级约定全集。
> USER.md 只留指针；本文件是权威源。执行政策相关任务前先读本文件。

## 1. 政策引用需求范围

- 七大部委：国务院 / 工信部 / 数据局 / 国资委 / 能源局 / 发改委 / 网信办
- 领域覆盖：数字化 / 数据要素 / AI+ / 智能制造 / 信创 / 绿色低碳
- 国家数据局域名：**nda.gov.cn**（非 ndrc）

## 2. 政策偏好（硬性）

1. 原文必须 gov.cn/zhengce/zhengceku/ 格式
2. local_path 字段必填
3. summary 字段（非 full_text）
4. format 字段（html/pdf/link）
5. PDF 配套 .txt 用于搜索
6. HTML 输出逐字引用 + 关键词高亮 + 验证标签
7. 元信息从缓存 JSON 读取，不硬编码
8. 不得虚构政策内容

## 3. Policy summary 写作规则（强制，不可违反）

NEVER fabricate or extrapolate content. Every claim in summary must be
verifiable by searching for key phrases in the source document. If a phrase
("智能矿山", "到2027年", etc.) doesn't appear in the source, do not include
it. When writing summaries for policies where only notification page is
available (gov.cn department files), mark as '[通知页]' explicitly.

## 4. HTML 输出铁律（Strong preference）

HTML output must contain 100% verbatim quotes from source documents — every
paragraph must be searchable in the original source. No rewrites, no
summaries, no "sounds-like-policy" fabrication. Use `<span class="hl">keyword</span>`
for highlighting (presentation only, content unchanged). Each document
section must have a `<div class="verification">✅ N段·逐字引用</div>` badge.

## 5. 双空间架构与冲突规则

- 系统空间（skills/research/ 只读 = 权威发版源）+ 用户空间（data/ 读写，永不覆盖）
- **冲突时系统空间优先**（同 doc_number 维护版本更完整）
- 监控功能（政策源检测）是开发者工具，不随 skill 分发，用户只需 git pull

## 6. 发版与 Changelog 规则

- **Changelog 补漏两分法**：数据已发版 → 无须再发；数据修正 → 必须发版
- 核心原则：cache/ 变了就必须发版——用户通过 ZIP/Release 获取技能包，git push 用户拿不到
- **开源 CHANGELOG 只保留用户可见变更**（功能新增、数据修复、架构改动），删除内部开发工具/流程内容（audit_cache.py/repair_cache.py 等运维脚本、Wiki 同步修复、发版流程描述）；GitHub Release 描述同步清理
- **发版时机（2026-09-14 补）**：cache/ 索引发生任何变更（含清理/删除类改动）必须**当日**发版，否则次日日常发版会将其静默并入 commit，CHANGELOG 无法追溯——与"无新政不发"互补、不冲突
- **分发 ZIP 打包（09-14 修复）**：必须用 `git archive` 生成（分发内容 == 仓库内容）并做非分发内容校验；**禁用 `zip -r .`** —— 实测会把本地草稿与 `cache/_backup_*/` 清理备份目录打进分发包；`.gitignore` 已加 `cache/_backup_*/`、`cache/_removed_*/`
- **缓存文件写入纪律（09-16 补）**：①手动写回 cache JSON 必须用 `indent=1`（与 pipeline 及各信源文件一致；用 `indent=2` 会整文件重排，产生千行级 diff 噪声，且下次 pipeline 写入会再次重排）②改完两空间必须同步，用 md5 校验 system/user 同名文件一致 ③临时备份放**仓库外**——`cache/gov.json.bak-*` 这类命名不匹配 `.gitignore` 的 `cache/_backup_*` 规则，会被发版的 `git add` 卷进提交；三条做完后按发版时机规则当日发版
- **wiki 验证误报**：`release_skill.py` 报 "⚠️ Wiki 验证未找到 vX.Y.Z" 属误报（它 curl 的是 GitHub 缓存页面）。正确验证 = clone wiki 仓库查 `Changelog.md` 头部版本 + `Home.md` 计数，再核远端 tag/release 是否存在

## 7. README 安装说明偏好

- 小白视角：去平台名噪音、加 Node.js 前置条件、加装完后的下一步指引
- 手动安装折叠一行"高级用户"
- 安装命令用完整 URL 格式：`npx skills add https://github.com/... --skill name`

## 9. 入库主题边界与剔除口径（2026-09-14 董伟拍板）

- **研究主题**：产业数字化 / 智能化（数智化转型）+ 科学技术创新。**非本领域专业事务不入库**。
- **"系列一致性"不得作为保留理由**（09-14 裁定）：某系列文件此前后每日重复入库，正是以"其他同类都在库里"为由保留所致。剔除口径以单条文件主题判定，不看同系列存量
- **农业口处置**：农业农村部"公告 第N号"系列（兽药/农药/品种注册登记类）及事务性文书（征集/认定/公示/遴选类）属主题外 → 剔除并清理存量。判定以**主发单位**为准（"农业农村部"须位于标题开头）——工信部等牵头的联合发文（如"农业领域机器人典型应用场景遴选通知"）仍保留。
- **仍属主题内、须保留的农业文件**：智慧农业指导意见、全国智慧农业行动计划、农业领域机器人典型应用场景、数据要素×现代农业、"人工智能+"农产品流通（产地市场体系规划）。
- **机制强度分层**（新增主题外规则时按此改）：
  1. 发现脚本 `policy_monitor.py` 的 `OFF_THEME_PATTERNS`（**确定性**：命中即不进候选，输出记录在候选 JSON 的 `auto_skipped`）
  2. cron prompt 剔除口径（**半强制**：LLM 逐条判断）
  3. 本条约定（**靠自觉**）——只改 ③ 等于没改。
- **存量清理记录（2026-09-14，随 v2.47.3 发版）**：8 条 × 双空间 = 16 个条目/文件移除，原件备份在用户数据目录的 `removed-backup-20260914/`，原文仍存于 git 历史。索引计数 210 → 202。
  - 中华人民共和国农业农村部公告 第1048 / 1056 / 1057 / 1059 / 1061 / 1062 号
  - 农业农村部办公厅关于异噁唑虫酰胺等化学物质特定用途管理认定的通知
  - 农业农村部办公厅关于征集2026年新型农业经营主体提质增效带动小农户增收经验做法的通知

## 10. 架构速查（原第 8 节顺延）

- policy-search-china skill 已发布至 GitHub dongwei6688/policy-search-china-skill，含 wiki（首页/使用指南/架构说明/更新日志）
- 架构：系统空间+用户空间分层叠加，更新不覆盖用户数据
- 初始化脚本 scripts/init.py 幂等
- rebuild_policy_html.py 支持 --topic/--all
- 自我进化：缓存随使用增长
