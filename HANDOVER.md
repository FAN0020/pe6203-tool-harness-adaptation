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

### 当前最新断点：discovery_contract 进入冻结的独立验证，尚未启动

- `fe9f500`已结束6单元开发试点；273原始文件、303源码输入文件归档并离线复核。变化任务候选正常完成2/2、SP1/2，TF9.9对9.8；完整质量均0/2，保持条件相等。全部四条未调用故障发现工具，完成差异原因未证实。只符合事前较弱的试点晋级规则，**不是双重改善**。
- `50dd4f5`冻结`experiments/discovery-contract-validation-v1.json`与对应config：两批各18条，总36条；repeat0–2为A、3–5为B。两批分别要求变化任务完成数及完整质量通过数同时严格高于SP，TF不下降；保持条件完成/质量/TF均不下降。未知不计pass。同一协调者盲审，不是独立人工审阅。
- 候选逐字复用试点的两处Context7说明替换、评分属性不变。原生源码/schema/模型/预算不变；不调参、不挑胜利重复、不因首批不利提前停止第二批。完整旧正负证据保留，不重跑试点或依赖探针。
- 下一步prepare/build36条，审计知识哈希与共享原PDF、冻结盲号映射/来源后执行。此断点无模型进程，HTTP4783已停，执行前需以同一fixture目录重启。Goal活动，目标未完成。

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
