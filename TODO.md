

20251127,已完成
1. 每个任务，处理进度 log 放在 logs 中；
2. 任务执行过程中，处理速度显示当前批次的处理速度，而不是累计处理速度；
3. 任务管理页面，"token 使用" 区分 input 和 output；
4. atomic 问答对生成存在部分答案缺失；
5. multi-hop 问答对生成中报如下提示"WARNING  Empty multi-hop response received"
6. multi-hop / atomic 答案需要适当延申，回答内容应该尽可能丰富篇幅尽可能长一些，建议修改相应的提示词；
7. atomic 问答对生成时应该只使用少量的图谱一跳信息，但是目前使用了太多的图谱实体和关系。