### Chatbot 실행
-  현재 Ollama 컨테이너가 안 올라가져 있어서 node/react.py 에 있는 base_url이 빈 값으로 되어 있다.
- 다음 순을 따라 main.py를 실행시킨다.

#### [Local Ollama]
1. 각자 서버에 Ollama를 올린다.
2. node/react.py의 ChatOllama의 base_url 주소에 올린 Ollama 서버 주소를 입력한다.
3. Chatbot 폴더에서 `python mian.py`를 실행시킨다.

#### [Container Ollama]
1. default 컨테이너 이름을 base_url에 고정으로 입력하고 커밋하여 사용한다.
2. Local Ollama에서 했던 작업 없이 그냥 바로 `python main.py`를 실행하기만 하면 된다.

#### 주의사항
- 위 방법을 수행하거나 개발하면서 발생하는 에러가 있다면 오류 수정하거나, 바로 이슈로 올려서 같이 수정한다.
- 현재는 base_url이 빈 값이기 때문에 바로 mian 파일을 실행시키면 에러 날 것 이다.