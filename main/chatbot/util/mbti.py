# chatbot/util/mbti.py
from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple

Answer = Literal["O", "X", "o", "x", True, False]

@dataclass
class SurveyResult:
    invest: str          # "에겐형" or "테토형"
    consume: str         # "에겐형" or "테토형"
    detail: Dict[str, List[int]]  # 각 축에서 가산된 문항 인덱스

def _count_true(answers: Dict[int, Answer], keys: List[int]) -> int:
    c = 0
    for k in keys:
        v = answers.get(k, "X")
        if isinstance(v, bool):
            c += int(v)
        else:
            c += int(str(v).upper() == "O")
    return c

def classify_egen_teto(answers: Dict[int, Answer]) -> SurveyResult:
    """
    answers 예시:
    {
      1:"O", 2:"X", 3:"O", ..., 10:"X"
    }
    """
    # 이미지 기준 매핑
    invest_egen = [2, 7, 8, 10]
    invest_teto = [3, 4, 6, 9]
    consume_egen = [5, 10]
    consume_teto = [3, 4, 9]

    i_egen = _count_true(answers, invest_egen)
    i_teto = _count_true(answers, invest_teto)
    c_egen = _count_true(answers, consume_egen)
    c_teto = _count_true(answers, consume_teto)

    invest_type = "에겐형(안정 추구)" if i_egen >= i_teto else "테토형(성장 추구)"
    consume_type = "에겐형(안정 추구)" if c_egen >= c_teto else "테토형(성장 추구)"

    detail = {
        "invest:+에겐": [q for q in invest_egen if str(answers.get(q, "X")).upper()=="O" or answers.get(q) is True],
        "invest:+테토": [q for q in invest_teto if str(answers.get(q, "X")).upper()=="O" or answers.get(q) is True],
        "consume:+에겐": [q for q in consume_egen if str(answers.get(q, "X")).upper()=="O" or answers.get(q) is True],
        "consume:+테토": [q for q in consume_teto if str(answers.get(q, "X")).upper()=="O" or answers.get(q) is True],
    }
    return SurveyResult(invest=invest_type, consume=consume_type, detail=detail)
