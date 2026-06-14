## v0.9.0-rc2 - 2026-06-14

### Fixed

- Fixed the Colab transcription flow so Google Drive upload processing runs after TXT/JSON/SRT output files are saved and before file completion is reported.
- Improved Google Drive upload logging in the GUI execution log.
- Google Drive upload start, per-file upload start/done, upload done, failed, skipped states are now surfaced to the GUI log.
- Resolved the issue where upload logs were filtered out because `[GUI]`-prefixed messages were ignored by the GUI log append path.

### Verified

- Verified Colab Large-v3 transcription with Google Drive auto upload ON using actual lecture MP3 files.
- Confirmed MP3/TXT/JSON/SRT upload for each processed file.
- Confirmed transcription completion logs appear after Google Drive upload completion.
- Confirmed credentials/token contents are not printed in logs.
- Confirmed no Google Drive delete logic or local auto-delete logic was added.

### Notes

- v0.9.0-rc2 requires a new PyInstaller build because `gui_main.py` changed after v0.9.0-rc1.

---

# 전사도우미 v0.9.0 Release Notes

작성일: 2026-06-13  
배포 구분: 배포 후보  
대상 사용자: 공인중개사 강의 MP3 전사 사용자

---

## 1. 개요

이번 버전은 공인중개사 강의 MP3를 로컬 Whisper 또는 Colab Large-v3로 전사하고, 결과 파일을 TXT/JSON/SRT로 저장하는 전사 자동화 도구의 배포 후보입니다.

파일명 정규화, 과목별 전사 품질 보강, Colab 연결 편의성, Google Drive 자동 업로드, 배포본 exe 패키징 안정성을 중심으로 개선했습니다.

---

## 2. 주요 기능

- MP3 강의 파일 전사
- TXT/JSON/SRT 결과 파일 생성
- 과정명/과목명 기준 파일명 정규화
- 로컬 Whisper 전사 지원
- Colab Large-v3 전사 지원
- 과목별 prompt/corrections 적용
- Google Drive 자동 업로드 옵션
- Colab URL 연결 확인
- Colab URL 클립보드 자동 감지
- CURRENT ETA 실시간 추정 표시

---

## 3. 이번 버전의 주요 개선사항

### 파일명 정규화

- GUI에서 선택한 과정명과 과목명을 기준으로 전사 전 파일명을 표준 형식으로 정리합니다.
- 표준 형식은 `과정명_과목명_N주차_N강`입니다.
- MP3 이름이 정리되면 TXT/JSON/SRT 결과 파일 stem도 동일하게 맞춰집니다.
- 주차/강 정보를 감지하지 못하면 잘못된 파일명으로 전사하지 않도록 전사 시작을 차단합니다.

### Colab Large-v3 안정화

- Colab 전사 chunk 기본 단위를 600초에서 300초로 줄여 장시간 전사 안정성을 높였습니다.
- HTTP 502/503/504/524 및 timeout 계열 오류에 대해 chunk 단위 재시도 로직을 적용했습니다.
- 6개 과목 기준 실제 Colab Large-v3 장시간 전사 검증을 완료했습니다.

### 전사 품질 보강

- 6개 과목별 prompt 파일을 보강했습니다.
- 공통 corrections 및 과목별 corrections JSON을 보강했습니다.
- 숫자/금액/기간 직접 치환처럼 위험한 치환은 제외했습니다.
- JSON 문법 검증을 완료했습니다.

### Colab 연결 UX 개선

- `trycloudflare.com` URL을 클립보드에서 자동 감지합니다.
- `/health`, `/transcribe`가 붙은 URL도 base URL로 정리합니다.
- URL을 복사하면 입력칸 반영과 연결 확인 흐름이 자동으로 진행됩니다.
- 기존 “클립보드에서 가져오기” 버튼도 유지됩니다.
- URL 전체를 로그에 출력하지 않도록 했습니다.

### UI/UX 개선

- 과정명/과목명 드롭다운의 빈 항목을 제거했습니다.
- 드롭다운 선택/hover 스타일을 정리했습니다.
- 알림창 문구와 줄바꿈 표시를 개선했습니다.
- CURRENT ETA가 전사 중 멈춰 보이지 않도록 1초 단위 추정 갱신을 추가했습니다.

### Google Drive 자동 업로드

- 전사 완료 후 MP3/TXT/JSON/SRT 4종 파일을 Google Drive로 업로드할 수 있습니다.
- 인증 파일은 `%APPDATA%\전사도우미\` 경로에서 사용합니다.
- credentials/token 파일은 저장소와 배포본에 포함하지 않습니다.
- 인증 파일이 없거나 손상된 경우 자동 업로드를 차단하고 안내합니다.

---

## 4. 검증 완료 내역

- 6개 과목 Colab Large-v3 장시간 전사 검증 완료
- 전 과목 TXT/JSON/SRT 생성 확인
- 전 과목 FILE_DONE/ALL_DONE 이벤트 확인
- Google Drive 자동 업로드 OFF 상태에서 DRIVE_UPLOAD 이벤트 미발생 확인
- prompt loaded / corrections loaded / corrections applied 로그 확인
- PyInstaller 빌드 완료
- 배포본 exe 기본 실행 확인
- 배포본 exe 시작 실패 원인이었던 `font_label` NameError 수정 및 재빌드 확인
- 배포본 산출물에 `google_credentials.json`, `google_drive_token.json` 파일이 포함되지 않음을 파일명 기준으로 확인

---

## 5. 알려진 제한사항

- 파일명 정규화는 주차/강 정보를 감지할 수 있는 강의 파일명을 기준으로 동작합니다.
- 주차 정보가 없는 임의 MP3 파일은 파일명 정규화 단계에서 전사 시작이 차단될 수 있습니다.
- 배포본 exe 전체 실사용 시나리오는 부분 검증 상태입니다.
- Google Drive 업로드 완료 후 로컬 파일 자동삭제 기능은 안전상의 이유로 제공하지 않습니다.
- Colab 연결은 외부 런타임과 Cloudflare tunnel 상태의 영향을 받을 수 있습니다.
- CURRENT ETA는 실제 Whisper 내부 진행률이 아니라 파일 길이, chunk 처리 시간, 평균 처리 속도 기반의 추정값입니다.

---

## 6. 사용 전 준비사항

### 로컬 Whisper 전사

- 배포본 exe를 실행한 뒤 전사할 MP3 파일을 선택합니다.
- 긴 파일 전사는 PC 성능에 따라 시간이 오래 걸릴 수 있습니다.

### Colab Large-v3 전사

- Colab notebook을 실행합니다.
- Cloudflare tunnel URL을 복사합니다.
- 앱에서 Colab Large-v3를 선택하면 URL이 자동 감지되거나, “클립보드에서 가져오기” 버튼으로 입력할 수 있습니다.
- 연결 확인 후 전사를 시작합니다.

### Google Drive 자동 업로드

Google Drive 업로드를 사용하려면 아래 파일이 필요합니다.

```text
%APPDATA%\전사도우미\google_credentials.json
%APPDATA%\전사도우미\google_drive_token.json
```

주의:

* 위 파일은 배포본에 포함되지 않습니다.
* 위 파일 내용은 로그에 출력되지 않습니다.
* 인증이 없거나 손상된 경우 Google Drive 업로드는 차단됩니다.

---

## 7. 권장 사용 흐름

1. 강의 MP3 파일을 과목별로 분리합니다.
2. 앱에서 과정명과 과목명을 선택합니다.
3. Google Drive 자동 업로드 사용 여부를 선택합니다.
4. 로컬 Whisper 또는 Colab Large-v3 전사 방식을 선택합니다.
5. 전사를 시작합니다.
6. 완료 후 TXT/JSON/SRT 결과 파일을 확인합니다.
7. Google Drive 자동 업로드를 켠 경우 업로드 완료 여부를 확인합니다.

---

## 8. 보류된 기능

### Google Drive 업로드 완료 후 로컬 파일 자동삭제

이번 버전에서는 제공하지 않습니다.

보류 이유:

* 원본 MP3 및 결과 파일 손실 위험
* 업로드 성공 판정과 삭제 조건을 엄격하게 검증해야 함
* 휴지통 이동, 삭제 대기 폴더 등 별도 안전 정책 필요

---

## 9. 배포 상태

이번 버전은 개인 사용 및 제한된 환경에서 사용할 수 있는 배포 후보입니다.

공개 배포 전에는 다음 항목을 추가 확인하는 것을 권장합니다.

* 배포본 exe에서 실제 강의 파일 기준 전사 1회 이상
* Google Drive ON 업로드 흐름
* 여러 과목 파일을 나누어 실행하는 실제 사용 흐름
* 릴리즈 태그 생성 여부

---

## 10. 변경 요약

* 파일명 정규화 개선
* Google Drive 자동 업로드 구현
* Colab Large-v3 prompt/corrections 적용
* Colab 장시간 전사 안정화
* Colab URL 클립보드 자동 감지 추가
* CURRENT ETA 실시간 추정 표시 개선
* 6개 과목 prompt/corrections 보강
* 배포본 exe 빌드 및 시작 실패 수정
