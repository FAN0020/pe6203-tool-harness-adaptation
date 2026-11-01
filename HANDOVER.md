# PE6203 交付交接 · 2026-10-31

## Git 大文件修复 · 2026-11-01

`weather-provenance-pilot-20261101/source-4e54a66.tar` 原始快照为 114.5 MiB，无法推送 GitHub。原文件保留本机并由 `.gitignore` 排除；仓库改用无损 `.tar.gz`（36.3 MiB）。原 source-manifest 的 tar 哈希和逐文件哈希不变，离线复算脚本支持两种封装，历史评分/轨迹/结论均未改。

仅重写该文件引入后的 7 个未发布提交；已发布基点 `554e7b42` 及其祖先不变。映射与包装哈希见 `results/evidence/weather-provenance-pilot-20261101/source-packaging.json`。原始文件及未发布提交 bundle 保存在仓库外 `../pe6203-history-backups/20261101-size-fix-aad5a59/`。继续研究时以当前 HEAD 为准，勿恢复旧提交而重新引入大文件。

## 新聊天接手入口：新版研究目标（2026-10-31）

**先读本节即可；其后是按时间保留的历史记录。** 用户最新明确选择：**仍须找到可复现的完成率与任务质量双重改善策略，负结果不能作为研究目标完成条件。** 取消总费用/总轨迹额度的授权仍有效；这不取消公平的单次执行预算，也不授权部署、发送 TA 消息或推送当前研究分支。不要用历史段落中的旧等待批准/旧 US$1 限额覆盖最新指示。

### 新版 Goal 文本

> 基于 PE6203 Group Project 4 brief 与 MCPEvol-Bench，设计并验证至少一种符合选择性工具知识适应范围的策略，使它在预先冻结的变化任务验证子集上，相比原 Selective Patch，取得可复现的正常完成率和任务质量双重改善，同时保持不变任务能力。No Update 与 Full Rewrite 保留为课程比较基线。任务质量同时检查 TF 和任务要求的实际产物正确性，不能以 PE 上升、提前结束、删减任务要求或选择性展示成功代替质量改善。
>
> 复用已有有效证据；每轮先定位具体机制、冻结知识差异和验收检查，再实施和验证。固定模型、供应商、解码、单次预算和评分协议；开发与独立复核分开。保存所有正负结果、原评分、轨迹和费用，报告 TF/PE/ECS、恢复、保持、完成状态及更新成本，不合成任意加权分数。失败候选可以淘汰，但未验证双重改善时，整个研究目标保持未完成。
>
> 不设总费用或总轨迹硬上限；按证据推进，不自动展开全笛卡尔矩阵，不对同一失败方案重复抽样直到赢。完成条件是：改善经独立重复支持、范围与局限明确、课程要求及报告/复现包/展示材料得到核对与整理。不能承诺一定存在这样的策略；若当前方法空间没有可检验的新机制，应如实说明障碍，不伪称目标完成。

### 2026-11-01 轻量交接到新聊天

用户要求降低上下文负担，已明确授权暂停旧聊天Goal并创建新聊天独占继续。旧聊天`01a19253-fa19-74f2-89ca-eae44eeb98fb`的Goal已暂停，研究目标未完成。新聊天先读本入口、新版Goal和下面当前断点，再读[`handoff/current.json`](handoff/current.json)，之后只按需读取其引用。可复制启动词见[`handoff/new-chat-prompt.txt`](handoff/new-chat-prompt.txt)。不要fork或读取完整旧聊天，不扫描全部轨迹/报告，不读取密钥。

交接时没有正在运行的实验或renderer。研究结果基点为`ac4c328`，本次交接不改任何旧结果。交接前仅出现EasyTool/Play2Prompt/工具描述重写的搜索线索，尚未完成原文与固定源码核对，也没有新候选或新模型调用；不能当作已完成研究。新聊天创建同一完整目标的Goal后自主推进，旧聊天不再并发研究。

### 当前最新状态：真实 actor 项目经验采集完成，未满足两结构正例门槛

- 同一完整 Goal active、未完成。主线程唯一写者/实验执行者；无新 agent/worktree、push、部署或外发。本轮真实执行是实质进展，不是重复阻塞轮。
- 报告 [`reports/project-episode-learning-admission.html`](reports/project-episode-learning-admission.html)，离线复核 `python3 results/evidence/project-episode-learning-20261101/verify_training.py`。
- 有边界检查：math validate_syntax 的 description/已有参数注释在 Early/Late 对照中未变，diff 是 schema 字段；不能将其问题归因完整替换描述。Early 部分 planner 文本已错误，不支持盲目回退。保留/删除机制本身仍是可检验空间。
- AWM 2409.07429v1 / 作者 SHA8c0ff8c 的成功轨迹抽象机制，转为闭集工具/字段/匿名ID流+属性标签；禁止问题/答案/推理/原题评分轨迹。以前native-only程序和失败Slidev训练未真正实现成功actor经验诱导；本轮仍未调用updater。
- `1867db0`冻结900401/900402完整6/12记录、各2SP、全部34工具、验收及条件开发/两批验证；`adb951c`冻结精确SP知识。模型/供应商/4096单次/12轮/原评分不变。15针对性测试通过。
- runner86948退出0，4/4 evaluated，20官方评分。`091e97e`提交全部4产物判断后才揭官方评分；同协调者，非独立人工。
- 900401两次正常/core均通过；900402两次均12轮耗尽、最终答复空，正常/core均失败。**4/4保存记录、全部字段及层级/依赖均正确**。平均TF8.8/PE7.9/ECSnull，不用高分替代交付。
- 两条12record实际序列：round1项目；round2三根；round3–11按dependsOn ID链逐条创建；round12列表读取。原生错误0，最后completion224/204、reasoning56/25，均tool_calls而非length。可定位已采用路径耗尽轮次，不能证明知识干预效果；规模/深度/输入长度并未隔离。
- 两结构各至少1正常+全项正例的冻结门槛失败：关闭此采集源，不补采，不放宽；updater0，没有候选、原题开发或验证。不否定所有经验学习，6record真实成功是新证据。
- 下一具体判别：源码约束的依赖延期构造，完整字段与parent顺序保留，跨任务dependsOn待IDs齐后update。已有native direct_deferred保持字段/缩短理论依赖路径证据；需要核清只延后dependsOn的等价性、actualchanged知识host并冻结原题SP对照。不是parse_prd批量提示重写；不得把本轮失败准入池包装成AWM诱导。
- 69请求=47actor+20judge+2preflight，USD0.054594420，未知0/未结0；170raw/116source文件离线核验通过，全部原始文件与评分/费用保留。NU/FR、原题严格双提升与两独立批、最终报告/复现/展示仍未完成。

### 已结束上一轮：批量路线完整成本诊断完成，不能普遍节省预算

- 同一 Goal active、未完成；本轮为实质诊断进展。无新 agent/worktree、模型调用、push、部署或外发，无运行实验。
- 报告 [`reports/native-batch-cost-diagnostic.html`](reports/native-batch-cost-diagnostic.html)；离线命令 `python3 results/evidence/native-batch-cost-diagnostic-20261101/verify.py`。
- `68493fe` 在任何新原生调用前冻结3个独立合成结构（900301-303）、8路径、69调用。比较直接创建、先创建后补链接、原生批量导入后恢复字段；ID仅从原生收据/列表取，磁盘状态仅评测。runner65881退出0。
- 所有正文、优先级、复杂度、工时、标签、状态、层级和依赖逐字段一致。默认平铺3：direct5调用/3理论轮次，batch3/3；完整字段浅树6：direct8/4，deferred12/4，batch10/5；完整字段长链6：direct8/8，deferred13/4，batch10/5。
- 理论轮次仅是所指定算法的数据依赖下界，假定独立参数无限容纳；不是实际actor轮次，不保证4096tokens能装下，也非所有混合算法最优。Native walltime/UTF8字节不等于模型预算；请求字节含目录名差异。
- 新证据否定“fanout必然释放模型轮次”的泛化：完整字段需要逐条恢复；浅树batch调用/轮次都更差，长链有取舍。上轮候选28/29、SP37/47正文满足短ASCII域，不能主要归因全部文本不适用；每条都设置非文本字段。该投影从既有输出取得，仅回顾分析、不进updater。
- 不再优先调整同一batch提示/位置/名称。未测实际actor采用与reasoning分配，不能声称找到截断根因。原native_record_batch四单元结果不改，开发失败、两批验证仍未开始。
- 另一方向：逐字段判断旧知识是否保留。只排除无校验的整体回退：Early list_tasks的跨项目说明及旧思考工具保证不成立。不能以这些错误否定所有源证据约束的字段保留；目前无下一已冻结模型候选。
- 新模型calls/tokens/USD全0；69原生调用+8目录读取保留在独立native ledger。204归档成员含全部收据/状态/工作区/stdout/stderr和固定源码，离线复算通过；未重采。
- 合成诊断不算原benchmark成功或独立验证。NU/FR、所有正负评分费用保留；最终课程综合报告/复现/展示与完整双提升Goal继续未完成。

### 已结束上一轮：原生批量路线完成4条开发，未被采用、未双提升

- 同一完整 Goal active、未完成；本轮为真实机制试验，不是阻塞轮。主线程唯一写者/实验执行者；无新 agent/worktree、push、部署或外发。
- 报告 [`reports/native-record-batch-development.html`](reports/native-record-batch-development.html)，离线复核 `python3 results/evidence/native-batch-knowledge-20261101/verify_archive.py`。
- 定向复查上一轮3条283调用顺序：每条只分析复杂度一次，首次第10/11轮，之前主要创建与依赖写入。因此不支持“反复分析循环”；仍未隔离真正截断原因。
- 复用 EasyTool v3 / microsoft JARVIS `7624cf3` 的可调用验证参数知识机制，不改其执行器。本项目扩展：原生 parse_prd 一次写多条记录，三阶段实现相同；并非新增工具。`c577a3d` 冻结12次通用原生准入，全部预定属性成立：短段落保存、取ID补链接、坏语法fallback、长段落截断、重复非幂等。
- `8ac249b` 冻结实现/4单元开发及条件验证，`8ec44b8` 冻结知识；56针对性测试通过。仅实际变化 create_project 记录增加3条 usage_rules，保护全部其他记录/schema/runtime/actor/预算，235精确K0。无模型updater，无题目/答案/评分轨迹进入候选生成。
- runner22445退出0，4/4 evaluated，20评分槽位。全部4产物审查先于评分/方法揭盲，在 `e47c8d3` 提交；同协调者，可从行为推测方法，不称独立人工。
- 原283Late：SP/候选完成均0/1、core均0/1、TF均9；PE8.6/9.2，calls70/56，保存47/29个任务，结构引用有效且三领域覆盖。SP12轮耗尽、答复空；候选第10轮length、4096输出含4083reasoning、最终54字符半句话。停止字段证明截断，不证明根因。
- 两组 parse_prd 均0调用。预定批量写入中介未激活；调用下降或PE上升不能归因该机制，也不能证明正确采用batch仍无效。下一机制须区分采用与适用性解释，不能再加命令句或重跑到赢。
- 235都完成、TFPE10，core SP0/1候选1/1；SP把8月下跌称plateau。两组知识相同，不作适应因果解释；即使宽松接受该词，283拒绝不变。未改原判定。
- 新费用48请求（26actor/20judge/2preflight）USD0.085840668，未知0/未结0，updater0；12原生调用无模型费用。196原始归档成员（含日志/原生状态/12固定native源码）和358执行源码文件离线核验通过。
- 本版关闭，预注册两批各12条验证未启动，无运行实验或下一已准入候选。既有NU/FR和全部正负结果保留；最终综合报告/复现/展示与完整原benchmark双提升仍欠，不能用此次归档或负结果标complete。

### 已结束上一轮：失效能力撤下完成6条开发，未双提升

- 同一完整Goal active、未完成；本轮是实际机制检验，不是阻塞轮。原分支未切换，无新agent/worktree、push、部署或外发。
- 报告[`reports/capability-withdrawal-development.html`](reports/capability-withdrawal-development.html)，离线复核`python3 results/evidence/capability-withdrawal-20261101/verify_archive.py`。
- 复用ExpeL v3及e41ec9a规则撤回源码机制，明确为本项目扩展：三个有源码+独立原生失败证据的Late工具从静态知识撤下，清理五处直接推荐。SP/警告诊断/撤下主候选，原283Late+235Late各一次，共6条。原生工具/执行器/模型/4096与12轮/评分和验收不变；34->31模型可见工具。
- `78f2b27`冻结协议和实现（57测试）；`23b4df6`冻结全部知识及审查ID；runner95975退出0，6/6 evaluated、30原评分。`1389af4`保存全部评审后读单元映射。**偏差：runner自动打印分组均分时，最后两份235评审尚未写入；不能称六份严格盲审。** 全部283判断此前已保存。
- 原283Late：三组完成/全项质量都0/1；SP TF9.8/PE9.6/calls77，警告9.2/8.6/72，主候选9.8/8.6/43。实际保存54/43/36有效任务，最终答复均为空；都12轮耗尽，末轮finish_reason=tool_calls而非length。主候选首轮12008tokens对SP14903，降低输入/调用未转化为交付。被撤下3工具在SP也0调用，故避免失效调用中介未激活。
- 235知识逐字相同；均完成，TF SP10/警告10/主候选9.8；质量0/1、1/1、1/1。不能把相同K0波动归因适应。C04/C05措辞与C03结构未知敏感性均不改变拒绝。主候选关闭，两批各12条验证未启动，警告组不能事后晋级。
- 新费用74请求（42actor/30judge/2preflight）USD0.135451632，未知0/未结0；updater0，原生探针直接复用未重采。260原始文件和351源码文件离线核验通过。
- 新源码排除证据：securitybuilder的22本地模块、models.yaml、package.json三阶段相同，无支持改变它的依赖边；不声称全外部运行时证明。workspacehealth只条件失效，保留可能成功分支，不作全局无效工具撤下。
- 无下一已准入候选。不重跑本版本、不简单换删除子集或重复预算提示；下轮须有不同且可证伪的机制依据。课程最终综合报告/复现/展示及严格完整Goal继续保留，不能用本轮负结果标complete。

### 已结束上一轮：无效可选参数投影完成9条开发，质量增益失败

- 同一完整Goal当前工具状态为active，目标未完成。本轮是实质进展，没有新阻塞计数；沿用分支，未新建agent/worktree、未push/部署/外发。
- 报告见[`reports/optional-parameter-projection-development.html`](reports/optional-parameter-projection-development.html)。复用固定EasyTool论文/作者源码；本项目扩展为从模型知识schema移除源码证明无效的可选字段，区别于继续改写描述。原生server/schema、必需参数、有效能力、执行器和单次预算均保持。
- `8e06de6`冻结20次通用省略等价/必需参数缺失负控制，全部通过；`3b8a6ae`实现新投影并冻结9单元及条件18+18验证；`a709448`冻结全部知识。Middle移除2个、Late4个可选属性；235三组知识逐字相同。74针对性测试通过。
- runner93931退出0，9/9 evaluated、45/45原评分槽位。`49ab4e6`先提交9份产物审查再揭盲；同协调者，非独立人工；只做AST/控制流与良性标准库参照，没有执行生成代码。
- 原133 M/L：**SP完成0/2、core0/2、TF9.3、PE7.6、调用24；描述修订诊断2/2、0/2、10、7.9、18；主参数投影1/2、0/2、9.8、6.8、30。** 正常结束也有实现错误，截断不能解释全部质量失败。主候选未双提升，不启动独立验证，也不事后选择诊断组。
- SP使用12个无效参数值，另两组都0；投影没有进一步减少已被描述修订避免的参数使用。继续换同组字段子集信息增益低，不否定全部schema适应方法。下一候选仍须合法、机制清楚、依赖齐全且可证伪，无需先证成功。
- 验收敏感性必须保留：P08主代码可解析，但明确提供的回归测试与实现矛盾；忽略该矛盾并计为pass会改变本轮开发门槛。按冻结验收保留失败，不声称对此稳健。235均完成/TFPE10，core SP0/1、其余1/1，知识相同不可归因；P05约29%的粗略措辞也已披露。
- 新增76请求(29actor/45judge/2预检)，USD0.090926484、未知0；无新增updater请求，既有v2一次性0.003234600单列不重复计费。373原始文件、338源文件及全部指标/费用离线复核通过，见`results/evidence/optional-parameter-projection-20261101/reproduction.txt`。
- 无运行实验；课程NU/FR和全部旧正负结果保留，最终报告/复现提交/展示与under-over归因缺口仍在，不能代替尚未实现的双提升。

### 上一实验断点：LLM契约维护已完成开发，严格双提升未通过

- 用户授权继续同一完整Goal；本轮完成有边界五类失败复盘、限制来源核查和唯一只读独立审查。课程DOCX哈希重新核实，严格双提升来自用户要求。旧实现的append-only、一跳关系或特定正例门槛没有升级为永久禁区。
- 研究链见[`reports/semantic-claim-repair-development.html`](reports/semantic-claim-repair-development.html)。复用ACE/A-MEM/Reflexion，定向核查固定ExpeL源码的failure_critique；无正确actor正例不能否定所有反例学习。新机制不是仅换措辞：LLM按源码和通用探针判断每条契约保留/替换/未知，程序保护真实diff、字段、依据和无关知识。
- `22351ca`冻结3个通用native探针；`07576b0`冻结联合编辑/影响范围v1，Late两次依据校验失败，3次updater后关闭，无actor。`539a2c4`冻结职责拆分v2，程序固定范围，2次updater产生14项决策（4保留/10替换）；语义审查通过后`c41848b`冻结6单元原题开发。模型、供应商、解码、预算、执行器、评分和验收均未改变，updater无benchmark问题/答案/评分轨迹。
- 原共用账本在本地预检因更新器/actor预算身份不同被拒绝，未发API请求。`c0471ba`冻结分开actor账本后的执行计划，6份知识和顺序完全相同；原失败及计划保留，不是actor重试。
- runner42786退出0，6/6 evaluated、30/30原评分槽位。原133 M/L：**SP与候选完成均1/2、core均0/2；TF9.3/9.9、PE5.9/7.7、工具调用62/13**。候选validation属性改善，但Late代码仍有未处理OverflowError，Middle交付CI片段截断。不能用工具/官方高分替代产物正确，也不能从停止字段推断根因。
- 235L保持：两组均完成、TF/PE均10；core SP0/1、候选1/1，知识完全相同，不作补丁因果解释。产物审查先以文件哈希冻结再揭示策略/TF/PE；同协调者，非独立人工。C03主实现小型正例通过；即使宽松忽略损坏CI片段记为core通过，完成率仍打平，不能晋级。
- **本具体v2开发失败，不启动两批各18单元独立验证，不重复抽样到赢。** 只否定当前版本的充分性，不否定LLM维护或声明方法空间穷尽。后续依赖传播若被选择需要真实源码关系，但这不是其他机制的通用准入前提。
- 本轮60笔请求（5 updater/23 actor/30 judge/2预检），USD0.072323580、未知0；3独立ledger、所有失败/成功/原评分保留。66项针对性测试通过；离线verify_archive.py验证290原始文件、331源文件及指标/费用通过。复现说明在`results/evidence/semantic-claim-repair-20261101/reproduction.txt`。
- 课程NU/FR独立保留，最终整合报告/提交包/展示及under/over-update因果案例仍待完成，不能替代研究突破。当前无运行实验；同一Goal未完成。应用工具仍保留旧blocked状态，本轮没有再次设置blocked、创建新Goal或标记complete；旧阻塞审计不覆盖新授权和实际进展。

### 历史状态（被本轮授权与实际进展接续）：Goal 曾阻塞，目标未完成

同一机制准入障碍在本聊天连续三轮存在；最后两轮没有新进展。已核对干净的`f445fa5`、未准入候选及训练失败门槛，Goal工具已返回`blocked`。完整目标、研究边界和全部结果保留，不把阻塞当完成。具体三轮审计和恢复所需的新证据见`handoff/current.json`的`blocked_audit`。没有新模型调用或未完成实验；不要自动重跑已关闭方案或重复文献归档。

### 最近实质进展：新聊天接手并完成接口学习线索准入复盘

- 本聊天`01a19594-5645-7520-bf4f-98de0419fc4e`已按同一完整objective创建active Goal，无总token预算；旧Goal仍暂停。直接使用`codex/completion-quality-study`，未切分支或新建worktree。
- 新证据见`results/evidence/interface-mechanism-review-20261101/bounded-review.json`与`reports/interface-mechanism-admission.html`。核读EasyTool2401.06201v3、Play2Prompt2503.14432v2、Trace-Free+2602.20426v2（亦读v1相关段），固定三个作者仓库SHA及定向源码。没有执行作者程序或模型。
- 定向离线复算：457 Early/Middle均19工具，description均1113字符；Late21工具/1732字符。bulk在Early已存在、描述三阶段均74字符，Middle仅其parameters改变。最近原457的W02/W04/W05/W06均0bulk、0set_page/add_page调用。字符不等于token；未排除schema/观察负担或定义暴露影响，未建立截断原因。
- 不准入单纯描述压缩/再加示例（新机制依据不足）、Play2Prompt直接移植（问答/ground-truth调用进入反思，与当前边界不兼容）、Trace-Free+发布权重（替换冻结更新器；复制提示不等于其学习机制）。初步“隔离新增bulk”前提错误，未形成候选。不是否定整类方法，也不是方法空间穷尽。
- 新agent/judge/updater/native调用均0，新模型费用0；未生成候选、未开启开发/验证。离线诊断脚本只读固定fixture和四份既有review输入，五个输入哈希保留；原评分、全部结果及执行代码未改。
- 交接三条文献线索已完成本轮必要阅读，不要重复搜索/归档当进展。下一实验须有不同、范围内、可反驳的新机制和具体证据；没有则如实保留机制证据不足，不重开旧训练、不缩题、不修改模型/预算、不重跑到赢。Goal仍未完成；课程报告/复现/展示及失败案例最终核对仍有工作。

### 上一实质实验断点：经验驱动局部替换的训练准入失败，尚未产生候选知识

- 同一Goal/分支/全部旧文件、正负结果保留。新报告 `reports/experience-gated-learning-admission.html` 完成“已有失败→原始论文/固定源码→不同学习机制→四次实际训练准入”的链条；未重启旧程序/预算提示，也未重开377日志路线。
- 复用五类失败矩阵、此前局部收益和ACE/A-MEM/Reflexion等阅读。新增GEPA2507.19457v2（2026-02-14），官方SHA`8c7b697a71977980afc7537dac0881e784eef99f`；反思、候选评估、Pareto选择和MCP适配器关键位置与许可在`results/evidence/experience-gated-learning-20261101/`。复核ExpeL2308.10144v3、SHA`e41ec9a24823e7b560c561ab191441b56d9bcefc`的task_critique/parse_rules/update_rules。官方GEPA的两次调用执行器及含问题/最终输出的反思输入不符合当前公平边界，因此未直接采用；不声称完整复现GEPA/ExpeL。
- 机制选定为：固定通用actor真实正反经验→一次受约束的局部description替换→新颖性/依据审查→原题开发。区别于只从原生程序收据抽取旧顺序提示。必须先有至少1正常完成且core通过正例和1失败；否则不调用更新器、不追加抽样。多候选运行时选择超出当前执行边界；信用累计仍缺经验来源，均未伪称实现。
- `72ba610`模型前冻结独立合成训练900201/900202、种子800201/800202、各2次原SP，顺序201/202/202/201。完整输入嵌入问题，四页决策简报含审计数据、算术、双约束选择和实际文稿；答案仅评测，独立目录/哈希/七属性验收。全部SP知识不变，尚无候选差异。固定现有模型/DigitalOcean/解码/单次预算/5judge；专用ledger避免旧路径问题。原457Middle/Late+235Late的6开发/18+18条件验证日程预先指定，未按新结果选题。
- 反馈投影只允许工具操作、参数名/封闭枚举和属性标签，不含问题/正文/最终答案/reasoning/oracle。10项边界测试先红后绿；全467离线测试通过、15integration不重复。63份冻结源/输入归档。训练知识冻结在前，若能学习，精确候选仍须在新开发前单独冻结；不把学习后文本伪称预先确定。
- runner84029退出0，4/4 evaluated，20/20首有效judge。`117f654`在查看官方分数前冻结全部实际产物审查；同协调者、仅遮蔽分数，四例都是SP，不称独立人工或方法盲审。**合成训练完成0/4、core0/4，平均TF1.35、PE6.75、ECS=null。** 各TF1.2/1.2/1.0/2.0，PE6.6/6.4/7.8/6.2。
- 四例均只有单页占位封面，实际set_page/add_page为0。最终completion均4096，reasoning3683/3826/4096/3242；三个返回半截未执行调用文本，一个空最终内容。最后prompt7626–11610，不能把失败只归为超大上下文，也未建立设计行为的因果解释。三个封面原字节渲染可读；E02自选midnight-brief不存在，共同renderer退出1，未补装或修内容。所有截图/日志/原始错误保留，renderer均已关闭。
- 22调用外层isError为false，但E03首次load内部success=false，`inner-outcome-audit.json`单列。冻结投影字段仅代表外层错误，不等于业务成功；投影没有发送更新器，今后复用须另行冻结内部结果处理。初始化JSONRPC警告保留，不归因为已证明的截断原因。
- 43请求（21agent+20judge+2preflight）USD0.032424492，未知0；更新器calls/tokens/USD0。174原始文件归档；`verify_training.py`独立离线复算通过。原benchmark本轮没有新候选/保持运行；235和NU/FR历史证据仍独立保留，不能从训练结果宣称保持或原题改善。
- **固定训练准入失败，没有产生候选知识，不运行反思/原题开发/两批验证，不重试此采集方案直到赢。** 这是经验来源缺少正例的具体障碍，不是否定整类GEPA/ExpeL或声明方法空间穷尽。当前无可晋级候选；下轮必须先有不同、范围内、可反驳且有新依据的机制，不能移植旧提示或缩题抽到正例。Goal仍未完成；这轮有实际4次实验，不是重复阻塞/状态检查；未push/部署/外发。

### 已归档：AWM/AutoManual逐页程序记忆已完成原题开发，仍未达双提升

- 同一Goal、分支与所有旧结果保留。新报告 `reports/prefix-workflow-memory-development.html` 已完成“有边界失败复盘→原始论文/作者源码→新程序机制→准入→原题模型开发→独立离线复算”的完整链条。没有读完整历史或全量旧轨迹，377路线保持关闭。
- 复用五类失败矩阵和既有ACE/A-MEM/Reflexion/ExpeL/Voyager阅读；新增AWM2409.07429v1、官方SHA8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1，以及AutoManual2405.16247v4、官方SHAaeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324。实现位置、许可边界、实际借鉴和完整方法差异在 `results/evidence/workflow-memory-learning-20261101/bounded-review.json`。283原候选已执行同一分析/平铺流程，因此没有改名重试。
- 新机制 `prefix_workflow_memory`：从18条通用成功训练收据将9步抽象为7步，路径/标题/正文变量化、连续add_page归并为逐页循环；每次提交一页并保留已写内容。只改变化bulk工具的一处description，SP参数/路由/其余规则保持，235精确K0。是固定语法的规则抽取，不是完整AWM/AutoManual，也没有新增执行器。
- `ac5c819`冻结合成原生准入；40调用全部通过，4/5页训练/留出共18页内容/暗色/边界与视觉检查通过。首次渲染误用IPv4而服务监听IPv6导致4次采集失败，修正采集URL后测量同一产物，未重跑native或修内容。所有页有WakeLock权限诊断，采集器额外“零pageerror”标志仍为false，不能写成全部检查通过。原冻结页面属性单独判定通过。22输入及所有日志归档；`verify_admission.py`离线通过。
- `d0b535c`冻结严格开发与条件验证；16机制测试先红后绿，全457离线测试通过、15integration不重跑。留出值只评测，不进更新器；离线展开匹配已有留出实测动作，中途load挑战单列。原457三PDF字节与既有冻结一致，共同renderer/模型/provider/解码/单次预算和评分不变。
- `180436e`在模型前冻结6单元、6知识文件和229源文件；`cfb1e7a`在读分数前提交全部产物审查。runner15339退出0，6/6 evaluated，30/30首个有效judge；原PDF服务59378已关闭。方法标签/工作区路径及评分遮蔽，但同协调者可从行为推测，不称独立人工复核。
- **原457：SP与候选正常完成均0/2、core均0/2；平均TF2.3/1.8、PE5.1/4.4（SP/候选）。** 四运行最后4096/4096reasoning截断，最终内容空，实际set_page/add_page均0。候选Middle仅暗色封面，SPMiddle仅封面且自选clean-dark主题无法解析；两Late无文稿。原生程序有效未转化为模型正文写入，不能把此版本失败泛化为整类工作流记忆无效。
- **保持235：两组完成1/1、TF/PE均10；core SP1/1、候选0/1。** 候选错称广东超过浙江两倍，15.8/9.7约1.629；同K0差异不作适应因果解释。部分Middle/Late日程ECS=null，NU/FR既有课程证据保留独立解释。
- 58请求（26agent+30judge+2preflight）USD0.077459352、未知0；更新器calls/tokens/USD0。费用配置沿用旧ledger路径，58新请求追加在旧56请求后；114合并记录完整保留，严格按响应ID分离，本轮旧账本已恢复不可变归档原字节。首次复核缺账本失败保留，没有改模型/分数或重跑。`ledger-reconciliation.json`完整披露。
- `results/evidence/prefix-workflow-pilot-20261101/`保存283原始文件归档、229源文件归档、原始评分、审查、最后响应定向机制投影和费用核对。`verify_trial.py`独立离线通过；报告1280/390布局及本地链接检查通过。具体版本开发失败，**不启动18+18两批条件验证，不重复抽样到赢**。
- 下一步只有建立不同、有证据且范围内的机制才可预注册新候选；不能简单把同程序搬到邻近描述、追加预算提示或寻找新工具故障。本轮有实质原题模型试验进展，不是阻塞轮；当前无运行实验、无已准入下一候选，未宣称范围内方法已穷尽。Goal继续未完成；未push/部署/外发。

### 已归档：程序记忆新开发试验已结束，严格双提升失败

- 从上一轮程序记忆离线准入继续，未重启旧实验。新报告`reports/program-memory-development.html`完整连接失败证据、Voyager原始论文/固定源码、程序值记忆和已执行验证；ACE/A-MEM/Reflexion/ExpeL及三个候选比较复用，不只追加工具提示。
- 预选两个原生组件不变；单独提供双方相同React/TSX/别名/样式环境，23组件编译通过、仅预选两组件渲染/属性变形/动画负控制通过。第一次原生调用因成功stderr进度文本被判错；共同builder调整诊断输出后，另一次预注册原生调用及渲染通过。原始失败保留，未改原生工具。依赖1649项及13.6MB归档在`results/evidence/program-memory-runtime-20261101/`。
- 新`verified_component_memory`保留7处路由描述，并在2处附上2481字节完整通用源码。只改description，schema/routing/usage_rules不变；235精确K0；不含解析器/统计答案/页面。新12项TDD先红后绿、429离线测试通过、15integration未重复；共同builder2项边界测试单独通过。
- `65543d0`/`f049dd2`冻结机制与新扩展日程；`316befc`在模型前冻结900101/900102/900103、种子700101/700102/700103、三个oracle、1805源文件/知识/共同环境。草稿同时存在宽松和严格dev门槛，已在零模型请求时移除冲突；最终门槛完成与core各自严格>SP，TF及235保持不降。准备路径错误与所有失败保留。
- runner session46751退出0，4/4 evaluated、20/20首个有效judge。`70d98a0`先提交质量审查再读分数；**方法盲化不完整**：原始绝对workspace路径泄露单元身份，明确记为遮蔽评分的同协调者审查，不称独立/完全盲审。合成缺失产物由检查器独立确认。
- **合成900101：SP与候选正常完成均0/1，core均0/1，TF均1；PE为5.2/7.0。** 两者output_truncated且无parse-logs.cjs/data.json/index.html。候选知道记忆中已有源码，仍取整类TextAnimations(62090序列化字符)，未执行源码复用。两组均7工具调用，最后prompt19444/33186，4096tokens截断；SP reasoning4096，候选3865并输出半截未执行DSML文本。不能把相关观察写成完整因果解释。
- **保持235：两组完成1/1、TF10、core0/1；PE SP8.2/候选7。** 图表规格/单位正确，候选错报12月/2月倍数2.9(实际3.18)，SP错称三类别均1.3–1.4倍(家电实际1.15)。K0相同，不作适应因果解释。Late-only ECS=null。
- 44请求(22agent+20judge+2preflight)USD0.040018260，全部固定模型/DigitalOcean，未知0；更新器calls/tokens/USD0。`results/evidence/extensions/program-memory-dashboard-v1/`保留725原始文件归档、1805源文件归档、质量审查、机制投影与独立离线复核脚本。原SP/NU/FR、旧扩展和所有正负结果保留。
- **此确切候选开发未晋级：不执行两批验证，不再重试到赢。** 已冻结验证数据/日程保留未执行。只否定本具体版本的充分性，不泛化为程序记忆/Voyager无效。原变化题无新增完整MagicUI任务；377始终“原始输入缺失，当前不可评估”，永久不重开日志查找/等待。
- 下一步不再补通用工具/预算提示。结果信用候选仍需不含benchmark答案的通用程序成功/失败经验对；动态检索仍超出固定执行器范围。只有建立不同、范围内、输入完整且可反驳的机制后，才冻结新的最低开发试验；本轮未准入下一候选。不要重复已有环境/测试/状态检查制造进展。Goal仍未完成，也未宣称方法空间穷尽；未push/部署/外发。

### 已归档：有边界的经验/论文/源码复盘与程序记忆准入

- 最新用户要求把后续设计建立在历史证据、原始论文与作者实现上，不能继续主要追加工具提示或寻找下一个工具故障。之前所有agent实验已终结；本轮未重启任何旧候选。377始终为**原始输入缺失，当前不可评估**，不重开查找/等待路线。
- `reports/method-learning-and-program-memory.html`连接“失败证据→文献/源码→三个不同候选→已执行准入”。仅用六组汇总和定向证据，按知识适应、执行/预算、产物错误、环境/数据、评测不确定性分类，分别标注直接支持事实、观察与假说。没有加载完整聊天/全量轨迹/密钥。
- 原ACE/A-MEM/Reflexion阅读复用并核对官方源码，新增ExpeL v3与Voyager v2。五个作者仓库均固定完整SHA/实现位置，18份源码/许可证保留。旧delta/linked/feedback_notes没有复现论文完整机制；ACE该SHA的curator操作也仅实现ADD，不能把论文全部编辑能力写成源码事实。
- 选择的新设计为**经验证的程序值记忆**，而非继续追加错误规避说明。`386649a`在查看候选代码/依赖结果前冻结离线准入：两个归档原生类别各选源码最短组件，同长按名称，不允许失败后换下一个。23个组件中选animated-gradient-text(871字节)和meteors(1610字节)，合计2481字节通过16000字节上限；现有隔离Node环境不能直接解析TSX，react和@/lib/utils无法解析，样式/浏览器效果未验证，结果**not_ready_for_agent_trial**。这是执行依赖缺口，不是agent策略失败，也不是整类程序记忆无效。
- 定向上下文核算：在固定已观察轨迹下，首轮全部输入仅占最后prompt的SP13.37%、候选4.73%；静态工具知识更小。只约束直接压缩通道，不包含知识改变后续调用的效应，也不证明大上下文造成截断。
- `results/evidence/method-learning-20261101/`含失败矩阵、各指标/成本投影、固定文献源码、候选否定条件、准入协议/原始失败和离线复核。新model/native请求0、USD0；无新agent评分，TF/PE/ECS均不适用。保留NU/FR及旧扩展独立解释，不混汇。
- 当前没有通过准入可直接开跑的候选。继续程序记忆需先单独声明、验证双方相同的React/TSX/别名/样式构建环境，并证明冻结原生组件有效；另一候选需建立不含原benchmark答案的通用程序正反经验。不得把新环境回填为本轮通过、把已有评分轨迹灌给updater或直接重试旧提示。新的完整开发试验仍须先冻结知识/任务/验收/日程，通过后才两批独立验证。原benchmark Goal仍未完成，没有宣称穷尽方法空间；没有新阻塞计数或重复状态检查。

### 已归档：受控合成扩展开发试验失败，候选停止；377等待路线永久关闭

- 最新用户授权仍有效：原题377记为**原始输入缺失，当前不可评估**，不是策略失败；不得再索要路径、检查缺失目录、等待或重复阻塞审计。下方旧等待段落仅历史保留。
- `42de07c`与`209d99d`在模型前冻结独立扩展900001/900002/900003、三个种子、数据/答案哈希、七描述候选、4+12+12条件日程与可执行产物检查。正确答案只在评测目录，agent只收到input/logs及同一任务要求；原题235保持任务无fixture/提示/知识改动。原No Update/Full Rewrite证据保留。
- 四单元开发已全部evaluated，runner77284退出0。`9e4dbf0`先提交所有产物盲审再揭盲。合成扩展：SP与候选均正常完成0/1、core0/1、TF1、PE3.2；两者均4096 reasoning tokens后output_truncated，没有解析器/JSON/网页。保持235：两者均完成1/1、TF10、PE10，实际图表规格正确但解读错误，core均0/1。ECS因Late-only不适用，不能填0。
- 机制确实触发：SP调用2个已知失效精确接口；候选0次并取得两类真实代码。但候选最后prompt55195 tokens，SP18890；不能把伴随观察写成已证实因果。没有完成率或产物质量改善。开发门槛失败，**不运行两批验证、不重试同一方案直到获胜**。验证数据与日程保留未执行。
- 37请求（15agent+20judge+2preflight）USD0.040553940，未知0，全部固定模型/DigitalOcean。更新器calls/tokens/USD0。417离线测试通过、13integration未重复；首次3个旧入口调用兼容失败及修正前准备完整保留。
- `results/evidence/extensions/magicui-log-dashboard-v1/`含183原始文件归档、115冻结源文件归档、盲审、逐单元原始评分/成本/调用投影、原题筛选及decision。`python3 results/evidence/extensions/magicui-log-dashboard-v1/verify_trial.py`已离线通过，无网络/API。报告`reports/magicui-controlled-extension-development.html`。
- 路线1既有MagicUI四题缺口按事实保留；固定142/161/309筛查没有新运行源码变化/完整必需机制。时间与PDF必需路径追加审查亦未建立新候选，不重复旧模型试验，不宣称穷尽所有方法。
- Goal仍未完成。此轮完成了实质开发实验及可复算负结果；下一步只推进不同且有新具体证据、输入/运行/产物检查齐全的原题机制。不得以合成结果、负结果或当前方法未找到成功来宣称Goal完成。所有文件保留，未push/部署/外发。

### 已归档：用户关闭377原日志路线，授权原题筛选与受控合成扩展

- 2026-11-01最新用户指示优先于下方旧等待/阻塞记录：**377原始输入缺失，当前不可评估**；等待、继续搜索或索要原日志路径的路线永久关闭。旧审计仅作历史保留，不再累计同一缺失、不重复检查目录或询问用户。
- 路线1先按现存证据排除MagicUI原题171/217/246；377保留为不可评估，非策略失败。固定追加检查142/161/309：相关包各阶段无运行源码变化，142/161还缺原题time运行profile；不能直接作为新漂移机制候选。继续仅在具体必需路径有新证据时选择输入完整原题，不能按最终模型分数选题。
- 路线3已获明确授权，独立目录`experiments/extensions/magicui-log-dashboard-v1/`。任务900001/900002/900003均标记controlled_synthetic_extension，对应开发/验证A/验证B；绝不覆盖377或混入原benchmark汇总。固定种子314159/271828/161803，输入/正确答案隔离。具体任务、机制、检查与4+12+12条件日程在protocol.json；模型运行前还须冻结源文件与知识、提交预注册。
- 精确复用ef97a48/cee763a/b0f957e更新器和原生探针；只改7处MagicUI描述。固定SP直接对照和235保持任务；原NU/FR课程证据保留。开发不过则不运行此候选验证；每个验证批次都须完成数和core严格提高，TF及保持不降。
- 新增任务入口防止正式ID覆盖/答案字段泄漏，检查实际解析重跑、追加输入变形测试、网页运行及统计呈现。正确答案仅在评测目录，agent只得到input/logs与统一任务要求。合成实验通过也不能宣称原benchmark Goal完成。
- 此处为实质新实验准备，旧Goal工具blocked状态源自已被用户取代的原日志等待路线；不能因此停工或重复阻塞审计。无push、部署或外发。

### 已归档：恢复后第3轮仍缺原始输入，重新阻塞审计通过

- 本次工具确认Goal状态已由blocked恢复为active；此前`3350879`的阻塞次数不沿用。新的`results/evidence/goal-resumed-blocked-audit-20261101.json`从第1轮记录，尚未达到再次blocked阈值。上轮属于无进展的阻塞结束；不是活跃实验等待。
- 恢复后第2轮再次核对：仓库无其他变化，`logs/`、`anotation_path/logs/`、公开附件的logs目录均不存在，没有用户路径答复或新agent日程。没有新实质研究进展；本轮仅记录相同阻塞，不重复服务/模型/离线测试。新审计累计2轮，Goal仍active，尚未达到再次blocked阈值。
- 恢复后第3轮再次确认上述三个目录均不存在，分支无额外修改、无新输入/模型日程/研究进展；自主必要准备已经完成。新审计累计3轮，`threshold_reached=true`，满足重新blocked条件；本轮下一步调用Goal状态工具设为blocked，不能设complete。原始日志问题仍待答复，未重新发送问题或重跑实验。实际Goal状态以工具记录为准。
- 补查此前未核对的入口：学习工作区只查同名文件/相关归档名，无匹配；作者GitHub当前main仍为固定`888c779a...`，完整树362项、未截断，无Ableton日志，Release列表为空。记录在`resumed-public-attachment-check.json`和`resumed-input-source-audit.json`，只读目录/资产名，无参考答案/轨迹。
- 检查公开输入代码的相关行：`log_analysis.py`随机生成当前时间的通用`app.log`，不是二月Ableton日志恢复器；`new_aggregator.py`是news.db/RSS新闻聚合。未执行这些脚本，也未用它们补造正式数据。
- 没有新增native/agent/judge请求或重跑离线测试。既有更新器工作已完成，仍需原日志路径/可信附件来源，或另一条已证明完整原题路径的新具体证据。Goal活动但双重改善未成立；条件协议与严格验收不变。

### 已归档：上一轮正式试验输入阻塞，Goal未完成

- `results/evidence/goal-input-blocked-audit-20261101.json`记录连续三轮相同条件：`10bac8a`收尾时原日志缺失；`b0f957e`收尾时仍缺失；本轮再核对仍无logs目录、Ableton附件或用户提供路径。前两轮分别完成原生准备和更新器实现，本轮没有新的实质研究进展，不能把状态复查/写审计算作进展。
- 当前自主可完成的更新器、404离线测试与独立证据核验均已闭环；没有活跃实验、没有新agent日程，也没有其他已建立的就绪候选。满足“条件连续三轮且当前确实无法有意义推进”的阻塞审计，下一步将Goal设为blocked；绝不能设为complete。
- 恢复需要：任务377原始Ableton日志的可信来源/本机路径，或能建立另一条完整原题必需路径的新具体证据。原日志问题已询问，尚无答复。不能用合成canary替换正式数据，不能重跑淘汰方案直到获胜。此处不是成功策略不存在的证明。
- 分支及全部证据保持原样；未push/部署/外发。收到有效新输入后，从下节已完成实现继续，先冻结真实统计oracle与实际网页/脚本验收，再按条件协议预注册模型日程。

### 已归档前置：MagicUI 知识更新器离线闭环；正式试验等待原始日志

- 上一轮`10bac8a`完成两套探针及原始附件核验，属于实质进展。本轮确认仍无原始logs或用户路径答复；没有启动模型试验。但知识更新器可独立实现，先完成这项必要工作，不把写计划/等待当进展。
- `experiments/native-argument-routing-updater-v1.json`冻结Late三条空参数工具及四条直接相关路由说明，共7处description，五条原生事实证据。所有schema/routing/usage_rules/其他工具保持SP；未知契约或缺证据拒绝，Early/Middle/无相关变更返回SP/K0。只预注册离线实现与测试，不是agent日程。
- `ef97a48`在实现前冻结精确知识差异/证据/测试，首测按预期Unsupported strategy失败。已实现`native_argument_routing`并注册到公共adapt入口；相关82测试与全部404离线测试通过（13integration排除），两新模块/测试ruff通过。首次实现有1个测试错误：按最后一项找无关工具，而SP把新增工具追加其后；改为按server_id定位，原验收不变。原始red、全套测试及说明在`results/evidence/native-argument-routing-updater-20261101/`。
- `cee763a`实现后，公共adapt及prepare_tools完成4组/8次离线适应：MagicUI Early/Middle/Late与235真实留存原生目录。独立标准库校验确认仅Late7处description改变，模型实际接收的parameters/routes保持原样；235两方法知识文件均与原始Early K0字节相同。37个选定文件归档168019字节，`python3 results/evidence/native-argument-routing-updater-20261101/verify_offline.py`可无服务复核。
- 全部执行已终结，pytest21293退出0，没有新native/agent/judge请求，确定性更新calls/tokens/USD均0。`decision.json`明确本轮为实质进展而非已达到连续阻塞阈值。原始日志问题尚无用户答复，未创建agent日程；不能把离线通过当完成率/实际任务质量双改善。
- 现在可独立完成的更新器工作已闭环；下一步需要真实原日志（来源/格式/统计oracle冻结）或新的、有原题必需路径依据且输入齐全的机制。保留条件协议的原4单元开发与两批各12验证门槛。不要重复已通过的离线检查制造进展、不要重跑旧失败候选、不要以合成canary替代正式输入。Goal仍活动，目标未达成；尚未证明方法空间不存在成功策略。

### 已归档前置：MagicUI 原生机制与原题依赖核对

- `7c5f0af`预注册的9工具调用/3catalog已全部完成，执行器session95656已退出；0模型/0评分/USD0。独立离线核验56归档文件与34冻结源码输入通过，见`results/evidence/magicui-argument-routing-probes-20261101/verification.json`；不要重跑。
- Late三个新增精确工具均暴露空参数schema：单项查询报Component undefined、批量报No valid component names（均isError=true），搜索丢失query/category，返回78项且isError=false。三阶段原有getTextAnimations均返回逐字相同的14个真实实现，canary含9476字符代码。确认了原生参数路由缺陷和通用替代，尚未测agent改善。
- `results/evidence/mechanism-screening-20261101/magicui-task-readiness-screen.json`记录定向依赖筛查：377原始logs/ableton文件未在公开附件找到；171所需mcp-mermaid包三阶段缺失且不属选定201题；246原CSV无购买字段；217虽有XLSX但原工具集无文件读取能力。106名片图片亦未提供。不得补造数据、把其他Mermaid包当别名或修原生源码后计作知识收益。
- 补充原始附件核对：固定HF revision仅README与三份server归档，三个ZIP中央目录均无ableton-error或image_01.jpg；结果在mechanism-screening目录的published-dataset-root-listing及magicui-published-archive-filename-check。已异步询问用户是否另有原日志本机路径，尚无答复。
- `f7763cb`预注册的两个新依赖调用也已完成，session74220退出0：Late code-runner准确读写隔离canary/JSON/HTML，getSpecialEffects返回9个实现（magic-card代码6314字符）。39文件/22源码归档与独立离线复核在`results/evidence/magicui-artifact-dependencies-20261101/`。原code-runner三条stdout调试信息触发非致命JSONRPC告警，日志保留且未修源码。仅就绪检测，不能替代正式日志；不要重跑。
- 具体条件设计在`experiments/magicui-conditional-next-protocol.json`：只修正这三个空参数工具及分类路由的知识；真实日志/逐日统计oracle/可运行网页和脚本验收须先冻结。拟4单元开发、仅晋级后两批各12独立验证，沿用每批严格完成+core双提升、TF与保持不降。该文件**不是生效预注册**，没有新agent日程；不得拿合成canary开跑。
- `post-magicui-required-path-screen.json`记录黄历与两种记忆图的追加必需路径核对，仍未找到新的可检验替代。当前没有运行服务，也没有已建立的其他就绪候选；未宣称方法空间穷尽。Goal继续，双重改善未成立。本轮有实质进展（两套原生探针闭环与原附件核验），连续阻塞计数尚未成立。下一步优先处理用户的原日志路径答复；否则只在新具体机制/新来源证据出现时继续，不重复无效实验。全部旧文件/负结果保留，无push/外发。

### 已归档前置：MagicUI 参数路由机制预注册


- 上一轮`discovery_contract`已淘汰且不可重跑（下节）。本轮定向源码核对发现不同机制：MagicUI Late三个新精确查询工具用普通JSON对象注册，当前SDK把它们当annotations，可能导出空参数schema并把request context传给handler，丢失真实用户参数。目录不一定失败，原有无参分类接口可能仍可用；目前仅源码假设。
- `experiments/magicui-argument-routing-probes-v1.json`冻结固定canary=text-animate、9次工具调用/3catalog/0模型；collector在`results/evidence/magicui-argument-routing-probes-20261101/run_probes.py`。先检查Early目录/真实分类代码，再Middle索引/分类，最后Late三条故障及分类替代。意外错误/缺少canary立即停止，不重试/换查询/修原生源码。共用profile仅按三阶段原包bin补入dist/server.js，不传凭据。
- 尚无新的agent候选/评分日程。若原生证据通过，再单独验证task377原始日志与code-runner依赖，冻结实际网页/统计产物规则和公平对照；不能把原生调用成功当双重改善。Saleskit新增参数偏向OCR可选规则/差旅，task106仅单张名片且需外部OCR与上传，未调用这些服务。

### 已结束：discovery_contract 两批独立验证已淘汰；后续源码筛查

- 闭环提交`32da2d3`后新增有边界源码复核：`results/evidence/mechanism-screening-20261101/post-discovery-required-path-screen.json`，27源码hash、8项判断，原生/agent/judge新增调用均0。Draw.io预设/复制、Smart Reviewer摘要、Bilibili未传递过滤、WHOIS raw、AIM邻域、Mermaid可选config、ntfy通知、Playwright代码生成均未建立新必需完成路径，具体理由保留。尚无新候选或实验进程；不是穷尽性证明。下一定向入口可查MagicUI过滤和Saleskit工作流与原题的必要联系。
- 36/36 evaluated、180/180 judge完整，runner70532退出0；PDF HTTP27070及报告HTTP66095均已关闭，浏览器已关闭。全部36份逐属性盲审在`9a117d2`冻结提交后才揭示方法/分数。**不要重跑或调参本候选**；Goal仍活动，双重改善未成立。
- A批变化任务候选完成6/6对SP5/6、core均0/6、TF7.4667对9.9333；保持完成均3/3、core候选0对SP1、TF均10。B批候选完成5/6对SP6/6、core均0/6、TF9.8对9.9333；保持完成3/3、core0/3、TF10相等。两批均未通过事前严格双改善门槛；不能用合并后均11/12或PE替代。
- 机制确有行为触发差异：SP4/12变化单元调用故障`list-popular-libraries`，候选0/12；但这4条SP全部自行恢复并正常完成。避免故障不等于完成/质量改善。论文主问题为把相似开源工具错误写成RT-2直接实现、超出来源的能力/历史断言、未执行的DSML写入文本。图表原生值正确，最终文字仍有算术/排序错误或无依据归因。全部原判定/unknown保留；同K0保持差异没有适应因果解释。
- `50dd4f5`事前冻结两批各18条（repeat0–2为A、3–5为B）；`79b3795`冻结六份知识逐字等于试点候选和306源码输入。仅两处Context7说明替换，原生源码/schema/模型/供应商/预算未改。没有因首批不利停止第二批或事后改评分属性。同一协调者盲审，不是独立人工审阅。
- 归档`results/evidence/discovery-contract-validation-20261101/`：1459原始文件、306源码输入，56计划输入/305补充输入hash全核验。376请求（194agent+180judge+2preflight）$0.407556684，未知0，1336.859216秒；确定性更新模型calls/tokens/USD0，ECS不适用。与试点66请求的响应ID无重合。完整原始归档35.4MB、源码归档51.3MB，均低于GitHub单文件限制。
- 两组相同请求（OpenVLA resolver与popular）返回相同，22个重叠PDF页一致且均包含于整文返回；无观察到服务异常。没有完全相同query-docs请求，实时检索并非完全受控，不能声称因果隔离。两次PDF页数组参数错误均恢复。
- 可读报告`reports/discovery-contract-validation.html`，离线复算`python3 results/evidence/discovery-contract-validation-20261101/verify_trial.py`，无需重启模型。报告浏览器检查7表/36行/9证据链接，顶部和底部截图在`output/playwright/discovery-contract-validation/`；仅favicon404，无正文溢出。
- 前置试点`fe9f500`仍保留：6单元仅按较弱开发门槛晋级，273原始/303源码输入文件；不能并入验证、改写为胜利或重跑。旧原生探针也不要重复。
- 下一步寻找**不同且影响必需工作的具体工具知识机制**；先读定向原题/变化投影及必要源码，必要时事前冻结原生合成探针，再决定新候选。不把本轮一般内容幻觉/DSML泄漏改称知识漂移，不给87添加论文答案提示，不重复此候选直到赢。此前失败列表与筛查记录仍适用；未宣称方法空间穷尽。保留原分支所有文件，无push/部署/外发。

### 已归档前置：Context7发现接口缺陷与原生替代已实测

- `890aacb`事前冻结`experiments/context7-discovery-probes-v1.json`与collector、20个源码/配置hash。session25317退出0，8工具调用/3catalog/0模型/0评分、费用0；完整42文件归档在`results/evidence/context7-discovery-probes-20261101/`，`verify_probes.py`离线核验通过。不要重跑。
- Middle/Late新增`list-popular-libraries`均返回`ReferenceError: CONTEXT7_API_BASE_URL is not defined`，且`isError=false`，不能把信封成功当发现成功。原入口未导入所用常量/函数；没有修原生源码。
- 合成Zod查询的三阶段`resolve-library-id`均得到`/colinhacks/zod`，搜索全文相同；接着`query-docs`均返回实际最小字符串长度文档。Middle/Late文档相同，Early最后一段Unicode示例来源不同；原文/diff/时间全部保存，不能声称实时内容完全受控。
- 新`query-docs`可选参数仅在wrapper传递，下游函数只读query/libraryId；这是源码结论，本轮没有额外网络参数对照。共用profile按原包bin加入`@upstash/context7-mcp:dist/index.js`，子进程没有凭据；无修改SDK/服务端/查询端点。
- 新筛查`context-and-swift-screen.json`：Swiftipedia新relationships读取与helper的relatedSymbols/conformsTo不一致，但原题要求示例，旧task430已经SP完成3/3，不重复。其他复核理由保留，不宣称穷尽。
- **下一步**：task87确有文档库发现需要，其原始RT-2 PDF文件已找到；还须复用/核对PDF读取与隔离记忆写入依赖。之后才可冻结具体选择性知识差异、逐项产物质量及6单元开发/独立重复验收。当前尚无新agent候选/日程；本轮只证明机制与替代，Goal活动，双重改善未成立。

### 已归档前置：必需路径源码复核；没有新模型日程

- 上轮native_media_contract六单元仍淘汰，见下节；本轮是有边界的源码/包布局复核，新增记录`results/evidence/mechanism-screening-20261101/post-media-required-path-screen.json`。无新原生工具、agent或judge请求，未改运行时/源码。不是方法空间穷尽证明。
- HeroUI默认docs路径保留；新增wrapper的数组下标对齐风险尚无真实响应证据，task378还缺当前React源码。Flowbite新显式样式控制未发现必需操作阻塞，Figma新工具不在原题要求内。fetch旧raw→response_format迁移保留GET/auto；filesystem范围/排序默认兼容；commands新增忽略的资源/环境参数暂无原题必需依赖。不要用可选能力代替完成率机制。
- Agentic新增bulk-create.js是孤立文件，server.js没有import/注册；不能把它当原生可用批量接口或修改注册后声称知识策略改善。不要据此重跑283。
- Orchestrator prompt确实被当一个文件路径，excludePaths/severity也被塞进文件数组；原run_sequence接受具体params。但三阶段相同shared客户端ESM fallback查找node_modules/node_modules/@j0kz/...，实际该位置不存在；smart-reviewer在正常平铺位置，security-scanner/test-generator/architecture-analyzer/doc-generator均未随归档提供。共享pipeline还会把单步success:false包装为外层success:true。已保存具体源码hash/存在性；尚无原生调用证明/有效替代。
- 此处环境障碍不是新知识策略的胜利。若未来检查对称的依赖布局，应单独冻结并保持原生源码，不能修上游代码、伪造子工具成功或直接展开模型对照。当前没有需要等待的实验进程；Goal活动、目标未完成，继续寻找与原题必需工作相关的新机制。

### 已结束的上一轮：native_media_contract 六单元开发未晋级

- session37884退出0，6/6 evaluated、30/30 judge。全部六份盲审在`9c50dc2`冻结后才揭示方法/分数。**不要重跑此候选，不进入36条独立验证**；Goal仍活动，双重改善未成立。
- 新机制：Middle/Late图标style筛选读取helper已移除字段，导致假空；Late PlantUML保存引用块外response，报not defined。8次图标+10次依赖/URL替代原生调用、10catalog、模型费0；`69badd6`与`9d09faa`完整归档。依赖Early/Middle保存PNG并视觉检查，Late单独冻结URL替代成功。不要重复探针。
- `056b00c`事前冻结策略/验收，`15fd01c`实现，`53d0b58`模型前冻结全部知识、盲审映射、54计划输入/120额外路径/121源码输入文件。Middle2规则、Late3规则，其他字段逐字等于原SP，235精确K0；无任务事实/通用预算或原生修补。5新测试先红后绿，57相关及379离线测试通过（13integration排除）。
- 任务57两组正常完成均2/2，完整产物通过均0/2；候选TF10/PE7.2，SP9.1/6.2。**四条都没传style或output_path，目标故障没有在agent中触发**。SP Late一次图表语法错自行恢复；候选13工具调用对SP18，不是完成率改善证据。
- 四个生成图像URL按冻结协议事后只取一次，均HTTP403；图像可读性unknown，不计pass，也不等于原生生成失败；没有换客户端/重试/改URL或重画图回填。SP Middle示例缺状态变量/导入且图像Markdown漏右括号；候选Late错报11种样式（实际10种）；其他Card示例正确。全部原判定及限制保留。
- 235均完成1/1、core0/1、PE10；候选TF9.4对SP10。两份图表数值均正确，摘要遗漏月度下降；知识同K0，不作适应因果解释。候选同时未满足保持TF门槛。
- 报告`reports/native-media-contract-pilot.html`；离线`python3 results/evidence/native-media-contract-pilot-20261101/verify_trial.py`。257原始文件、121源码文件与全部冻结hash已核验；52请求（20agent+30judge+2preflight）$0.049647696，未知0，188.31851秒；更新模型calls/tokens/USD0，ECS不适用。当前无本轮模型/MCP进程。
- 后续只读筛查已保存`results/evidence/mechanism-screening-20261101/post-media-source-screen.json`与`required-tool-registration-screen.json`。注册名正则只找到已实测task90旧每日题删除；会漏掉Swiftipedia条件过滤，不能称穷尽。复用了原task430/90报告，没有重跑。VoltAgent入口完整diff未建立新必需阻塞机制，没有新增原生/模型日程。
- 下一步找**必需工作**的不同机制，优先检查工具删除/重命名及必要语义迁移；不要继续改此候选或重复task57到赢。图像证据路径需要未来独立合成验证，不能回填本轮unknown。Context7/Swiftipedia/HeroUI等尚未完整审完，筛选不穷尽。保留原分支所有文件，无push/部署/外发消息。

### 已归档前置：图标样式过滤缺陷和原生替代接口已复现

- `8f018f9`事前冻结合成query=calendar/style=stroke-rounded、8调用+3catalog；全部执行结束，模型/评分请求0、费用0。三阶段默认搜索均返回完全相同66项；Middle/Late加style均为空；三阶段对首项名称的get_icon_glyph_by_style均返回相同有效字形。
- 原生search helper只投影id/name/tags/category/featured/version；新增style筛选读取不存在style/variant/stroke，造成假空。只证明这一固定合成查询的过滤缺陷与原生替代路径，不证明agent收益。原task57没有明确样式要求，策略触发率/完成率空间仍未知。
- 证据`results/evidence/icon-style-filter-probes-20261101/`，离线`verify_probes.py`核验源码、协议、全部返回和归档；不要重跑8次探针。共用hugeicons入口build/index.js对应原包bin，未改工具实现/schema。
- 下一步先单独冻结并验证task57依赖Ant Design文档和PlantUML生成路径可用，再决定固定规模的策略对照；知识仅限过滤语义及已有字形接口，不含题目答案/通用预算规则。当前没有模型进程，Goal继续，双重改善尚未成立。

### 已结束的上一轮：新增源码筛查完成；城市/车站过滤探测在原生启动处停止

- 上一轮contract_reconcile已淘汰（下节），本轮没有agent/judge请求。新筛查记录`results/evidence/mechanism-screening-20261101/post-reconciliation-source-screen.json`含20组有边界的判断；不是穷尽性证明。PDF、QR、图书/Maven、Remotion、思考工具、新闻、博客、LeetCode、游戏卡、SwiftUI、Meme、HeroUI、Clojars、OpenTofu、whois、memory、12306及Pollinations均保留具体理由和未审范围。
- 补查非JS运行时源码/资源：`non-js-runtime-change-index-v2.json`覆盖224个包/阶段行，在明确筛选范围内没有新增程序/模板差异。首次v1哈希扫描误纳入包自带data/memory JSON，只计算hash、未解析或展示内容；v2明确排除data/memory/log/cache，重新统计文件数量。1301项跨阶段状态文件差异不是工具实现变化，不能当作新机制。两个索引均保留。
- 新假设：12306的城市代表码可能对应多个实际发到站；新增directOnly/stationExactMatch按原始车站码相等过滤，可能删掉有效城市间直达高铁。源码依据明确，但真实服务的城市展开/丢失行为尚未验证。`95de81f`冻结天津→济南、Early日期+3天、默认/精确过滤，最多11工具调用+3catalog，禁止换日期/路线或失败重试；没有基准路线/答案进入probe。
- 首次在本地profile守卫处停止，0工具/0catalog/0原生启动。`fc08638`按包bin补上共用`12306-mcp: build/index.js`入口，并事前冻结v2原封不动的未执行日程；未改原生源码/SDK/行为或给子进程凭据。
- v2 session14722已退出0；Early原生Node进程在顶层await getLCQueryPath()时退出，stderr为`Error: get station name js file failed.`，源码的`var lc_search_url`网页正则未匹配。按冻结规则停止所有余下调用：仍是0工具/0catalog/0模型请求，不能称过滤机制已复现。不要在外部状态不变时重试或启动agent对照；不能把修改原生初始化实现冒充知识策略改善。
- 完整失败、协议和9个原生源码文件归档于`results/evidence/city-station-filter-probes-v2-20261101/`（23文件）；离线复核`python3 results/evidence/city-station-filter-probes-v2-20261101/verify_probes.py`，只证明归档/启动失败，不证明过滤行为或有效性。首次profile失败在`results/evidence/city-station-filter-probes-20261101/`保留。共用入口配置有效，当前没有运行中的本轮进程。
- 下一步仍需不同且可检验的必需工作机制。未全面审完的部分包括Context7打包入口、Swiftipedia完整API调用、HeroUI/图标类接口；不必自动展开全矩阵。OpenTofu compact函数作用域错误是源码推断，但相关原题要求部署/公开发布，当前授权不覆盖；不以删掉发布步骤来降低任务门槛。Goal仍活动，未达到双重改善，不能以多次负结果或本次服务不可用宣称整体完成/穷尽。

### 已结束的上一轮：contract_reconcile 六单元开发已淘汰

- session88871退出0，6/6 evaluated、30/30 judge；六份盲化质量审阅在`738ac3f`提交后才揭示方法/分数。**不要重启此候选，不进入36条独立验证**。Goal仍活动，未找到可复现的完成率与任务质量双重改善。
- 新干预与旧observed_contract不同：不在矛盾描述后追加观察，而是直接替换已证伪的工具/参数说明。Middle3处、Late6处，只涉及math-mcp::validate_syntax；所有类型/必填/默认/范围/路由/输出schema/已有规则/无关工具保留SP。235精确K0。复用旧16次合成probe与处理器源码，21个probe清单项及3个源码hash已核验，没有重跑探测。
- `5c79cae`冻结方案/验收，`56d7f16`实现；9个新增测试先红后绿，52项策略相关、374项离线测试通过（13 integration排除）。专用候选校验器按精确说明白名单验证，原SP校验器未放宽。源字段/原生行为/模型/供应商/预算/原评分未改。
- **流程偏差：**补充审计误将235的Early K0按Late封套校验而断言失败，shell未设set-e，后续review/run仍执行。原plan、53个输入hash及knowledge-lock在请求前已固定；补充审计、盲号映射及额外源码冻结晚于启动。`45cacfc`完整披露并核清：候选实际符合冻结3/6处差异，所有输入未改，补充审计时尚未读取模型结果或分数。不得把补充冻结写成事前完成，不重跑替换本次试点；以后依赖步骤必须set-e。
- 133变化任务：两组正常完成均0/2、全项质量均0/2、TF均9.7；候选PE9.2对SP5.9。候选合计4轮/10调用对SP12轮/40调用，但四条最终响应全部4096tokens/finish_reason=length。候选输出更长且仍含真实缺陷，减少调用/提高PE不能算双重改善。
- SP Late/R01的drop-in类缺少_eval且答复止于bare raise；SP Middle/R06止于except SyntaxError as。候选Late/R02错误推荐**转^后交给不允许BitXor的Python AST；Middle/R05声明1e300上限却只检查float，允许的整数嵌套乘方可越界，future.cancel也不终止运行中子任务。仅静态检查，没有执行生成代码。逐属性结果均保留。
- 235两组完成/TF/PE均1/1、10、10；候选R04全项通过，SP R03摘要遗漏二月下降且电子产品占比比较错误。相同K0的差异没有适应因果解释，也不补偿变化任务无改善。
- 报告`reports/contract-reconcile-pilot.html`；离线复核`python3 results/evidence/contract-reconcile-pilot-20261101/verify_trial.py`。257原始文件、106选定源码/输入文件归档，53计划输入及补充输入全匹配；盲化投影逐字对应原轨迹。52请求（20agent+30judge+2preflight）$0.061722108、未知0、167.390044秒；更新模型calls/tokens/USD均0，ECS不适用。执行已结束，没有遗留本轮MCP进程。
- 新源码筛选`results/evidence/mechanism-screening-20261101/post-weather-source-screen.json`：parse_prd是未变的旧能力，描述截500字符、扁平创建并清空依赖，不能作为可靠的新批量契约。该结论仅源码检查，无新原生调用。
- 下一步寻找**不同的必需工作阻塞机制**；不要继续改写本候选说明、重复暴露的133子集或追加旧通用预算/省略代码规则。已有证据表明修正此契约可减少探索，但没有解决输出截断和代码一致性。尚未登记新agent日程；不得因负结果反复而宣称整个方法空间穷尽或Goal完成。

### 已结束的上一轮：weather_provenance 六单元开发未晋级

- session18267退出0；6/6 evaluated、30/30 judge。六份盲化属性审阅在`cc702c4`冻结后才揭示方法/分数。**不要重启本候选，不进入36条独立验证**；Goal仍活动，未得到可复现双重改善。
- 新机制：Middle/Late新增天气建议用纬度公式生成“体感温度”，没有天气/时间来源。`99f185f`冻结7次原生调用+3catalog，`61f282c`归档；两个合成经度返回相同26°C，三阶段真实NWS预报均可用且14时段逐字一致。模型费用0。离线复核`results/evidence/weather-provenance-probes-20261101/verify_probes.py`；不要重跑这些probe。
- `7008795`事前冻结任务26 Middle/Late＋235 Late、仅2条来源/替代工具知识和全部验收；`4e54a66`实现，43策略/365离线测试通过（13integration排除）；`6cf1341`执行前冻结。未改工具、schema、模型、供应商、单次预算或原评分；没有通用预算规则或任务天气事实进入updater。
- 26变化任务正常完成两组均2/2；候选全项质量1/2、SP0/2；TF均10，PE候选7.7/SP8.0。候选天气依据属性2/2、SP0/2：SP都采用了纬度生成的约66°F体感温度。四条均真实保存项目/装备任务。候选Late仍虚称周三日期已设入项目，实际无dueDate；Middle全项通过。**局部质量提高不是完成率提高。**
- 235两组完成1/1、图表数据正确、TF/PE均10；候选摘要称二月后持续加速，忽略八月下降，全项0/1对SP1/1。两组精确K0，该差异没有适应因果解释，但仍按冻结保持门槛计入，因此不晋级。
- 四条预报分别请求7/8/10/10个昼夜时段；所有重叠时段逐字相同且均成功，长度差异来自agent参数选择。没有观察到动态来源差异造成的对照混淆。全部原始文本、时间与hash保留。
- 可读报告`reports/weather-provenance-pilot.html`；离线复核`python3 results/evidence/weather-provenance-pilot-20261101/verify_trial.py`。261原始文件、203选定源码/输入文件、52计划输入、152额外路径核验。59请求（27agent+30judge+2preflight）$0.046529376、未知0，135.199秒；更新calls/tokens/USD均0，ECS不适用。没有运行中的实验/原生服务。
- 本轮源码筛选记录`results/evidence/mechanism-screening-20261101/post-thinking-source-screen.json`。工作流prompt错作文件路径、黄历Late函数作用域等仍是源码推断，未证明任务内替代路径；不能写成已复现的agent因果机制。筛选不穷尽所有工具，未读取参考答案/完整历史/全量旧轨迹/密钥。
- 下一步：另找**影响必需工作完成**的不同机制，先做有针对性的源码/本地证据检查再冻结方案。本次两组正常完成已100%，不要重复本候选换样本直到赢。字段未持久化/长度拒绝是新观察，但不能直接假定它们造成完成失败；不要据此马上增加通用提醒或继续同候选。当前无已登记的新agent日程。

### 已结束的上一轮：thinking_contract 四单元开发已淘汰

- session36385退出0，4/4 evaluated、20/20 judge齐全；全部质量属性审阅在b049456冻结后才揭示方法/分数。**不要重启本候选，不进入24条独立验证**；Goal继续，仍未得到可复现双重改善。
- 29Late 两组完成与全项质量均1/1，候选TF8/PE8.4对SP9/PE5。候选用4次只读命令，不调用思考工具；SP首个sequentialthinking调用报missing-method后，自行用一次真实CSV读取完成。两组都正确预览并识别缺少购买数据，没有编造消费额。避免一次工具错误没有带来完成/质量提高。
- 235两组完成与全项质量1/1，TF/PE10，知识精确K0。评分器部分把未计算消费额当缺陷，部分认定“先规划和预览”已完成；原TF候选9/6/5/10/10、SP5/10/10/10/10均保留，不能据此换协议或再抽样。
- 报告`reports/thinking-contract-pilot.html`；离线复核`python3 results/evidence/thinking-contract-pilot-20261101/verify_trial.py`。187原始文件、152源码文件、53计划输入、30额外冻结文件及CSV未改均核验。32请求（10agent+20judge+2preflight）$0.024899796、未知0，75.674秒；更新模型calls/tokens/USD均0；ECS不适用。
- 预注册cfa4d6b，c7f499f仅修正反馈文件名冲突并逐字恢复原probe协议；ea35e07实现，12c04b6执行前冻结。39策略/361离线测试通过（13integration排除）。仅追加3条知识规则、无任务事实或通用预算指令、没有修工具/放宽原生输出schema。所有MCP进程已退出。
- 下一步应离开这个已能自行恢复的可选思考工具路径，寻找**直接阻碍必需产物的不同变化机制**，先核实任务可用性与实际失败，再冻结新方案。不要把PE提高、减少错误或简单任务完成率的上限当双重改善；不要因本次无提升就重复同候选换样本直到赢。当前没有已登记的新agent日程。

### 已归档的新机制探测：原生思考工具契约

- 在3ccebd3/v1、8b49b7a/仅余Late续接、f2adb7b/v2预注册，共19工具调用+8catalog、模型费0；所有正负结果和首次采集中断日志在3ba9471归档。不要重跑。
- Late sequentialthinking 新增调用不存在的getThoughtHistory；Middle/Late parallel-thinking 在readyForSynthesis=true返回额外字段pathsSummary/synthesisReady，触发原生输出schema拒绝；Late convergent-synthesis始终返回未声明synthesisData，也会照抄不存在来源的输入结论。
- 已实测单路径totalPaths=1，终态pathStatus=completed、readyForSynthesis=false能正常返回并从activePaths移除。仅关闭记录路径，不证明外部工作完成。三阶段原run_process均可逐字读取原始客户CSV预览；新增共享command profile已核实。
- 离线复核`python3 results/evidence/thinking-contract-probes-v2-20261101/verify_probes.py`；79文件归档含源码和日志。仅采集器保存原始响应后继续原生校验，未改工具/SDK。v1 Middle最后调用响应仅在异常日志；已执行调用没有重跑，余六个Late调用在新进程续接。

### 已结束的上一轮：project_state_contract 四单元开发已淘汰

- session31424 正常退出，4/4 evaluated、20/20 judge。四份盲化产物审阅在 `1f71f01` 冻结后才揭示方法和评分。**不要重启本候选，不进入 24 条独立验证**；Goal仍活动。
- 283Late 两组正常完成均0/1、质量全项均0/1、TF均9.8；候选PE9.0对SP8.2。候选25个有效任务记录，第11轮4096输出tokens全计reasoning而截断；SP50个有效记录，第12轮仍在创建子任务而耗尽轮数。两组最终答复为空，交付属性unknown，不算完整质量通过。
- 235两组完成、TF/PE10，图表数据正确但摘要错误，全项0/1；知识均精确K0，不对文字差异作适应因果解释。候选只改3条规则的机制/公平条件与原验收保持不变。
- 报告 `reports/project-state-pilot.html`；离线核验 `python3 results/evidence/project-state-pilot-20261101/verify_trial.py`。181原始文件、141源码文件、52计划输入及20额外冻结文件均核验。49请求（27agent+20judge+2preflight）$0.092103372、未知0，220.413秒；更新模型calls/tokens/USD均0；ECS不适用。
- 两组首轮都调用另一新增工具 review_workspace_health，报 `memoryStorage.listMemories is not a function`，本候选未覆盖它。此处只有实际错误观察，**不能直接假定再补一条规则就改善，也不能把截断包装成知识漂移**。下一步先筛查不同任务/工具的具体可修复机制；若研究workspace工具，须本地冻结探测并证明与目标要求相关，再决定新实验，不能直接重复此候选。
- 原预注册9ca6064、实现04cd085、执行前冻结0e7a9c4；358离线测试通过。所有MCP进程已退出，无需PDF/渲染服务。原course/NU/FR/所有负结果保留，无push/部署/TA消息。

### 已完成的前置探测：层级/项目状态机制

- document_sequence 已在`be1ce54`完整归档并淘汰（下节）。之后仅做源码/目录筛选与合成工具探测，**没有新 agent/judge 请求**，Goal仍活动。排除日志28/Excel305/财务等未证明机制候选；筛选索引`results/evidence/mechanism-screening-20261101/`，没有读参考答案或全量旧轨迹。
- 新探测在`cd50478`预注册v1：发现bulk_create_tasks虽有新增源码但没有注册到实际catalog；仅1次create_project后采集脚本停止。原文件/失败全部保留。**不能再以这个未注册bulk作为变化工具依据。**
- `da268fc`冻结v2，用实际create_task建立合成父+2子，共29调用（Middle14、Late15）+2catalog。Late第11次真实调用发现新`review_project_status`报`storage.getTasksByProject is not a function`；采集断言停止。`87ce944`事前冻结仅余4调用的续接，新MCP进程执行尾段，未重跑已完成调用；须披露非连续session。合计本地30调用+3catalog、模型费用0。
- 已复现：持久化3个有效ID，默认层级列表把子任务重复为根，显示5条；`list_tasks(showHierarchy=false)`且省略parentId返回3个唯一ID，但标题错误地称top level。父复杂度得分在真实子任务拆分前后均9，两个子任务各3；父字段完全未改，分析器不考虑子任务覆盖。
- 自动拆分缺陷：autoCreateSubtasks先写3条legacy记录，ID全为空；下一次list会自动迁移，仍保留空ID。重复后共9条，6个空ID、3个模板名称各重复2次。还在stdout发非JSON迁移日志（已保存）。不能把它当可靠的任务分解/难度验证，不能静默修数据。此行为为继承限制，新增漂移是Late的broken status工具。
- 完整证据`results/evidence/hierarchy-contract-probes-v2-20261101/mechanism-review.json`与`state-checks.json`；99文件归档含所有源码/原结果/失败日志。离线复核：`python3 results/evidence/hierarchy-contract-probes-v2-20261101/verify_probes.py`。**不要重跑这些probe**。所有MCP进程均已退出。
- 下一步：先冻结不同候选。可围绕实际新增Late `review_project_status`及有直接共享任务依赖的list/analysis工具，提供已实测的flat读取替代、记录级复杂度含义、自动拆分写坏ID的边界与真实create_task+parentId路径。不能添加通用预算指令、任务答案、跳过真实叶任务难度检查或降低字段来消警。Middle没有这个新增状态工具，不应假称同一机制适用两阶段。建议先定向task283 Late（已有真实产物覆盖但常无最终答复）+235保持，重新事前冻结具体开发/独立重复日程与沿用的实际质量规则，再实施；尚无新updater或新模型实验。

### 已结束的上一轮：document_sequence 开发对照已淘汰

- 六单元日程正常退出，session61462结束；30评分齐全。6份逐属性审阅/全部3页渲染在`5b1538b`冻结后才揭示方法。**不要重启本候选或追加抽样**。PDF/两个渲染服务及浏览器均已关闭。
- 457变化任务：候选正常完成0/2，对SP1/2；完整产物两组均0/2。候选TF4.6/PE7.6，SP TF1.8/PE6.6。235两组完成1/1、TF/PE10，摘要均错、全项0/1。开发门槛失败，不进入36条验证；Goal仍活动。
- 候选Middle只有封面：最后15,469字符DSML式set_page文本并非真正调用，在4096tokens截断，TF却7.8。候选Late及SP Late末轮4096tokens全被计为reasoning。SP Middle虽然runner completed，但只有DSML正文、零实际调用；保留冻结完成定义，不能当成功交付。SP Late留下空白页+白底标题页。没有修改产物或再试模型。
- 协议`experiments/document-sequence-v1.json`，2dd0efb预注册、03a2574实现/355离线测试、7df0b69执行前冻结。仅4条直接依赖工具规则，235精确K0。55计划输入与11额外文件hash均保持一致。
- 可读报告`reports/document-sequence-pilot.html`；离线复算`python3 results/evidence/document-sequence-pilot-20261101/verify_trial.py`。284原始文件、138源码文件、全部原分数/产物/失败均归档；56请求（24agent+30judge+2preflight），$0.070742700，未知0；更新模型calls/tokens/USD均0。ECS不适用于本局部日程。
- 下一步应离开已失败的长文档生成路径，定位其他变化工具的可复现接口/行为缺口。DSML泄漏、截断、算术错误属于执行/一般生成问题，不能未经证据包装成知识漂移；不改变模型、供应商、预算或评分，不重复已淘汰候选。先读定向任务/变化投影与必要源码，冻结新的本地probe，再决定是否有新策略。未加载完整历史或密钥。

### 已完成的前置机制探测：文档写入顺序

- 下节artifact_contract已淘汰，不能重跑。随后仅做新的本地序列化探测：`experiments/slidev-document-write-probes-v1.json`在`4cdb2c3`冻结24调用；其后按源码定位的丢页原因，在`9eb8b38`冻结v2的14调用。共38本地工具调用+4catalog、模型费0，两个正负路径全部保留。
- 已证明：`set_page`会自动添加页frontmatter；把完整文档头放进content会制造空页。多页正文可以一次写入文件，但它暂时仍是内存中的单个记录；**紧接apply_theme会把后续页丢掉**，因为`updateSlideFrontmatter`仅保留split的parts[1]。
- 正确的已实测路径仅限新建单封面项目：set_page(0, first-page正文+后续页显式frontmatter/正文) → **load_slidev拆分记录** → apply_theme(dark)。Middle/Late均得到恰好3页、3个canary各一次、根主题dark；再次load文件字节不变。两阶段最终文件hash一致，真实渲染3页均正确/深色/可读。
- 可复核证据：`results/evidence/slidev-document-write-probes-v2-20261101/mechanism-review.json`、`state-checks.json`、`render-dom.json`、3截图与`probe-and-source.tar.gz`；v1负路径在`results/evidence/slidev-document-write-probes-20261101/`。归档hash已核验。**不要重跑这些probe**。
- 下一步：基于这一具体写入/重载/主题顺序，先冻结不同的新候选及知识差异，再做一次6条开发对照。建议仍用457Middle/Late与235Late、同模型供应商/预算/5judge、同产物质量门槛；不能用合成3页成功冒充真实15分钟演示成功。知识只含工具行为和合成格式，不含论文事实。还未实现新updater、未启动新agent实验，Goal未完成。
- 适用边界：只验证新项目及短3页Markdown；不保证清除既有其他页、任意HTML/长文档，不能声称writer行为是新增漂移。可将其作为变化bulk能力需要真实内容时的受影响写入路径，但必须明确这是继承限制/跨工具依赖。

### 已结束的上一轮：artifact_contract 开发对照淘汰，Goal继续

- 当前六条批次已正常结束，session48967退出0；30次评分齐全，PDF服务与渲染服务已关闭。**不要重启本候选或按旧运行中记录续跑**。6份盲化审阅在`554e7b4`冻结后才揭示方法/TF/PE。
- task457变化任务：正常完成两组均0/2；必需产物全项均0/2。原SP TF4.0/PE6.6，候选TF2.0/PE6.0。235两组均完成/TF10/PE10，但摘要均有事实错误，全项均0/1。开发门槛失败，不进入36条验证。
- 候选两条只留下封面；三条截断轨迹（候选2+SP Late）最后4096输出tokens均被供应商计为reasoning，无工具调用或正文。SP Middle耗尽12轮，只有部分正文并出现嵌套frontmatter/白底浅字。不要把这些普通生成/文档格式问题都叫知识漂移。
- 可读报告`reports/artifact-contract-pilot.html`；独立离线复核`python3 results/evidence/artifact-contract-runtime-pilot-20261031/verify_trial.py`。691原始文件、135源码文件、25页真实渲染证据、55冻结输入和9额外运行环境输入均核验。证据/原分数/全部失败均保留。
- 本批71次请求（39agent+30judge+2preflight），$0.087692292，未知0；更新模型调用/tokens/USD均0。中止基础设施批另$0.040542072+1笔未知；总已知$0.128234364+1笔未知，不把预留额当实付。ECS仍不适用于局部日程；NU/FR/课程主证据保留不混池。
- 下一步仅考察新、可验证的文档写入路径：已看到set_page自动包装frontmatter且覆盖第0项时丢失根主题；将其content当完整文件会制造空白页。要先用独立合成内容验证**多页Markdown正文能否一次持久化、在load往返后保持，并用apply_theme恢复根主题**，再考虑是否形成不同的选择性知识机制。不能通过改预算、读答案或重复抽样宣称改善。

### 上一检查点：共用环境修正与运行期记录（已由上述完成状态取代）

- 在`0d49e0a`先冻结新策略机制、五项实际产物质量检查、开发门槛和两批独立验证规则。`artifact_contract`仅向变化的`create_bulk_slides`加入一条经合成probe核实的持久化效果/精确内容写入知识；无任务事实/答案/预算指令。352离线测试通过，13integration排除。
- 新任务457必须读取三份原始PDF并生成有事实内容的15分钟dark Slidev deck；保持任务235。独立验证仍要求每批完成数与完整产物通过数均严格高于SP、TF不降，且235保持不降；不是只改善工具调用或主题参数。
- 共用环境在模型前修复：固定原生canvas依赖；PDF本地路径分支传Buffer导致错误，因此三份逐字相同的原始PDF经只读`127.0.0.1:4783`URL供应，两组获同一文件清单。3阶段均成功读取3篇的1–3页，失败启动/本地路径尝试也归档。原生代码、上游工具未改。
- 共用渲染器固定Slidev53.0.0、默认主题0.25.0；本地dark主题导入默认基础排版与发布工具原有dark CSS。未经改写的合成deck真实呈现dark/default差异与内容canary；同一非致命FloatingVue错误记录保留。不能宣称任意产物已通过或官方独立部署兼容。证据`results/evidence/slidev-readiness-20261031/`。
- 第一份build在任何模型请求前因read_pdf旧式exclusiveMinimum布尔schema失败，原目录`results/raw/artifact-contract-pilot-20261031`保留。`fd12f0c`加入针对该已核实位置的两组共用等价格式转换，记录原/新值，不改变接受页码集合。新协议`experiments/artifact-contract-ready-v1.json`只增加环境说明，策略/质量门槛不变。
- 第一次模型批次因原始`check_environment`未在PATH找到本地CLI而尝试全局npm安装，已安全中止session7284：2条已评分、第三条执行已落盘而评分未完；已知$0.040542072+1笔未知费用（预留$0.319488不能当实付）。全局npm现报告CLI53.0.0；没有运行前清单，不能完全重建主机副作用，未卸载或回滚用户全局包。711原始文件归档`aborted-attempts.tar.gz`，5390依赖缓存文件本机原样保留并列hash；不据此判定候选/合并为正式样本。
- 在`74b22ca`固定共用PATH：Node24.13.0与本地CLI53.0.0优先，npm prefix/cache进一步限制在每个workspace。三个阶段各一次原始check_environment均成功返回53.0.0，未创建npm安装缓存。新协议`experiments/artifact-contract-runtime-v1.json`仅补基础环境；**6份知识与中止批逐字相同，原质量门槛不变**，不是调参或重复直到赢。
- **当前执行目录**：`results/raw/artifact-contract-pilot-runtime-20261031`；证据目录：`results/evidence/artifact-contract-runtime-pilot-20261031`。主执行session48967、PDF只读服务session10459，日志`run.log`。先查现有进程/experiment.json，**不要启动第二份或重跑已完成cell**。
- 用`collect_blind.py`采集本轮已完成的匿名答案/调用和实际slides.md/theme.css。属性审阅存`blind-reviews/`，在全部冻结前不揭示方法/TF/PE；同一协调者不等于独立人类审阅。必须渲染真实deck检查全部页面，不能按schema或文件存在代替设计质量。
- 原负结果全部保留；Goal仍活动。开发结束按事前门槛判定是否进入两批共36条独立验证，失败则淘汰，不能重复直到赢。

### 上一个检查点：Slidev持久化产物机制已实测，候选agent尚未启动时的记录

- 观测契约36条验证已完整关闭，负结果本地提交`613a0d1`；下节保留全部结论。Goal仍活动，不算完成。
- 随后仅做离线机制筛选。任务管理器必填/长度约束已完整反映在公开schema，图谱新遍历工具也未证明接口错误，未据此重复跑模型。任务244缺少月度趋势数值且无明确新故障，未选择。使用现有`benchmark-inventory.json`中的question/server投影，未读取新任务的参考答案/评分/轨迹。
- 在`8ca1ece`先冻结`experiments/slidev-artifact-probes-v1.json`，之后完成Middle/Late各2个合成案例、共36个本地MCP调用+2次catalog，模型费0，无外网工具、导出、渲染、部署或上游修改。
- 已确认：初始2页，bulk声称生成6页，实际持久化变7页；同参数再调用变12页，旧页始终保留。Late显式`clearExistingSlides=true`也未清空，因为handler修改`getSlidevContent()`返回的副本。`customInstructions`中的独立内容canary始终没有进入文件；`set_page`则准确保存指定内容。默认bulk覆盖封面会将dark重置default，`preserveCover=true`保留dark。
- 证据：`results/evidence/slidev-artifact-probes-20261031/mechanism-review.json`、逐调用返回/每次文件快照、源码与`probe-and-source.tar.gz`；清单已校验。**区分新增与继承**：Late清空控制是新增承诺；忽略customInstructions/只生成主题模板是继承限制，不能假称都是环境变化新引入。
- 下一步明确：以原task457（真实PDF→有事实内容的dark Slidev deck）为候选机制适用范围，先验证其`@sylphlab/pdf-reader-mcp`与三份PDF路径在隔离环境可用；其后冻结精确的产物后置条件知识规则、所需属性和开发/两批独立验证验收，保留235。策略方向是向变化的bulk工具补充**真实持久化效果与可证实的逐页内容写入路径**，不再追加泛用预算/少做工作规则。尚未实现策略、没有agent或judge请求，不能声称改善。不要重跑已完成probe。

### 已结束的上一轮：观测契约36条独立验证，候选淘汰（2026-10-31）

- 原session28325已正常退出，36/36新轨迹、180/180原协议评分全部完成。**不要恢复该session或重跑这组候选。** 当前Goal继续活动，仍未找到可复现双重改善。
- 36份匿名属性审阅全部在本地提交`c30aec3`冻结后才揭示方法/TF/PE。变化任务133：候选正常完成**5/12**，原SP**8/12**；必需产物全项通过两组均**0/12**。候选工具解释通过9/12对2/12，但Python产物错误/截断仍在，不能以局部进步冒充目标成功。
- A批变化完成3/6对4/6，TF9.2对9.4667；B批2/6对4/6，TF9.6对9.8667；每批全项通过均0/6。235保持任务均6/6完成、TF10，候选全项2/6对SP3/6；两组精确K0，差异不能归因于适应。两个批次按事前规则均失败。
- 可读入口：[`observed-contract-validation.html`](reports/observed-contract-validation.html)。离线复算：`python3 results/evidence/observed-contract-validation-20261031/verify_validation.py`。1367个原始文件、42个源码/配置文件、知识与输入hash、280次请求费用、全部逐属性证据都已归档。6份共享适应与pilot知识逐字一致、52个冻结输入匹配；供应商固定DigitalOcean，没有fallback。
- 验证费用$0.352885824，未知0；加开发试验共$0.412739556。验证98次agent、180次judge、2次预检；更新模型调用/tokens/USD均0。原始评分未修改，ECS仍不适用于局部日程。课程27条/PDF/Slides及历史NU/FR/ECS保留。
- 下一步先离线寻找**不同的选择性知识机制**：优先检查尚未验证的变化工具契约是否直接阻碍任务必需产物；区分知识遗漏与一般代码生成/截断。没有新机制证据前不展开模型实验、不重跑本轮、不放宽产物验收。先读本报告和必要的元数据diff，不读全部历史轨迹或密钥。
- 下列开发/运行中记录是保留的历史检查点；最新状态以本节为准，旧`continuation.json`/review17快照不表示当前仍有实验进程。

### 接手后历史进展：观测契约机制与开发试验（2026-10-31）

- 已按新版Goal继续，当前活动Goal仍未完成。平台不允许覆盖未完成objective，未把旧/新目标伪标完成。仍使用现有研究分支，无push/部署/TA消息。
- 排除了把283 Middle的UUID抄写/层级重复计数当成知识变更；创建任务/复杂度API没有相应变化。新机制是133校验参数的承诺与实际响应不一致，以及旧probe_note丢弃isError=false的实际文本。
- 16次独立安全语法探测确认变量禁用、深度限制和AST输出参数没有对应效果，语法错误也能返回isError=false。源码handler仅读取expression。新`observed_contract`仅在已变化的validate_syntax追加输入/响应原文，不加预算或通用少做任务规则；其余元数据保持原SP，235精确K0。
- 协议在实现/agent前冻结：`experiments/observed-contract-v1.json`。6条开发对照、30评分已完成并归档：候选/原SP变化任务正常完成1/2对0/2，TF9.6对8.5；校验解释通过2/2对0/2；**必需产物全项通过均0/2**（Python实现仍有错误）。235均正常结束/TF10，摘要各有事实错误。不是双重改善结论。
- 可读入口：[`observed-contract-pilot.html`](reports/observed-contract-pilot.html)。原始256文件、源码41文件、盲化输入/先冻结属性审阅、独立复算见`results/evidence/observed-contract-pilot-20261031/`。52模型请求共$0.059853732，未知0；16本地probe零模型费。344离线测试通过/13integration排除。源码f892cad。
- 通过原先较弱的进入验证门槛。下一步是已登记的两个独立批次、每条件每批3次，共36条：`experiments/observed-contract-validation-v1.json`，输出`results/raw/observed-contract-validation-20261031`。候选知识须与pilot哈希完全相同；**每批都必须正常完成数和产物全项通过数严格高于SP、TF不下降，并保持235能力**。不得根据结果修改候选/验收或重复直到赢。科学split为independent_validation；CLI的development字段仅承载日程，避开旧108格PE晋级逻辑。
- **独立验证已启动**：36条日程及两组知识均在执行前核验；6份知识与pilot逐字相同，配置仅ledger路径变化。运行状态/续接信息见`results/evidence/observed-contract-validation-20261031/continuation.json`，原始输出`results/raw/observed-contract-validation-20261031/`。先查现有进程/experiment.json，不启动第二份或重跑已完成cell；验证结束后还需盲化属性审阅、独立复算与两批判定。
- **验证审阅检查点**：原session28325已再次确认存活；20条以上执行已落盘，17份盲化属性审阅已冻结且输入hash/冻结属性键核对通过。`results/evidence/observed-contract-validation-20261031/progress-20261031-review17.json`记录此时状态；运行`collect_blind.py`获得待审阅ID，`verify_blind_reviews.py --require-complete`只在36份全部完成后使用。方法映射与TF/PE尚未揭示，不能提前晋级。
- 盲化隐藏方法/分数，但由同一协调者审阅、可从答案推知方法，非独立审阅者；独立性来自冻结方法后的新执行。原27条课程/NU/FR/ECS与全部旧阴性保留。生成代码仅静态检查，未执行。

### 执行解释与接手前历史断点（已由上方当前断点推进）

- **验收先冻结：**正常完成与 TF 分开；质量检查只覆盖任务必需的功能、数据、代码或产物，逐项 pass/fail/unknown，不事后加条款。TF 已接近满分时，以预先定义的产物正确性检验改善，但不能隐瞒 TF 退化。独立复核必须采用未据结果改写的方法和同一检查；五个 judge 不是五次 agent 重复。具体重复数与比较规则先写入下一份协议，不套用旧 PE +0.5 门槛，不要求每格或每个基线都胜出。
- **代码位置：**`/Users/fanysmacpro/Developer/agents/pe6203-agent-harness-safety`；当前研究分支 `codex/completion-quality-study`。本次目标整理前最新证据提交 `fcadce5fbf6f1e49d88189948a94e8a9307971db`。当前研究尚未 push；不要从 main 创建空白工作区后误以为最新研究丢失。
- **Goal 平台状态：**本次读取为 `paused`，旧 objective 仍是“找到更好策略”。本文更新研究约定，没有编辑应用内 Goal 的 objective。现有工具只能新建目标或改变状态，不能改写未完成目标/恢复暂停目标；需用户在应用中替换并恢复，或在新聊天用上述文本启动 Goal。不要为绕过限制把旧目标标成完成。
- **最新实测：**六条定点复核中原 SP 与 budget_feedback 都正常完成 2/3；TF 9.8 vs 8.9333，PE 9.4 vs 8.0。此前完成收益未复现，尚无可靠双重改善结论。全部实验进程已在上一轮结束；本次只整理目标与接手说明，无模型/评分/部署调用。
- **已知故障边界：**283 的轮数耗尽、UUID 抄写恢复及上游层级重复计数，133 的生成校验代码错误，不能直接认定都是过期工具知识。更多通用规则尚未解决这些问题。下一步先离线区分知识适应可修复机制与执行器/上游/一般代码生成错误，再选单一机制；不先重跑旧候选。
- **课程与研究分开：**原 27 条主实验/PDF/Slides 已冻结；研究未赢不抹去课程交付。受控 under-update 缺参及 over-update 无关路由的局部损害有证据；是否满足 TA 对方法失败分析的期待仍待确认。Full Rewrite 完整重建目录并改写所有描述，但结构字段/usage rules 取元数据，解释待 TA。不得称课程已经验收。

### 按需读取，避免重新灌入全部历史

1. 本节与 [README](README.md)，然后核对课程 brief §§2–4：`/Users/fanysmacpro/Documents/Graduate_learning/PE6203-BoAn/group_project/PE6203 Group Project 4 - Tool Harness Adaptation under Environment Change.docx`。
2. 最新跨研究汇总：[existing-method-recheck.html](reports/existing-method-recheck.html)。需要逐格事实时才读 `results/evidence/existing-method-recheck-20261031/quality-review.json`、`judge-audit.json` 和 `trial-verification.json`。
3. 课程交付：[report-final.html](submission/report-final.html)；新增无关知识损害证据：[routing-fault-results.html](reports/routing-fault-results.html)。迁移扩展按需要读 `reports/tool-migration-results.html`、`reports/daily-migration-results.html`。
4. 研究实现：`src/pe6203/selective.py`、`patch_variants.py`、`baselines.py`；公平执行配置：`configs/existing-method-recheck-v1.json`。原始包/源码快照按报告索引定位，不批量解包打印。不要读取或打印 `.env`、`.env copy`；实验费用账本不是 Codex 聊天 credits 账单。
5. 零 API 复算命令：`python3 results/evidence/existing-method-recheck-20261031/verify_trial.py`。本次仅核对文档差异与路径，没有重跑此前已通过的完整审计。

新聊天可以直接使用：

```text
在 /Users/fanysmacpro/Developer/agents/pe6203-agent-harness-safety 的现有
codex/completion-quality-study 分支接手；先读 HANDOVER.md 的“新聊天接手入口”，
再按需读它列出的文件，不读取整个聊天、全部历史轨迹或密钥。
按其中“新版 Goal 文本”创建并推进目标。我要求可复现的完成率和任务质量双重改善，
不能以负结果宣告研究目标完成；不设总费用/轨迹上限，但保留公平单次预算及完整记账。
从断点继续，先离线冻结具体机制和验收规则，不重跑已完成实验或自动展开大矩阵。
```

## 历史交付与研究记录（下文保留原状态，当前指示以上节为准）

**最新授权：用户要求“请不要设置上限和额度限制，以完成任务为优先目标”。后续研究按证据继续，不设总费用/轨迹额度；保持逐条记账、公平执行设置及历史证据。下文各轮限额及等待批准的表述仅描述当时状态。最新已完成：`experiments/existing-method-recheck-v1.json` 的6条定点复核，完成收益未复现，不晋级。可读汇总：[`reports/existing-method-recheck.html`](reports/existing-method-recheck.html)。另有12条实时信息、12条Swift迁移和2条无关路由诊断（文末）。不含部署授权。**

课程交付已冻结。四条获批诊断已经结束；PE +0.5 和历史 promotion gates 不属于课程要求。后续新增的完成率 / 任务质量研究另列在文末；文末获批的 12 条试验已执行并归档，总费用 US$0.1572164470；**授权已用完，不自动扩展实验或部署**。课程验收仍需组内审阅及 TA 澄清，不以策略胜出为条件。

## 当前可交付内容

- 最新整合报告：[`submission/PE6203-final-report.pdf`](submission/PE6203-final-report.pdf)，可读 HTML：[`submission/report-final.html`](submission/report-final.html)。原报告、诊断附录、两个本机 ZIP 保留为历史快照，旧的“strict natural”措辞由本次 brief 核查取代。
- 27 条主实验和 135 个评分从归档独立复算一致。Patch 九个 PE：133 = 10/8/7，235 = 10/10/10，283 = 9/9.4/8.6；82/9 = 9.1111。它的 PE 最高，但 TF、ECS 和正常完成率不领先。评分与完成状态分开，历史分数未修改。
- 最新离线审计：[`submission/handover-20261031/audit.json`](submission/handover-20261031/audit.json)。完整原始轨迹路径、变化前后字段和实际调用均在其中或以下案例文件中。
- [共享 Slides](https://docs.google.com/presentation/d/1vcofhraTu_EJuhCm45WDVUMQzRFrY36T/edit)：13 页主讲 + 5 页 Q&A 附录，团队仍需排练 10 分钟讲解 / 5 分钟问答。当前讲稿见 [`speaker-notes-final.html`](submission/handover-20261031/speaker-notes-final.html)，机器版本为同名 JSON。
- 仓库未找到适用的 AGENTS.md 或已有 handover，因此创建本文件。入口仍为 README，细节保存在 submission/。

## 证据结论与未完成项

| brief 条款 | 已核实 | 未解决 / 下一步 |
| --- | --- | --- |
| §§2、4.1 三方法 | 原 No Update、确定性 Patch、全目录 Full Rewrite 均有实测轨迹；Early 共用 K0。 | Full Rewrite 重建全部目标记录，LLM 改写每条 description；schema、routing、output schema 和 usage rules 从目标元数据复制，并非每字段都由 LLM 生成。是否符合教师对“all knowledge regenerated”的预期，列入 TA 草稿。不能改实现后沿用旧成绩。 |
| §3.2 固定设置 | 3 tasks × 3 stages × 3 methods × 1 execution = 27。模型、温度、agent 预算、任务、judge rubric/槽位一致。 | 单次执行不支持总体显著性或广泛泛化；5 次 judge 不是 5 次 agent。方法同时改变更新范围与生成机制，不能解释为纯范围消融。 |
| §3.2 三类变化 | PARAM：133 validator；DESC：283 create_project；TOOL：283 Late 新增 workspace review，FR/Patch 各调用一次。 | TOOL 是可选新增，未测必需工具删除/重命名；部分新增工具零调用。描述被呈现、工具被调用不证明描述改写引起行为差异。详见报告覆盖表与 audit.json。 |
| §4.2 under-update | 受控删除 allow_variables 后 8 次缺参拒绝，完整条件 0 次；机制 confirmed。 | 这是人为修改已有知识快照，未证明原 updater 自身遗漏。TF 均 10，PE 5.8 vs 5.6，截断 vs 完成。brief 没有要求“自然发生”；人工注入是否足够作为课程案例仍待 TA 判断。 |
| §4.2 over-update | 一条 evaluate usage rule 保留时 22 次调用、PE 7.8、截断；回退时 4 次、PE 10、完成，但 TF 10→9.8。 | 该规则涉及变化后的 validator，语义上有关联。元数据未变不等于知识无关；单次对照不能确认规则造成损害。因此仅 suggestive，尚无已确认的“无关知识修改→正常行为受损”链条。 |
| §4.2 负例、成本 | 旧 6 条 chart 回退诊断均 TF/PE 10，负结果保留；已审计 317 条历史轨迹。主实验已知 $0.40691929208 + 1 笔未知费用；4 条诊断 $0.04600192，无未知项。 | 不将未知费用填零；不把上游缺陷、网络失败、judge 错误或预算耗尽自动算成补丁错误。完整账单需用户查供应商记录。 |
| §4.3 展示 / 提交 | 报告、来源、离线复算、Slides 和讲稿可审阅。 | 团队核对姓名/分工、排练、确认 TA 接受范围及课程提交记录。推送 GitHub 不等于已完成课程系统登记。 |

## 案例索引

- **U1 confirmed，仅 No Update 局部失败**：`submission/evidence/case-details/U1.json`。主实验 task133 Late，旧 schema 缺少 mandatory allow_variables，最初 4 次调用被拒绝，之后自行恢复。不能直接称为 Patch under-update。
- **U2 contradicted，原 Patch 漏参假说**：`submission/evidence/case-details/U2.json`。正确字段已存在，三次 validator 调用均传入，零工具错误。
- **受控 under-update**：`submission/diagnostics-20261031/exact-knowledge-diffs.json`、`audit.json`、`plan.json`；原始包 `submission/evidence/targeted-diagnostics-20261031.tar.gz` 内 `raw/cells/under_omitted` 和 `raw/cells/under_complete`。只删除 validator 属性及 required 条目，错误观察能直接支持缺参机制。complete 条件另外遇到 batch_evaluate 实现缺陷，四个 judge 理由错误声称工具不存在，分数保留。
- **受控 rule 对照，suggestive**：同包 `raw/cells/over_note` 与 `raw/cells/over_reverted`。只回退一条 evaluate usage rule，其他三个历史规则保持相同。它是历史 linked_notes 变体，不能冒充主实验 Patch；没有证明规则“无关”。
- **O1 suggestive / O3 inconclusive**：`submission/evidence/case-details/O1.json`、`submission/evidence/diagnostic-review.json`。历史 FR 重写未变化的 28 个 chart 描述并低分，但 dataValueUnit 指引仍在；六次反事实未复现损害，3 份答案的算术错误分布在两组。不能用这个例子宣称 Patch over-update 因果已确认。
- **O2 suggestive**：`submission/evidence/case-details/O2.json`，旧 linked_notes 有四个记录同时不同，比本次单规则对照混杂更多。
- 主实验归档：`results/evidence/course-v1.3-20261031/raw-trial.tar.gz`，前缀 `course-v1.3-final-20261031/cells/`。知识在各 cell 的 `adaptation/knowledge.json`，调用/观察在 `run/raw_trace.json`，评分在 `run/EVAL/` 和 `judge-attempts/`。诊断原始包的路径以实际 raw-manifest.json 为准。

## 待 TA 确认的问题草稿（未发送）

1. brief §4.2 要求 under-update 轨迹。我们从正确的更新知识中受控删除一个必需参数，确认 8 次对应拒绝和最终截断，完整条件没有缺参拒绝；但这是 fault injection，且 TF 没降低、PE 没改善。明确披露这些限制后，是否可作为该类失败分析？是否还要求证明开发的 updater 自身会遗漏？我们不假定必须自然发生，也不假定注入自动合格。
2. over-update 定义要求修改无关知识并损害正常行为。现有一条规则对照涉及语义相关工具；历史未变化 chart 描述的回退实验未重现损害。可以提交提示性案例、负结果与未证实结论，还是需要另一个有直接证据的案例？我们不会把相关工具等同于无关知识。
3. Full Rewrite 对完整目录所有记录重新构建，LLM 改写全部 description，schema/output schema/routing 取目标元数据，usage rules 原样保留。这是否满足 §§2、4.1 的完整知识再生成，还是希望 usage rules 等文本也重新生成？现有结果仅代表已描述实现。
4. 当前子集实际调用覆盖 PARAM、DESC 与 TOOL 新增；新增工具是可选的 workspace review，FR 成功而 Patch 因上游缺陷失败。必需删除/重命名、某些新增工具未覆盖。这样的有限覆盖是否符合 §3.2，还是期待特定子类型？

## 离线复核与禁止自动执行的边界

从 repo 根目录运行（Python 3.12+ 标准库，不需要 key、依赖下载或网络）：

```bash
python3 submission/handover-20261031/verify.py
```

脚本重建 10,959 个冻结历史文件到临时目录，复核 27 主轨迹 / 135 评分、209 条 FR 描述、三类目录差异及实际调用、72 个候选 / 9 个深审案例 / 6 个旧负诊断，并独立复算 4 条新诊断 / 20 个评分。输入只读，网络显式禁用。新增 `corpus-extra.tar.gz` 仅补足 19 个原归档未含的 424 个历史文件，不含新实验。

原 205 MB 主 ZIP、2.2 MB 诊断 ZIP 和原 PDF 仍是冻结快照，未覆盖；不要重新运行它们的打包脚本去混入后来结果。GitHub 通过既有历史归档、补充日志包和源码包提供复核输入；大型 ZIP 不进入 Git。当前整合报告与本 handover 优先于旧包的交付状态叙述，评分与费用数据仍以原始归档为准。

已取消 `.env copy` 跟踪并保留本机文件，避免在最新提交树继续分发凭据。旧 Git 历史已包含该文件；删除最新版本不会撤回旧凭据。用户应轮换其中仍有效的 key；本次不擅自操作账户或重写共享历史。

下一位接手者先查看本文件、最新报告与 `submission/handover-20261031/verification.json`。未得到用户新批准，不运行 experiment/driver/preflight，不重评已有轨迹、不扩充实验、不部署 Netlify。TA 回复如要求补充，先提出最小、独立计费的方案再获批执行。

## Git 交付回执

主交付已通过非 force push 合并到 main：`e95b51a3601a5966d06f05ae1e729f8e8bad60f9`。远端 ref 已核对，GitHub Adapter checks 成功；核查内容提交为 `61a3cf3`。本节和 [`delivery.json`](submission/handover-20261031/delivery.json) 的后续记录提交仅补交付回执。当前未解决项仍以上表为准，没有宣称课程验收已完成。

## 后续研究：完成率与任务质量（12 条完成，未晋级）

工作位于 `codex/completion-quality-study`，基于已推送的 main `ef96d08`；此研究仅本地提交，尚未合并或推送。课程报告、Slides、27 条主实验及所有历史评分保持冻结。

- 用户明确批准“这 12 条，费用上限 US$1”。按原计划验证已有 `budget_feedback`，没有新增策略。3 tasks × Middle/Late × 2 arms × 1 次，12/12 轨迹、60/60 原协议评分已结束。两组正常完成均 **4/6**（变化任务 2/4、保持任务 2/2），133 Middle 均截断、283 Late 均耗尽轮数。
- 原 Patch：TF **9.9667**、PE **9.0**、agent+judge **$0.0726556104**；候选：TF **10**、PE **8.8**、**$0.0845529246**。共享预检 $0.000007912，合计 **$0.1572164470**，未知费用 0；69 agent + 60 judge + 2 preflight = 131 请求，约 10.56 分钟。更新无模型调用、无新增探测。没有 Early，不计算新 ECS。
- **判定：未证明完成率与任务质量同时改善，不晋级。** 候选图表答案的部分算术更准确，283 Middle 容器解释更清楚；但两个保持格的地图缺少金额单位，133 Middle 误把不支持 `**` 推断成不支持指数及消除 DoS。原 Patch 也有月度合计和安全代码测试错误。没有改 judge 分数；逐属性 pass/fail/unknown 与证据均保留。
- **公平性限制：**模型 ID、解码、任务、预算、judge 协议相同；57 个冻结输入和执行前源码哈希未漂移，task235 两组是精确 K0。但 OpenRouter 实际后端供应商不同，工作目录也含策略名；冻结协议“只有知识不同”的措辞过强。原协议保留，结果报告明确补充这项限制，不能作纯补丁因果结论。相同 K0 下的输出差异不能证明适应机制造成保持退化。
- **可读入口：**[`reports/completion-quality-results.html`](reports/completion-quality-results.html)。完整证据目录：`results/evidence/completion-quality-20261031/`：`raw-trial.tar.gz`（500 文件）、`raw-manifest.json`、`source-98c4f8e.tar.gz`、`trial-verification.json`、`trial-facts/facts.json`、`quality-review.json`、`artifact-checks.json`、`post-run-input-verification.json`、`reproduction.json`。知识/工具/调用在原始包，五个 judge 原始分值逐格披露。
- `quality-review-template.json` 是填表前模板，最终状态以 `quality-review.json` 为准。`protocol-audit.json` / `verification.json` 是批准前快照；`approval.json` / `approved-verification.json` 是执行前批准及核验。勿将快照状态当成当前状态。
- 冻结执行代码为 `98c4f8e`。`experiments/completion-quality-v1.json` 与 `configs/completion-quality-v1.json` 未因结果修改。请求级费用预留和相同 provider 价格上限已覆盖全部调用；账本已结算，未触发预算封锁。供应商接口价格/上下文约定仍是保护前提。
- **未完成：**没有找到本轮标准下同时改善两项的策略。上文 TA 接受范围、over-update 因果证据和 Full Rewrite 解释仍未解决。不能用本轮 TF 接近满分关闭这些问题，也不能把旧开发阶段的 6/6 代替这轮 4/6。
- **下一步：**先审阅本报告。课程可按已有交付推进；若继续性能研究，先提出针对后端控制、截断和知识边界的最小方案、费用和预期证据，再单独获批。当前没有新候选、重复或扩展获批，不恢复旧 R2/R3，不重跑低分，不部署，不自动改课程 Slides。

本轮离线核查（只用 Python 标准库，不启动模型或服务）：

```bash
python3 results/evidence/completion-quality-20261031/verify_trial.py > /tmp/pe6203-trial-verified.json
```

原始包 SHA-256：`9954a1039a946f7e7bd46c39e56b1ce63cb35d1d188941d3889b5a5b4370d9b6`。源码包不含安装后的全部依赖；原 CLI 命令只是历史复现说明，不是新增付费调用的授权。


### 下一候选的离线提案（批准前历史快照；当前状态见下节）

上一目标回合属于 progress：12 条真实试验得到新反例并完成归档。随后离线追踪确认：预算规则已注入，但不含具体 12 轮 / 4096 token 限额；133 Middle 在最终答案处截断，283 Late 无工具错误仍逐组扩写到轮数耗尽。因果修复仍是待检验假说。

- 已拟且仅拟一个 `budget_contract`：以 `budget_feedback` 为对照，只替换一条预算规则，明确限额、先覆盖所需工作再细化、预留核验/汇报；不提高预算、不放宽质量属性、不修改不变工具。候选尚未注册到运行框架。
- [可读提案](reports/budget-contract-proposal.html)；`results/evidence/budget-contract-proposal-20261031/proposal.json` 为机器方案，`knowledge-diffs.json` 是精确差异，`mechanism-evidence.json` 是逐轮证据。9 个静态知识条件仅替换原有 29 处规则；5 个 Early/retention 条件保持 K0。复核：`python3 results/evidence/budget-contract-proposal-20261031/verify_preview.py`。这些不是新轨迹或新质量分数。
- 拟申请 6 条：133 Middle、283 Late、235 Middle × 原 budget_feedback / 新候选，各 1 次；30 个原协议评分槽、至多 2 次可用性预检。拟固定 DigitalOcean 端点、禁止 fallback，使用不含方法名的 cell/workspace IDs。公开端点元数据已读取，无凭据、无推理调用；真实端点可用性仍未测试。
- 预计 US$0.15–0.40、5–12 分钟，申请独立 US$1 上限。先前 12 条批准不能复用于这一轮。完整路径也已说明：初筛阳性后，与原 Patch 的完整 Middle/Late 对照最多再需 9 条；若将新方法列为课程主结果，匹配三阶段及 No Update/Full Rewrite 最多再需 21 条。均须另批，阴性/不确定即停，绝不自动执行后续矩阵。
- **当前等待事项：**用户批准或拒绝这 6 条及单候选接入。在回答前不注册新策略、不预检模型、不评分、不运行新实验。独立可做的设计、差异检查、费用估算和文档已完成；仍没有验证出符合双重改善目标的策略，课程 TA 缺口也未关闭。


### 六条 budget_contract 试验（已完成，停止，不晋级）

用户随后批准“这轮目标能够完成都可以批准”，范围按此前问题限定为单候选接入、6 条轨迹、30 个有效评分槽、至多 2 次预检、独立 US$1 上限；不是承诺结果必为正或无限扩展。批准记录在 `results/evidence/budget-contract-proposal-20261031/approval.json`，原提案快照保留。

- **实现与核验：**源码冻结 `418ed2b`，协议 `experiments/budget-contract-v1.json`，配置 `configs/budget-contract-v1.json`。只替换原预算规则，133 Middle 5 处、283 Late 11 处、235 Middle 0 处，与批准预览完全一致。两组固定 DigitalOcean、禁止 fallback，使用不暴露方法名的 cell 路径；12 轮/4096 tokens 等实际预算不变。333 项离线测试通过；全部 57 项冻结输入在执行后仍匹配。
- **结果：**指定三对均完成，6/6 轨迹和30/30评分。对照 budget_feedback：完成3/3、变化任务2/2、保持1/1，TF **9.9333**、PE **9.7333**；候选 budget_contract：相同完成数，TF **9.8667**、PE **8.9333**。无 Early，不计算 ECS。不将当前成功与旧失败拼成修复效果。
- **费用：**61 请求＝29 agent +30 judge +2 preflight，全部实际响应为 DigitalOcean。总计 **$0.089010216**，未知项0；约3.83分钟 API 执行窗口。对照 agent/judge $0.033376212/$0.010540008；候选 $0.033273108/$0.011807928；共享预检 $0.00001296。确定性更新无模型调用。费用来自响应，未另核账户账单。
- **质量：**283 Late 候选的35=6+29任务及204h汇总准确；对照M3写67h但落盘79h，并虚构一次参数失败。候选133却误把不支持 `**` 推断为没有指数，把解析与求值混淆，其示例MAX_DEPTH检查不递增深度。保持任务两组数据与单位均保留，但渲染图未存档。候选改名已拆分父节点后警告清零，仅能说明分析器对文本敏感，不能据此认定根因解决或已确认over-update。20属性为12 pass/4 fail/4 unknown，未合成分数；judge错误独立记录，原评分不改。
- **判定：**本轮未证明完成率与任务质量同时提高，不晋级，停止新增调用。单次已暴露任务、后端内部版本未知、规则内多句无法独立归因；不能泛化。仍没有达到双重改善研究目标。
- **审阅：**`reports/budget-contract-results.html`；完整证据 `results/evidence/budget-contract-20261031/` 含原始包（262文件）、哈希、源码包、独立复算、产物事实、质量审阅、judge审计、执行环境及命令。原始包 SHA-256 `b82b34719e304d3037ab465ecfe1bc46c7d1ff9be0712b1123623a39600c115a`。本轮只在 `codex/completion-quality-study` 本地提交；未合并/推送main，未改课程PDF/Slides，未部署。
- **下一步和边界：**可独立审阅本报告；本轮没有剩余实验。后续重复、候选或扩展均未获批，不运行既提到的9/21条或旧R2/R3。课程原有TA接受受控under-update、无关知识over-update因果证据、Full Rewrite解释与工具删除/重命名覆盖缺口均未关闭；问题草稿仍在既有交付中，不发送。

离线复算（零模型调用）：

```bash
python3 results/evidence/budget-contract-20261031/verify_trial.py
```


### 最新：取消总额度后的补充对照（已完成，质量仍未过关）

本节取代上文历史“未获批9条/后续每轮必须另批”的当前授权表述。用户明确要求“请不要设置上限和额度限制，以完成任务为优先目标”；后续证据驱动的必要研究不再申请每批费用额度。单条12轮/4096 tokens等公平执行条件固定；部署、给TA/他人发消息不在授权内。无总费用/总轨迹硬上限，不等于无假说地自动展开矩阵。

- **已执行：**既有budget_feedback vs原Selective Patch，补9条、45评分，复用前一六条试验中的候选133Middle、235Middle、283Late；无新候选、探测或updater模型调用。全部新调用DigitalOcean，正常端点，103请求（含2预检）。新费用 **$0.151974408**，未知项0；465.04秒。前三轮新增研究合计已知$0.398201071，不含更早课程/历史研究。
- **合并12格独立复算：**候选完成 **6/6**、变化任务 **4/4**、保持 **2/2**、TF **9.8**、PE **9.2667**；原Patch完成 **2/6**、变化任务 **0/4**、保持 **2/2**、TF **9.4**、PE **8.3667**。两阶段不算ECS。没有Early/NU/FR新全矩阵，不替换课程主表。
- **证据支持的收益：**同批次283Middle候选的36=4+32记录、356h及73/69/104/110h分项均准确，并真实拆分两项工作、新增四个任务；原Patch在M3耗尽轮数，M4–M8只有空里程碑。
- **仍未过质量检查：**候选133Late完成但示例字典语法错误，字符过滤拒绝其合法sqrt测试，AST括号深度建议错误。候选235Late的年度合计及江苏服装数字错误；原Patch图表总结也错误。复用283Late的67vs79h及虚构失败、133Middle的安全完整性未知仍保留。故**不晋级，双重改善完整目标尚未完成**，不因TF/完成率较高启动81/108条确认。
- **公平性限制：**三条来自已看过结果的前一批次，且本轮移除总费用/单价准入上限、改变账本路径；完整执行协议哈希因此不同。模型、解码、judge实现/规则、工具版本与知识不变。不能称为纯同时随机对照或全部配置相同，旧12条两组4/6的负结果仍有效。新旧批次各一份完整协议哈希已独立重算。
- **工具/评分异常：**上游Middle的file-storage.js第53/56行console.log迁移信息触发JSONRPC警告；执行继续，未证实影响耗尽。原Patch一次create_subtask虚构父ID导致拒绝。所选judge理由错误已单列，旧分数未修正。完整控制台流未单独存档；调用、观察、产物与费用均在原始包。
- **审阅与复现：**`reports/matched-existing-results.html`；`results/evidence/matched-existing-20261031/`含382文件原始包、源码包、逐文件哈希、独立verify_trial.py、check_artifacts.py、trial-verification.json、quality-review.json、judge-audit.json、runtime-observations.json、reproduction.json。原始包SHA256：`6f1d6a5bbcf78f076793faf74f466d3050f133491793e8154a86a3936800e837`。执行源码 **f896388**，339项离线测试通过；本轮无运行中的实验。
- **接手下一步：**先读报告与最终quality-review.json；设计一个针对变化工具证据边界的修正，避免把工具语言验证当成已验证的Python实现或安全保证，明确何时仅需建议而非生成完整实现。先冻结具体diff和质量检查，再做针对性配对验证；不修改相同K0来“修复”保持任务的随机错误，不重新包装旧成功为新验证。不设资金/轨迹总帽，也不盲目重复直到赢。候选全阶段验证、under/over案例适用性与TA问题仍未完成，原草稿未发送。

本研究仍在`codex/completion-quality-study`本地分支；课程main、PDF与共享Slides不因探索结果自动改写。


### 当前研究：evidence_scope 局部证据规则（执行前冻结）

沿用最新无总额度授权。只在budget_feedback的变化/新增记录中追加一条固定证据边界usage rule，防止将工具观察扩展为未经验证的实现、可选汇总或虚构执行历史；保留原任务全部交付，不改模型/预算/评分。三个Late条件133/235/283 × 原budget_feedback/候选，各1次，6条同批次配对、30个原评分槽；预计$0.10–0.30、5–12分钟，均为估算。此阶段检查质量修复并保持完成率，不要求击败已经满完成率的budget_feedback；最终目标仍须对原Patch和课程基线完成三阶段验证。

协议`experiments/evidence-scope-v1.json`，配置`configs/evidence-scope-v1.json`；精确规则和九个task-stage知识差异在`results/evidence/evidence-scope-pilot-20261031/offline-knowledge-checks.json`。五个Early/retention条件均为精确K0。Late133追加10条、283追加11条、235为0；其余字段逐项与budget_feedback一致。340项离线测试通过，尚未据此宣称行为改善。结果归档后以新结果节为准，不启动自动网格或108条确认。


### evidence_scope 六条配对（完成，不晋级）

- 冻结源码 `422178236198454f673748a782550a4438e81d44`；`experiments/evidence-scope-v1.json` 与同名 configs。3 tasks × Late × budget_feedback/evidence_scope，每格一次；没有复用旧agent轨迹、增加探测、部署或改评分。
- 新候选1/3正常完成（变化0/2），对照2/3（变化1/2）；TF9.6/9.8，PE9.0667/9.4667。候选133截断，两组283耗尽12轮；235均完成且知识精确K0。不能推广之前6/6成功，更不能把judge高分当正常结束。
- 64请求=32 agent+30 judge+2预检，全为DigitalOcean；已知$0.107351724、未知0，269.35秒。总费用/轨迹额度仍为null；单轨迹公平预算保持。更新0模型tokens/调用/$0，合计1.0873秒。
- 归档265文件含console：`results/evidence/evidence-scope-pilot-20261031/raw-trial.tar.gz`，SHA-256 `ecf66965bbdb672cba6a4a3192491bb951edb49ca85329ffa2e86afb4b85a130`。同目录含独立verify_trial.py、trial-verification.json、quality-review.json、artifact-checks.json、judge-audit.json、reproduction.json及冻结源码包。57个输入和知识锁复核无漂移。
- 可读报告：`reports/evidence-scope-results.html`。候选仍扩写未请求的数学实现；283十次缺workingDirectory，但字段已在知识中。两组283有真实拆分和有效引用，但无最终回答。保留工具实现缺陷、judge描述不存在最终答复等反证，不称已确认under/over-update。
- **后续先查原因：**规则重复/长度、参数契约落实、输出与轮次预算；不继续叠加同类泛化提示。课程27条/PDF/Slides仍冻结。TA问题及研究目标尚未解决；本轮阴性，不可写成已找到稳健策略。最新授权允许必要研究继续，无需按旧额度逐轮询问，仍不部署。

离线复核：`python3 results/evidence/evidence-scope-pilot-20261031/verify_trial.py`。

### 最新：真实工具删除覆盖补充（12条已完成，未证明全面质量胜出）

这是按发布版mutation覆盖选择的task430，不是修改旧任务或按成绩挑成功；没有新增策略。`search_symbols`在Late删除，其查询功能迁到`browse_module.query`。仍用既有budget_feedback，与原Patch、No Update、Full Rewrite三阶段各一次对照。四组Early均精确K0；新任务在开发历史之后选入，不是受保护的独立测试集。

- **结果：**原Patch/budget_feedback各3/3正常完成，NU/FR各1/3；四组TF均9.9333、ECS总体9.8391/样本9.8179。PE分别7.4667、7.5333、6.1333、8.6667。Late旧工具调用NU为7，其他为0；只有原Patch实际调用新query，候选/FR使用其他可用文档入口。完整逐格结果见`reports/tool-migration-results.html`。
- **质量与限制：**12条核心CounterView都通过本机Swift类型检查；4条截断均已有主体答案，高TF不自动构成judge错误。候选Early从来源继承错误CardView，Late把onDelete放在List上；独立核查确认，原评分不改。Early差异不能归于适应；本轮单任务/单次且实时公开内容，不能宣称稳定双重改善、所有基线胜出或泛化。旧各轮负结果继续有效。
- **费用和公平：**115请求=51 agent+60 judge+2 updater+2预检；实际全部DigitalOcean，同一model、decoding和judge。总$0.128198580，未知0；账本跨度548.25秒。FR更新5546tokens/$0.00187308/7.080秒；选择性方法0更新模型tokens/$0。本次只新增可选updater后端固定与统一记账，FR仍重建全目录、LLM改写全部15条描述，其他结构字段从目标元数据复制。新代码不能倒推旧实验已用相同设置。
- **证据：**`results/evidence/tool-migration-pilot-20261031/`含490文件原始包、源码eae035e包、逐文件hash、独立verify_trial.py、quality-review、judge-audit、coverage-touch、类型检查与环境/复现信息。原始包SHA256 `ea10b0d11d776670d79adf5f0c822d471788cd87c7850a7609c80fc22eddd32e`；47冻结输入执行后无漂移。执行前341离线测试通过/13integration排除。新报告浏览器已核对；未部署、未修改主27/PDF/共享Slides。
- **课程缺口状态：**Tool删除现在有补充实测，但不要把同任务Wikipedia保持当成独立retention或替换原235。No Update stale-tool失败不是Patch under-update。原受控缺参机制仍confirmed，课程适用性待TA；旧over-update对照仍相关，不能认定无关知识损害。
- **最小下一项已有具体方案：**`results/evidence/routing-fault-proposal-20261031/plan.json`及两份knowledge，只把无关Wikipedia.readArticle的routing.tool_name改成read_article。原验证器明确拒绝该修改（scope-guard-check.json）；若执行，只能标为受控故障注入/guard消融，不是自然候选失败。拟2条agent、10个judge槽及2次同参数公开只读replay，预计$0.02–0.08、2–6分钟，均为估算而非上限。当前未运行此诊断；先明确此有限机制演示是否值得补入课程，不因研究未赢就启动81/108或继续追加通用提示规则。TA问题已写在plan中，未发送。
- **验收解释：**课程不要求每个附加片段完美、显著胜出、PE+0.5或自然失败；也不能因不要求赢就声称研究双重改善已证实。可提交透明的混合结果。若目标仍是稳健提高完成与质量，当前证据尚不足，明确保留此未完成结论。

本轮已无运行中的模型实验。当前研究仅在`codex/completion-quality-study`本地归档提交；没有新增main push。原课程main交付状态不变。

零模型离线复算：`python3 results/evidence/tool-migration-pilot-20261031/verify_trial.py`。

### 最新：无关路由受控诊断（已完成，局部机制确认）

上一目标回合为progress：12条迁移对照与独立审阅已提交9f9e0c9。本回合按持续研究授权完成上节方案中的2条agent/10评分及2次公开同输入重放；不设总额度，无新策略或部署。

- **唯一差异：**430Late现有budget_feedback知识中，`wikipedia-mcp::readArticle.routing.tool_name`从`readArticle`改成`read_article`。Wikipedia元数据三阶段完全不变，与Swiftipedia迁移无依赖；模型看到的工具定义一致。正确路由直接返回41,962字符文章，错误路由明确Tool not found。
- **完整轨迹：**cell-001故障组第2、3轮两次触发该错误；cell-002控制组第2轮成功。两组均7次工具调用，agent轮数5/4，都正常结束。故障组如实披露读失败，使用搜索摘要完成解释和示例。原TF9.6/10、PE6.0/6.8，独立复算10个原评分一致；多份judge误判了已有batch材料或重试数，原分未修改。
- **结论分类：**无关路由改动→局部读功能损害：confirmed（受控）；整个任务失败：contradicted；TF/PE差值的因果归属：suggestive（首轮已随机分岔，且评分错误）；正常updater自然产生此错：未观察到，本次明确不是。正常scope/identity验证器会拒绝3项违规，实验只从研究replay入口注入，未改正式验证器。
- **课程解释：**现在under缺参和over无关路由两类受控局部机制均有真实轨迹。brief没有自然发生要求，也没有明说必须导致整个任务失败；但guard消融/局部损害是否满足教师对方法失败分析的预期仍待TA，不能自动写成已验收。旧evaluate相关规则对照仍suggestive，6条chart负结果和主27结果不变。问题草稿在新evidence-review.json，未发送。
- **归档：**`results/evidence/routing-fault-check-20261031/`含87文件raw-trial.tar.gz，SHA256 `50fa23e2b4120c95ef5cf5f2eba1413617e94d63c5383c043d29ad5ef4e58ae8`；driver/protocol冻结37dd2d0，51个source/diagnostic输入执行后无漂移。标准库verify_trial.py、evidence-review、原始费用、执行/复现说明俱全。19请求=9agent+10judge，实际DigitalOcean；$0.021366768、未知0，77.54秒。无updater或模型预检调用。
- **阅读与交付：**`reports/routing-fault-results.html`已生成；迁移报告链接更新为已执行状态，旧提案保持执行前快照。本附录还没有合入冻结课程PDF/共享Slides，main未push。后续整合必须区分受控局部机制与自然失败，不能把9.6→10当方法晋级。当前没有运行中的模型实验。
- **目标仍未完成：**这对条件不构成新的改进策略。已有budget_feedback在匹配开发对照中有完成/TF收益，同时保留反例；不能把“每个附加片段完美、统计显著或击败所有baseline”自设为课程要求，也不能只凭一项高分宣称整体质量更好。下一步应寻找具体、任务相关的知识适应机制与质量证据，不再堆叠同类通用规则。研究可继续，无需旧额度确认；不自动恢复81/108网格。
- **数据边界提醒：**一次过宽的官方任务打印暴露了9/24/72/90的原答案/轨迹（未送入updater、agent或judge，也未因此选择/执行新实验）。今后这些只能标为已暴露开发案例；选任务时只读取idx/question/servers/tool_calls字段，勿再整条打印。潜在下一项是先离线评估90的真实每日题工具删除及其公开服务依赖，保留现有133/235/283/430；若不可运行或无法辨别恢复，不执行。不要为更容易得到阳性而丢弃旧任务或失败。

独立离线复核：`python3 results/evidence/routing-fault-check-20261031/verify_trial.py`。


### 最新：task90 实时信息迁移对照与评分可见性审计

本目标回合为 **progress**：先完成无关路由诊断归档（51136de），再以官方删除记录为依据核查并执行task90。没有新增策略，没有因费用额度停止，也没有启动81/108确认矩阵。当前所有进程均已正常结束，无待执行模型请求。

- **冻结方案：**`experiments/daily-migration-v1.json`。原任务/完整server set，Early/Middle/Late × NU/FR/原SP/budget_feedback ×1，共12条、60个评分。源码52abbcf（44ecdb2加入两个公开服务启动profile）；没有改策略、执行器、评分器。实际模型/供应商、解码、预算相同；源配置47项执行后核验。全部费用经同一不限额账本记录。
- **结果：**四方法正常结束均3/3。SP TF10/PE9.8/ECS总体10；BF 10/9.3333/10；FR 9.9333/9.6/9.8391；NU 8.9333/8.6667/7.4248。样本SD口径同时披露。所有Early精确K0；不能把其差异解释成更新收益。Late NU两次调用已删除get_daily_challenge（仅一次重试）并最终披露无法取得；另外三方法用get_problem(daily=true)成功。
- **独立事实：**12/12均取得正确卡牌详情及相同64,036-byte JPEG；11/12取得并正确标识2026-10-31每日题3665/Twisted Mirror Path Count。这里是实时内容恢复，而不是正常结束率改善。图片只被执行器保存并作为base64 JSON文本供模型/评分器处理，没有自动展示或视觉理解的验证。BF Middle把setcode221误标为卡片密码，原SP Middle有附加方向限定；趣闻和“图片已经显示”等未支持说法均保留。
- **成本：**100请求＝36agent＋60judge＋2updater＋2preflight，全部DigitalOcean；$0.202212588，未知0。更新FR11,842 tokens/$0.00392868/13.270s，SP/BF零更新tokens/API费用。账本首尾309.34s包含审查间隔；另有5次公开只读服务探测、零模型费用。无账户账单复核。
- **评分解释更正：**官方`truncate_tool_content(...,max_length=1000)`截断每条工具观察；daily的difficulty/stats/hints被截掉。独立重建每条观察，与保存的judge-original-prompt逐字匹配。此前routing故障中Form/Section/Picker/Slider/NavigationStack/onDelete也在截断区外。因此旧“judge遗漏已返回资料”必须进一步区分为**评分协议没有展示这些资料**；不能据此指责judge漏读已见文本。旧raw/评分/evidence-review快照均未改，routing HTML加入显式解释更正。计数错误（两次总调用说成两次重试）仍是独立可确认问题。
- **覆盖：**新`coverage-touch.json`逐项区分环境变化、任务相关、实际调用。Late同时触达Tool删除及Parameter/Description迁移；不能分离三者的独立因果。Middle hints新增未触达，get_problem描述变化不是该阶段完成任务的必要步骤。卡牌搜索有参数变化，仅详情/图片两个契约作为不变能力保持；原task235独立保持任务不混入此cohort。
- **证据：**`results/evidence/daily-migration-pilot-20261031/`含492文件原始包、42文件源码包、独立复算、产物事实、12份答案审阅、60份TF/PE理由审阅、coverage、judge可见性重建及复现说明。raw SHA256 `11484dcaf903b5601c02fbb5b26d40e6c5c0ec661411783654e24d3d40d5b5e1`。服务核查在`results/evidence/daily-migration-readiness-20261031/`。首次临时离线检查漏载dotenv，CLI因缺少审查记录拒绝执行，未产生agent/judge调用；修复加载后继续，拒绝日志保留。
- **可读入口：**`reports/daily-migration-results.html`；原routing报告增加解释更正。当前仅在`codex/completion-quality-study`本地提交，未推送main、部署、修改课程PDF/共享Slides或发送TA问题。
- **仍不能宣称：**BF全面优于原SP、统计显著、广泛泛化或自然updater失败。task90曾暴露原答案/轨迹，当前事实也做过公开可用性探测，明确为开发扩展；这些答案没有进入updater/agent。FR Middle将描述译成中文，也已在执行前审阅中披露。与task430证据互补，不能静默混算或替换原133/235/283与27条主实验。
- **优先下一步：**汇总已有方法的收益与反例，并把两个迁移附录、无关路由受控机制及评分可见性限制整合进交付材料；先处理这些离线工作，再判断是否确有新实验必要。无需为“未在每个指标胜过所有baseline”继续扩展。课程未要求统计晋级、每句附加内容完美或自然失败；也不能只凭满分把用户的完成率/质量研究目标标成达成。是否采用BF作为最终方法，应依据跨cohort证据和明确的适用范围，而非择优展示本轮。
- **待外部确认：**TA是否接受受控under/over-update及保护结构的FR解释；团队姓名/分工、10分钟排练和正式提交记录仍需用户/团队确认。问题草稿未发送。旧main交付已经完成，当前研究分支的新增结果尚未要求推送。

零API复算：`python3 results/evidence/daily-migration-pilot-20261031/verify_trial.py`；`check_artifacts.py`、`coverage_touch.py`、`audit_judge_context.py`均从归档读取，不触发模型或服务。


### 当前：既有方法定点复核（执行前冻结）

上一轮为progress：task90及judge可见性审计已归档。此次不开发新候选；按最新无总额度授权，固定budget_feedback与原SP，重复283Middle的既有完成/产物收益，同时保留133Late安全建议与235Late图表保持两个不利条件。协议`experiments/existing-method-recheck-v1.json`，配置`configs/existing-method-recheck-v1.json`，共6个预先指定格、30评分槽，预计$0.10–0.30/5–12分钟，均非上限。12轮/4096tokens等只作为两方法相同的执行条件。

`results/evidence/existing-method-recheck-20261031/preexecution-review.json`确认六份知识与旧matched-existing对应快照逐字解析相同，235两份精确K0，无updater调用。此复核检验观察的可重复性，不把旧成功视为普遍胜出，也不要求每句附加内容完美；原质量rubric保留。结束后汇总所有正负cohort，再决定是否需要其他研究，不低分重跑直到赢。课程27/PDF/Slides和历史评分不改，不部署或push。


### 最新：既有方法复核结束与跨研究汇总（未晋级）

本目标回合为 **progress**。六条预先指定的新轨迹全部执行、30份原评分完成；没有新策略或重跑低分。最新报告`reports/existing-method-recheck.html`把原27、迁移、负规则试验和本次复核分开，七组研究从原始包重新复算一致；课程27/135评分、10,959历史文件及4诊断再次离线复核通过。

- **结果：**原SP与budget_feedback均完成2/3，变化任务均1/2，不变任务均1/1。SP TF9.8/PE9.4；BF TF8.9333/PE8.0。283Middle两者均max_rounds；此前matched-existing的完成/产物收益真实存在，但这次没有复现。不根据某次阳性宣布胜者，也不把本次TF差值直接归为补丁因果。任务/供应商/批次不同不混成一个总分，复用的3条BF不重复计数。
- **产物：**SP规划41记录=10父+31叶、604h；BF58=8父+50叶、538h，都有CSV/日志/可视化具体工作且父/依赖关系有效，均无最终回答。BF7次父UUID中441b误写411b，第6轮纠正后7条均创建；不是原参数重复失败。两份133答案中的Python校验器均漏掉遍历到的Add节点，静态证明普通加法被拒；BF另把不支持**误推为无指数风险，上游源码支持^。生成代码未执行，安全完整性unknown。235两组图表原数据/单位都正确；SP摘要23.4应为25.4且漏二月下降，BF摘要正确；相同K0差异不能归因于适应。
- **评分和上游：**SP层级list_tasks显示55但只有30个不同ID，getTasks根查询返回全体后递归重复子节点；同轮复杂度分析也只统计30，后续11个子任务使最终41。此错来源上游，不把引用55全归为judge幻觉。另有judge凭空描述空答案的最终主张、把修正ID恢复说成不变参数重试、误称成功调用的code-analysis工具不存在、对chart错误合计仍满分等。保留全部原分；观察截断1000字符限制继续披露。
- **费用：**65请求=33agent+30judge+2预检，全部DigitalOcean；$0.116399760，未知0，账本首尾305.263秒。两方法均0更新模型tokens/API费用；没有总费用/轨迹额度。12轮/4096输出tokens为公平单次条件，不是授权总帽。
- **冻结与交付：**源码e59c430；57源码/配置输入、12知识文件执行后无漂移。六份知识与旧matched-existing完全一致；50相关离线测试通过。证据`results/evidence/existing-method-recheck-20261031/`含266文件raw包SHA256 `4733c0c06af382f09d806835dad6b07d74105ff3bdb3e43cb330638fd5f29d40`、43文件源码包、费用、console、逐格事实、质量/评分审计、4份上游源码及复现命令。`verify_trial.py`、`check_artifacts.py`、`check_math_examples.py`、`check_observations.py`只做离线检查。
- **研究结论未完成：**尚不能确认budget_feedback同时带来可重复的完成率与任务质量改善；没有把“必须胜过所有baseline”“PE+0.5”“每句附加内容完美”当作课程要求。课程可接受混合结果，但研究目标不能因想收尾而写成已证明。下一步先核对具体知识缺口与方法架构：当前重复追加通用规则没有解决问题，UUID抄写和新代码生成错误也不是已确认的过期工具知识。不要自动再跑同一批直到赢，不恢复81/108网格，不把新实现冒充已有验证；若有新方法，须先离线冻结单一可检验机制。
- **课程未决：**受控under缺参与over无关路由的局部机制confirmed；TA是否接受guard消融/局部损害、FR完整重建但保护结构的解释仍待确认，草稿未发送。原相关usage-rule对照仍suggestive、旧chart负诊断保留。团队排练/提交尚需团队操作。当前研究仅本地分支；没有修改冻结PDF/Slides、部署或新main push。所有模型进程已结束，无待执行请求。
