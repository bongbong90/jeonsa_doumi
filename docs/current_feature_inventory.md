# 전사도우미 현재 기능 인벤토리

작성일: 2026-05-27  
기준 코드: `gui_main.py`, `auto_transcribe.py`, `colab_transcribe.ipynb`

## 1. 앱 개요
- 앱명: 전사도우미
- 플랫폼: Windows 데스크톱(PySide6)
- 입력: MP3
- 출력: TXT / JSON / SRT
- 전사 엔진: 로컬 Whisper(`medium`) / Colab Large-v3

## 2. UI/작업 기능
- 탭 구조: `Transcriptions`, `Dashboard`, `Folders`
- 파일 큐 테이블:
  - 컬럼: `체크`, `Filename`, `Duration`, `Status`, `Action`
  - 상태: `WAITING`, `PROCESSING`, `DONE`, `FAILED`, `MOVED`, `STOP`
- MP3 길이 계산:
  - 1순위 `mutagen`
  - 2순위 `tinytag`
  - 3순위 MP3 프레임 파싱 폴백
- 파일 이동 흐름:
  - 선택 MP3를 전사자료 폴더로 이동
  - 이동 후 바로 전사 시작 가능
  - 전사자료 폴더 전체 전사 시작 가능
- 파일명 처리:
  - `.mp3` 확장자 보정
  - 파일명 끝 페이지 표기 패턴 제거(`(p.12)`, `(p.12~34)` 등)

## 3. 로컬 Whisper 기능
- 워커 파일: `auto_transcribe.py`
- 모델 기본값: `medium`
- GPU(CUDA) 사용 가능 시 자동 사용, 실패 시 CPU 폴백
- 완료 파일 스킵 기준:
  - `txt/json/srt` 3종 존재
  - `txt/json` 1바이트 초과
  - `json`에 `text`, `segments` 키 존재
- 진행률 기준:
  - 전체 발견 MP3 수가 아니라 이번 실행 실제 처리 파일 수
- 이벤트:
  - `TOTAL_FILES`, `FILE_INDEX`, `START_FILE`, `FILE_DONE`, `FILE_SKIP`, `FILE_FAIL`
  - `STOPPED`, `ALL_DONE`, `ALL_STOPPED`, `PROCESS_CRASHED`

## 4. Colab Large-v3 기능
- GUI 전사 방식 콤보 지원(`로컬 Whisper` / `Colab Large-v3`)
- Colab URL 입력 패널/연결 확인/Colab 열기 버튼 제공
- 연결 확인은 `/health` 호출, 성공 시 `연결됨 ✓` 상태
- URL 정규화:
  - 입력 URL에 `/health` 또는 `/transcribe`가 포함돼도 내부 정규화
  - transcribe 요청은 `/transcribe` 기준
- 분할 전송:
  - `ffmpeg` 필수
  - 600초 단위 분할
  - 조각명 `chunk_0000.mp3` 형식
- 조각 병합:
  - 조각별 segment `start/end`에 offset 합산
  - 병합 결과를 `TXT/JSON/SRT` 저장
  - 임시 chunk 폴더 정리
- 중지:
  - 현재 조각 완료 후 중단(`ALL_STOPPED`)

## 5. 상태/세션/이어하기
- 로컬 세션 파일: `transcribe_session_state.json`
  - 상태값: `running`, `completed`, `stopped_by_user`, `crashed`, `corrupt_session`
  - `completed_files` 저장/복원
  - `tmp` 파일 기록 후 `os.replace`
  - 저장 실패 재시도(`PermissionError`/`OSError` 계열)
  - 오래된 `transcribe_session_state.json.tmp` 자동 정리
  - 이전 `running` 세션은 `stop.flag` 존재 여부로 사용자중지/비정상종료 분기
- 중지 플래그: `stop.flag`
  - GUI 중지 버튼이 파일 생성
  - 워커가 루프/파일 시작 전/저장 전 지점에서 확인
  - 중지 시 `stopped_by_user` 기록 + `ALL_STOPPED`
- Colab 이어하기 파일: `progress.json`
  - 키: `session_id`, `engine`, `total_files`, `completed_files`, `last_updated`
  - 앱 시작 시 이어하기 여부 확인
  - 완료 파일 skip 후 잔여 파일만 실행
  - 전체 완료 시 파일 정리

## 6. Dashboard/Folders 기능
- Dashboard
  - 누적 완료 파일 수
  - 누적 오디오 시간
  - 오늘 완료 파일 수
  - 평균 전사 속도
  - 최근 완료 파일 목록
  - 통계는 QSettings(`ui_settings.ini`)에 저장
- Folders
  - 필터: `전체`, `완료`, `미완료`, `결과만`
  - 컬럼: `파일명`, `유형`, `전사 상태`, `수정일`
  - TXT 미리보기(500자) + 전체 보기
  - 완료 판정: MP3 + TXT/JSON/SRT 모두 존재

## 7. 알림/종료/패키징
- 트레이 아이콘 및 트레이 메뉴(열기/종료)
- 커스텀 토스트 알림(폴더 열기 버튼 포함)
- 파일별 완료 알림 / 전체 완료 알림
- 전체 완료 후 종료 옵션:
  - 대기시간 `즉시`, `15초`, `30초`
- PyInstaller spec:
  - `전사도우미.spec`
  - dist 루트에 `auto_transcribe.py` 배치
  - 아이콘 탐색 경로는 일반 실행/`_internal`/`_MEIPASS` 경로 모두 고려
  - 시작 시 Windows Start Menu 바로가기 생성 시도
