FROM continuumio/miniconda3:25.3.1-1

LABEL maintainer="zero"
LABEL version="0.1"

WORKDIR /project
RUN mkdir -p /project/main

RUN apt-get update && \
    apt-get install -y git\
    curl\
    wget\
    vim && \
    rm -rf /var/lib/apt/lists/*

# 필요 라이브러리 설치
COPY ./env/requirements.txt /project/env/requirements.txt

# readme 파일 복사
COPY ./readme.md /project/README.md

# Jupyter 설정 파일 복사
COPY ./env/jupyter_config.py /project/env/jupyter_config.py

# entrypoint 스크립트 복사
COPY ./env/entrypoint.sh /project/env/entrypoint.sh
RUN chmod +x /project/env/entrypoint.sh

# conda 가상환경 생성 (Python 3.12)
RUN conda create -n kb_env python=3.12 -y

# conda 환경 활성화를 위한 설정
SHELL ["conda", "run", "-n", "kb_env", "/bin/bash", "-c"]

RUN pip install --upgrade pip && \
    pip install -r /project/env/requirements.txt

# conda 환경을 기본으로 설정
RUN echo "conda activate kb_env" >> ~/.bashrc
ENV PATH /opt/conda/envs/kb_env/bin:$PATH
ENV CONDA_DEFAULT_ENV kb_env

# 포트 설정 (fastapi 서버 포트)
EXPOSE 7860
EXPOSE 8888

# 기본 명령어 설정
ENTRYPOINT ["/project/env/entrypoint.sh"]
CMD ["/bin/bash"]