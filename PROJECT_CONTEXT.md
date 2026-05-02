# 전사도우미 PROJECT CONTEXT (최종 확정본 초안)

최종 업데이트: 2026-05-02  
목적: 전사도우미 프로젝트의 Codex 인수인계 기준 문서

---

## 1. 프로젝트 개요

- 프로젝트명: 전사도우미
- 목표: MP3 파일을 전사자료 폴더에서 Whisper로 전사(txt/json/srt)하고, GUI에서 전사 실행/중지/진행률/로그/트레이를 통합 관리
- 실행 환경: Windows 데스크톱
- 기술 스택(코드 기준): **PySide6 GUI + Python + Whisper**
- 배포 방식: **PyInstaller onedir**

참고: 과거 문서에 있던 `PyQt5` 표기는 현재 코드와 불일치하며, `gui_main.py` import 기준으로 `PySide6`가 맞음.

---

## 2. 현재 코드 기준 파일 구조

### 2-1. 소스 구조

- `gui_main.py`: GUI 본체(레이아웃, 진행률 표시, 로그 표시, 트레이 동작, 프로세스 제어)
- `auto_transcribe.py`: Whisper 전사 엔진(파일 스캔, 전사, 결과 저장, 세션 상태 저장, stop.flag 처리)
- `전사도우미.spec`: onedir 빌드 스크립트(아이콘/datas 포함, 루트 `auto_transcribe.py` 자동 배치)
- `assets\`: 아이콘/리소스 폴더
- `transcribe_helper.ico`: 앱 아이콘 원본

### 2-2. 배포 구조(확인 기준)

```text
dist\전사도우미\
├─ 전사도우미.exe
├─ auto_transcribe.py
└─ _internal\
```

최근 확인 결과:
- `dist\전사도우미\전사도우미.exe` 존재
- `dist\전사도우미\auto_transcribe.py` 존재
- `dist\전사도우미\_internal` 존재

---

## 3. 절대 유지 규칙 (배포/구조)

- `PyInstaller onedir` 유지
- `onefile` 전환 금지
- `auto_transcribe.py`는 `전사도우미.exe`와 **같은 폴더**에 존재해야 함
- `dist\전사도우미\_internal` 삭제/이동 금지
- `assets` 폴더 삭제 금지
- `transcribe_helper.ico` 삭제 금지

---

## 4. 최근 완료 작업 반영 상태

아래 항목은 코드/히스토리 기준으로 완료 반영됨.

1. 프로젝트 폴더 구조 정리
2. PROJECT_CONTEXT.md 작성 및 최신화 진행
3. 세션 상태 저장 오류 안정화(retry/backoff + tmp 정리)
4. 사용자 중지와 비정상 종료 구분
5. 진행률 분모 기준을 “이번 실행 실제 처리 대상 수” 기준으로 정리
6. UI/UX 디자인 개선
7. 앱 아이콘 반영
8. PyInstaller onedir 빌드 후 `auto_transcribe.py` 루트 배치 자동화
9. 섹션 제목 한글화
10. 체크박스 시인성 개선
11. 실행 로그 패널 보완
12. `dist\전사도우미` 내부 `전사도우미.exe / auto_transcribe.py / _internal` 존재 확인

---

## 5. 완료 기능 목록 (현재 기준)

- 다운로드 폴더 선택
- 전사자료 폴더 선택
- MP3 파일 목록 불러오기
- 선택 MP3 이동
- 선택 MP3 이동 후 전사 시작
- 전사자료 폴더 전체 전사 시작
- 파일명 끝 페이지 표기 제거
- `+` 기호 공백 변환 및 연속 공백 정리
- 전체 진행률 표시
- 현재 파일 진행률 표시
- 즉시 중지
- 재실행/복구 흐름
- 로그창 보기/숨기기
- 트레이 이동/복원/우클릭 메뉴
- 전사 완료 후 컴퓨터 종료 옵션
- 세션 상태 저장 안정화
- 사용자 중지(`stopped_by_user`) / 비정상 종료(`crashed`) / 세션 손상(`corrupt_session`) 구분
- 실제 처리 대상 수 기준 진행률 계산
- 아이콘 로딩/적용(앱, 창, 트레이, 알림)
- onedir 빌드 + 루트 `auto_transcribe.py` 자동 배치

---

## 6. UI/UX 현황 (현재 코드 반영)

- 기본 폰트: `Malgun Gothic` 중심 폰트 체계
- 색상 방향: Deep Blue / Slate 계열 팔레트
- 구조: 좌측 설정 패널 + 우측 작업 영역
- 진행 상태: 카드형 진행 대시보드
- 섹션 제목: 주요 섹션 한글화(폴더 설정 / 알림 및 종료 옵션 / 실행 로그 / MP3 파일 목록 / 실행 제어)
- 로그 패널: 접힘 상태 안내 문구 + 펼침/숨김 토글 보완
- 체크박스: 선택 상태 시인성 개선
- 아이콘: `transcribe_helper.ico` 기준 적용
- 긴 텍스트: 경로/상태/목록 말줄임(`ElideMiddle`, `ElideRight`) 처리

---

## 7. 세션/중지 안정화 기준

### 7-1. 세션 저장 안정화

- 세션 파일: `transcribe_session_state.json`
- 임시 파일: `transcribe_session_state.json.tmp`
- 저장 방식: tmp 저장 후 `os.replace` 원자적 교체
- 실패 대응: retry/backoff 적용
  - retry 횟수: 5
  - backoff: 0.2, 0.3, 0.4, 0.5, 0.5초
- 오래된 tmp 파일 정리 로직 포함

### 7-2. 세션 상태 구분

- `running`
- `completed`
- `stopped_by_user`
- `crashed`
- `corrupt_session`

### 7-3. 중지/비정상 종료 구분

- `stop.flag` 존재 + 이전 상태 `running`이면 사용자 중지로 처리
- `stop.flag` 없이 `running` 흔적이면 비정상 종료로 처리
- GUI 종료 시 전사 중이면 종료 대신 트레이 이동
- 즉시 중지는 `stop.flag` 생성 → terminate 시도 → 필요 시 kill

### 7-4. 완료/미완료 파일 판정

- `txt/json/srt` 결과 3종 생성 여부 확인
- `json` 구조(`text`, `segments`) 유효성 확인
- 이번 실행 대상 계산 시 완료 파일 제외

---

## 8. 빌드/검증 절차 (현재 기준)

### 8-1. 클린 빌드

1. `build`, `dist` 삭제
2. spec 기반 빌드 실행

```powershell
python -m PyInstaller --noconfirm "전사도우미.spec"
```

### 8-2. 빌드 후 구조 확인

```powershell
Test-Path "dist\전사도우미\전사도우미.exe"
Test-Path "dist\전사도우미\auto_transcribe.py"
Test-Path "dist\전사도우미\_internal"
```

### 8-3. spec 핵심 유지 사항

- `datas`: `assets`, `transcribe_helper.ico`, `auto_transcribe.py`
- `icon`: `transcribe_helper.ico`
- `CollectWithRootAutoTranscribe`: dist 루트에 `auto_transcribe.py` 자동 배치

---

## 9. 현재 남은 작업 (우선순위)

1. `CURRENT PROGRESS 0%` 텍스트와 진행률바 겹침 수정
2. MP3 파일 목록 다중 로드 시 하단 잘림 수정
3. 좌측 옵션 카드 간격 등 UI 마감 미세 보완
4. 최종 exe 실행 테스트 및 배포본 확정

참고: “전체 진행률 분모 계산 수정”은 **완료 처리**(다음 작업에서 제외).

---

## 10. Codex 인수인계 메모

- 다음 작업자는 먼저 `PROJECT_CONTEXT.md` 확인 후 작업 시작
- 코드 수정 범위 최소화 원칙 유지
- UI 이슈와 전사 로직 이슈를 분리해 진단
- 배포 문제는 반드시 `전사도우미.spec` 및 dist 구조를 먼저 확인

---

## 11. 설명 방식 원칙

- 사용자는 개발자가 아님
- 단계별(1단계, 2단계…) 안내
- 반드시 다음 순서 포함:
  1. 어떤 파일을 여는지
  2. 무엇을 찾는지
  3. 무엇을 지우는지
  4. 무엇을 붙여넣는지
  5. 저장 후 무엇을 실행하는지
  6. 어떤 결과면 성공인지
  7. 실패 시 무엇을 캡처해 전달할지
- 부분 코드보다 전체 코드본 우선 제시

---

## 12. 노션 운영 원칙

- 노션 정리는 사용자 요청 시에만 수행
- 작업 중에는 기술 작업/테스트 우선
- 필요 시 정리 순서:
  1. 작업관리
  2. 이슈관리
  3. 변경이력
  4. 버전관리
