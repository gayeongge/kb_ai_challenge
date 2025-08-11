import sys
import os

# 'main' 디렉토리를 프로젝트의 루트 경로로 설정
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import fastapi
import uvicorn

from chatbot.graph.builder import GraphBuilder
from chatbot.state.schema import InputState
from chatbot.util.db_util import create_db_and_tables, insert_and_query_example

app = fastapi.FastAPI()
builder = GraphBuilder()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/test/create/test_table")
async def create_db_and_tables_test():
    """PostGreSQL 연결 확인을 위한 테스트 테이블 생성 요청"""
    return create_db_and_tables()

@app.get("/test/insert/test_data")
async def insert_and_query_example_test():
    """PostGreSQL 연결 확인을 위한 테스트 데이터 삽입 요청"""
    return insert_and_query_example()

@app.post("/chat")
async def chatbot_api(request: InputState):
    """Chatbot API - 수정 가능"""
    return builder.run_graph_streaming(request['input'])



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
