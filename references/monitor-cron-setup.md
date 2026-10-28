# 每日监控 cron 的建立与验收

新机/新 profile 里重建「政策监控·每日 12:00」时照本文件走。cron 会话没有历史上下文、不能提问，所以提示词必须自带全部约束。

## 建之前先把环境备齐

1. 工人脚本在 `$HERMES_HOME/scripts/`（`policy_daily_pipeline.py`、`policy_theme_gate.py`、`release_skill.py` 等），不在分发包里。
2. `<scratch>` 目录存在：`$HERMES_HOME/data/policy-search-china/scratch/`（不存在就先建；禁用 `/tmp`）。
3. **发版源必须是 git 仓库且有 remote** —— `git -C <skill目录> describe --tags` 能出 tag；`.git` 丢了先按 SKILL.md「唯一工作区铁律」里的迁移恢复流程重挂。
4. GitHub token 先验：`curl -o /dev/null -w '%{http_code}' -H "Authorization: token $TOKEN" https://api.github.com/user` 必须 200，否则发版当天必挂。
5. 装 `chinesecalendar`（系统 python）：否则工作日闸门只会跳周末，法定节假日照跑、调休日不补。

## 任务形态

| 字段 | 值 | 理由 |
|---|---|---|
| schedule | `0 12 * * 1-5` | 工作日中午；周末靠下一工作日的 10 天窗口补扫 |
| script（前置） | `policy_workday_check.py` | 输出 `RUN <日期> 工作日` / `SKIP`；stdout 会注入提示词 |
| enabled_toolsets | terminal / file / web / skills | web 给困难源兜底 |
| no_agent | **否** | 需要 Commander 做主题审核与剔除清单 |

## 提示词必须包含的硬约束（缺一条就会在无人值守时出错）

- **首步看前置输出**：含 `SKIP` 直接回 `[SILENT]`，不许继续跑。
- **审核先于入库**：入库必须带 `--require-skip`，剔除清单必须先写。
- **剔除清单格式**：`[{"title": ..., "reason": ...}]` 数组（对象 map 会被静默忽略）。
- **主题口径**：程序/事务类与名单/公示/遴选/申报类剔除；中央/国务院与网信系统核心文件不受 10 天窗口（补录要在日报注明）。
- **date 口径**：成文/签发日优先 → 页面发布日（记 `published_date`）→ 取不到写 `scratch/pending_dates.json` 交用户，**禁止默认入库日**。
- **无新政不发版**；发版用 `release_skill.py --bump patch --notes <文件>`（notes 先写文件）。
- **跑 python 一律清环境**：`env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3 <脚本>`，PATH 里的 `python3` 是别的解释器。
- **报告**：有入库就逐条列（日期/标题/文号），无入库只写一行“今日无新政入库”+扫描量；平实语言、不写排查经过。

## 验收（首次一定要手工跑一次）

触发后用 `cronjob action=run` 跑一轮，然后**独立核**，不要只看任务自己的汇报：

1. 库内条目数 = 旧值 + 本次入库数，且用户/系统两个空间一致；
2. 被点名剔除的标题在 `cache/*.json` 里 `grep` 不到；
3. `git log --oneline -1` / `git tag | sort -V | tail -1` / 工作树干净；
4. `GET /releases/tags/<新版本>` 返回 200，正文是标准「Added 新增政策入库 N 条」；
5. 历史 Release 本来就不挂 zip 资产，本地 `~/.hermes/output/*.zip` 存在即可，别把“assets 为空”当成发版失败。

## 无人值守发版的凭据

cron 里没人输密码，`git push` 需要凭据。`credential.helper=store` 会把 token **明文**写进 `~/.git-credentials`——能用，但那是 classic PAT（`repo` 全权限），一旦主机再被突破就等于交出全部仓库。优先换成**只对单个仓库有写权限的 Deploy Key**，并在汇报里主动说明当前凭据强度。
