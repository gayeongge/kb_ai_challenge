# chatbot/node/feedback.py
import json
import re
from typing import Dict, Any, List
from langchain_ollama import ChatOllama
from chatbot.util.mbti import classify_egen_teto
from chatbot.util.rag import rag_search

SYSTEM = """당신은 개인 금융 코치입니다.
- 응답은 한국어로 작성합니다.
- 기본 형식: 1) 한줄요약 2) 지출 분석 3) 다음달 액션 3가지(금액/비율/구체 실행) 4) 추천 제도/상품(근거·주의사항).
- 과도한 투자권유 금지, 원금손실/세금/한도 경고 포함.
"""

# 간단 분류 모드(두 줄만) 전용 시스템 프롬프트
SYSTEM_CLASSIFY_ONLY = """너는 설문 분류 결과를 그대로 출력하는 분석기다.
- 한국어로 작성한다.
- 아래 형식 **그대로** 출력한다:
투자 성향: {투자 성향}
소비 성향: {소비 성향}
- 다른 문장이나 설명을 절대 추가하지 않는다.
"""

def _to_int_amount(x: Any) -> int:
    if x is None:
        return 0
    s = str(x)
    # 숫자/소수점/마이너스만 남기기
    s = re.sub(r"[^\d\.\-]", "", s)
    if s == "" or s == "." or s == "-":
        return 0
    try:
        return int(float(s))
    except Exception:
        return 0

class FeedbackAgentNode:
    def __init__(self, base_url: str = "", model: str = "gemma3:1b"):
        # 필요시 매개변수 조정 (temperature/top_p 등)
        self.llm = ChatOllama(model=model, streaming=True, base_url=base_url)

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # ── 입력 꺼내기
        survey = state.get("survey_answers", {}) or {}
        seg = state.get("user_segment", "사회초년생")
        recs: List[Dict[str, Any]] = state.get("card_records", []) or []

        # ── 설문 분류(에겐/테토)
        sr = classify_egen_teto(survey)  # invest, consume, detail 같은 속성 제공 가정

        # ── 카드 요약 (카테고리 합계: amount 누적)
        by_cat: Dict[str, int] = {}
        for r in recs:
            cat = (r.get("category") or r.get("cat") or "기타")
            amt = _to_int_amount(r.get("amount"))
            by_cat[cat] = by_cat.get(cat, 0) + amt

        # ── RAG 컨텍스트
        try:
            rag_ctx = rag_search(
                f"{seg}에게 적합한 절세/정부지원/저축/신용·보험 팁과 주의점",
                k=5
            ) or ""
        except Exception:
            rag_ctx = ""

        # ── 분기: 간단 분류 모드(두 줄만)
        # - /classify처럼 결과만 원할 때 state["mode"] == "classify" 또는 state["simple"] == True로 호출
        if state.get("mode") == "classify" or state.get("simple") is True:
            prompt = f"""{SYSTEM_CLASSIFY_ONLY}

[입력]
투자 성향: {sr.invest}
소비 성향: {sr.consume}
"""
            out = self.llm.invoke(prompt).content
            return {"output": out}

        # ── 기본(코치형) 프롬프트
        prompt = f"""{SYSTEM}

[사용자 세그먼트] {seg}

[설문 결과]
- 투자 성향: {sr.invest}
- 소비 성향: {sr.consume}
- 근접 문항(참고): {json.dumps(sr.detail, ensure_ascii=False)}

[카드내역 합계(카테고리:금액)] {json.dumps(by_cat, ensure_ascii=False)}

[내부 지식 컨텍스트]
{rag_ctx}

위 정보를 반영하여 이번 달 소비 패턴의 핵심 이슈와 다음 달 개선 액션을 제시하세요.
'에겐형'이면 안전/현금흐름 중심, '테토형'이면 성장/리스크관리 중심으로 톤을 조절하세요.
"""
        out = self.llm.invoke(prompt).content
        return {"output": out}
