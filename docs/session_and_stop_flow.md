# 세션/중지 플로우 정리

작성일: 2026-05-27  
기준 코드: `auto_transcribe.py`, `gui_main.py`

## 1. 로컬 세션 파일 위치
- 파일명: `transcribe_session_state.json`
- 생성 위치: 전사 폴더(`target_folder`)의 부모 디렉터리
- 예시:
  - 전사 폴더: `D:\work\transcribe`
  - 세션 파일: `D:\work\transcribe_session_state.json`

## 2. 세션 상태값
- `running`
- `completed`
- `stopped_by_user`
- `crashed`
- `corrupt_session`

GUI 번역 표시는 `running/완료/사용자 중지/비정상 종료/세션 손상` 형태로 변환됩니다.

## 3. 세션 payload 핵심 필드
- `status`
- `current_file`
- `updated_at`
- `completed_files`
- 상황별 부가 필드:
  - `total_discovered_files`
  - `skipped_files`
  - `target_files_total`
  - `completed_count`
  - `last_done_file`
  - `last_error`, `error_type`
  - `stop_reason`

## 4. 세션 저장 안정성 처리
- 저장은 `transcribe_session_state.json.tmp`에 먼저 기록
- `flush + fsync` 후 `os.replace(tmp, final)`로 교체
- `PermissionError`/`OSError` 계열 실패 시 백오프 재시도
- 오래된 `transcribe_session_state.json.tmp`는 실행 시작 시 정리

## 5. 이전 세션 판정 로직
- 이전 세션 파일 파싱 실패(JSON 손상 등):
  - `PREVIOUS_SESSION_CORRUPT` 이벤트
  - 상태를 `corrupt_session`으로 기록
- 이전 상태가 `running`:
  - `stop.flag` 존재 -> 사용자 중지 이력(`stopped_by_user`)
  - `stop.flag` 없음 -> 비정상 종료(`crashed`)
- 이전 상태가 `stopped`/`stopped_by_user`:
  - 사용자 중지 이력 이벤트 처리

## 6. stop.flag 처리
- 파일명: `stop.flag`
- 생성 위치: 세션 파일과 동일한 부모 디렉터리
- GUI `전사중지` 버튼 클릭 시:
  - stop.flag 파일 생성
  - 로컬 워커 종료 요청 상태 표시
  - 지연 시 `terminate`, 추가 지연 시 `kill` 폴백
- 워커는 다음 지점에서 stop.flag 확인:
  - 파일 루프 진입 전
  - 파일 시작 직전
  - 전사 완료 후 결과 저장 전
  - KeyboardInterrupt 처리 시

## 7. 중지 시 이벤트/상태
- 워커가 stop 감지 시:
  - `STOPPED` 이벤트
  - `ALL_STOPPED` 이벤트
  - 세션 상태 `stopped_by_user` 기록
- GUI가 `ALL_STOPPED` 수신 시:
  - 현재 상태를 사용자 중지로 업데이트
  - `PROCESSING` 행을 `STOP` 상태로 전환
  - ETA/현재 파일 표시 리셋

## 8. 완료 파일 스킵 판정
로컬 워커 및 GUI 공통 기준:
- `txt/json/srt` 모두 존재
- `txt/json` 파일 크기 > 0
- `json` 파싱 가능 + `text`, `segments` 키 존재

판정에 통과한 MP3는 재실행 시 skip 대상이며, 진행률 분모에서도 제외됩니다.

## 9. Colab 이어하기(progress.json)와의 관계
- Colab 모드는 로컬 세션 파일과 별개로 `progress.json`을 사용
- `completed_files` 목록을 기반으로 남은 파일만 실행
- 중지 후 재실행 시 이어하기 선택 가능
- 전체 완료 시 progress 파일 정리
