# 전사도우미 PROJECT CONTEXT (최종 확정본)

최종 업데이트: 2026-05-10  
목적: 전사도우미 프로젝트의 현재 확정 상태(기능/구조/남은 작업) 인수인계 문서

---

## 1. 프로젝트 개요

- 프로젝트명: 전사도우미
- 플랫폼: Windows 데스크톱 앱
- 핵심 목적: MP3 자동 전사 및 결과물(`.txt`, `.json`, `.srt`) 생성
- GUI: PySide6
- 배포: PyInstaller `onedir`

---

## 2. 전사 방식 구조 (확정)

- 로컬 Whisper
  - 모델: `medium`
  - CUDA 자동 감지
  - GPU 가능 시 가속 사용, 불가 시 CPU 폴백

- Colab Large-v3
  - `faster-whisper` 기반 (`colab_transcribe.ipynb`)
  - `cloudflared` 터널 URL 연동
  - 앱에서 `/health` 연결 확인 후 `/transcribe` 요청

---

## 3. 완료 기능 목록 (최신)

- 로컬 Whisper `medium` + GPU 가속(CUDA 자동 감지) 적용
- Colab Large-v3 전사 연동 완료
  - `faster-whisper` 기반
  - MP3 10분(600초) 단위 분할 전송
  - TXT/JSON/SRT 결과 저장
  - `progress.json` 중간 저장/재개
  - 전사 중지 시 조각 단위 처리(현재 조각 완료 후 중단)
  - Colab 연결 확인 버튼(`/health`)
  - Colab 열기 버튼(브라우저 자동 실행)
  - 마지막 통신 시간 표시
- 전사 완료 파일 대기열 자동 제외
- 전사 대기열 우클릭 기본 컨텍스트 메뉴 제거
- 트레이 종료 확인 팝업 배경 수정
- 실행 로그 한글 깨짐 수정

---

## 4. 현재 루트 파일/폴더 구조 (확정)

```text
C:\Users\User\Desktop\전사프로그램
├─ gui_main.py
├─ auto_transcribe.py
├─ colab_transcribe.ipynb
├─ 전사도우미.spec
├─ PROJECT_CONTEXT.md
├─ README.md
├─ .gitignore
├─ transcribe_helper.ico
├─ transcribe_helper.svg
├─ pyrightconfig.json
├─ assets\
├─ docs\
└─ .vscode\
```

---

## 5. 운영/유지 원칙

- 작업 시작 전 `PROJECT_CONTEXT.md` 확인
- UI 이슈와 전사 엔진 이슈를 분리해 진단
- 사용자 승인 전 `git add .`, 커밋, 푸시 금지
- 배포 점검 시 `onedir` 구조와 실행 파일 동작을 우선 확인

---

## 6. 남은 작업

- exe 최종 검수 (내일 예정)
