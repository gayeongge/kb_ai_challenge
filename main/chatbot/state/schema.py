from __future__ import annotations

from typing import Any, List, Dict, Optional, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, field_validator, ConfigDict

# ---------------------------------------------------------------------
# Pipeline States
# ---------------------------------------------------------------------

class InputState(TypedDict, total=False):
    input: str
    egen_teto_data: str  # raw or serialized data for classifier

class OutputState(TypedDict, total=False):
    output: Any

class OverallState(InputState, OutputState):
    """OverallState is a combination of InputState and OutputState."""


# ---------------------------------------------------------------------
# Core Domain Schemas
# ---------------------------------------------------------------------

PersonaLabel = Literal["EGEN-안정 추구형", "TETO-성장 추구형", "NEUTRAL-중립형"]

class CardTx(BaseModel):
    """
    원화 기준 카드 거래
    - amount: +지출 / -환불
    - date: YYYY-MM-DD
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    date: str = Field(..., description="YYYY-MM-DD")
    merchant: str = Field(..., min_length=1, max_length=200)
    amount: int = Field(..., description="원 단위(+지출, -환불)")

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        # 간단한 형식 체크 (정밀 파싱은 분석 단계에서 수행)
        # 허용 예: 2025-08-14
        import re
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v or ""):
            raise ValueError("date must be 'YYYY-MM-DD'")
        return v

    @field_validator("merchant")
    @classmethod
    def validate_merchant(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("merchant is required")
        return v


class SurveyAnswer(BaseModel):
    qid: int = Field(..., ge=2, le=10)  # 2~10 문항
    answer: bool = Field(..., description="O=True, X=False")


class SessionState(BaseModel):
    """
    세션 단위의 진행 상태:
    - survey_answers: 2~10 문항 O/X 기록
    - survey_done: 설문 완료 여부
    - egen_teto_type: 최종 라벨 (없을 수 있음)
    - cards: 업로드된 카드내역 (정규화된 표준 스키마)
    - salary: 급여(원)
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: str = Field(..., min_length=1)
    survey_answers: Dict[int, bool] = Field(default_factory=dict)
    survey_done: bool = False
    egen_teto_type: Optional[PersonaLabel] = None

    cards: List[CardTx] = Field(default_factory=list)
    salary: Optional[int] = Field(default=None, ge=0)

    @field_validator("survey_answers")
    @classmethod
    def validate_survey_keys(cls, v: Dict[int, bool]) -> Dict[int, bool]:
        # 키가 2~10 사이인지 간단 체크
        for k in v.keys():
            if not (2 <= int(k) <= 10):
                raise ValueError("survey_answers keys must be between 2 and 10")
        return v


class RunRequest(BaseModel):
    """
    피드백 생성 요청 스키마
    - session_id: 필수
    - salary: 선택(프론트에서 덮어쓰기 가능)
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: str = Field(..., min_length=1)
    salary: Optional[int] = Field(default=None, ge=0)
