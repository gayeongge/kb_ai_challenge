# main.py
import os, io, json
from typing import Dict, List, Any, Tuple

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pathlib import Path
import pandas as pd

# OpenAI SDK (v1.x)
from openai import OpenAI

# .env를 main/chatbot/main.py 기준으로 2단계 위(프로젝트 루트)에서 찾음
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

try:
    from dotenv import load_dotenv
except ImportError:
    raise RuntimeError(
        "python-dotenv가 없습니다. `pip install python-dotenv` 후 다시 실행하세요."
    )

# 같은 프로세스/리로드 시에도 .env를 확실히 반영
load_dotenv(dotenv_path=ENV_PATH, override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError(
        f"OPENAI_API_KEY가 비어있습니다. 다음을 확인하세요.\n"
        f"1) {ENV_PATH} 파일에 OPENAI_API_KEY=... 추가\n"
        f"2) uvicorn 실행 경로가 프로젝트 루트인지\n"
        f"3) .env 경로 오타 여부"
    )

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 규칙 분류기 (이미 프로젝트에 있는 파일 사용)
from node.egen_teto_classifier import EgenTetoClassifierNode

# -----------------------------------------------------------------------------
# FastAPI & CORS
# -----------------------------------------------------------------------------
app = FastAPI(title="SASHA Finance Coach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 개발 중엔 전부 허용. 배포 시 도메인 제한 권장
    allow_methods=["*"],
    allow_headers=["*"],
)

# FastAPI가 422 Validation 에러를 JSON으로 깔끔히 내리도록(바이너리 필드 제거)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    sanitized = []
    for e in exc.errors():
        if "input" in e and isinstance(e.get("input"), (bytes, bytearray)):
            e = {k: v for k, v in e.items() if k != "input"}
        sanitized.append(e)
    return JSONResponse(status_code=422, content={"detail": sanitized})

# -----------------------------------------------------------------------------
# 간단한 상태 확인
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

# -----------------------------------------------------------------------------
# KB / RAG (로컬 ./kb의 .md/.txt 문서를 읽어서 OpenAI 임베딩)
# -----------------------------------------------------------------------------
KB_DIR = os.path.join(os.path.dirname(__file__), "kb")
EMBED_MODEL = "text-embedding-3-small"   # 가성비
CHAT_MODEL  = "gpt-4o-mini"              # 응답 모델

_kb_chunks: List[Dict[str, Any]] = []    # {id, title, text}
_kb_embs: List[List[float]] = []         # 임베딩 캐시

def _bootstrap_kb():
    """./kb 폴더가 없거나 비어있으면 샘플 문서를 하나 만든다."""
    os.makedirs(KB_DIR, exist_ok=True)
    if not any(fn.endswith((".md", ".txt")) for fn in os.listdir(KB_DIR)):
        sample = """# 정기예금(은행 보증)
- 원금 손실 위험이 매우 낮고 고정금리를 제공
- 중도해지 시 이자 불이익 가능 → 목적자금/만기 계획 수립 필요
- 안정 추구형/단기 유동성 요구가 낮은 경우 적합

# 적금
- 매월 일정액 강제 저축, 소비 통제/현금흐름 관리
- 중도해지 시 이자↓, 자동이체 권장

# 장기투자(ETF)
- 분산/저비용/장기 복리
- 단기 변동성 감내 필요, 리스크 안내 필수
"""
        with open(os.path.join(KB_DIR, "금융_기본.md"), "w", encoding="utf-8") as f:
            f.write(sample)

def _chunk(text: str, size: int = 900, overlap: int = 150) -> List[str]:
    text = text.strip()
    if len(text) <= size:
        return [text]
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i+size])
        i += size - overlap
    return out

def load_kb():
    """KB 조각을 메모리에 적재."""
    global _kb_chunks
    if _kb_chunks:
        return
    _bootstrap_kb()
    did = 0
    for fn in os.listdir(KB_DIR):
        if not fn.endswith((".md", ".txt")):
            continue
        path = os.path.join(KB_DIR, fn)
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        for c in _chunk(raw):
            _kb_chunks.append({"id": did, "title": fn, "text": c.strip()})
            did += 1

def embed_kb():
    """KB 조각 임베딩 생성(최초 1회)."""
    global _kb_embs
    if _kb_embs:
        return
    load_kb()
    texts = [c["text"] for c in _kb_chunks]
    _kb_embs = []
    B = 200
    for i in range(0, len(texts), B):
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i+B])
        _kb_embs.extend([d.embedding for d in resp.data])

def _cosine(a: List[float], b: List[float]) -> float:
    from math import sqrt
    dot = sum(x*y for x, y in zip(a, b))
    na = sqrt(sum(x*x for x in a)) or 1.0
    nb = sqrt(sum(y*y for y in b)) or 1.0
    return dot / (na * nb)

def rag_search(query: str, k: int = 4) -> List[Dict[str, Any]]:
    load_kb()
    embed_kb()
    q_emb = client.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding
    scored = [(_cosine(q_emb, emb), ch) for ch, emb in zip(_kb_chunks, _kb_embs)]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]

# -----------------------------------------------------------------------------
# 카드 파일 파서 & 요약
# -----------------------------------------------------------------------------
def parse_card_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """CSV/XLSX 모두 지원. 금액 컬럼을 'AMOUNT'로 표준화."""
    buf = io.BytesIO(file_bytes)
    if filename.lower().endswith(".csv"):
        df = pd.read_csv(buf, encoding="utf-8", engine="python")
    else:
        df = pd.read_excel(buf)  # openpyxl 필요
    # 금액 컬럼 추정
    cand = ["금액", "이용금액", "결제금액", "AMOUNT", "amount"]
    amount_col = next((c for c in df.columns if c in cand), None)
    if amount_col is None:
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            raise ValueError("금액 컬럼을 찾을 수 없습니다.")
        amount_col = max(num_cols, key=lambda c: df[c].abs().sum())
    df.rename(columns={amount_col: "AMOUNT"}, inplace=True)
    df["AMOUNT"] = pd.to_numeric(df["AMOUNT"], errors="coerce").fillna(0)
    return df

def quick_analysis(df: pd.DataFrame, monthly_salary: float | None) -> Dict[str, Any]:
    total_spend = float(df["AMOUNT"].sum()) if not df.empty else 0.0
    tx_count = int(len(df)) if not df.empty else 0
    mean_tx = float(df["AMOUNT"].mean()) if not df.empty else 0.0
    spending_rate = None
    if monthly_salary and monthly_salary > 0:
        spending_rate = round((total_spend / monthly_salary) * 100, 2)
    return {
        "total_spend": round(total_spend, 2),
        "tx_count": tx_count,
        "mean_tx": round(mean_tx, 2),
        "spending_rate": spending_rate,  # %
    }

# -----------------------------------------------------------------------------
# LLM 프롬프트 & 호출
# -----------------------------------------------------------------------------
SYSTEM_PROMPT = """당신은 개인 금융 코치입니다.
- 답변은 한국어로만 합니다.
- 출력 형식은 반드시 아래처럼 유지합니다(텍스트 한 덩어리):
성향: <한줄>   # 반드시 [분류 결과]의 성향 값을 그대로 적는다.

==== 최종 피드백 ====
1) 한줄요약: <문장 1~2개, 핵심만>

2) 지출 분석: <숫자 근거 포함 1~2문장>

3) 다음달 액션 3가지:
  1. <액션1: 금액/비율/구체 실행>
  2. <액션2: 금액/비율/구체 실행>
  3. <액션3: 금액/비율/구체 실행>

4) 추천 제도/상품: <상품명>
  - 적용조건: <핵심 조건>
  - 주의사항: <원금손실, 세금, 한도 등 경고 포함>

- 과도한 투자 권유 금지. 위험/유동성/세금/한도 경고는 꼭 포함.
- '성향'은 LLM이 임의로 바꾸지 말고 [분류 결과] 값을 그대로 사용.
"""

def build_user_prompt(answers: Dict[str, Any], stats: Dict[str, Any], kb_ctx: List[Dict[str, Any]]) -> str:
    ans_fmt = ", ".join(f"Q{id}: {val}" for id, val in answers.items())
    stats_lines = [
        f"- 총 지출 합계: {stats.get('total_spend', 0):,.0f}원",
        f"- 거래 건수: {stats.get('tx_count', 0)}건",
        f"- 평균 거래액: {stats.get('mean_tx', 0):,.0f}원",
    ]
    if stats.get("spending_rate") is not None:
        stats_lines.append(f"- 월급 대비 지출 비율: {stats['spending_rate']}%")
    stats_block = "\n".join(stats_lines)

    ctx = "\n\n".join([f"[{c['title']}] {c['text']}" for c in kb_ctx])
    return f"""[사용자 O/X 응답]
{ans_fmt}

[카드 내역 요약]
{stats_block}

[지식(RAG) 발췌 상위]
{ctx}
"""

def call_openai_final_feedback_with_prompt(user_prompt: str) -> str:
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content.strip()

# -----------------------------------------------------------------------------
# /chat : FormData(answers + file + salary) 처리
# -----------------------------------------------------------------------------
@app.post("/chat")
async def chat_endpoint(
    answers: str = Form(...),                 # JSON 문자열 {"2":"X","3":"O",...}
    file: UploadFile = File(None),            # CSV/XLSX
    salary: str = Form(None)                  # 옵션: 월급(문자열로 와도 됨)
):
    # 1) answers 파싱
    try:
        ans_dict = json.loads(answers) if answers else {}
    except json.JSONDecodeError as e:
        return JSONResponse(status_code=400, content={"error": f"Invalid JSON in 'answers': {str(e)}"})

    # 2) 파일 파싱(있다면)
    df = pd.DataFrame()
    if file is not None:
        raw = await file.read()
        try:
            df = parse_card_file(raw, file.filename)
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"파일 파싱 실패: {str(e)}"})

    # 3) 요약 통계
    monthly_salary = None
    if salary is not None and str(salary).strip() != "":
        try:
            monthly_salary = float(salary)
        except Exception:
            monthly_salary = None
    stats = quick_analysis(df, monthly_salary)

    # 4) 규칙 기반 에겐/테토 분류 (여기가 핵심!)
    try:
        cls = EgenTetoClassifierNode()
        state_for_cls = {"survey_answers": ans_dict}  # 문자열 O/X여도 내부에서 변환 처리
        egen_teto_type = cls.compute_type(state_for_cls)
    except Exception as e:
        # 분류기 오류 시에도 서비스는 계속되도록
        egen_teto_type = "NEUTRAL-중립형"

    # 5) RAG 컨텍스트
    rag_query = "예금/적금/ETF 장단점, 안정/성장 성향별 권장사항, 리스크 경고"
    top_ctx = rag_search(rag_query, k=4)

    # 6) LLM 프롬프트(분류 결과 고정값 prepend)
    user_prompt = build_user_prompt(ans_dict, stats, top_ctx)
    user_prompt = f"[분류 결과] 성향: {egen_teto_type}\n\n" + user_prompt

    # 7) LLM 호출
    try:
        final_feedback = call_openai_final_feedback_with_prompt(user_prompt)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"LLM 호출 실패: {type(e).__name__}: {e}"})

    # 8) 프론트로 반환
    return {
        "final_feedback": final_feedback,
        "egen_teto_type": egen_teto_type
    }
