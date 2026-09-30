# RepoStew

执行者直接读取和修改 Markdown，不经过自定义脚本或任务协议。

四个名单位于 D:/repo/repostew/state：

1. 待做新库 new-repositories.md：近期 issue 处理，再做代码审计；真正完成后移除。
2. 关注旧库 followed-repositories.md：标题下放子列表，允许重合；从上次扫描时间接续新 issue，不重复全审计。
3. 未完成事项 unfinished.md：只放公开链接和一句原因，解决后移除。
4. 旧库全表 old-repositories.md：从完整历史 state 恢复，不是关注子集；逐库保留有证据的上次巡检时间、范围和覆盖边界，缺失标未知。

GitHub 通知和关注库扫描位置放在 read-positions.md；邮箱位置放在私密目录
private/mail-position.md。保留精确时间、原生 ID、修订值和边界 ID。
评论、review、CI 和正文实时读取，不复制为状态库。

把仓库名直接加到对应标题下即可扩展子列表：

```md
## agent
- bytedance/deer-flow

## bytedance
- bytedance/deer-flow
```

扫描合并去重；移除一个子列表的成员不影响其他列表。
整个关注名单抓取成功、事项已处理或保留后，才推进全局扫描时间；部分失败不推进。
关注不代表维护权限。通知/邮箱和开放工程巡检保持已有独立定时任务，不新增调度层。
当前关注名单排除 dajiaohuang/* 和 SagaSmithAI/*，不删除历史旧库全表，也不影响通知或已提交工程巡检。
按用户要求重分类时，自建 issue 或提交 PR 才算贡献；评论不算。改名核对原生 ID，不可访问不算零提交。
编辑前重读对应段落，定点修改并保留其他内容；未完成事项按原生链接去重。
若请求备份发布，只同步审阅后的四个名单和公开读取位置到私有状态仓库；
邮箱位置、私密事项、恢复归档及凭据不上传。state 和 skill 分别提交，不强推。

执行细节见 [工作流程](references/workflows.md)，提交边界见 [安全规则](references/safety.md)。
仅在明确请求并行时由协调者带独立仓库 leaf；协调者单独写共享 state，完成即补位，并核实安全释放本次干净工作树。
旧代码、JSON 和测试留在工作区恢复归档，不参与运行。
