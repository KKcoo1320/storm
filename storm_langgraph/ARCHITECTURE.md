# STORM LangGraph 拆解

这个目录不是直接照抄 `stanford-oval/storm`，而是按你们 `lightrag_core_simplified` 的思路，把 STORM 拆成了更适合 `LangGraph` 的四层：

1. `modules/`
   这里放真正的业务逻辑，和你们 LightRAG 精简版里的 `chunking_module / graph_module / retrieval_module` 对齐。
2. `nodes/`
   这里只做状态读写，把模块封装成 `LangGraph` 节点。
3. `state.py`
   定义整条流水线共享状态。
4. `main_pipeline.py`
   定义图结构。

## 1. STORM 原版核心步骤

原版 `STORMWikiRunner` 实际上就是 4 个大模块串起来：

1. `run_knowledge_curation_module`
   入口文件：`knowledge_storm/storm_wiki/engine.py`
   内部核心：`modules/knowledge_curation.py`
   作用：多 persona 对话式检索，收集 conversation log 和 raw references。
2. `run_outline_generation_module`
   核心：`modules/outline_generation.py`
   作用：先直接生成 draft outline，再结合 conversation 精炼 outline。
3. `run_article_generation_module`
   核心：`modules/article_generation.py`
   作用：按一级 section 并行写段落，并把 citation index 统一映射回 article。
4. `run_article_polishing_module`
   核心：`modules/article_polish.py`
   作用：补 lead/summary，可选去重。

## 2. 和 LightRAG 的关键差异

LightRAG 精简版主链是：

`document -> chunk -> entity/relation extraction -> vector store -> graph retrieval -> answer`

STORM 主链是：

`topic -> perspective/persona -> multi-turn research conversation -> information table -> outline -> section writing -> polish`

所以两者最大的结构差异不是“模型不同”，而是“状态对象不同”：

- LightRAG 的中心状态是 `chunks / graph / vectors`
- STORM 的中心状态是 `conversation_log / information_table / outline / article`

## 3. Chunk 与文本切分

这部分最容易混淆，我单独写清楚：

1. STORM 原版主流程没有像 LightRAG 那样在入口就做全量 chunking。
2. STORM 的“切分”主要出现在两个地方：
   - `knowledge_storm/utils.py -> WebPageHelper`
     把网页正文按 `snippet_chunk_size=1000` 左右切成 snippets，供搜索结果引用。
   - `knowledge_storm/utils.py -> QdrantVectorStoreManager.create_or_update_vector_store`
     当使用 `VectorRM` 接用户自带语料时，使用 `RecursiveCharacterTextSplitter`，默认：
     - `chunk_size=500`
     - `chunk_overlap=100`
     - separators 包含换行、句号、逗号、空格、中英文标点
3. 原版 STORM article generation 阶段真正拿来检索的是 `snippet`，不是 LightRAG 那种语义 chunk + graph hybrid。

所以如果你们后面要“把 STORM 往 LightRAG 的 chunk/graph 风格靠”，正确做法不是硬抄 graph，而是先决定：

- 保持 STORM 原味：`snippet retrieval + outline writing`
- 或做混合版：`snippet retrieval + entity graph memory + outline writing`

这两条都能进 LangGraph，但不是同一个系统。

## 4. 这个 LangGraph 版本里每个 py 在做什么

- `config.py`
  把 STORM 里零散超参数收束成一个配置对象。
- `types.py`
  提供 `Information / DialogueTurn / StormInformationTable / StormArticle` 等核心数据结构。
- `text_splitter.py`
  抽出 STORM 在 `VectorRM/WebPageHelper` 里隐含的切分策略，便于后续换成你们自己的 splitter。
- `modules/persona_module.py`
  负责 persona 生成，对应 STORM 的 `persona_generator.py`。
- `modules/curation_module.py`
  负责多 persona 多轮对话式检索，对应 `knowledge_curation.py`。
- `modules/outline_module.py`
  负责 draft outline + refined outline，对应 `outline_generation.py`。
- `modules/article_module.py`
  负责 section 检索与 section 写作，对应 `article_generation.py`。
- `modules/polish_module.py`
  负责 lead 和去重，对应 `article_polish.py`。
- `modules/benchmark_module.py`
  给出后续做 FreshWiki / WildSeek 对齐时建议看的指标。
- `nodes/*.py`
  模块到 `LangGraph` 节点的薄封装。
- `main_pipeline.py`
  组图，形成：
  `persona -> curation -> outline -> article -> polish`

## 5. 当前版本的边界

这个版本先解决“结构迁移”和“核心步骤显式化”，还没有直接绑定某一个真实 LLM / Search / Qdrant 后端。

这样做是有意的，因为 STORM 原版强依赖：

- DSPy
- 外部搜索 API
- 外部 LLM
- 可选 Qdrant / 向量库

我这里先把这些都变成了接口层，后面你们只要把现有模型调用器接进来，就能保留 LangGraph 编排，同时尽量贴近原版行为。

