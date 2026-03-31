from ..modules import curation_module


def build_node(config, question_asker, query_generator, retriever, answer_synthesizer):
    async def node(state):
        information_table, conversation_log = curation_module.run(
            config=config,
            topic=state["topic"],
            personas=state["personas"],
            question_asker=question_asker,
            query_generator=query_generator,
            retriever=retriever,
            answer_synthesizer=answer_synthesizer,
            ground_truth_url=state.get("ground_truth_url", ""),
        )
        return {
            **state,
            "information_table": information_table,
            "conversation_log": conversation_log,
        }

    return node

