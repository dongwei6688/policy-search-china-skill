# 信源体系 — 政策搜索覆盖范围与来源识别

本文档记录了 policy-search-china skill 覆盖的权威政策发布渠道、综合政策文件库，以及信源归属判断规则。当搜索或缓存写入需要确定一篇政策的官方来源时，依据本文档的表进行 URL 域名匹配和文号前缀兜底，确保每条政策原文准确归入对应信源文件。

## 权威政策发布渠道

以下 7 个部委/机构是政策搜索的核心信源，每个信源对应独立的缓存文件（`{信源}.json`）：

| 部门 | 主域名 | 政策专栏路径 | site: 搜索前缀 |
|------|--------|-------------|---------------|
| 国务院 | `gov.cn` | `www.gov.cn/zhengce/` | `site:gov.cn 政策` |
| 工信部 | `miit.gov.cn` | `www.miit.gov.cn/zwgk/zcwj/` | `site:miit.gov.cn` |
| 国家数据局 | `www.nda.gov.cn` | `www.nda.gov.cn/sjj/zwgk/list/` | `site:nda.gov.cn` |
| 国资委 | `sasac.gov.cn` | `www.sasac.gov.cn/n2588035/` | `site:sasac.gov.cn` |
| 国家能源局 | `nea.gov.cn` | `www.nea.gov.cn/policy/zxwj.htm` | `site:nea.gov.cn` |
| 发改委 | `ndrc.gov.cn` | `www.ndrc.gov.cn/xxgk/zcfb/` | `site:ndrc.gov.cn 政策` |
| 网信办 | `cac.gov.cn` | `www.cac.gov.cn/wxzw/zcfg/A093703index_1.htm` | `site:cac.gov.cn` |

### 高速缓存文件映射

| 缓存文件 | 覆盖范围 |
|---------|---------|
| `gov.json` | 国务院、中国政府网（`gov.cn`） |
| `miit.json` | 工信部（`miit.gov.cn`） |
| `nda.json` | 国家数据局（`www.nda.gov.cn`） |
| `sasac.json` | 国资委（`sasac.gov.cn`） |
| `nea.json` | 国家能源局（`nea.gov.cn`） |
| `ndrc.json` | 发改委（`ndrc.gov.cn`） |
| `cac.json` | 网信办（`cac.gov.cn`） |

## 综合政策文件库（补充信源）

当政策在对应部委官网未找到时，从以下综合平台检索原文：

| 平台 | 用途 | site: 语法 |
|------|------|-----------|
| 中国政府网政策文件库 | 国务院全部公开发文的统一入口 | `site:gov.cn/zhengce/zhengceku/` |
| 北大法宝/北大法意 | 法律/行政法规数据库（公开版） | `site:pkulaw.com` |
| 国研网 | 政策研究与解读 | `site:drcnet.com.cn` |

## 信源归属判断规则

政策原文提取完成后，按以下优先级依次匹配 `source_url` 域名，确定该政策写入哪个缓存文件。URL 匹配全部失败时，通过 `doc_number` 前缀兜底。

### URL 域名优先级匹配

| 优先级 | 判断依据 | 命中则写入 |
|-------|---------|-----------|
| 1 | `source_url` 包含 `nea.gov.cn` | → `nea.json` |
| 2 | `source_url` 包含 `nda.gov.cn` | → `nda.json` |
| 3 | `source_url` 包含 `miit.gov.cn` | → `miit.json` |
| 4 | `source_url` 包含 `sasac.gov.cn` | → `sasac.json` |
| 5 | `source_url` 包含 `cac.gov.cn` | → `cac.json` |
| 6 | `source_url` 包含 `ndrc.gov.cn` | → `ndrc.json` |
| 7 | `source_url` 包含 `gov.cn` | → `gov.json` |

### doc_number 前缀兜底

当 URL 域名匹配全部失败时，按文号前缀判断归属：

| 文号前缀 | 归属信源（缓存文件） |
|---------|-------------------|
| `国能发` | → `nea.json` |
| `国数`、`国家数据局` | → `nda.json` |
| `工信部` | → `miit.json` |
| `发改` | → `ndrc.json` |
| `国资`、`国资委` | → `sasac.json` |
| `国办发`、`国发`、`国函` | → `gov.json` |
| 其他/无法判断 | → `gov.json`（兜底） |

### 写入步骤

1. 按上述规则确定目标缓存文件名
2. 读取现有缓存文件内容（不存在则创建空数组）
3. 检查该文号是否已在缓存中（避免重复）
4. 追加新记录
5. 按 `date` 字段重新排序（升序）
6. 写入用户空间对应信源的缓存文件

> **注意：** 写入操作仅作用于用户空间（`~/.hermes/data/policy-search-china/cache/`），不修改系统空间（`{skill_dir}/cache/`），确保 skill 更新时用户数据不被覆盖。
