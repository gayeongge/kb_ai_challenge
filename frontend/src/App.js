// src/App.js
import React, { useEffect, useMemo, useRef, useState } from "react";

/** 질문 정의 */
const questions = [
  { id: 1, text: "카드 내역 파일을 업로드 해주세요. (CSV/XLSX)", type: "file" },
  { id: 2, text: "기대 수익률이 낮더라도 원금 손실이 없는 상품을 우선 고려하시나요?", type: "OX" },
  { id: 3, text: "경제/투자 정보를 뉴스·유튜브·커뮤니티 등에서 적극적으로 찾아보시나요?", type: "OX" },
  { id: 4, text: "안정보다 성장(다소 위험 감수) 쪽을 선호하시나요?", type: "OX" },
  { id: 5, text: "정부 지원 상품보다 본인 투자 수익을 더 자신하시나요?", type: "OX" },
  { id: 6, text: "정부/은행 보증의 안정적인 상품을 선호하시나요?", type: "OX" },
  { id: 7, text: "손실의 고통(–10%)이 이익(+10%)의 기쁨보다 더 크게 느껴지나요?", type: "OX" },
  { id: 8, text: "타인 성공사례/트렌드보다 자신의 분석을 더 신뢰하나요?", type: "OX" },
  { id: 9, text: "매달 예산을 세우고 지출을 꼼꼼히 추적하려고 노력하시나요?", type: "OX" },
  { id: 10, text: "단기 매매보다 장기투자가 더 맞다고 생각하시나요?", type: "OX" }
];

/** 유틸 */
const uuid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
const STORAGE_KEY = "sasha_chat_messages_v1";
const ANSWER_KEY = "sasha_answers_v1";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [answers, setAnswers] = useState({});
  const [currentStep, setCurrentStep] = useState(1);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const currentQuestion = useMemo(
    () => questions.find((q) => q.id === currentStep),
    [currentStep]
  );

  // 로컬 저장소 복원
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    const savedAns = localStorage.getItem(ANSWER_KEY);
    if (saved) {
      try { setMessages(JSON.parse(saved)); } catch {}
    }
    if (savedAns) {
      try { setAnswers(JSON.parse(savedAns)); } catch {}
    }
  }, []);

  // 로컬 저장소 저장
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    localStorage.setItem(ANSWER_KEY, JSON.stringify(answers));
  }, [answers]);

  // 첫 진입 시 환영 + 첫 질문
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        { id: uuid(), role: "assistant", content: "안녕하세요! 저는 **사샤** 금융 코치예요. 몇 가지 질문만 답하면, 월급/카드내역 기반으로 맞춤 피드백을 드릴게요.", createdAt: Date.now() },
        { id: uuid(), role: "assistant", content: questions[0].text, createdAt: Date.now() }
      ]);
    }
  }, [messages.length]);

  // 자동 스크롤
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  /** 메시지 추가 */
  const pushMessage = (msg) => {
    setMessages((prev) => [...prev, { ...msg, id: uuid(), createdAt: Date.now() }]);
  };

  /** OX 응답 핸들러 */
  const handleOX = (value) => {
    if (!currentQuestion) return;
    pushMessage({ role: "user", content: `${value}` });
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: value }));
    goNextStep();
  };

  /** 파일 업로드 핸들러 */
  const onFileChange = (e) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const f = e.target.files[0];
    setFile(f);
    pushMessage({ role: "user", content: `파일 업로드: ${f.name}`, fileName: f.name });
    goNextStep();
  };

  /** 다음 질문 or 분석 유도 */
  const goNextStep = () => {
    const next = currentStep + 1;
    setCurrentStep(next);
    const nextQ = questions.find((q) => q.id === next);
    if (nextQ) {
      pushMessage({ role: "assistant", content: nextQ.text });
    } else {
      pushMessage({ role: "assistant", content: "답변 감사합니다! 아래 **분석 시작** 버튼을 눌러 최종 피드백을 받아보세요." });
    }
  };

  /** 분석 실행 */
  const runAnalysis = async () => {
    const formData = new FormData();
    formData.append("answers", JSON.stringify(answers));
    if (file) formData.append("file", file);

    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/chat", { method: "POST", body: formData });
      const raw = await res.text();
      let data = {};
      try { data = JSON.parse(raw); } catch {
        pushMessage({ role: "assistant", content: `에러(${res.status})\n${raw}` });
        return;
      }
      const text = data.final_feedback || data.output || data.result || data.message || data.error;
      pushMessage({ role: "assistant", content: text || "응답이 없습니다." });
    } catch (e) {
      pushMessage({ role: "assistant", content: `서버 요청 오류: ${String(e)}` });
    } finally {
      setLoading(false);
    }
  };

  /** 초기화 */
  const resetChat = () => {
    setMessages([]);
    setAnswers({});
    setFile(null);
    setCurrentStep(1);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(ANSWER_KEY);
  };

  /** **bold** / 줄바꿈 처리 */
  const toHtml = (src) =>
    src
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br/>");

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <header style={styles.header}>
          <h1 style={styles.logo}>사샤 – 금융 코치</h1>
          <div style={styles.headerBtns}>
            <button style={styles.resetBtn} onClick={resetChat}>대화 초기화</button>
          </div>
        </header>

        <div style={styles.chatWindow}>
          {messages.map((m) => (
            <div key={m.id} style={{ ...styles.bubble, ...(m.role === "assistant" ? styles.assistant : styles.user) }}>
              {m.fileName ? (
                <div><div style={styles.fileBadge}>📎 {m.fileName}</div></div>
              ) : (
                <div dangerouslySetInnerHTML={{ __html: toHtml(m.content) }} />
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div style={styles.controls}>
          {currentQuestion?.type === "OX" && (
            <div style={styles.actionsRow}>
              <button style={styles.actionBtn} onClick={() => handleOX("O")}>O</button>
              <button style={styles.actionBtn} onClick={() => handleOX("X")}>X</button>
            </div>
          )}

          {currentQuestion?.type === "file" && (
            <div style={styles.actionsRow}>
              <label style={styles.fileLabel}>
                파일 선택
                <input type="file" style={{ display: "none" }} onChange={onFileChange} />
              </label>
              {file && <span style={styles.fileName}>{file.name}</span>}
            </div>
          )}

          {currentStep > questions.length && (
            <div style={styles.actionsRow}>
              <button style={{ ...styles.primaryBtn, opacity: loading ? 0.7 : 1 }} onClick={runAnalysis} disabled={loading}>
                {loading ? "분석 중…" : "분석 시작"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { background: "#0b1420", minHeight: "100vh", padding: "24px 0" },
  container: { maxWidth: 820, margin: "0 auto", padding: "0 20px", color: "#e7edf6", fontFamily: "Pretendard, system-ui, sans-serif" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  logo: { margin: 0, fontSize: 22, fontWeight: 800 },
  headerBtns: { display: "flex", gap: 8 },
  resetBtn: { background: "transparent", border: "1px solid rgba(255,255,255,.2)", borderRadius: 10, color: "#e7edf6", padding: "8px 12px", cursor: "pointer" },
  chatWindow: { background: "#0f1b2d", borderRadius: 14, padding: 16, height: "62vh", overflowY: "auto", boxShadow: "0 0 0 1px rgba(255,255,255,0.06) inset" },
  bubble: { maxWidth: "78%", padding: "10px 12px", borderRadius: 12, marginBottom: 10, lineHeight: 1.5, wordBreak: "break-word", fontSize: 15 },
  assistant: { background: "rgba(255,255,255,0.06)", borderTopLeftRadius: 4, alignSelf: "flex-start" },
  user: { background: "#3b82f6", color: "#fff", borderTopRightRadius: 4, marginLeft: "auto" },
  fileBadge: { fontSize: 14 },
  controls: { marginTop: 12 },
  actionsRow: { display: "flex", gap: 8, alignItems: "center", justifyContent: "flex-start", flexWrap: "wrap" },
  actionBtn: { padding: "10px 16px", borderRadius: 10, background: "#1f2b3e", color: "#e7edf6", border: "1px solid rgba(255,255,255,.15)", cursor: "pointer", fontSize: 16 },
  fileLabel: { padding: "10px 16px", borderRadius: 10, background: "#1f2b3e", border: "1px solid rgba(255,255,255,.15)", cursor: "pointer" },
  fileName: { opacity: 0.8 },
  primaryBtn: { padding: "12px 18px", borderRadius: 10, border: "none", background: "#3b82f6", color: "#fff", fontSize: 16, cursor: "pointer" }
};
