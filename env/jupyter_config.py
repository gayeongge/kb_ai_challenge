# Jupyter Notebook 설정 파일
c = get_config()

# 네트워크 설정
c.NotebookApp.ip = '0.0.0.0'
c.NotebookApp.port = 8888
c.NotebookApp.open_browser = False
c.NotebookApp.allow_root = True

# 보안 설정 (개발환경용)
c.NotebookApp.token = ''
c.NotebookApp.password = ''
c.NotebookApp.allow_origin = '*'
c.NotebookApp.disable_check_xsrf = True

# 외부 접근을 위한 추가 설정
c.NotebookApp.allow_remote_access = True
c.NotebookApp.allow_origin_pat = '.*'

# 작업 디렉토리 설정
c.NotebookApp.notebook_dir = '/project/main/jupyter'

# 자동 저장 설정
c.FileContentsManager.post_save_hook = None