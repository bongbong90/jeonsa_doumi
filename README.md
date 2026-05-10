# 전사도우미

전사도우미는 MP3 파일 자동 전사를 위한 Windows 데스크톱 앱입니다.  
전사 대기열 관리, 진행률 표시, 로컬/Colab 전사 모드를 한 화면에서 운영할 수 있습니다.

## 프로젝트 소개

- MP3 파일을 전사자료 폴더 기준으로 일괄 전사
- 결과물을 `.txt`, `.json`, `.srt` 형식으로 저장
- 전사 진행 상태, 로그, 트레이 동작을 GUI에서 통합 관리

## 주요 기능

- 전사 대기열 관리
- 로컬 Whisper 전사 (`medium` + GPU 가속 자동 감지)
- Colab Large-v3 전사 연동 (`faster-whisper`)
- 전사 진행률/ETA 실시간 표시
- Dashboard / Folders 탭 제공
- 전사 완료 후 컴퓨터 종료 옵션

## 기술 스택

- GUI: PySide6
- 전사 엔진: OpenAI Whisper / faster-whisper
- 배포: PyInstaller onedir

## Colab 연동 사용법

1. 앱에서 `Colab 열기` 버튼 클릭
2. Colab 런타임을 `T4 GPU`로 선택
3. 노트북 셀 `모두 실행`
4. 생성된 터널 URL을 앱의 `Colab URL` 입력칸에 붙여넣기
5. `연결 확인` 성공 후 전사 시작

## 로컬 실행 방법

1. 필요 패키지 설치

```bash
pip install -r requirements.txt
```

`requirements.txt`가 없거나 환경에 따라 추가 설치가 필요한 경우:

```bash
pip install PySide6 openai-whisper torch pydub
```

2. 앱 실행

```bash
python gui_main.py
```
