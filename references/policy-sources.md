# 信源体系 — 政策搜索覆盖范围与来源识别

本文档记录了 policy-search-china skill 覆盖的权威政策发布渠道、综合政策文件库，以及信源归属判断规则。

## 权威政策发布渠道（16 个部委/机构）

| 部门 | 主域名 | 协议 | 缓存文件 |
|:-----|:-------|:-----|:---------|
| 国务院 | `gov.cn` | HTTPS | `gov.json` |
| 工信部 | `miit.gov.cn` | HTTPS | `miit.json` |
| 国家数据局 | `nda.gov.cn` | HTTPS | `nda.json` |
| 国资委 | `sasac.gov.cn` | HTTP | `sasac.json` |
| 国家能源局 | `nea.gov.cn` | HTTPS | `nea.json` |
| 发改委 | `ndrc.gov.cn` | HTTPS | `ndrc.json` |
| 网信办 | `cac.gov.cn` | HTTPS | `cac.json` |
| 科技部 | `most.gov.cn` | HTTPS | `most.json` |
| 财政部 | `mof.gov.cn` | HTTPS | `mof.json` |
| 交通运输部 | `mot.gov.cn` | HTTPS | `mot.json` |
| 生态环境部 | `mee.gov.cn` | HTTPS | `mee.json` |
| 农业农村部 | `moa.gov.cn` | HTTPS | `moa.json` |
| 教育部 | `moe.gov.cn` | HTTPS | `moe.json` |
| 文旅部 | `mct.gov.cn` | HTTPS | `mct.json` |
| 水利部 | `mwr.gov.cn` | HTTP | `mwr.json` |
| 人社部 | `mohrss.gov.cn` | HTTP | `mohrss.json` |
| 住建部 | `mohurd.gov.cn` | ❌ 不可达 | 托底 |
| 卫健委 | `nhc.gov.cn` | ❌ 412 | 托底 |
| 自然资源部 | `mnr.gov.cn` | ❌ 不可达 | 托底 |

> **托底说明：** 住建部、卫健委、自然资源部官网不可达，其政策通过**中央政策文件库**（`sousuo.www.gov.cn`）托底搜索。

## 中央政策文件库

- **URL**: `https://sousuo.www.gov.cn/zcwjk/policyDocumentLibrary`
- **用途**: 国务院政策文件库统一搜索入口，覆盖全部部委公开发文
- **策略**: 搜索结果按 `source_url` 域名归属到对应部委缓存文件

## 信源归属判断规则

### URL 域名优先级匹配（从上到下，命中即止）

| 优先级 | 判断依据 | 写入 |
|:------|:---------|:-----|
| 1 | `source_url` 包含 `nea.gov.cn` | `nea.json` |
| 2 | `source_url` 包含 `nda.gov.cn` | `nda.json` |
| 3 | `source_url` 包含 `miit.gov.cn` | `miit.json` |
| 4 | `source_url` 包含 `sasac.gov.cn` | `sasac.json` |
| 5 | `source_url` 包含 `cac.gov.cn` | `cac.json` |
| 6 | `source_url` 包含 `ndrc.gov.cn` | `ndrc.json` |
| 7 | `source_url` 包含 `most.gov.cn` | `most.json` |
| 8 | `source_url` 包含 `mof.gov.cn` | `mof.json` |
| 9 | `source_url` 包含 `mot.gov.cn` | `mot.json` |
| 10 | `source_url` 包含 `mee.gov.cn` | `mee.json` |
| 11 | `source_url` 包含 `moa.gov.cn` | `moa.json` |
| 12 | `source_url` 包含 `moe.gov.cn` | `moe.json` |
| 13 | `source_url` 包含 `mct.gov.cn` | `mct.json` |
| 14 | `source_url` 包含 `mwr.gov.cn` | `mwr.json` |
| 15 | `source_url` 包含 `mohrss.gov.cn` | `mohrss.json` |
| 16 | `source_url` 包含 `gov.cn` | `gov.json` |

### doc_number 文号前缀兜底

| 文号前缀 | 归属 |
|:---------|:-----|
| `国能发` | `nea.json` |
| `国数`、`国家数据局` | `nda.json` |
| `工信部` | `miit.json` |
| `发改` | `ndrc.json` |
| `国资`、`国资委` | `sasac.json` |
| `国科发`、`科技部` | `most.json` |
| `财` | `mof.json` |
| `交` | `mot.json` |
| `环`、`生态环境部` | `mee.json` |
| `农` | `moa.json` |
| `教` | `moe.json` |
| `文旅` | `mct.json` |
| `水`、`水利部` | `mwr.json` |
| `人社` | `mohrss.json` |
| `国办发`、`国发`、`国函` | `gov.json` |
| 其他/无法判断 | `gov.json`（兜底） |

### 写入步骤

1. 按规则确定目标缓存文件
2. 读取现有内容（不存在则创建空数组）
3. 检查文号是否重复
4. 追加新记录
5. 按 `date` 字段升序排序
6. 写入**用户空间**缓存（不修改系统空间）
