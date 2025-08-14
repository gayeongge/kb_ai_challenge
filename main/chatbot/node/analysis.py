# main/chatbot/node/analysis.py
from __future__ import annotations
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# from state.schema import OutputState  # 현재 노드에선 미사용
# from .react import ReactNode          # 파이프라인에서 호출하므로 여기선 import 불필요

CAT_KEYWORDS = {
    "식비":    ["카페", "커피", "스타벅스", "버거", "맥도날드", "식당", "분식", "배달", "요기요", "배달의민족"],
    "쇼핑":    ["쿠팡", "11번가", "G마켓", "SSG", "무신사", "마켓컬리", "네이버페이"],
    "교통":    ["지하철", "버스", "택시", "카카오T", "고속도로", "하이패스", "주차"],
    "구독":    ["넷플릭스", "왓챠", "유튜브 프리미엄", "멜론", "티빙", "디즈니", "웨이브", "쿠팡와우"],
    "통신":    ["SKT", "KT", "LGU", "알뜰폰", "통신요금"],
    "생활":    ["편의점", "이마트", "홈플러스", "롯데마트", "다이소"],
    "의료":    ["병원", "약국", "의원", "치과", "검진"],
}

def _safe_int(x) -> int:
    try:
        s = str(x).replace(",", "").replace("원", "").strip()
        if "(" in s and ")" in s:  # (1,000) → -1000
            s = s.replace("(", "").replace(")", "")
            return -int(s)
        return int(s)
    except Exception:
        try:
            return int(float(s))
        except Exception:
            return 0

def _parse_date(s: str) -> datetime | None:
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d", "%y-%m-%d", "%y.%m.%d", "%y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s.replace(".", "-").replace("/", "-"))
    except Exception:
        return None

def _infer_category(merchant: str) -> str:
    m = merchant or ""
    for cat, keys in CAT_KEYWORDS.items():
        for k in keys:
            if k.lower() in m.lower():
                return cat
    return "기타"

def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m") if dt else "unknown"

class AnalysisNode:
    """
    사용자 카드내역을 분석하고 요약 메트릭을 state['analysis_result']에 채운다.
    - 입력: state = { 'user_data': { 'salary': int, 'card_history': [{date, merchant, amount}, ...] } }
    - 출력: state['analysis_result'] 딕셔너리
    """
    def __init__(self, only_current_month: bool = False):
        self.only_current_month = only_current_month

    def __call__(self, state: Dict) -> Dict:
        user_data = state.get("user_data", {}) or {}
        salary = _safe_int(user_data.get("salary", 0))
        card_history: List[Dict] = user_data.get("card_history", []) or []

        # 날짜 파싱 + 월 필터
        now = datetime.now()
        items: List[Tuple[datetime | None, str, int]] = []
        for tx in card_history:
            dt = _parse_date(tx.get("date"))
            if self.only_current_month and dt and (dt.year != now.year or dt.month != now.month):
                continue
            mrch = str(tx.get("merchant", "")).strip() or "미상"
            amt = _safe_int(tx.get("amount", 0))
            items.append((dt, mrch, amt))

        # 지출/환불 분리
        expenses = [(dt, m, a) for dt, m, a in items if a > 0]
        refunds  = [(dt, m, a) for dt, m, a in items if a < 0]

        total_spent = sum(a for _, _, a in expenses)
        total_refund = -sum(a for _, _, a in refunds)  # 양수화
        tx_count = len(expenses)
        avg_tx = round(total_spent / tx_count, 2) if tx_count else 0.0
        spend_ratio = round((total_spent / salary) * 100, 2) if salary > 0 else 0.0

        # 상위 가맹점 TOP3
        top_merchants: Dict[str, int] = {}
        for _, m, a in expenses:
            top_merchants[m] = top_merchants.get(m, 0) + a
        top3 = sorted(top_merchants.items(), key=lambda x: x[1], reverse=True)[:3]

        # 카테고리 집계
        cat_sum: Dict[str, int] = {}
        for _, m, a in expenses:
            cat = _infer_category(m)
            cat_sum[cat] = cat_sum.get(cat, 0) + a
        cat_top = sorted(cat_sum.items(), key=lambda x: x[1], reverse=True)

        # 월별 집계(필요 시)
        by_month: Dict[str, int] = {}
        for dt, _, a in expenses:
            key = _month_key(dt) if dt else "unknown"
            by_month[key] = by_month.get(key, 0) + a

        state["analysis_result"] = {
            "salary": salary,
            "total_spent": total_spent,
            "total_refund": total_refund,
            "spend_ratio": spend_ratio,
            "tx_count": tx_count,
            "avg_tx": avg_tx,
            "top_merchants": top3,      # [("쿠팡", 25900), ...]
            "category_sum": cat_sum,    # {"식비": 100000, ...}
            "category_rank": cat_top,   # 정렬된 리스트
            "by_month": by_month,       # {"2025-08": 123000, ...}
            "only_current_month": self.only_current_month,
        }
        return state
