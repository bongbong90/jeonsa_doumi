# 전사도우미

## 1. 프로젝트 개요
전사도우미는 Windows 데스크톱용 PySide6 기반 전사 보조 프로그램입니다.  
MP3 파일을 전사해 같은 폴더에 `TXT / JSON / SRT` 결과를 생성하며, GUI에서 파일 관리, 전사 실행/중지, 진행률, 결과 폴더 접근까지 처리합니다.

## 2. 주요 기능
- MP3 파일 큐 관리(체크박스, 파일명, 재생시간, 상태, 액션)
- 전사 대상 파일 이동 및 `선택한 MP3 이동 후 전사 시작`
- `전사자료 폴더 전체 전사 시작`
- GUI 과정명/과목명 선택 기반 MP3 파일명 자동 정규화
- 전사 완료 후 Google Drive 자동 업로드 (MP3, TXT, JSON, SRT 4종)
- 로컬 Whisper(`medium`) 전사
- Colab Large-v3 전사(`faster-whisper` 서버 연동) + 과목별 prompt/앱 corrections 후처리
- 완료 파일 자동 스킵(결과물 무결성 기준)
- Dashboard 통계(누적/오늘/속도/최근 완료)
- Folders 탭 파일 필터/미리보기
- 트레이 아이콘 + 커스텀 토스트 알림 + 상황형 알림창 UI 최적화 + 전체 완료 후 종료 옵션

## 3. 화면 구성
상단 탭은 아래 3개입니다.
1. `Transcriptions`
2. `Dashboard`
3. `Folders`

`Transcriptions` 탭
- 전사자료 폴더 선택
- MP3 파일 목록 불러오기
- 파일 큐 테이블 컬럼: `체크박스 / Filename / Duration / Status / Action`
- 상태값: `WAITING / PROCESSING / DONE / FAILED / MOVED / STOP`
- MP3 재생시간 계산 순서: `mutagen` -> `tinytag` -> MP3 프레임 직접 파싱
- 왼쪽 사이드바 구성 (옵션 영역 QScrollArea 적용으로 잘림 방지):
  - `전사 파일 분류`: 과정명, 과목명 선택 (여러 과목 섞임 방지 안내 포함)
  - `Google Drive 업로드`: 자동 업로드 켜기/끄기
  - `알림 및 종료 옵션`

`Dashboard` 탭
- 누적 완료 파일 수
- 누적 오디오 시간
- 오늘 완료 파일 수
- 평균 전사 속도(`오디오 1분 -> 약 n분`)
- 최근 완료 파일 목록

`Folders` 탭
- 현재 폴더 파일 관리
- 필터: `전체 / 완료 / 미완료 / 결과만`
- 표기: `파일명 / 유형 / 전사 상태 / 수정일`
- TXT 미리보기 + `전체 보기`
- 완료 판정: MP3 원본 + TXT/JSON/SRT 존재

## 4. 전사 방식
### 4.1 로컬 Whisper
- 워커: `auto_transcribe.py`
- 기본 모델: `medium`
- 입력: `.mp3`만 처리
- 출력: 같은 폴더에 `txt/json/srt` 저장
- 완료 기준:
  - `txt/json/srt` 모두 존재
  - `txt/json` 1바이트 초과
  - `json`에 `text`, `segments` 키 존재
- 진행률 분모는 `전체 MP3 수`가 아니라 `이번 실행 실제 처리 파일 수` 기준
- 이벤트는 `[EVENT]` 형식으로 GUI 전달
  - `TOTAL_FILES`, `FILE_INDEX`, `START_FILE`, `FILE_DONE`, `FILE_SKIP`, `FILE_FAIL`, `STOPPED`, `ALL_DONE`, `ALL_STOPPED`, `PROCESS_CRASHED`

### 4.2 Colab Large-v3
- GUI 전사 방식 콤보에서 `Colab Large-v3` 선택
- Colab 모드 선택 시 URL 입력 영역 활성화
- `클립보드에서 가져오기` 버튼으로 텍스트에서 `https://...trycloudflare.com` URL을 자동 추출
- URL에 `/health`, `/transcribe`, 공백, 줄바꿈 등이 붙어 있어도 앱이 base URL만 추출
- `연결 확인` 버튼은 `/health` 호출
- 성공 시 버튼 텍스트가 `연결됨 ✓`로 변경
- `Colab 열기` 버튼 제공
- URL에 `/health` 또는 `/transcribe`가 붙어 있어도 내부 정규화

Colab 전송/병합
- GUI에서 선택한 과목명을 기준으로 prompt를 로드
- prompt는 앱에서 읽은 뒤 Colab `/transcribe` multipart form-data에 `initial_prompt`로 전달
- 함께 `subject`도 전달
- Colab notebook 서버는 `initial_prompt`를 수신하고, `faster-whisper model.transcribe()` 호출 시 조건부로 전달
- Colab 서버는 전사만 수행하고 corrections 파일은 노트북으로 보내지지 않음
- 앱이 chunk 결과를 수신하고 segment offset을 보정한 뒤 전체 `merged_result`를 생성
- 병합된 결과를 저장 직전에 corrections를 적용
- corrections는 `common_terms.json` + 과목별 JSON을 사용하며 `text`와 `segments` 모두 대상
- prompt/수정 원문은 로그에 출력하지 않으며, 로그에는 prompt 파일명과 문자 길이, corrections 로드 수/치환 수만 표시
- `ffmpeg`가 PATH에 없으면 시작 불가
- MP3를 600초 단위로 분할(`chunk_0000.mp3`, `chunk_0001.mp3`, ...)
- 각 조각을 Colab `/transcribe`로 전송
- 조각 결과 `segment start/end`에 offset을 더해 전체 타임라인 병합
- 병합 결과를 `TXT/JSON/SRT`로 저장
- 임시 조각 폴더(`colab_chunks_*`)는 처리 후 정리
- 중지 요청 시 현재 조각 완료 후 중단

Colab 이어하기
- `progress.json`으로 진행 상태 저장
- 주요 키: `session_id`, `engine`, `total_files`, `completed_files`, `last_updated`
- 앱 시작 시 기존 `progress.json`이 있으면 이어하기 확인
- 이어하기 선택 시 완료 파일은 건너뛰고 남은 파일만 처리
- 전체 완료 시 `progress.json` 삭제

## 5. 설치 및 실행
현재 저장소에는 `requirements.txt`가 없습니다. 아래 패키지를 직접 설치해 실행합니다.

로컬 앱 실행용 예시:
```bash
pip install PySide6 openai-whisper torch mutagen tinytag
python gui_main.py
```

참고:
- `mutagen`, `tinytag`가 없어도 MP3 프레임 파싱 폴백이 동작합니다.
- Colab 분할 전송 사용 시 `ffmpeg` 설치 및 PATH 등록이 필요합니다.

## 6. Colab 사용 방법
1. 앱에서 전사 방식을 `Colab Large-v3`로 선택합니다.
2. `Colab 열기` 버튼으로 `colab_transcribe.ipynb`를 엽니다.
3. 노트북에서 서버 실행 셀을 순서대로 실행합니다.
4. 출력된 `https://...trycloudflare.com` 주소를 복사합니다.
5. 앱에서 `클립보드에서 가져오기`를 누릅니다.
6. URL이 자동 입력되고 연결 확인이 실행됩니다.
7. 상태가 `연결됨 ✓`이면 전사를 시작합니다.
8. 전사는 `initial_prompt`, `subject`를 multipart로 전송하고, Colab 서버는 전사만 수행합니다.
9. 앱은 수신한 chunk 결과를 병합하고 `common_terms.json` + 과목별 corrections를 적용해 TXT/JSON/SRT를 생성합니다.

노트북 서버는 Flask + flask-cors 기반이며, 아래 엔드포인트를 제공합니다.
- `/health`
- `/transcribe`(legacy 동기 응답)
- `/transcribe/start`
- `/jobs`
- `/jobs/<job_id>/status`
- `/jobs/<job_id>/result`

알림창 개선
- 알림창 본문에서 `\n\n` 같은 줄바꿈 문자열이 그대로 보이지 않지 않도록 공통 정규화 처리됨.
- 정보/경고/오류 알림 제목은 상황형 문구로 개선되어 표시됩니다.

## 7. 기본 사용 흐름
1. 전사자료 폴더 선택
2. MP3 목록 불러오기
3. 필요 시 선택 파일 이동
4. 전사 파일 분류 영역에서 과정명 및 과목명 선택 (한 폴더에 여러 과목이 섞여 있다면 체크박스로 나누어 선택)
5. 필요 시 Google Drive 자동 업로드 체크
6. 전사 방식 선택(로컬/Colab)
7. 전사 시작 (시작 전 파일명 자동 정규화 내역 확인)
8. 진행률/로그/알림 확인
9. 결과 파일 및 Drive 업로드 확인 (TXT/JSON/SRT)

## 8. 출력 파일 및 파일명 정규화 구조
GUI에서 선택한 과정명/과목명 기반으로 전사 시작 전 대상 MP3 파일명을 표준 형식으로 정규화합니다.
- 표준 형식: `과정명_과목명_N주차_N강`
- 예: 다운로드 원본명 `1강_[1주차]_26...mp3` / GUI `개념완성`, `민법` 선택 → `개념완성_민법_1주차_1강.mp3`로 변경 후 전사
- 주차/강 번호는 폴더 내 natural sort 또는 명시적 `[N-M]` 패턴(학개론 등)을 기준으로 부여합니다.

입력 MP3 기준으로 같은 폴더에 결과 파일 3종을 생성합니다. 기존 결과물이 있다면 MP3 변경 시 같은 stem으로 변경됩니다.

```text
예: 개념완성_민법_1주차_1강.mp3
 -> 개념완성_민법_1주차_1강.txt
 -> 개념완성_민법_1주차_1강.json
 -> 개념완성_민법_1주차_1강.srt
```

### 8.1 Google Drive 자동 업로드
GUI에서 `Google Drive 자동 업로드`를 켜면 로컬 전사 결과물 저장 완료(`FILE_DONE`) 직전에 MP3/TXT/JSON/SRT 4종 파일을 Drive에 업로드합니다.
- 파일명 정규화 조건을 만족해야 업로드가 진행됩니다. (`분류대기`, `과목불명` 상태일 경우 폴더 생성/업로드 차단)
- 업로드 중에는 `97% Google Drive 업로드 중` 상태가 표시됩니다.
- 경로 정책: `2026 제37회 공인중개사 자격시험/전사자료/{과정명}/{차수 과목 폴더}/{과정명_과목명_N주차}`
- 인증 파일: `%APPDATA%\전사도우미\google_credentials.json`, `google_drive_token.json`에 위치하며, 저장소에 포함되지 않습니다. 인증 파일이 없거나 손상 시 자동 업로드 차단 안내를 띄웁니다.

## 9. 세션/중지/이어하기
로컬 전사 세션
- 파일: `transcribe_session_state.json`
- 상태값: `running / completed / stopped_by_user / crashed / corrupt_session`
- `completed_files`를 저장해 이전 완료 파일 복원
- 저장 방식: `*.tmp`에 기록 후 `os.replace` 교체
- `PermissionError`/`OSError` 계열 저장 실패 시 재시도
- 오래된 `transcribe_session_state.json.tmp` 자동 정리
- 이전 세션이 `running`으로 남아 있으면:
  - `stop.flag` 존재 시 사용자 중지로 판단
  - 미존재 시 비정상 종료로 판단

중지 처리
- GUI `전사중지` 버튼은 `stop.flag`를 생성해 로컬 워커 중지 요청
- 워커는 파일 시작 전/루프 진입 전/전사 후 저장 전 등 여러 지점에서 `stop.flag` 확인
- 중지 시 `stopped_by_user` 기록 + `ALL_STOPPED` 이벤트 전송

Colab 이어하기
- `progress.json` 기반으로 완료 파일 목록을 유지
- 재시작 시 이어하기 선택 가능

## 10. 알림 및 종료 옵션
- 파일별 완료 알림(`파일별 완료 알림 켜기`)
- 전체 완료 알림(`전체 완료 알림 켜기`)
- 트레이 아이콘 알림
- 커스텀 토스트 알림(폴더 열기 버튼 포함)
- 전체 완료 후 컴퓨터 종료 옵션
- 종료 대기 옵션: `즉시 / 15초 / 30초`

## 11. 문제 해결
- `Colab URL을 먼저 입력하고 연결을 확인해 주세요.`
  - 전사 방식이 Colab인지 확인
  - URL 입력 후 `연결 확인` 성공(`연결됨 ✓`) 상태인지 확인
- `ffmpeg를 찾을 수 없습니다...`
  - `ffmpeg` 설치 후 PATH 등록
- `이번 실행에서 처리할 파일이 없습니다.`
  - 이미 결과물 3종이 완성된 파일만 있는지 확인
- 로컬 전사 중지가 늦음
  - 현재 파일 처리 종료 지점 이후 중지될 수 있음
  - 프로세스 지연 시 GUI에서 terminate/kill 폴백 수행

## 12. 현재 제한사항
- 입력 확장자는 MP3만 지원
- Colab 분할 전송은 ffmpeg 의존
- Colab notebook 서버의 작업 실행기는 `ThreadPoolExecutor(max_workers=1)`로 순차 처리 성격
- legacy `/transcribe`는 요청 완료까지 대기하는 동기 방식
- requirements 잠금 파일이 없어 환경별 설치 편차가 있을 수 있음

## 13. 개발자 참고 사항
- GUI 엔트리: `gui_main.py`
- 로컬 워커: `auto_transcribe.py`
- Colab 서버 노트북: `colab_transcribe.ipynb`
- PyInstaller spec: `전사도우미.spec`
- 설정 저장: `QSettings` (`ui_settings.ini`)
- 시작 메뉴 바로가기 자동 생성 로직 포함(Windows)
