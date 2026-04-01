from __future__ import annotations


END = "__end__"


class StateGraph:
    def __init__(self, _state_type=None):
        self._nodes = {}
        self._edges = {}
        self._entry_point = None

    def add_node(self, name, func):
        self._nodes[name] = func

    def set_entry_point(self, name):
        self._entry_point = name

    def add_edge(self, source, target):
        self._edges[source] = target

    def compile(self):
        graph = self

        class CompiledGraph:
            async def ainvoke(self, state):
                current = graph._entry_point
                current_state = dict(state)
                while current and current != END:
                    node = graph._nodes[current]
                    current_state = await node(current_state)
                    current = graph._edges.get(current, END)
                return current_state

        return CompiledGraph()
