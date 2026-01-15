"""Memo
1. green agent负责接收purple call来的message，决定是执行环境操作还是发布下一个问题，即当前是否一个turn结束了。
2. 算分数的逻辑放在evaluator之类的文件里，green agent决定一个turn结束之后调用打一个轮次分数，evaluator自动计算总分 - 最终在src/agent.py里evaluator需要通过update artifacts上传评测结果
"""