### KB AI 경진 대회 공통 환경 이미지 구축 및 빌드

- 현재는 개발 코드는 수시로 작업될 예정이라 이미지에 넣지 않고, 볼륨 연결하여 진행합니다.
- 그래서 이미지 올렸을 때 자동으로 app이 실행되지 않고, 주피터가 올라갑니다.


#### Docker Desktop에서 사용법
1. 명령어 방식 (CLI) - 개발자 선호
- 터미널/PowerShell/CMD에서:
- bash# 프로젝트 폴더로 이동
- cd C:\your\project\folder

**[빌드 및 실행]**
- docker-compose up --build

**[백그라운드 실행]**
- docker-compose up --build -d

**[중지]**
- docker-compose down

**[로그 확인]**
- docker-compose logs -f

2. GUI 방식 (Docker Desktop) - 초보자 친화적
방법 1: Compose 파일 직접 실행

- Docker Desktop 실행
- 좌측 메뉴에서 "Compose" 클릭
- "Create" 또는 "+" 버튼 클릭
- docker-compose.yml 파일이 있는 폴더 선택
- "Start" 버튼 클릭

방법 2: 폴더 드래그 앤 드롭

- 프로젝트 폴더를 Docker Desktop 창에 드래그 앤 드롭
- 자동으로 docker-compose.yml 감지
- "Start" 버튼 클릭

방법 3: 이미지 빌드 후 실행

- "Images" 탭 → "Build" 버튼
- Dockerfile 선택하여 이미지 빌드
- "Containers" 탭에서 컨테이너 생성 및 실행