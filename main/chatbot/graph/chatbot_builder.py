from langgraph.graph import StateGraph, END

from node.analysis import AnalysisNode
from node.egen_teto_classifier import EgenTetoClassifierNode
from node.get_user_data import GetUserDataNode
from node.greet import GreetingNode
from state.schema import OverallState



class ChatBuilder:
    def __init__(self):
        self.greeting_node = GreetingNode()
        self.egen_teto_classifier_node = EgenTetoClassifierNode()
        self.get_user_data_node = GetUserDataNode()
        self.analysis_node = AnalysisNode()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(OverallState)
        graph.add_node("greeting", self.greeting_node)
        graph.add_node("egen_teto_classifier", self.egen_teto_classifier_node)
        graph.add_node("get_user_data", self.get_user_data_node)
        graph.add_node("analysis", self.analysis_node)
        graph.set_entry_point("greeting")
        graph.add_edge("greeting", "egen_teto_classifier")
        graph.add_edge("egen_teto_classifier", "get_user_data")
        graph.add_edge("get_user_data", "analysis")
        graph.add_edge("analysis", END)

        compile_graph = graph.compile()
        return compile_graph
    
    def run_graph_streaming(self, input_text: str):
        return self.graph.invoke({"input": input_text})