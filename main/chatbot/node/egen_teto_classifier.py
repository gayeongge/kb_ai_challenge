class EgenTetoClassifierNode:
    """
        사전 정의된 에겐 테토 분류 질문을 수행하고 그 결과를 반환하는 노드
    """
    def __init__(self):
        pass

    def __call__(self, state):
        # egen_teto 질문은 코딩으로 했다 치자.
        state['egen_teto_data'] = "너는 에겐이야."
        return state