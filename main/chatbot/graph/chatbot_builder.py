# chat_builder.py
from langgraph.graph import StateGraph, END
from node.analysis import AnalysisNode
from node.egen_teto_classifier import EgenTetoClassifierNode
from node.greet import GreetingNode
from state.schema import OverallState

class ChatBuilder:
    def __init__(self):
        self.greeting_node = GreetingNode()
        self.egen_teto_classifier_node = EgenTetoClassifierNode()
        self.analysis_node = AnalysisNode()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(OverallState)
        graph.add_node("greeting", self.greeting_node)
        graph.add_node("egen_teto_classifier", self.egen_teto_classifier_node)
        graph.add_node("analysis", self.analysis_node)

        graph.set_entry_point("greeting")
        graph.add_edge("greeting", "egen_teto_classifier")
        graph.add_edge("egen_teto_classifier", "analysis")
        graph.add_edge("analysis", END)
        return graph.compile()

    def run_graph_streaming(self, input_text: str, user_data: dict | None = None):
        init_state = {"input": input_text}
        if user_data:
            init_state["user_data"] = user_data   # {"salary":..., "card_history":[...]}
        return self.graph.invoke(init_state)
