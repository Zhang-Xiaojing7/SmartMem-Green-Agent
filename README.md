# agentbeats的主要交互逻辑
agentbeats平台把scenario.toml里的参赛者等配置发给green， green开始评估流程，中间状态变化通过update_status更新，最终的评估结果通过add_artifacts提交，这会被更新在leaderboard上（默认是results文件夹里）

green评估过程中通过talk_to_agent和purple交互

# green_agent_v2
它继承自原来的green agent文件夹，去除了各种通用设施，保留了核心的试题生成和评估逻辑。

- 各种基础的数据结构定义被统一存放到了base.py中

- 原先的AdaptiveGenerator(https://vscode.dev/github/ziiiiiiiiyan/SmartMem-Green-Agent/blob/main/archieved/green_agent/adaptive_loop.py#L508)改造成了instruction_generator.py中的AdaptiveGenerator，添加了生成初始题组的逻辑，强制生成了金字塔形的配比。抽离出了生成题目的prompt放在prompt.py中，负责生成题目的LLM被包装在LLMCaseGenerator中。

- 原先的adaptive_loop.py中的WeaknessAnalyzer、AdaptiveEvaluator(x 逻辑搬错了已删除，直接放agent.py/run里去)被放到现在evaluator.py中。考虑green agent发出instruction后未必purple agent能够一次性执行完成、同时单纯的对话指令实际上没有评估对象，我把evaluator调整为和analyser联动的版本，即evaluator接收每个turn的执行历史进行评估，调用analyser同步弱点信息。green可以调用evaluator.analyser.get_top_weaknesses(k)来获取前k个弱点丢给AdaptiveGenerator生成新的题组。

- adaptive_loop.py中的主循环AdaptiveTestLoop逻辑被放在了src/agent.py中

- **还没有完成的**

   1. 可视化和报告生成这部分还没搬运

   2. prompt里直接把设备信息写死，但是现在还保留了占位符

## MEMO
一个test round包含n个test case，test case的数量=当前关注的前k个弱点的数量\times希望针对每个弱点生成的test case的数量