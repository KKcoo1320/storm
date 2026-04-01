# STORM LangGraph 流程图

## 1. 总体 LangGraph 流程

```mermaid
flowchart TD
    A["Input Topic"] --> B["Persona Node"]
    B --> C["Curation Node"]
    C --> D["Outline Node"]
    D --> E["Article Node"]
    E --> F["Polish Node"]
    F --> G["Final Article / Artifacts"]
```

## 2. RAG / Research 主链

```mermaid
flowchart LR
    Q["Topic / User Goal"] --> P["Persona Expansion"]
    P --> W["Question Asking"]
    W --> X["Query Generation"]
    X --> R["Retriever"]
    R --> S["Snippet / Evidence Collection"]
    S --> A["Answer Synthesis"]
    A --> H["Conversation History"]
    H --> W
    H --> T["Information Table"]
    T --> O["Outline Refinement"]
    O --> G["Section Retrieval + Writing"]
    G --> L["Lead / Polish"]
```

## 3. 并行 Agent 结构

STORM 的“并行”更准确地说是多 persona research 并行，而不是多个完全独立的大模型随意互聊。

```mermaid
flowchart TB
    T["Topic"] --> P1["Persona 1"]
    T --> P2["Persona 2"]
    T --> P3["Persona 3"]

    P1 --> C1["Ask -> Query -> Retrieve -> Answer"]
    P2 --> C2["Ask -> Query -> Retrieve -> Answer"]
    P3 --> C3["Ask -> Query -> Retrieve -> Answer"]

    C1 --> M["Merge Conversations"]
    C2 --> M
    C3 --> M

    M --> I["StormInformationTable"]
    I --> O["Outline Generation"]
    O --> S["Section-by-section Writing"]
    S --> F["Final Polish"]
```

## 4. 和 LightRAG 思路的差异

```mermaid
flowchart LR
    subgraph LightRAG
        L1["Document"] --> L2["Chunk"]
        L2 --> L3["Entity / Relation Extraction"]
        L3 --> L4["Graph + Vector Store"]
        L4 --> L5["Hybrid Retrieval"]
        L5 --> L6["Answer"]
    end

    subgraph STORM
        S1["Topic"] --> S2["Persona / Research"]
        S2 --> S3["Conversation Log"]
        S3 --> S4["Information Table"]
        S4 --> S5["Outline"]
        S5 --> S6["Section Writing"]
        S6 --> S7["Polish"]
    end
```

## 5. 当前 demo 的运行方式

运行文件：

- `storm_langgraph/demo/run_demo.py`

运行后会产出：

- `storm_langgraph/demo_output/demo_article.txt`
- `storm_langgraph/demo_output/demo_state.json`

