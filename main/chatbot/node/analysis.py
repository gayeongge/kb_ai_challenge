from state.schema import OutputState


class AnalysisNode:
    """
        RAG 데이터와 사용자 성향 데이터, 그리고 소비 데이터를 분석하여 피드백하는 노드
    """
    def __init__(self):
        pass

    def __call__(self, state):
        return OutputState(output="Graph 연결 확인 용 리턴 값")