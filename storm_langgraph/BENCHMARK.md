# Benchmark 建议

## 可以对齐到什么程度

如果你们把真实的：

- persona generator
- question asker
- query generator
- retriever
- answer synthesizer
- outline generator
- section writer
- polisher

都接成和原版 STORM 同档次的模型/检索器，这套 LangGraph 结构在“流程拓扑”上已经可以做到非常接近原版：

- 相同的研究阶段
- 相同的 outline 阶段
- 相同的 section-by-section 写作阶段
- 相同的 polish 阶段

真正会拉开差距的通常不是 `LangGraph` 本身，而是下面三件事：

1. 检索后端
   Bing / You / Serper / VectorRM 会直接决定信息覆盖率。
2. conversation 阶段的 question quality
   STORM 的强项就在这里。
3. section writing 与 citation remapping
   如果写作模型弱，最后文章会明显变差。

## 推荐 benchmark 维度

### FreshWiki

更接近 STORM 论文原始任务，建议看：

1. `Outline Tree Similarity`
   比较生成大纲和参考文章大纲的层级相似度。
2. `Section-level ROUGE-L`
   按一级或二级 section 比较文本覆盖。
3. `Citation Coverage`
   最终文章里带 citation 的句子比例。
4. `Reference Diversity`
   独立 url 数量、每节平均引用源数量。

### WildSeek

更适合看“是否帮用户完成复杂信息搜集”，建议看：

1. `Goal Coverage`
   是否覆盖用户目标里的关键子问题。
2. `Human Preference`
   两两对比原版 STORM 和 LangGraph 版。
3. `Citation Helpfulness`
   引用是否真的支持结论，而不是装饰性引用。

## 如果你们要做和 LightRAG 的交叉 benchmark

我建议不要直接比“生成文章全文质量”，而是拆两层：

1. `Research Quality`
   看检索出来的信息是否全面、是否重复少。
2. `Writing Quality`
   在同一份 evidence 上比较 outline 和 article generation。

否则会把 “retrieval 差异” 和 “writing 差异” 混在一起。

## 当前目录下还没直接跑 benchmark 的原因

现在还没有接入：

- 真实搜索 API
- 真实 LLM
- FreshWiki / WildSeek 数据

所以这次先把 benchmark 方案和接口位置定下来，等你们确认要用哪套模型与数据源，我就可以继续往下把评测脚本补齐。
