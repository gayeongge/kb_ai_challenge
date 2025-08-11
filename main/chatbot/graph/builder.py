from langgraph.graph import StateGraph, END
from chatbot.state.schema import InputState
from chatbot.node.react import ReactAgentNode

class GraphBuilder:
    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(InputState)
        react_node = ReactAgentNode()
        graph.add_node("react", react_node)
        graph.add_edge("react", END)
        graph.set_entry_point("react")
        compile_grpah=graph.compile()
        return compile_grpah

    def run_graph_streaming(self, input_text: str):
        return self.graph.invoke({"input":input_text})
        # for output in self.graph.stream({"input": input_text}):
        #     yield output