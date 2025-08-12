import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

import fastapi
import uvicorn

from graph.builder import GraphBuilder
from graph.chatbot_builder import ChatBuilder
from state.schema import InputState
from util.db_util import create_db_and_tables, insert_and_query_example


app = fastapi.FastAPI()
test_builder = GraphBuilder()
builder = ChatBuilder()

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

@app.post("/test/chat")
async def chatbot_api(request: InputState):
    """Chatbot API - 수정 가능"""
    return test_builder.run_graph_streaming(request['input'])

@app.post("/chat")
async def chatbot_api(request: InputState):
    """Chatbot API - 수정 가능"""
    logging.info(f"Received input: {request['input']}")
    return builder.run_graph_streaming(request['input'])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
