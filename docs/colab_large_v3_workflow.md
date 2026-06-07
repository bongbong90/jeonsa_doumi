# Colab Large-v3 전사 워크플로우

작성일: 2026-05-27  
기준 코드: `gui_main.py`, `colab_transcribe.ipynb`

## 1. 개요
전사도우미의 Colab 모드는 로컬 Whisper 대신 Colab 서버(`faster-whisper large-v3`)를 사용합니다.  
GUI는 MP3를 600초 단위로 분할 전송하고, 응답 segment를 시간 오프셋 보정해 하나의 결과로 병합합니다.

Colab Large-v3 전사는 GUI에서 선택한 과목명 기준 prompt를 앱이 로드하고, prompt는 Colab `/transcribe` 요청의 multipart form-data로 `initial_prompt`와 함께 전달됩니다.  
Colab 서버는 prompt 기반 전사만 수행하고 corrections 파일은 노트북으로 보내지지 않습니다.  
앱은 chunk 결과를 수신한 다음 segment offset을 보정해 `merged_result`를 만든 뒤, 저장 직전에 `common_terms.json`과 과목별 JSON corrections를 `text`와 `segments`에 적용해 TXT/JSON/SRT를 생성합니다.

## 2. GUI에서의 실행 조건
1. 전사 방식이 `Colab Large-v3`여야 함
2. Colab URL 입력 또는 `클립보드에서 가져오기` 버튼으로 URL 추출 필요
3. `연결 확인` 성공 상태(`연결됨 ✓`) 필요
4. `ffmpeg`가 PATH에 있어야 함

미충족 시 전사 시작 전에 GUI에서 경고/안내 후 중단합니다.

## 3. Colab URL 정규화 규칙
- 스킴이 없으면 `https://` 자동 보정
- 클립보드에서 URL을 가져올 때 `/health`, `/transcribe`, 공백, 줄바꿈 등이 붙어 있어도 base URL만 추출
- 경로 끝이 `/health` 또는 `/transcribe`이면 해당 접미를 제거 후 대상 엔드포인트 재조립
- 연결 확인용 URL: `.../health`
- 전사용 URL: `.../transcribe`

## 4. 분할 전송 및 병합 흐름
1. 원본 MP3를 임시 폴더 `colab_chunks_*`에 분할
2. 분할 단위: 600초 (`COLAB_CHUNK_SECONDS`)
3. 파일명: `chunk_0000.mp3`, `chunk_0001.mp3`, ...
4. GUI에서 선택한 과목명 기준 prompt를 로드
5. 각 조각을 multipart/form-data로 `/transcribe` POST, `initial_prompt`와 `subject`를 함께 전달
6. Colab 서버는 prompt를 수신하고 `faster-whisper model.transcribe()` 호출 시 조건부로 전달
7. Colab 서버는 전사만 수행하고 corrections 파일은 노트북으로 보내지지 않음
8. 조각별 결과의 segment에 `offset` 적용
9. 앱이 chunk 결과를 수신하고 전체 `merged_result`를 생성
   - `text`: 조각 text 결합
   - `segments`: 보정된 전구간 segment 목록
10. 저장 직전에 corrections를 적용
    - `common_terms.json` + 과목별 JSON
    - `text`와 `segments` 모두 대상
11. 병합 결과를 `TXT/JSON/SRT`로 저장
12. 임시 chunk 폴더(`colab_chunks_*`)는 처리 후 정리
13. 중지 요청 시 현재 조각 완료 후 중단

## 5. Colab 중지 동작
- GUI `전사중지` 시 Colab은 즉시 프로세스 kill이 아니라 `현재 조각 완료 후 중단` 정책
- 워커 루프에서 `_colab_stop_after_current` 플래그를 검사
- 중지 시 이벤트 `ALL_STOPPED` 발생

## 6. progress.json 이어하기
- 위치: 전사 폴더(`target_folder`) 하위 `progress.json`
- 기본 구조:
  - `session_id`
  - `engine` (`colab`)
  - `total_files`
  - `completed_files` (파일별 mp3/txt/json/srt 경로 + 완료시각)
  - `last_updated`
- 앱 시작 시 파일이 존재하면 이어하기 여부 확인
- 이어하기 선택 시 완료된 source mp3는 skip
- 전체 완료 시 progress 파일 제거

## 7. Colab Notebook 서버 구조
노트북 파일: `colab_transcribe.ipynb`

구성
- 패키지 설치: `faster-whisper`, `flask`, `flask-cors`
- 모델: `WhisperModel("large-v3")`
- Flask + CORS
- Cloudflare quick tunnel(`cloudflared tunnel --url http://127.0.0.1:5000`)

작업 처리
- 메모리 기반 `JOBS` 딕셔너리
- 만료 정책: `JOB_TTL_SECONDS = 6시간`
- 실행기: `ThreadPoolExecutor(max_workers=1)`  
  -> 동시 다중 작업이 아닌 사실상 순차 처리

엔드포인트
- `GET /health`
  - 상태 확인(`status=ok`, model, engine, jobs_in_memory)
- `POST /transcribe/start`
  - 비동기 작업 생성 엔드포인트 alias
- `POST /jobs`
  - 비동기 작업 생성
- `GET /jobs/<job_id>/status`
  - 상태 조회(`queued/running/done/failed`)
- `GET /jobs/<job_id>/result`
  - 결과/오류 조회
- `POST /transcribe` (legacy)
  - 내부적으로 job 생성 후 완료될 때까지 polling 대기
  - 즉시 job id 반환이 아니라 완료 결과를 동기 응답

## 8. GUI와 노트북 API 사용 관계
- 현재 GUI Colab 전사는 `/transcribe`(legacy 동기 응답) 사용
- 노트북에는 비동기 `/jobs` 계열 API도 존재하지만, GUI 기본 경로는 legacy `/transcribe`입니다.

## 9. 검증 완료
- Mock Colab 서버로 `/health` 및 `/transcribe` 흐름 확인
- PySide6 테스트 스크립트로 GUI 연결 UX 확인
- 클립보드 URL 추출 확인
- 잘못된 URL 연결 실패 알림 확인
- 정상 URL 연결 시 `상태: 연결됨 ✓` 확인
- `initial_prompt`, `subject` multipart 전송 확인
- 과목별 prompt 로드 확인
- `common_terms.json` + 과목별 corrections 로드 확인
- corrections 적용 후 TXT/JSON/SRT 생성 확인
- 다운로드 원본명 → 표준명 rename 확인
- Google Drive OFF 상태에서 Drive 이벤트 미발생 확인
- 테스트 산출물 삭제 완료
