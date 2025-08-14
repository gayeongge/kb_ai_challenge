import React, { useMemo, useRef, useState, useEffect } from 'react';
import './SurveyChat.css';

type QAKind = 'OX' | 'segment' | 'input' | 'file';
type QAItem = { id: number; text: string; kind: QAKind };
type HistoryItem = { q: string; a: string };

const QUESTIONS: QAItem[] = [
  { id: 1,  text: '안녕하세요! 저는 사회초년생 및 결혼 준비 커플을 위한 금융 비서입니다. 어떤 유형이신가요?', kind: 'segment' },
  { id: 2,  text: '기대 수익률이 낮더라도 원금 손실이 없는 상품을 우선 고려하시나요?', kind: 'OX' },
  { id: 3,  text: '경제/투자 정보를 뉴스·유튜브·커뮤니티 등에서 적극적으로 찾아보시나요?', kind: 'OX' },
  { id: 4,  text: '안정보다 성장(다소 위험 감수) 쪽을 선호하시나요?', kind: 'OX' },
  { id: 5,  text: '단기 매매보다 장기투자가 더 맞다고 생각하시나요?', kind: 'OX' },
  { id: 6,  text: '정부 지원 상품보다 본인 투자 수익을 더 자신하시나요?', kind: 'OX' },
  { id: 7,  text: '정부/은행 보증의 안정적인 상품을 선호하시나요?', kind: 'OX' },
  { id: 8,  text: '손실의 고통(–10%)이 이익(+10%)의 기쁨보다 더 크게 느껴지나요?', kind: 'OX' },
  { id: 9,  text: '타인 성공사례/트렌드보다 자신의 분석을 더 신뢰하나요?', kind: 'OX' },
  { id: 10, text: '매달 예산을 세우고 지출을 꼼꼼히 추적하려고 노력하시나요?', kind: 'OX' },
  { id: 11, text: '추가로 어떤 피드백을 받고 싶나요? (예: 구독/식비 절감, 또래 비교 등)', kind: 'input' },
  { id: 12, text: '카드 내역 파일을 업로드 해주세요. (CSV/XLSX)', kind: 'file' },
];

const API = 'http://localhost:8000'; // 혹은 프록시 쓰면 ''(빈 문자열, 상대경로)

export default function SurveyChat() {
  const [step, setStep] = useState<number>(0);
  const [segment, setSegment] = useState<'사회초년생'|'결혼 준비 커플'|''>('');
  const [answers, setAnswers] = useState<Record<number, 'O'|'X'>>({});
  const [freeInput, setFreeInput] = useState<string>('');
  const [file, setFile] = useState<File|null>(null);

  // 서버 응답
  const [cards, setCards] = useState<any[]>([]);        // sample (상위 N행)
  const [cardCount, setCardCount] = useState<number>(0); // rows (전체 건수)
  const [cols, setCols] = useState<string[]>([]);        // 열 이름(선택)

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string>('');
  const scrollRef = useRef<HTMLDivElement>(null);

  const q = QUESTIONS[step];
  const progress = useMemo(() => Math.round((step / QUESTIONS.length) * 100), [step]);

  useEffect(() => {
    // 히스토리 최하단으로 자동 스크롤
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [history, step]);

  const pushHistoryAndNext = (question: string, answer: string) => {
    setHistory(prev => [...prev, { q: question, a: answer }]);
    setStep((s) => s + 1);
  };

  const chooseSegment = (value: '사회초년생'|'결혼 준비 커플') => {
    setSegment(value);
    pushHistoryAndNext(QUESTIONS[0].text, value);
  };

  const chooseOX = (id: number, value: 'O'|'X') => {
    setAnswers(a => ({ ...a, [id]: value }));
    const item = QUESTIONS.find(it => it.id === id)!;
    pushHistoryAndNext(item.text, value);
  };

  const nextFromInput = () => {
    if (!freeInput.trim()) return;
    pushHistoryAndNext(QUESTIONS[10].text, freeInput.trim());
  };

  const nextFromFile = async () => {
    if (!file) return alert('파일을 선택해 주세요.');
    setLoading(true);
    try {
      const form = new FormData();
      form.append('file', file); // 키 이름 반드시 'file' (백엔드와 동일)
      const res = await fetch(`${API}/parse_cards`, { method: 'POST', body: form });

      // JSON 파싱
      const json = await res.json();

      if (!res.ok) {
        // 서버가 400일 때 detail에 원인 들어 있음
        throw new Error(json?.detail || '업로드/파싱 실패');
      }

      // 서버 응답: { ok, rows, cols, sample }
      setCards(json.sample || []);
      setCardCount(Number(json.rows || 0));
      setCols(Array.isArray(json.cols) ? json.cols : []);

      pushHistoryAndNext(QUESTIONS[11].text, `파일 업로드 완료 (${json.rows}건)`);
    } catch (e:any) {
      alert('파일 파싱 실패: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  };

  const send = async () => {
    const payload = {
      input: freeInput || '이번 달 지출 피드백을 요약해 주세요.',
      user_segment: segment || '사회초년생',
      survey_answers: {
        '2': answers[2] || 'X','3': answers[3] || 'X','4': answers[4] || 'X','5': answers[5] || 'X',
        '6': answers[6] || 'X','7': answers[7] || 'X','8': answers[8] || 'X','9': answers[9] || 'X','10': answers[10] || 'X',
      },
      card_records: cards, // 현재는 sample만 보내지만, 필요시 전체 전송 로직으로 확장
    };

    setLoading(true);
    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      setResult(json.output ?? JSON.stringify(json, null, 2));
    } catch (e:any) {
      setResult('요청 실패: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sc-wrap">
      <header className="sc-header">
        <div className="sc-title">샤샤 • 금융 코치</div>
        <div className="sc-steps">Step {Math.min(step+1, QUESTIONS.length)} / {QUESTIONS.length}</div>
        <div className="sc-progress"><div className="sc-progress-bar" style={{ width: `${progress}%` }} /></div>
      </header>

      {/* 히스토리 영역 */}
      <div className="sc-history" ref={scrollRef}>
        {history.length === 0 && (
          <div className="sc-empty">대화를 시작해 볼까요?</div>
        )}
        {history.map((h, i) => (
          <div className="sc-pair" key={i}>
            <div className="sc-bubble sc-q">
              <span className="sc-chip">Q{i+1}</span>{h.q}
            </div>
            <div className="sc-bubble sc-a">
              <span className="sc-chip sc-chip-a">A</span>{h.a}
            </div>
          </div>
        ))}
      </div>

      {/* 현재 프롬프트 카드 */}
      {q && (
        <div className="sc-card">
          <div className="sc-qtext">문항 {q.id}. {q.text}</div>

          {q.kind === 'segment' && (
            <div className="sc-actions">
              <button className="sc-btn sc-btn-primary" onClick={() => chooseSegment('사회초년생')}>사회초년생</button>
              <button className="sc-btn" onClick={() => chooseSegment('결혼 준비 커플')}>결혼 준비 커플</button>
            </div>
          )}

          {q.kind === 'OX' && (
            <div className="sc-actions">
              <button className="sc-btn sc-btn-choice" onClick={() => chooseOX(q.id, 'O')}>O</button>
              <button className="sc-btn sc-btn-choice sc-btn-danger" onClick={() => chooseOX(q.id, 'X')}>X</button>
            </div>
          )}

          {q.kind === 'input' && (
            <>
              <textarea className="sc-textarea"
                        rows={4}
                        placeholder="예: 구독/식비 절감 위주로, 또래 대비 비교도 부탁!"
                        value={freeInput}
                        onChange={(e) => setFreeInput(e.target.value)} />
              <div className="sc-actions">
                <button className="sc-btn sc-btn-primary" onClick={nextFromInput}>다음</button>
              </div>
            </>
          )}

          {q.kind === 'file' && (
            <>
              <label className="sc-file">
                <input type="file" accept=".csv,.xlsx" onChange={(e)=>setFile(e.target.files?.[0] || null)} />
                <span>{file ? file.name : '파일 선택'}</span>
              </label>
              <div className="sc-actions">
                <button className="sc-btn" onClick={() => setStep((s)=>Math.max(0, s-1))}>이전</button>
                <button className="sc-btn sc-btn-primary" onClick={nextFromFile} disabled={loading}>
                  {loading ? '분석 중…' : '다음'}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* 업로드 미리보기(선택) */}
      {cards.length > 0 && (
        <div className="sc-preview">
          <div className="sc-preview-title">업로드 미리보기 (상위 {cards.length}행 / 총 {cardCount}건)</div>
          <div className="sc-preview-table">
            <table>
              <thead>
                <tr>
                  { (cols.length ? cols : Object.keys(cards[0] || {})).map((c) => <th key={c}>{c}</th>) }
                </tr>
              </thead>
              <tbody>
                {cards.map((row, idx) => (
                  <tr key={idx}>
                    {(cols.length ? cols : Object.keys(row)).map((c) => (
                      <td key={c}>{String(row[c] ?? '')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 제출 */}
      {step >= QUESTIONS.length && (
        <div className="sc-footer">
          <button className="sc-btn sc-btn-primary sc-btn-lg" onClick={send} disabled={loading}>
            {loading ? '요청 중…' : '피드백 받기'}
          </button>
          {/* 표시는 전체 건수 기준 */}
          {cardCount > 0 && <span className="sc-badge">거래 {cardCount}건</span>}
        </div>
      )}

      {/* 결과 */}
      {result && (
        <div className="sc-result">
          <div className="sc-result-title">결과</div>
          <pre className="sc-result-pre">{result}</pre>
        </div>
      )}
    </div>
  );
}
