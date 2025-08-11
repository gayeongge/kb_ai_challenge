import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from graph import GraphBuilder

# PostgreSQL 연결 문자열
# Container에서 실행시키려면 localhost -> pgvector-db 로 변경
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

# SQLAlchemy 엔진 및 세션 설정
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 모델 베이스 클래스
Base = declarative_base()


# User 모델 정의
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, Sequence("user_id_seq"), primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)


# 테이블 생성 함수
def create_db_and_tables():
    print("📦 데이터베이스 테이블을 생성 중...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 테이블이 성공적으로 생성되었습니다.")
    except SQLAlchemyError as e:
        print(f"❌ 테이블 생성 중 오류 발생: {e}")


# 데이터 삽입 및 조회 예제
def insert_and_query_example():
    print("🔍 예시 사용자 추가 및 조회를 시작합니다...")
    try:
        with SessionLocal() as db:
            # 중복 사용자 확인
            user_exists = db.query(User).filter(
                (User.username == "testuser") | (User.email == "test@example.com")
            ).first()

            if not user_exists:
                new_user = User(username="testuser", email="test@example.com")
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                print(f"👤 사용자 추가 완료: {new_user.username}")
            else:
                print("ℹ️ 이미 동일한 사용자가 존재합니다.")

            # 사용자 전체 조회
            print("📋 현재 등록된 사용자:")
            for user in db.query(User).all():
                print(f" - ID: {user.id}, Username: {user.username}, Email: {user.email}")

    except SQLAlchemyError as e:
        print(f"❌ 데이터 처리 중 오류 발생: {e}")


if __name__ == "__main__":
    # TEST 용
    create_db_and_tables()
    insert_and_query_example()

    # CHAT TEST 용
    builder = GraphBuilder()
    user_input = input("질문을 입력하세요: ")
    for chunk in builder.run_graph_streaming(user_input):
        print(chunk)
        # print(chunk.get("output", ""), end="", flush=True)
