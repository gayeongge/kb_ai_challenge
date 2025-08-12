from node.react import ReactAgentNode
from langgraph.graph import StateGraph, END

from state.schema import OverallState


class GraphBuilder:
    def __init__(self):
        self.react_node = ReactAgentNode()
        self.graph = self.build_graph()

    def build_graph(self):
        graph = StateGraph(OverallState)
        graph.add_node("react", self.react_node)
        graph.add_edge("react", END)
        graph.set_entry_point("react")
        compile_graph=graph.compile()
        return compile_graph

    def run_graph_streaming(self, input_text: str):
        return self.graph.invoke({"input":input_text})