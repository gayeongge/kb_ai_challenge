import os
import logging
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from state.schema import OutputState

# ✅ RAG util 경로 주의: 프로젝트 구조에 맞춰 조절
# from util.rag import rag_context                # (현재 파일 기준 상위/util이면 이거)
from util.rag import rag_context          # (예: main/chatbot/util/rag.py 인 경우)

# -----------------------------------------------------------------------------
# .env 로드 (명시 경로 → 실패 시 기본 탐색)
# -----------------------------------------------------------------------------
ENV_EXPLICIT = r"C:\kb_proj\kb_ai_challenge\.env"
if os.path.exists(ENV_EXPLICIT):
    load_dotenv(dotenv_path=ENV_EXPLICIT)
else:
    load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# LLM 생성: OpenAI 우선 → 실패 시 Ollama 폴백
# -----------------------------------------------------------------------------
def create_llm() -> ChatOpenAI | ChatOllama:
    api_key = os.getenv("OPENAI_API_KEY", "")
    # OpenAI 시도
    if api_key and not api_key.startswith(("your_ope", "sk-xxxxx")):
        try:
            logger.info("[LLM] Using OpenAI gpt-4o-mini")
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=api_key,
                streaming=True,   # 스트리밍 콜백 안 쓰면 내부적으로 chunk를 모아 반환
                temperature=0.4,
                timeout=60,
            )
        except Exception as e:
            logger.warning(f"[LLM] OpenAI init failed, fallback to Ollama: {e}")

    # Ollama 폴백
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        logger.info(f"[LLM] Fallback to Ollama (base_url={base_url})")
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            streaming=True,
            base_url=base_url,
            temperature=0.4,
        )
    except Exception as e:
        # 최후: OpenAI(키 없어도) 시도하여 에러를 명확히 표면화
        logger.error(f"[LLM] Ollama init failed: {e}")
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key or "invalid",
            streaming=False,
            temperature=0.4,
        )

LLM = create_llm()

# -----------------------------------------------------------------------------
# 선택적: 간단한 에이전트 노드 (사용 안 하면 삭제해도 OK)
# -----------------------------------------------------------------------------
class ReactAgentNode:
    """데모용: 간단 툴을 가진 ReAct 에이전트. (현재 파이프라인에서 필수는 아님)"""
    def __init__(self):
        from langchain_core.tools import Tool
        from langchain.agents import initialize_agent, AgentType

        base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        agent_llm = ChatOllama(model="gemma3:1b", streaming=True, base_url=base_url)

        add_tool = Tool(
            name="Calculator",
            func=self.add_numbers,
            description="Adds numbers given as space-separated input. Example input: '3 5'",
        )
        tools = [add_tool]

        self.executor = initialize_agent(
            tools, agent_llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
        )

    @staticmethod
    def add_numbers(input: str) -> str:
        try:
            parts = [p for p in input.strip().split() if p.replace(".", "", 1).isdigit()]
            nums = [float(p) for p in parts]
            return str(sum(nums))
        except Exception:
            return "Error..."

    def __call__(self, state) -> OutputState:
        input_text = state["input"] if isinstance(state, dict) and "input" in state else state
        output = self.executor.invoke({"input": input_text})["output"]
        return OutputState(output=output)

# -----------------------------------------------------------------------------
# 메인: RAG + LLM 피드백 노드
# -----------------------------------------------------------------------------
class ReactNode:
    """
    성향(에겐/테토/중립) + 카드내역 분석 결과로 질의문을 만들고,
    rag_data 임베딩 문맥을 끌어와 LLM으로 최종 피드백을 생성.
    """

    def __init__(self):
        pass

    @staticmethod
    def _persona_from_type(egen_teto_type: str) -> str:
        if not egen_teto_type:
            return "NEUTRAL"
        if egen_teto_type.startswith("EGEN"):
            return "EGEN"
        if egen_teto_type.startswith("TETO"):
            return "TETO"
        return "NEUTRAL"

    @staticmethod
    def _build_query(
        egen_teto_type: str, analysis_result: Dict, card_history: List[Dict]
    ) -> Tuple[str, str, str]:
        persona = ReactNode._persona_from_type(egen_teto_type)

        salary = int(analysis_result.get("salary", 0) or 0)
        total_spent = int(analysis_result.get("total_spent", 0) or 0)
        spend_ratio = float(analysis_result.get("spend_ratio", 0) or 0.0)
        tx_count = int(analysis_result.get("tx_count", 0) or 0)
        avg_tx = int(analysis_result.get("avg_tx", 0) or 0)

        # 상위 가맹점
        top_merchants: Dict[str, int] = {}
        for tx in card_history or []:
            try:
                amt = int(tx.get("amount", 0) or 0)
            except Exception:
                amt = 0
            if amt <= 0:
                continue
            m = str(tx.get("merchant", "")).strip() or "미상"
            top_merchants[m] = top_merchants.get(m, 0) + amt

        top_3 = sorted(top_merchants.items(), key=lambda x: x[1], reverse=True)[:3]
        top_str = ", ".join([f"{m}:{amt:,}원" for m, amt in top_3]) if top_3 else "없음"

        query = (
            f"{persona} 성향 사용자의 월급 {salary:,}원, 총지출 {total_spent:,}원, "
            f"월급대비 {spend_ratio:.1f}% 사용. 거래수 {tx_count}건, 평균 {avg_tx:,}원/건. "
            f"상위 가맹점: {top_str}. "
            "이 사용자에게 적합한 저축/투자/세제/주의사항/실행액션 가이드를 제시해줘."
        )
        return query, persona, top_str

    def __call__(self, state: Dict) -> Dict:
        egen_teto_type = state.get("egen_teto_type") or "NEUTRAL-중립형"
        analysis_result = state.get("analysis_result", {}) or {}
        user_data = state.get("user_data", {}) or {}
        card_history = user_data.get("card_history", []) or []

        # 1) 질의/페르소나
        query, persona, _ = self._build_query(egen_teto_type, analysis_result, card_history)

        # 2) RAG 컨텍스트 안전 호출
        try:
            context = rag_context(query=query, k=6, persona=persona)
        except Exception as e:
            logger.warning(f"[RAG] rag_context failed: {e}")
            context = "(RAG 컨텍스트 불러오기에 실패했습니다. 기본 지침만 활용하세요.)"

        # 3) 프롬프트
        prompt = f"""당신은 개인 금융 코치입니다. 한국어로만 답하고, 과도한 투자 권유는 금지하세요.
다음 정보를 기반으로 성향에 맞춘 피드백을 4개의 섹션으로 출력하세요.

[성향] {egen_teto_type}
[요약 데이터]
- 월급: {analysis_result.get('salary', 0):,}원
- 총지출: {analysis_result.get('total_spent', 0):,}원 ({analysis_result.get('spend_ratio', 0)}%)
- 이용건수/평균건당: {analysis_result.get('tx_count', 0)}건 / {analysis_result.get('avg_tx', 0):,}원

[참고 컨텍스트(RAG)]
{context}

=== 출력 형식 ===
1) 한줄요약: (한 문장)
2) 지출 분석: 수치 기반 핵심 2~3줄
3) 다음달 액션 3가지: 금액·비율·구체 실행 포함 (번호 목록)
4) 추천 제도/상품(근거·주의): 제도명·적용조건·주의사항 간략 명시
"""

        # 4) LLM 호출 (오류 내성 + 폴백 한 번 더)
        try:
            resp = LLM.invoke(prompt)
            text = getattr(resp, "content", None) or getattr(resp, "text", None) or str(resp)
        except Exception as e:
            logger.error(f"[LLM] invoke failed: {e}")
            # 최후 폴백: 간단한 정적 메시지라도 반환
            text = (
                "[임시 피드백]\n"
                "현재 생성 모델 응답에 문제가 발생하여 기본 가이드를 제공합니다.\n"
                "- 소비 비율을 월급 대비 5~10%p 낮추는 것을 목표로, 상위 지출 2개 카테고리부터 절감\n"
                "- 자동이체 저축(월급일+1일), 카드 고정결제(구독/통신) 점검\n"
                "- 세제혜택: IRP/연금저축 한도 체크, 체크카드/신용카드 공제율 비교 후 최적화\n"
            )

        state["final_feedback"] = str(text).strip()
        return state
