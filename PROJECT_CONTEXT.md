# 전사도우미 PROJECT CONTEXT

최종 업데이트: 2026-05-27  
용도: Codex/개발 보조 AI 인수인계를 위한 현재 코드 기준 문서

## 1. 프로젝트 목적
- 프로젝트명: `전사도우미`
- 플랫폼: Windows 데스크톱 앱
- 목적: MP3 전사를 수행하고 결과물 `TXT/JSON/SRT` 생성
- GUI에서 전사 준비, 실행, 중지, 진행률, 폴더 관리, 알림, 종료 옵션까지 통합 제공

## 2. 현재 기술 스택
- UI: `PySide6`
- 로컬 전사: `openai-whisper` (`medium`, CUDA 가능 시 가속)
- Colab 전사: `faster-whisper large-v3` + Flask 서버
- 통신: `urllib.request` 기반 HTTP (`/health`, `/transcribe`)
- 설정 저장: `QSettings` (`ui_settings.ini`)
- 배포: `PyInstaller onedir` (`전사도우미.spec`)

## 3. 주요 파일 역할
- `gui_main.py`
  - 메인 GUI
  - 탭 구성(Transcriptions/Dashboard/Folders)
  - 로컬/Colab 전사 실행 제어
  - stop.flag 생성, 세션 표시, 알림/트레이/종료 옵션
  - Dashboard 통계 및 Folders 파일 관리
- `auto_transcribe.py`
  - 로컬 Whisper 워커 프로세스
  - MP3 탐색, 완료 파일 스킵, 전사 실행, 결과 저장
  - `transcribe_session_state.json` 세션 상태 기록
  - `[EVENT]` 라인으로 GUI와 이벤트 통신
- `colab_transcribe.ipynb`
  - Colab 서버 노트북
  - `faster-whisper large-v3` 모델 로딩
  - Flask 엔드포인트(`/health`, `/transcribe`, `/jobs*`) 제공
  - `cloudflared` quick tunnel URL 생성
- `전사도우미.spec`
  - PyInstaller 빌드 정의
  - `assets`, `transcribe_helper.ico`, `auto_transcribe.py` 포함
  - dist 루트에 `auto_transcribe.py` 복사하는 `CollectWithRootAutoTranscribe` 포함

## 4. 현재 앱 구조
- 상단 탭: `Transcriptions`, `Dashboard`, `Folders`
- 전사 엔진 선택: `로컬 Whisper(local)` / `Colab Large-v3(colab)`
- Transcriptions 파일 큐 상태: `WAITING`, `PROCESSING`, `DONE`, `FAILED`, `MOVED`, `STOP`
- 전사 파일 분류: 과정명, 과목명 선택 (파일명 정규화 기준, 여러 과목 혼합 방지)
- Google Drive 자동 업로드: 전사 완료 후 MP3/TXT/JSON/SRT 4종 업로드 토글
- 선택 파일 이동/이동 후 전사/전체 전사/즉시 중지 버튼 제공

## 5. 로컬 전사 흐름
1. 과정명/과목명 선택값 기반 파일명 정규화 미리보기 후 승인
2. GUI가 `QProcess`로 `auto_transcribe.py <runtime_folder> --upload-drive (옵션)` 실행
3. 워커가 MP3 목록 탐색 후 완료 파일(`txt/json/srt` 무결성 기준) 스킵
4. `TOTAL_FILES(전체/스킵/실처리)` 이벤트 전송
5. 실처리 파일만 대상으로 `FILE_INDEX -> START_FILE -> FILE_DONE/FILE_FAIL` (Drive 업로드 설정 시 `FILE_DONE` 직전 업로드 수행)
6. 완료 시 `ALL_DONE`, 중지 시 `STOPPED + ALL_STOPPED`, 치명 오류 시 `PROCESS_CRASHED`

핵심 포인트
- 진행률 분모는 전체 발견 수가 아닌 `이번 실행 실제 처리 파일 수`
- 파일명 정규화: `과정명_과목명_N주차_N강` 형식으로 전사 시작 전 원본 MP3명 및 기존 결과물 rename
- Google Drive 자동 업로드: `--upload-drive` 인자 전달 시 로컬 저장 완료 후 4종 파일 업로드
- 결과 파일은 MP3와 같은 폴더에 저장

## 6. Colab 전사 흐름
1. GUI에서 `Colab Large-v3` 선택 시 URL 패널 표시
2. `연결 확인` 버튼으로 `/health` 호출
3. 성공 시 버튼 텍스트 `연결됨 ✓`
4. 전사 시작 시 URL을 `/transcribe`로 정규화
5. `ffmpeg` 확인 후 MP3를 600초 단위 분할(`chunk_%04d.mp3`)
6. 조각별 `/transcribe` 요청 후 segment offset 보정 병합
7. 병합 결과를 `TXT/JSON/SRT` 저장
8. 조각 폴더 정리 후 다음 파일 처리
9. 중지 요청 시 현재 조각 완료 후 `ALL_STOPPED`

노트북 서버 구조
- Flask + CORS
- 작업 저장: 메모리 `JOBS` 딕셔너리
- TTL: `JOB_TTL_SECONDS = 6시간`
- 실행기: `ThreadPoolExecutor(max_workers=1)` (순차 처리)
- 엔드포인트:
  - `GET /health`
  - `POST /transcribe` (legacy 동기 대기형)
  - `POST /transcribe/start`
  - `POST /jobs`
  - `GET /jobs/<job_id>/status`
  - `GET /jobs/<job_id>/result`

## 7. 상태/세션/중지 관리
로컬 세션 파일
- 파일명: `transcribe_session_state.json`
- 위치: 전사 폴더의 부모 디렉터리
- 상태값: `running`, `completed`, `stopped_by_user`, `crashed`, `corrupt_session`
- `completed_files` 저장/복원
- 저장 방식: `*.tmp` 작성 후 `os.replace`
- `PermissionError`/`OSError` 계열에서 재시도 로직 포함
- 오래된 `transcribe_session_state.json.tmp` 자동 정리

이전 세션 판단
- 이전 상태가 `running` + `stop.flag` 존재: 사용자 중지 이력으로 전환
- 이전 상태가 `running` + `stop.flag` 없음: 비정상 종료(`crashed`)로 전환

중지 처리
- GUI 중지 버튼이 `stop.flag` 생성(로컬)
- 워커는 루프 진입 전/파일 시작 전/전사 후 저장 전 등에서 중지 확인
- 중지 시 `stopped_by_user` 기록 + `ALL_STOPPED` 이벤트
- Colab은 `_colab_stop_after_current=True`로 현재 조각 완료 후 중단

Colab 이어하기
- 파일: `progress.json` (기본 전사 폴더)
- 필드: `session_id`, `engine`, `total_files`, `completed_files`, `last_updated`
- 앱 시작 시 존재하면 이어하기 확인 다이얼로그 표시
- 이어하기 선택 시 완료된 source mp3는 skip
- 전체 완료 시 `progress.json` 삭제

## 8. UI 탭 구조
- `Transcriptions`
  - 왼쪽 사이드바: `폴더 설정`, `전사 파일 분류(과정/과목)`, `Google Drive 업로드`, `알림 및 종료 옵션`, `실행 로그` (스크롤 영역 처리로 UI 잘림 방지)
  - 메인 영역: 큐 테이블, 실행 제어, 전사 방식 선택, Colab URL 영역
- `Dashboard`
  - `TOTAL DONE FILES`
  - `TOTAL AUDIO TIME`
  - `DONE TODAY`
  - `AVG TRANSCRIBE SPEED`
  - `RECENT COMPLETIONS`
- `Folders`
  - 현재 폴더 파일 목록
  - 필터(`전체/완료/미완료/결과만`)
  - TXT 미리보기(최대 500자) + 전체 보기

## 9. 저장 설정 구조
설정 파일
- `QSettings(get_ui_settings_path(), IniFormat)`
- 우선 경로:
  1. `%APPDATA%\전사도우미\ui_settings.ini`
  2. `%PUBLIC%\Documents\ESTsoft\CreatorTemp\전사도우미\ui_settings.ini`
  3. runtime base dir 하위 `ui_settings.ini`

저장 키(주요)
- `ui/target_folder`
- `ui/notify_each_file`
- `ui/notify_total`
- `ui/shutdown_after_done`
- `ui/shutdown_wait_seconds`
- `ui/transcription_engine`
- `ui/colab_url`
- `dashboard/*` 통계 키

## 10. 최근 구현 상태
- Colab 모드 연결 확인/전송/분할/병합/이어하기 구현됨
- 트레이 + 커스텀 토스트 + 폴더 열기 버튼 동작 + 상황형 알림창 UI 및 톤 매너 최적화
- GUI 과정명/과목명 선택값 기반 파일명 자동 정규화(`과정명_과목명_N주차_N강`) 구현
- Google Drive 자동 업로드(MP3/TXT/JSON/SRT) 및 인증 권한 보호 연동 구현
- 왼쪽 사이드바 UI 영역 분리(분류/Drive/옵션) 및 QScrollArea 적용 완료
- PyInstaller 배포본 `auto_transcribe.py --upload-drive` 및 API 의존성 패키징 반영 성공

## 11. 작업 시 주의사항
- 문서/코드 작업 시 현재 `gui_main.py`, `auto_transcribe.py`, `colab_transcribe.ipynb`를 기준으로 판단
- Colab 관련 변경 시 GUI URL 정규화(`/health`, `/transcribe`)와 노트북 엔드포인트 호환성 유지
- 결과물 완료 판정 규칙(txt/json/srt + json key 검증) 깨지지 않게 유지
- selected/moved/all 실행 모드에서 runtime 폴더 동기화 흐름 확인

## 12. 금지사항
- 확인되지 않은 기능을 문서에 구현됨으로 기재 금지
- `git add .` 금지(개별 파일 add만 허용)
- 사용자 요청 없는 코드 대규모 리팩터링/로직 변경 금지
- `build/`, `dist/`, 캐시/로그 산출물 커밋 금지

## 13. 다음 작업 후보
1. requirements 잠금 파일(`requirements.txt` 또는 `pyproject.toml`) 정리
2. Colab 비동기 job 엔드포인트(`/jobs*`)를 GUI에서 선택 사용하도록 확장할지 검토
3. 패키징 산출물 기준 실사용 QA 체크리스트 자동화
4. Folders 탭 결과 미리보기(예: JSON/SRT 요약) 범위 확장 검토
