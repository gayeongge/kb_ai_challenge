# chatbot/util/rag.py
import os
from typing import List, Optional
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

DEFAULT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "rag_data")
)

class RAGStore:
    def __init__(self, data_dir: str = DEFAULT_PATH, chunk_size=800, chunk_overlap=120):
        self.data_dir = os.path.abspath(data_dir)
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.emb = OllamaEmbeddings(model="bge-m3")  # 임베딩 모델(로컬 올라마)
        self.vs = None

    def build(self):
        loader = DirectoryLoader(
            self.data_dir,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={
                "encoding": "utf-8",
                "autodetect_encoding": True,
            },
            show_progress=True,
            use_multithreading=True,
            silent_errors=True,
        )
        docs = loader.load()
        # 파일명으로 대략적 성향 태그 메타 넣기 (egen/teto/neutral)
        for d in docs:
            fname = os.path.basename(d.metadata.get("source", "")).lower()
            if "egen" in fname:
                d.metadata["persona"] = "EGEN"
            elif "teto" in fname:
                d.metadata["persona"] = "TETO"
            else:
                d.metadata["persona"] = "NEUTRAL"

        splits = self.splitter.split_documents(docs)
        self.vs = FAISS.from_documents(splits, self.emb)
        return self

    def load_or_build(self, index_path: str = None):
        if index_path and os.path.exists(index_path):
            self.vs = FAISS.load_local(index_path, self.emb, allow_dangerous_deserialization=True)
        else:
            self.build()
            if index_path:
                self.vs.save_local(index_path)
        return self

    def retriever(self, k: int = 4):
        if not self.vs:
            self.build()
        return self.vs.as_retriever(search_kwargs={"k": k})

def rag_search(query: str, k: int = 4, data_dir: str = DEFAULT_PATH) -> str:
    store = RAGStore(data_dir=data_dir).load_or_build()
    retriever = store.vs.as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(query)
    # ✅ 원문 대신 '제목/요지'만
    lines = []
    for i, d in enumerate(docs, 1):
        title = d.metadata.get("source", "").split(os.sep)[-1]
        snippet = (d.page_content[:200] + "…") if len(d.page_content) > 200 else d.page_content
        lines.append(f"[{i}] {title} :: {snippet}")
    return "RAG hits:\n" + "\n\n".join(lines)

# ✅ LLM 컨텍스트용: 성향(persona) 필터 + 본문 합성
def rag_context(query: str, persona: Optional[str] = None, k: int = 6, data_dir: str = DEFAULT_PATH) -> str:
    store = RAGStore(data_dir=data_dir).load_or_build()
    # top-많이 가져와서 간단히 필터링 (FAISS 기본 메타필터가 없어 post-filter)
    docs = store.vs.similarity_search(query, k=16)
    if persona:
        persona = persona.upper()
        docs = [d for d in docs if d.metadata.get("persona") in (persona, "NEUTRAL")]
    docs = docs[:k]

    parts = []
    for d in docs:
        src = os.path.basename(d.metadata.get("source", ""))
        parts.append(f"[{src}] {d.page_content.strip()}")
    return "\n\n".join(parts) if parts else "기본 가이드: 비상자금·세액공제·분산투자 원칙."