# 최근 개발 히스토리

최초 작성일: 2026-06-07  
최종 업데이트: 2026-06-12  
대상: 최근 Google Drive 업로드, 파일명 정규화, Colab Large-v3 품질 보강, UI/UX, 패키징 작업 묶음

## 최종 UX 및 ETA 개선

- 과정명/과목명 콤보박스 드롭다운 UI를 정리하고 빈 항목이 표시되지 않도록 개선했다.
- Colab Large-v3 선택 상태에서 `trycloudflare.com` URL을 클립보드에서 자동 감지해 URL 입력 및 연결 확인까지 자동으로 진행하도록 개선했다.
- 기존 "클립보드에서 가져오기" 버튼은 유지하여 수동 fallback 흐름을 보존했다.
- CURRENT ETA가 전사 중 멈춰 보이지 않도록 1초 단위 추정 갱신을 추가했다.
- Colab 전사는 chunk 시작/완료 이벤트 기반으로 ETA를 추정하고, 로컬 전사는 음원 길이와 평균 처리속도 기반으로 ETA를 추정한다.
- Whisper 내부 progress hook, tqdm/stderr 파싱, Colab notebook 수정 없이 GUI 표시 로직 중심으로 개선했다.

## 전체 요약

이번 작업 묶음은 전사 시작 전 파일 분류와 파일명 정규화, 로컬/Colab 전사 품질 보정, Google Drive 자동 업로드, 배포본 포함 리소스까지 하나의 사용 흐름으로 맞추는 데 초점을 두었다.

최종 상태는 다음과 같다.

- 다운로드 원본명 파일도 GUI에서 선택한 과정명/과목명 기준으로 `과정명_과목명_N주차_N강` 표준명 정리가 가능하다.
- 로컬 Whisper와 Colab Large-v3 모두 과목별 prompt/corrections 경로를 사용할 수 있다.
- Google Drive 자동 업로드는 전사 완료 후 MP3/TXT/JSON/SRT 4종 파일 업로드 흐름으로 구현되어 있다.
- Google Drive 인증 파일은 AppData 경로에 두고 저장소/패키징에 포함하지 않는 보호 정책이 적용되어 있다.
- PyInstaller 배포본에 Colab notebook, prompts, corrections, Drive 업로드 관련 리소스가 포함되는 것을 확인했다.
- 사이드바 UI/UX와 정보/경고/오류 알림창 톤 정리가 완료되었다.
- Google Drive 업로드 성공 후 로컬 파일 자동삭제 기능은 위험성이 있어 이번 단계에서 보류했다.

## 기능별 완료 현황

### 1. 파일명 정규화
- GUI에서 선택한 과정명/과목명을 우선 사용해 전사 시작 전 MP3 이름을 표준 형식으로 정리한다.
- 표준 형식은 `과정명_과목명_N주차_N강`이다.
- 다운로드 원본명 예시:
  `1강_[1주차]_26_03_07_[교재]+총칙+(p.+12+~+).mp3`
  -> `개념완성_민법_1주차_1강.mp3`
- MP3 rename 시 기존 TXT/JSON/SRT 결과물이 있으면 동일 stem으로 함께 동기화한다.
- 과정명/과목명/주차/강 감지 실패, 충돌 가능성, rename 실패가 있으면 전사 시작을 차단한다.

### 2. GUI 과정명/과목명 선택
- Transcriptions 사이드바에 `전사 파일 분류` 영역을 두고 과정명/과목명을 선택하도록 정리했다.
- 선택값은 파일명 정규화, 과목별 전사 보정, Google Drive 업로드 경로 산정에 사용된다.
- 과정명/과목명이 비어 있으면 전사 실행 전에 안내하고 진행을 막는다.
- 선택한 과정/과목은 이번 전사 대상 전체에 적용된다는 확인 절차를 둔다.

### 3. 여러 과목 섞임 주의
- 한 폴더에 여러 과목 파일이 섞인 상태에서 전체 전사를 바로 실행하면 잘못된 과목명으로 정규화될 수 있다.
- UI 안내와 확인창에서 과목별로 파일을 체크해 나누어 실행하도록 안내한다.
- 이 정책은 파일명 정규화와 Google Drive 업로드 경로 오류를 줄이기 위한 안전장치다.

### 4. Google Drive 자동 업로드
- GUI에서 `Google Drive 자동 업로드`를 켜면 로컬 전사 저장 완료 후 MP3/TXT/JSON/SRT 4종 파일을 Drive로 업로드한다.
- 워커는 `--upload-drive` 옵션을 통해 업로드 흐름을 실행한다.
- 업로드 이벤트는 `DRIVE_UPLOAD_START`, `DRIVE_UPLOAD_DONE`, `DRIVE_UPLOAD_BLOCKED`, `DRIVE_UPLOAD_FAIL`로 GUI에 전달된다.
- 업로드 중에는 현재 파일 진행률에 `Google Drive 업로드 중` 단계가 표시된다.
- 업로드 경로는 기존 Drive 구조인 `2026 제37회 공인중개사 자격시험/전사자료/{과정명}/{차수 과목 폴더}/{과정명_과목명_N주차}` 기준이다.
- 표준 파일명 감지 실패나 인증 문제로 업로드가 차단되어도 로컬 전사 결과물은 보존된다.

### 5. Google Drive 인증 파일 보호
- `google_credentials.json`, `google_drive_token.json`은 `%APPDATA%\전사도우미\` 경로에서 사용하는 정책이다.
- credentials/token 파일은 저장소 커밋 대상이 아니며 PyInstaller 패키징 대상에도 포함하지 않는다.
- GUI는 자동 업로드 실행 전 인증 파일 존재와 기본 JSON 구조를 확인한다.
- 인증 파일이 없거나 손상된 경우 자동 업로드를 막고 사용자에게 상황형 알림을 표시한다.
- 이번 정리 작업에서는 OAuth 인증이나 실제 업로드 테스트를 수행하지 않았다.

### 6. Colab Large-v3 prompt/corrections
- GUI에서 선택한 과목명 기준으로 prompt를 로드한다.
- Colab 요청에는 multipart form-data로 `initial_prompt`와 `subject`를 포함한다.
- Colab notebook은 `initial_prompt`를 받아 `faster-whisper` 전사 호출에 전달한다.
- corrections 파일은 Colab notebook으로 보내지지 않는다.
- 앱이 chunk 결과를 병합한 뒤 `common_terms.json`과 과목별 corrections를 `text` 및 `segments`에 적용해 TXT/JSON/SRT를 저장한다.
- 로컬 Whisper도 `auto_transcribe.py`에서 과목 감지 후 initial prompt와 corrections를 적용하는 흐름을 유지한다.

### 7. Colab 연결 UX
- 클립보드 텍스트에서 `https://...trycloudflare.com` URL을 자동 추출한다.
- URL에 `/health`, `/transcribe`, 공백, 줄바꿈이 붙어 있어도 base URL로 정규화한다.
- `연결 확인`은 `/health`를 호출하고 성공 시 버튼 상태를 `연결됨`으로 단순화한다.
- 실제 Colab 런타임 장시간 전사 검증은 아직 남은 개선 후보로 둔다.

### 8. 알림창 톤 통일
- 정보/경고/오류 알림창을 상황형 제목과 본문 중심으로 정리했다.
- 알림창 본문에서 `\n\n` 문자열이 그대로 보이는 줄바꿈 표시 문제를 수정했다.
- 파일명 정규화 경고, Drive 인증 안내, Colab 연결 안내 등 주요 사용자 안내 톤을 통일했다.

### 9. PyInstaller 패키징
- 배포본에 `auto_transcribe.py`, `google_drive_uploader.py`, `colab_transcribe.ipynb`, prompts, corrections 리소스를 포함하도록 보완했다.
- Google Drive API 관련 의존성과 Colab 리소스가 배포본에서 누락되지 않도록 확인했다.
- credentials/token 파일은 패키징 대상에서 제외하는 정책을 유지했다.

### 10. 문서 업데이트
- README, PROJECT_CONTEXT, Google Drive 설계 문서, Colab 워크플로우 문서가 최근 구현 상태를 반영하도록 업데이트되었다.
- 이번 문서는 기능별/커밋별/검증별 이력을 한 번에 복원하기 위한 별도 히스토리 문서다.

## 주요 커밋 히스토리

| 커밋 | 메시지 | 핵심 내용 |
|---|---|---|
| 37a118f | Use selected course and subject for filename normalization | GUI 선택 과정/과목을 파일명 정규화 우선 기준으로 사용 |
| 4760ba0 | Clarify course subject and Drive upload UI | 사이드바의 전사 파일 분류와 Drive 업로드 UI 문구/구조 정리 |
| c646a3d | Unify alert dialog tone and layout | 정보/경고/오류 알림창 레이아웃과 톤 통일 |
| 940694e | Document filename normalization and Drive upload flow | 파일명 정규화 및 Drive 업로드 흐름 문서화 |
| 700938a | Apply prompts and corrections to Colab transcriptions | Colab 전사에 initial_prompt/subject 전송 및 앱 corrections 후처리 적용 |
| dbd5ebc | Simplify Colab connection workflow | Colab URL 추출/정규화/연결 확인 UX 간소화 |
| 3235972 | Fix alert newline rendering and copy tone | 알림창 줄바꿈 표시 버그 수정 및 문구 개선 |
| e415ca6 | Polish filename normalization warning copy | 파일명 정규화 경고/확인 문구 개선 |
| e2058c2 | Document Colab quality and connection workflow | Colab 품질 보정과 연결 흐름 문서 업데이트 |
| f71bef6 | Include Colab resources in package | PyInstaller 패키징에 Colab notebook/prompts/corrections 리소스 포함 |

## 검증 완료 내역

### 파일명 정규화
- 다운로드 원본명 -> 표준명 rename 검증 완료
- MP3 rename 시 TXT/JSON/SRT stem 일치 검증 완료
- 정규화 충돌 또는 감지 실패 시 전사 시작 차단 흐름 확인

### prompt/corrections
- 민법 prompt/corrections 적용 검증 완료
- 로컬 Whisper에서 initial prompt 전달 및 corrections 후처리 흐름 확인
- Colab multipart 요청에 `initial_prompt`와 `subject` 포함 확인
- Colab notebook에서 `initial_prompt` 수신 및 `faster-whisper` 전달 확인
- Colab 병합 후 앱에서 corrections 적용 확인

### Google Drive
- Google Drive OFF 상태에서 Drive 이벤트가 발생하지 않음을 확인
- Google Drive ON 상태에서 `DRIVE_UPLOAD_START`/`DRIVE_UPLOAD_DONE` 이벤트 확인
- Google Drive 업로드 경로 산정 확인
- 인증 파일 손상 방지 및 검증 로직 확인
- 이 항목은 Drive 업로드 흐름 검증을 기준으로 정리하며, 이번 문서화 작업 중 OAuth 인증이나 추가 업로드 테스트는 수행하지 않았다.

### Colab 연결 및 장시간 전사
- Mock Colab 서버로 `/health` 및 `/transcribe` 흐름을 확인했다.
- PySide6 검증으로 URL 추출, 연결 확인, 정상/실패 안내 흐름을 확인했다.
- 실제 Google Colab 런타임에서 6개 과목 기준 장시간 전사 검증을 완료했다.
- 300초 chunk 분할 및 HTTP 524 retry 안정화 이후, 장시간 전사 흐름이 정상 완료됨을 확인했다.
- 전 과목에서 TXT/JSON/SRT 생성, FILE_DONE/ALL_DONE 이벤트, prompt/corrections 적용 로그를 확인했다.
- 검증은 Google Drive 자동 업로드 OFF 상태에서 수행했으며, DRIVE_UPLOAD 이벤트 미발생을 확인했다.

### UI/알림
- 알림창 줄바꿈 표시 버그 수정 확인
- 정보/경고/오류 알림창 톤 및 레이아웃 정리 확인
- 파일명 정규화 경고 문구가 현재 선택 과정/과목과 주의사항을 표시하는지 확인

### 패키징
- PyInstaller 빌드 성공 확인
- 배포본 exe 실행 유지 확인
- 배포본에 `auto_transcribe.py`, `google_drive_uploader.py`, `colab_transcribe.ipynb`, `prompts/`, `corrections/` 포함 확인
- credentials/token 파일은 패키징 제외 상태로 확인

## 보류한 기능

### Google Drive 업로드 완료 후 로컬 파일 자동삭제
- 위험성 때문에 이번 단계에서는 구현하지 않았다.
- 이유:
  - 원본 MP3 및 결과 파일 손실 위험
  - Drive 업로드 성공 판정과 삭제 조건을 매우 엄격하게 설계해야 함
  - 휴지통 이동, `send2trash`, 삭제대기 폴더 등 정책 결정 필요
- 추후 구현 시 권장 원칙:
  - 기본값 OFF
  - Google Drive 자동 업로드 ON일 때만 활성화
  - 업로드 성공 파일만 처리
  - `DRIVE_UPLOAD_FAIL`/`DRIVE_UPLOAD_BLOCKED` 시 삭제 금지
  - 영구 삭제보다 휴지통 이동 우선
  - 실제 운영 파일이 아닌 임시 폴더에서 mock 테스트 선행

## 남은 개선 후보

1. 배포본 exe 실사용 시나리오 테스트
2. 최종 PyInstaller 빌드 산출물 검증
3. 릴리즈 노트 작성
4. 버전 태그 생성 검토
5. Google Drive 업로드 후 로컬 파일 휴지통 이동 옵션 설계
6. Colab notebook UX 추가 개선

## 현재 안전 상태

- `pyrightconfig.json`은 untracked 상태로 유지하며 스테이징하지 않는다.
- credentials/token 파일은 저장소/패키징에 포함하지 않는다.
- build/dist 산출물은 커밋 대상이 아니다.
- Google Drive 업로드 완료 후 로컬 파일 자동삭제 기능은 미구현/보류 상태다.
- 배포본 exe 실사용 시나리오 테스트, 최종 릴리즈 노트, 버전 태그 생성은 아직 남은 단계다.
