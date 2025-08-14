# main/chatbot/node/get_user_data.py (혹은 네가 둔 파일 위치)

from .analysis import AnalysisNode
import io
import pandas as pd
from typing import Dict, List, Optional
from state.schema import CardTx
from datetime import datetime
import re
import os

# 후보 컬럼 확장 (국내 파일 다양성 반영)
REQUIRED_COLS = {
    "date": [
        "date","거래일자","승인일자","사용일자","이용일자","거래일시","이용일시","사용일시","일자"
    ],
    "merchant": [
        "merchant","가맹점","가맹점명","이용가맹점","사용처","상호","상호명","거래처명","내용","업종"
    ],
    "amount": [
        "amount","승인금액","금액","이용금액","결제금액","청구금액","거래금액","출금금액","지출금액"
    ],
}

def _normalize_key(s: str) -> str:
    return re.sub(r"\s+", "", str(s)).lower()

def _first_existing(df: pd.DataFrame, candidates) -> Optional[str]:
    norm_cols = { _normalize_key(c): c for c in df.columns }
    for c in candidates:
        key = _normalize_key(c)
        if key in norm_cols:
            return norm_cols[key]
    # heuristic: 키워드 포함으로 추정
    for col in df.columns:
        n = _normalize_key(col)
        if any(k in n for k in ["금액","amount"]) and "amount" in candidates:
            return col
    for col in df.columns:
        n = _normalize_key(col)
        if any(k in n for k in ["가맹","상호","거래처","merchant"]) and "merchant" in candidates:
            return col
    for col in df.columns:
        n = _normalize_key(col)
        if any(k in n for k in ["일자","일시","date"]) and "date" in candidates:
            return col
    return None

def _parse_date(x: str) -> str:
    s = str(x).strip()
    fmts = (
        "%Y-%m-%d","%Y.%m.%d","%Y/%m/%d",
        "%y-%m-%d","%y.%m.%d","%y/%m/%d",
        "%Y%m%d","%y%m%d",
        "%m/%d/%Y","%m-%d-%Y",
        "%Y-%m-%d %H:%M:%S","%Y/%m/%d %H:%M:%S","%Y.%m.%d %H:%M:%S",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except:
            pass
    # ISO 비슷한 포맷 fallback
    try:
        return datetime.fromisoformat(s.replace("/", "-").replace(".", "-")).strftime("%Y-%m-%d")
    except:
        return s  # 실패 시 원문(후처리에서 걸러질 수도 있음)

_AMOUNT_PAT = re.compile(r"-?\(?\d[\d,]*\)?")

def _parse_amount(x: str) -> int:
    s = str(x).replace("원","").replace("+","").replace(" ", "")
    # 괄호표기 (1,000) → -1000
    negative = "(" in s and ")" in s
    s = s.replace("(", "").replace(")", "")
    # 첫 숫자 블록 추출
    m = _AMOUNT_PAT.search(s)
    if not m:
        return 0
    num = int(m.group(0).replace(",", ""))
    return -num if negative else num

def _normalize_df_to_records(df: pd.DataFrame) -> List[CardTx]:
    # 컬럼 매핑
    c_date = _first_existing(df, REQUIRED_COLS["date"])
    c_mrch = _first_existing(df, REQUIRED_COLS["merchant"])
    c_amt  = _first_existing(df, REQUIRED_COLS["amount"])
    if not all([c_date, c_mrch, c_amt]):
        raise ValueError(f"필수 컬럼(날짜/가맹점/금액) 누락. 현재 컬럼: {list(df.columns)}")

    # 날짜
    dates = []
    for v in df[c_date].tolist():
        dates.append(_parse_date(v))
    df["_date"] = dates

    # 금액
    amts = []
    for v in df[c_amt].tolist():
        amts.append(_parse_amount(v))
    df["_amount"] = amts

    # 레코드 생성 (0 금액은 스킵; 환불/입금은 음수로 남김 → 필요 시 필터)
    out: List[CardTx] = []
    for _, r in df.iterrows():
        ds = r["_date"]
        if not isinstance(ds, str) or len(ds) < 8:
            continue
        mrch = str(r.get(c_mrch, "") or "").strip() or "미상"
        amt = int(r["_amount"])
        if amt == 0:
            continue  # 0원은 제외 (원하면 포함으로 바꿔도 됨)
        out.append(CardTx(date=ds[:10], merchant=mrch, amount=amt))
    return out

# --- 기존 CSV 함수는 유지하되, 인코딩/견고화 추가 ---
def normalize_cards_csv(file_bytes: bytes) -> List[CardTx]:
    # utf-8 → 실패 시 cp949 재시도
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="utf-8")
    except Exception:
        df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="cp949")
    return _normalize_df_to_records(df)

# --- XLSX/XLS 지원 ---
def normalize_cards_excel(file_bytes: bytes) -> List[CardTx]:
    df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    return _normalize_df_to_records(df)

# --- 확장자 자동 판별 진입점 ---
def normalize_cards(file_bytes: bytes, filename: str) -> List[CardTx]:
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    if ext in ("xlsx","xls"):
        return normalize_cards_excel(file_bytes)
    elif ext == "csv":
        return normalize_cards_csv(file_bytes)
    else:
        # 확장자 없으면 시그니처 추정 (간단 heuristics)
        # 엑셀 바이너리는 CSV로는 못 읽힘 → read_excel 먼저 시도
        try:
            return normalize_cards_excel(file_bytes)
        except Exception:
            return normalize_cards_csv(file_bytes)
