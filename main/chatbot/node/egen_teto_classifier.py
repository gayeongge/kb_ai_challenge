
from typing import Dict, Tuple, Optional

QUESTIONS = {
    2: "기대 수익률이 낮더라도 원금 손실이 없는 상품을 우선 고려하시나요?",
    3: "경제/투자 정보를 뉴스·유튜브·커뮤니티 등에서 적극적으로 찾아보시나요?",
    4: "안정보다 성장(다소 위험 감수) 쪽을 선호하시나요?",
    5: "단기 매매보다 장기투자가 더 맞다고 생각하시나요?",
    6: "정부 지원 상품보다 본인 투자 수익을 더 자신하시나요?",
    7: "정부/은행 보증의 안정적인 상품을 선호하시나요?",
    8: "손실의 고통(–10%)이 이익(+10%)의 기쁨보다 더 크게 느껴지나요?",
    9: "타인 성공사례/트렌드보다 자신의 분석을 더 신뢰하나요?",
    10: "매달 예산을 세우고 지출을 꼼꼼히 추적하려고 노력하시나요?"
}
class EgenTetoClassifierNode:
    """
        사전 정의된 에겐 테토 분류 질문을 수행하고 그 결과를 반환하는 노드
    """
    def __init__(self):
        pass

    def __call__(self, state: Dict):
        return state

    @staticmethod
    def next_question(state: Dict) -> Tuple[Optional[int], Optional[str]]:
                # 수정 — 문자열 키/값 변환
        answers_in = state.get("survey_answers", {}) or {}
        answers: Dict[int, bool] = {}
        for k, v in answers_in.items():
            try:
                qid = int(k)  # "2" -> 2
            except Exception:
                continue
            if isinstance(v, bool):
                answers[qid] = v
            else:
                answers[qid] = str(v).strip().upper() == "O"
        for qid in sorted(QUESTIONS.keys()):
            if qid not in answers:
                return qid, QUESTIONS[qid]
        return None, None

    @staticmethod
    def record_answer(state: Dict, qid: int, answer_ox: str):
        ans = True if str(answer_ox).upper() == "O" else False
        state.setdefault("survey_answers", {})[qid] = ans

    @staticmethod
    def compute_type(state: Dict) -> str:
        """
        2~10번 문항을 가중치 기반으로 스코어링.
        - 기본 원칙: O가 특정 성향에 +w, X는 반대 성향에 +w (단, Q5/10은 대칭 완화)
        - 결과 차이가 작으면 NEUTRAL 처리 (중립 밴드)
        """
        answers: Dict[int, bool] = state.get("survey_answers", {})

        # 문항별 O 응답의 기본 귀속 성향과 가중치
        # 2: 원금보전 선호 → EGEN, 3: 투자정보 탐색 → TETO, 4: 성장선호 → TETO
        # 5: 장기투자 선호 → EGEN(약하게), 6: 본인수익 자신 → TETO, 7: 보증상품 선호 → EGEN
        # 8: 손실회피 큼 → EGEN, 9: 자기분석 신뢰 → TETO, 10: 예산/추적 → EGEN(소비 습관)
        O_WEIGHT = {
            2: ("EGEN", 1.0),
            3: ("TETO", 1.0),
            4: ("TETO", 1.0),
            5: ("EGEN", 0.6),
            6: ("TETO", 1.0),
            7: ("EGEN", 1.0),
            8: ("EGEN", 1.0),
            9: ("TETO", 0.8),
            10: ("EGEN", 0.7),
        }

        # X 응답 시 반대로 가산. 다만 Q5/10은 ‘반대 성향’ 증거가 약하므로 완화 계수 적용
        # (예: 장기투자 X → 곧바로 TETO 확신이라기보단 약한 신호)
        X_WEAKEN = {5: 0.6, 10: 0.4}  # 1.0이면 대칭, <1.0이면 완화
        EGEN = 0.0
        TETO = 0.0

        for qid in range(2, 11):
            if qid not in answers:
                continue
            raw = answers[qid]
            if isinstance(raw, bool):
                ans = raw
            else:
                ans = str(raw).strip().upper() == "O"   # "O" -> True, "X" -> False
            if qid not in O_WEIGHT:
                continue

            target, w = O_WEIGHT[qid]
            if ans is True:  # O
                if target == "EGEN":
                    EGEN += w
                else:
                    TETO += w
            else:  # X → 반대 성향으로 가산
                weaken = X_WEAKEN.get(qid, 1.0)
                w2 = w * weaken
                if target == "EGEN":
                    TETO += w2
                else:
                    EGEN += w2

        # 중립 밴드: 차이가 작으면 중립 처리
        diff = TETO - EGEN
        THRESH = 0.5  # 임계값 (원하면 0.7~1.0로 조정)
        if abs(diff) < THRESH:
            return "NEUTRAL-중립형"
        return "TETO-성장 추구형" if diff > 0 else "EGEN-안정 추구형"