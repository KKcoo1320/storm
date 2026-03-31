# STORM 拆解与 LangGraph 迁移说明

这份文档的目标不是简单介绍 `stanford-oval/storm`，而是按你们已经做过的 `lightrag_core_simplified` 思路，把 STORM 拆成适合继续工程化的结构。

你可以把它理解成三件事：

1. 把 STORM 原仓库关键 `py` 文件看懂。
2. 判断哪些文件应该原样保留思想，哪些应该抽成 `LangGraph` 节点。
3. 说明怎样做，才能让 `LangGraph` 版跑出来的效果尽量接近原版 STORM。

---

## 一句话结论

STORM 不是一个“图检索 RAG”系统，它更接近一个“多视角调研 + 大纲规划 + 分节写作 + 引用整理”的知识策展流水线。

所以迁到 `LangGraph` 时，核心不是复刻 `graph retrieval`，而是复刻这条主链：

`topic -> persona -> conversation research -> information table -> outline -> section writing -> polish`

这也是为什么这次我在这个目录里搭的 `LangGraph` 版本，主图在 [main_pipeline.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/main_pipeline.py) 里是：

`persona -> curation -> outline -> article -> polish`

---

## STORM 原仓库怎么读

建议阅读顺序不是从 `README` 顺着翻，而是按下面这个依赖顺序读：

1. `knowledge_storm/storm_wiki/engine.py`
2. `knowledge_storm/storm_wiki/modules/knowledge_curation.py`
3. `knowledge_storm/storm_wiki/modules/persona_generator.py`
4. `knowledge_storm/storm_wiki/modules/outline_generation.py`
5. `knowledge_storm/storm_wiki/modules/article_generation.py`
6. `knowledge_storm/storm_wiki/modules/article_polish.py`
7. `knowledge_storm/storm_wiki/modules/storm_dataclass.py`
8. `knowledge_storm/interface.py`
9. `knowledge_storm/rm.py`
10. `knowledge_storm/utils.py`

原因很简单：

- `engine.py` 先告诉你总流程。
- `modules/*.py` 才是业务主体。
- `storm_dataclass.py` 告诉你状态对象到底长什么样。
- `interface.py` 告诉你这个仓库作者脑子里的抽象边界。
- `rm.py` 和 `utils.py` 是检索和切分细节。

---

## 每个关键 py 是干什么的

下面是按“是否关键”来讲，不是把仓库里所有 py 平铺罗列。

### 1. `knowledge_storm/storm_wiki/engine.py`

这是 STORM Wiki 主流水线总控。

关键内容：

- `STORMWikiLMConfigs`
  管不同阶段用什么 LLM。
- `STORMWikiRunnerArguments`
  管超参数。
- `STORMWikiRunner`
  真正把四个阶段串起来。

最重要的方法：

- `run_knowledge_curation_module()`
- `run_outline_generation_module()`
- `run_article_generation_module()`
- `run_article_polishing_module()`
- `run()`

你可以把这个文件理解成 STORM 的“应用层 orchestration”。

对应到你们简化思路里，它不该直接整块搬进 `LangGraph`，而应该拆成：

- 配置对象
- 状态对象
- 节点编排图

这也是我在这个目录里做的：

- 配置在 [config.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/config.py)
- 状态在 [state.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/state.py)
- 图在 [main_pipeline.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/main_pipeline.py)

### 2. `knowledge_storm/storm_wiki/modules/knowledge_curation.py`

这是 STORM 最核心的文件之一。

它定义了 STORM 真正与普通长文生成系统拉开差距的部分：研究过程不是“一次搜一次写”，而是“多 persona、多轮问答式研究”。

关键类：

- `ConvSimulator`
  负责整轮模拟对话。
- `WikiWriter`
  扮演写作者，负责继续提问。
- `TopicExpert`
  把问题拆成搜索 query，调用检索器，再根据结果生成回答。
- `StormKnowledgeCurationModule`
  封装整段 research 流程。

真正关键步骤：

1. 生成问题
2. 问题转 query
3. 检索信息
4. 用检索结果回答
5. 继续追问
6. 累积 conversation log

这部分在迁移时必须保留，因为它是 STORM 的“research engine”。

我在 `LangGraph` 里对应拆成了：

- [modules/curation_module.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/modules/curation_module.py)
- [nodes/curation_node.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/nodes/curation_node.py)

### 3. `knowledge_storm/storm_wiki/modules/persona_generator.py`

这是 STORM 的另一个重要文件。

它做的事不是“生成几个标签”，而是先找相关 Wikipedia 主题，再从类似页面结构中反推有哪些值得关注的 perspective，最后产出 persona。

关键点：

- persona 不是为了角色扮演，而是为了让 research 更广。
- 这是 STORM 里 “perspective-guided question asking” 的来源。

如果你们后面要做轻量版，可以先用固定 persona 模板代替。
如果要逼近原版效果，这块不能删，只能简化实现。

当前 `LangGraph` 对应文件：

- [modules/persona_module.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/modules/persona_module.py)
- [nodes/persona_node.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/nodes/persona_node.py)

### 4. `knowledge_storm/storm_wiki/modules/outline_generation.py`

这个文件是 STORM 的“信息组织”阶段。

它不是直接拿 topic 写大纲，而是先：

1. 用模型直接写一个 draft outline
2. 再根据 research conversation 去 refine

这样做的价值是：

- draft outline 给模型一个基础骨架
- conversation refinement 把真实搜到的信息注入结构里

关键类：

- `StormOutlineGenerationModule`
- `WriteOutline`

这块必须保留，因为 STORM 最终文章质量很大程度依赖 outline 质量。

对应 `LangGraph`：

- [modules/outline_module.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/modules/outline_module.py)
- [nodes/outline_node.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/nodes/outline_node.py)

### 5. `knowledge_storm/storm_wiki/modules/article_generation.py`

这个文件负责“按 section 写正文”。

核心机制：

1. 从 outline 里拿一级 section
2. 用 section title 及其子标题作为 retrieval query
3. 从 `information_table` 检索相关 snippets
4. 给 LLM 一个 section outline + collected info
5. 生成该 section 的带引用文本
6. 把 citation index 合并进全文 reference system

关键类：

- `StormArticleGenerationModule`
- `ConvToSection`

这是 STORM 的第二个真正核心文件，因为输出文章主要就在这里决定。

对应 `LangGraph`：

- [modules/article_module.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/modules/article_module.py)
- [nodes/article_node.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/nodes/article_node.py)

### 6. `knowledge_storm/storm_wiki/modules/article_polish.py`

这个文件负责最后收尾：

- 生成 lead / summary
- 可选全文去重

这部分不是决定 STORM 核心研究能力的地方，但对成品观感很重要。

对应 `LangGraph`：

- [modules/polish_module.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/modules/polish_module.py)
- [nodes/polish_node.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/nodes/polish_node.py)

### 7. `knowledge_storm/storm_wiki/modules/storm_dataclass.py`

这是最容易被忽略、但其实很重要的文件。

它定义了 STORM 流水线中间状态：

- `DialogueTurn`
- `StormInformationTable`
- `StormArticle`

这三个对象很关键：

- `DialogueTurn` 管一轮问答和检索结果
- `StormInformationTable` 管 research 阶段积累下来的全部信息
- `StormArticle` 管文章结构、内容和 citation 映射

这部分不能简单删掉，不然后面 graph state 会很乱。

当前对应：

- [types.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/types.py)

### 8. `knowledge_storm/interface.py`

这个文件是抽象接口层。

重点不是实现，而是作者定义了几条清晰边界：

- `Retriever`
- `KnowledgeCurationModule`
- `OutlineGenerationModule`
- `ArticleGenerationModule`
- `ArticlePolishingModule`
- `Engine`

这非常适合拿来迁移到 `LangGraph`，因为本质上它已经把可节点化的边界说清楚了。

当前对应：

- [interfaces.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/interfaces.py)

### 9. `knowledge_storm/rm.py`

这是检索器层。

支持：

- YouRM
- BingSearch
- VectorRM
- 其他搜索后端

你们如果想接自有语料，最该关注的是 `VectorRM`。

要点：

- STORM 对私有语料不是直接读全文，而是先进 vector store
- 查询时取 top-k chunks/snippets 作为 evidence

### 10. `knowledge_storm/utils.py`

这里最值得关注两块：

1. `QdrantVectorStoreManager.create_or_update_vector_store`
2. `WebPageHelper`

这两个地方决定了 STORM 的“文本切分方式”。

---

## STORM 的 chunk / 文本切分方式到底是什么

这是你前面特别强调的点，所以单独说清楚。

### 情况 A：STORM 用互联网搜索

不是先把整库文档预切 chunk。

流程是：

1. 搜索得到 URL
2. 下载网页正文
3. 通过 `WebPageHelper` 把网页切成 snippets

这里的切分特点：

- 默认 `snippet_chunk_size = 1000`
- `chunk_overlap = 0`
- 分隔符优先级大致是：
  - 双换行
  - 单换行
  - 句号
  - 中文句号
  - 逗号
  - 中文逗号
  - 空格
  - 空字符串

也就是说：

- 它更像“网页证据切片”
- 不是 LightRAG 那种“面向建图和向量检索的一体化 chunk”

### 情况 B：STORM 用自有语料 `VectorRM`

这时会先建 Qdrant 向量库。

切分发生在：

- `QdrantVectorStoreManager.create_or_update_vector_store`

默认参数：

- `chunk_size = 500`
- `chunk_overlap = 100`

分隔符仍然是多级递归分割策略，和 `RecursiveCharacterTextSplitter` 一样的思路。

### 对比 LightRAG

你们 `lightrag_core_simplified` 里：

- chunk 是入口级核心步骤
- 后面还要给 graph extraction 和 retrieval 用

而 STORM 里：

- chunk/snippet 是服务于 evidence retrieval 的
- 它的中心不是 chunk，而是 `information_table + outline + article`

这就是两边架构差异的根本。

---

## 哪些 py 应该“拿出来放到 LangGraph 里”

不是每个文件都该迁。

### 应该抽进 LangGraph 的关键 py

#### 必须迁

1. `knowledge_curation.py`
   因为它是 STORM research 核心。
2. `persona_generator.py`
   因为它决定多视角 coverage。
3. `outline_generation.py`
   因为它决定文章结构。
4. `article_generation.py`
   因为它决定正文质量。
5. `article_polish.py`
   因为它决定最终可读性。
6. `storm_dataclass.py`
   因为它提供状态容器。
7. `interface.py`
   因为它提供最适合 LangGraph 的边界。

#### 不建议整块直接迁

1. `engine.py`
   因为它是串流程的 runner，到了 `LangGraph` 应该改造成 graph orchestration。
2. `rm.py`
   应该保留思想和适配层，不要直接和主图强耦合。
3. `utils.py`
   应该只抽其中必要的 splitter / helper，不要整个搬进主逻辑。

---

## 现在这个 `storm_langgraph` 目录具体做了什么

这是你可以直接交给别人看的部分。

### 目录结构

- [config.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/config.py)
  STORM 超参数统一配置。
- [state.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/state.py)
  `LangGraph` 共享状态。
- [types.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/types.py)
  `Information / DialogueTurn / StormInformationTable / StormArticle` 的轻量实现。
- [interfaces.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/interfaces.py)
  把外部依赖抽成接口。
- [text_splitter.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/text_splitter.py)
  抽出 STORM 里最关键的切分逻辑。
- [modules](/Users/wangbozhi/Documents/New%20project/storm_langgraph/modules)
  真正业务逻辑层。
- [nodes](/Users/wangbozhi/Documents/New%20project/storm_langgraph/nodes)
  `LangGraph` 节点层。
- [main_pipeline.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/main_pipeline.py)
  主图定义。

### 当前主图

`persona -> curation -> outline -> article -> polish`

这已经和 STORM 原版四阶段一一对应了。

---

## 怎么保证 LangGraph 版效果“差不多”

先说结论：

只把结构迁过去，不自动等于效果接近。

要接近原版 STORM，至少要保住下面几个关键机制。

### 1. 保住多 persona research

如果你把 persona 去掉，效果通常会退化成“单路径搜索 + 单路径写作”。

这会直接损失：

- coverage
- breadth
- follow-up question quality

所以即使做简化版，也建议保留：

- 一个基础 factual persona
- 两到三个补充 persona

### 2. 保住多轮 conversation，而不是单轮搜

STORM 强不在“搜”，而在“搜完还能继续问”。

因此要尽量保留：

- `question -> query -> retrieve -> answer -> follow-up`

而不是只做：

- `topic -> retrieve -> write`

### 3. 保住 outline refinement

如果只直接生成 outline，不用 research 结果 refine，大纲会更像模型先验知识，不像真正被 evidence 约束后的结构。

### 4. section writing 继续使用 section-specific retrieval

STORM 不是把所有 evidence 一股脑塞给模型。

它会按 section 做 retrieval，然后单节写作。

这个机制必须保留，否则：

- 全文更容易重复
- section 跑偏概率更高
- citation 会更乱

### 5. citation 映射不能丢

这也是很多重写版最容易做坏的地方。

原版 STORM 很重视：

- section 内局部 citation
- 合并到全文后的统一 citation index

如果这块做差，最终可读性和可信度都会下滑。

---

## benchmark 应该怎么看

你问的不只是“能不能跑”，而是“效果差不多吗”。

这个问题必须拆成两个层面。

### 层面 1：流程对齐

也就是看你是否真的保住了 STORM 的 pipeline 逻辑。

检查项：

1. 是否有 persona 阶段
2. 是否有 multi-turn research
3. 是否有 outline refinement
4. 是否有 section-specific retrieval
5. 是否有 article polishing
6. 是否有 citation remapping

如果这些都没有，哪怕名字叫 STORM，也只是“受 STORM 启发”。

### 层面 2：结果对齐

建议分数据集来看。

#### A. FreshWiki

适合衡量“像不像论文里的 STORM”。

建议指标：

1. `Outline Tree Similarity`
   看生成大纲和参考文章结构像不像。
2. `Section-level ROUGE-L`
   看每节内容覆盖。
3. `Citation Coverage`
   有多少句子带证据引用。
4. `Reference Diversity`
   文章里用了多少独立来源。

#### B. WildSeek

适合衡量“对真实用户问题有没有帮助”。

建议指标：

1. `Goal Coverage`
2. `Human Preference`
3. `Citation Helpfulness`

### 如果你们还想和 LightRAG 方案比

不要直接只比最终文章。

建议拆成：

1. `Research Quality`
   哪个系统搜到的信息更全面、更少重复。
2. `Outline Quality`
   哪个系统组织结构更好。
3. `Writing Quality`
   在相同 evidence 条件下，哪个系统写得更完整。

这样才能知道差异来自：

- 检索
- 组织
- 写作

而不是全混在一起。

---

## 当前版本已经做到什么程度

### 已完成

1. 把 STORM 核心结构拆成 `LangGraph` 风格骨架。
2. 把关键 py 的职责和迁移逻辑写清楚。
3. 把 STORM 的文本切分方式单独抽出来说明。
4. 给出 benchmark 建议。
5. 所有新增 Python 文件已过 `py_compile` 静态语法检查。

### 还没做的

1. 没有接真实 LLM。
2. 没有接真实搜索 API。
3. 没有接真实 Qdrant / VectorRM。
4. 没有跑 FreshWiki / WildSeek 实验。

所以现在这份目录更准确地说是：

- 可迁移的工程骨架
- 结构上忠于 STORM
- 行为上还需要接真实后端才能验证“效果差不多”

---

## 如果下一步要把它做成真的可运行版本

优先顺序建议如下：

1. 把 `interfaces.py` 对应的外部实现接上
   - persona generator
   - question asker
   - query generator
   - retriever
   - answer synthesizer
   - outline generator
   - section writer
   - polisher
2. 先跑一个 `VectorRM` 版
   因为它最容易复现和评测。
3. 再跑一个搜索 API 版
   更接近 STORM 原味。
4. 最后再补 benchmark script

---

## 相关文件

- 架构说明：[ARCHITECTURE.md](/Users/wangbozhi/Documents/New%20project/storm_langgraph/ARCHITECTURE.md)
- Benchmark 说明：[BENCHMARK.md](/Users/wangbozhi/Documents/New%20project/storm_langgraph/BENCHMARK.md)
- 主图定义：[main_pipeline.py](/Users/wangbozhi/Documents/New%20project/storm_langgraph/main_pipeline.py)

---

## 最后一句话

如果你是要“做一个和 STORM 非常像的 LangGraph 版”，那关键不是把所有 py 搬过去，而是保住 STORM 的四个灵魂步骤：

1. 多视角调研
2. 基于调研的大纲生成
3. 基于 section 的证据写作
4. 基于引用系统的全文整理

这四步保住了，`LangGraph` 版才有机会和原版效果接近。
