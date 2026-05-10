# 전사도우미 PROJECT CONTEXT

최종 업데이트: 2026-05-10  
목적: 전사도우미 프로젝트의 현재 구조, 완료 상태, 남은 작업을 공유하기 위한 인수인계 기준 문서

---

## 1. 프로젝트 개요

- 프로젝트명: 전사도우미
- 목표: MP3 파일을 자동 전사하고(txt/json/srt), GUI에서 대기열/진행률/로그/중지/트레이를 통합 관리
- 실행 환경: Windows 데스크톱
- GUI 스택: PySide6
- 배포 방식: PyInstaller onedir

---

## 2. 전사 방식 구조 (현재 기준)

- 로컬 Whisper
  - 모델: `medium`
  - CUDA 사용 가능 시 GPU 가속 자동 적용
  - CUDA 미사용 환경에서는 CPU 자동 폴백
- Colab Large-v3
  - `faster-whisper` 기반 Colab 서버(`colab_transcribe.ipynb`) 연동
  - `cloudflared` 터널 URL을 앱에 연결하여 `/health`, `/transcribe` 사용

---

## 3. 현재 코드 기준 파일 구조

### 3-1. 핵심 파일

- `gui_main.py`: GUI 본체, 대기열/진행률/로그/트레이/Colab 연동 제어
- `auto_transcribe.py`: 로컬 Whisper 전사 엔진, stop.flag 처리, 결과 저장
- `colab_transcribe.ipynb`: Colab Whisper Large-v3 전사용 Flask 서버 노트북
- `전사도우미.spec`: PyInstaller onedir 빌드 스크립트
- `assets\`: 앱 리소스
- `transcribe_helper.ico`: 앱 아이콘

### 3-2. 배포 구조(확인 기준)

```text
dist\전사도우미\
├─ 전사도우미.exe
├─ auto_transcribe.py
└─ _internal\
```

---

## 4. 절대 유지 규칙

- `PyInstaller onedir` 유지
- `onefile` 전환 금지
- `auto_transcribe.py`는 `전사도우미.exe`와 같은 폴더에 존재해야 함
- `dist\전사도우미\_internal` 삭제/이동 금지
- `assets`, `transcribe_helper.ico` 삭제 금지

---

## 5. 최근 완료 작업 (최신 반영)

- Colab Large-v3 전사 연동 완료
  - `faster-whisper` 기반 `colab_transcribe.ipynb` 생성
  - MP3 10분(600초) 단위 분할 전송으로 HTTP 524 타임아웃 대응
  - Colab 응답 기반 TXT/JSON/SRT 저장
  - 전사 중지 시 조각 단위 처리 및 중단 반영
- 로컬 Whisper `medium` + GPU 가속(CUDA 자동 감지) 적용
- 전사 완료 파일(`.txt/.json/.srt` 3종 존재) 대기열 자동 제외
- Colab 연결 확인 버튼(`/health` 체크) 적용
- Colab 열기 버튼(브라우저 자동 실행) 적용
- 마지막 통신 시간 표시 적용
- 전사 대기열 우클릭 기본 컨텍스트 메뉴 제거
- 트레이 종료 확인 팝업 배경(흑색 문제) 수정
- 실행 로그 한글 깨짐 출력 문제 수정
- Dashboard/Folders 탭 구현 및 운영 상태 반영

---

## 6. 현재 주요 기능

- 전사 대기열 로드 및 상태 표시(WAITING/PROCESSING/DONE/FAILED/STOP)
- 체크 파일만 전사, 미체크 시 전체 전사
- 전사 시작/중지 버튼 제어 및 ETA/진행률 표시
- 파일명 정리 및 더블클릭 편집
- Dashboard 통계(누적/오늘/평균 속도/최근 완료) 저장/복원
- Folders 탭(파일 스캔, 상태 판정, TXT 미리보기/전체보기)
- 트레이 최소화/복원/종료 확인
- 전사 완료 후 컴퓨터 종료 옵션

---

## 7. Colab 연동 동작 요약

- 앱에서 Colab URL 입력 후 연결 확인(`/health`)
- Colab 모드 전사 시작 시 MP3를 10분 조각으로 분할
- 각 조각을 `/transcribe`로 순차 전송
- 조각별 `segments` 시간 오프셋 보정 후 병합
- 최종 결과를 TXT/JSON/SRT로 저장
- 중지 요청 시 현재 조각 완료 후 다음 조각/다음 파일 중단

---

## 8. 남은 작업 (업데이트)

- `progress.json` 중간 저장/재개 기능 설계 및 구현
- 빌드 결과물(onedir) 및 배포본 최종 검수

---

## 9. 작업 원칙

- 작업 시작 전 `PROJECT_CONTEXT.md` 먼저 확인
- 코드 수정 범위 최소화
- UI 이슈와 전사 로직 이슈 분리 진단
- 배포 이슈는 `전사도우미.spec`과 `dist` 구조부터 확인
- 사용자 승인 전 `git add .`, 커밋, 푸시 금지
