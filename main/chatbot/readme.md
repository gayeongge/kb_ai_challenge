### Chatbot 실행
- 다음 순을 따라 main.py를 실행시킨다.

#### [Local Ollama]
1. 각자 서버에 Ollama를 올린다.
2. chatbot/.env 파일에서 Ollama_BASE_URL을 자기 로컬 주소에 맞춘다.
3. Chatbot 폴더에서 `python mian.py`를 실행시킨다.

#### [Container Ollama]
1. default 컨테이너 이름을 Ollama_BASE_URL에 고정으로 입력하고 커밋하여 사용한다.
2. Local Ollama에서 했던 작업 없이 그냥 바로 `python main.py`를 실행하기만 하면 된다.

#### 주의사항
- 위 방법을 수행하거나 개발하면서 발생하는 에러가 있다면 오류 수정하거나, 바로 이슈로 올려서 같이 수정한다.