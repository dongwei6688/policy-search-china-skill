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

## 7. README 安装说明偏好

- 小白视角：去平台名噪音、加 Node.js 前置条件、加装完后的下一步指引
- 手动安装折叠一行"高级用户"
- 安装命令用完整 URL 格式：`npx skills add https://github.com/... --skill name`

## 8. 架构速查

- policy-search-china skill 已发布至 GitHub dongwei6688/policy-search-china-skill，含 wiki（首页/使用指南/架构说明/更新日志）
- 架构：系统空间+用户空间分层叠加，更新不覆盖用户数据
- 初始化脚本 scripts/init.py 幂等
- rebuild_policy_html.py 支持 --topic/--all
- 自我进化：缓存随使用增长
