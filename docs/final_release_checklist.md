# 최종 릴리즈 전 체크리스트

작성일: 2026-06-07
관련 커밋: `f067a9d Summarize recent development history` (마지막 원격 push 완료 시점)

---

## 1. 현재 상태 요약

- 기능 구현은 대부분 완료됨
- 파일명 정규화, Google Drive 자동 업로드, Colab 연결 UX, Colab prompt/corrections 적용 경로는 완료
- 문서 업데이트 및 PyInstaller 배포본 리소스 포함 검증 완료
- 하지만 릴리즈 전 최종 검증과 전체 과목 사전 품질 보강은 아직 남아 있음
- 현재 상태는 **"기능 구현 완료 / 릴리즈 전 안정화 미완료"**로 표현하는 것이 정확함

---

## 2. 완료된 작업과 미완료 작업 구분

| 항목 | 상태 | 비고 |
|---|---|---|
| 파일명 정규화 | 완료 | GUI 선택 과정/과목 기준 |
| Google Drive 자동 업로드 | 완료 | 4종 파일 업로드 검증 |
| Colab prompt/corrections 적용 경로 | 완료 | Mock/PySide6 검증 |
| 배포본 리소스 포함 검증 | 완료 | PyInstaller 산출물에 prompts/corrections 포함 확인 |
| 관련 문서 업데이트 | 완료 | recent_development_history.md 등 |
| 전체 과목 prompt/corrections 품질 보강 | 미완료 | 실제 전사 결과 기반 보강 필요 |
| 장시간 Colab 실제 전사 검증 | 미완료 | 과목별 샘플 필요, Mock 검증만 완료된 상태 |
| 배포본 실사용 시나리오 테스트 | 미완료 | exe 기준 종합 시나리오 미실행 |
| 릴리즈 노트 작성 | 미완료 | 초안 없음 |
| 버전 태그 생성 | 미완료 | 검토 전 |

> 주의: 위 표의 "완료" 항목은 Mock 검증 또는 부분 검증 기준이며, **실제 장시간 운영 환경 검증과는 구분**한다.

---

## 3. 최종 종료 기준

다음 조건을 모두 만족할 때 "릴리즈 준비 완료"로 판단한다.

- [ ] 6과목별 prompt/corrections 점검 완료
- [x] 실제 장시간 Colab 전사 검증 완료 (과목별 1개 이상)
- [ ] 배포본 exe 기준 실사용 시나리오 통과
- [ ] 릴리즈 노트 작성 완료
- [ ] 버전 태그 생성 여부 결정
- [ ] `git status`가 `?? pyrightconfig.json`만 남는 상태
- [ ] credentials/token 파일이 저장소에 포함되지 않음을 확인

---

## 3.5. 최근 UX 및 ETA 개선

- [x] 과정명/과목명 콤보박스 드롭다운 UI 정리 및 빈 항목 제거
- [x] Colab URL 클립보드 자동 감지 기능 구현
  - Colab Large-v3 선택 상태에서 trycloudflare URL 자동 감지 및 기존 연결 확인 로직 재사용
  - 기존 수동 “클립보드에서 가져오기” 버튼 유지
- [x] CURRENT ETA 실시간 추정 갱신 개선
  - Colab chunk 기반 ETA 추정 및 로컬 음원 길이/처리속도 기반 ETA 추정
  - Whisper 내부 진행률 파싱 없이 GUI 표시 로직 중심으로 구현

---

## Colab Large-v3 timeout resilience

- [x] Colab chunk 기본 단위가 600초에서 300초로 변경되었는지 확인
- [x] HTTP 502/503/504/524 transient 오류가 chunk 단위 retry 대상인지 확인
- [x] timeout 계열 예외가 chunk 단위 retry 대상인지 확인
- [x] HTTP 404 등 non-retry 오류는 재시도하지 않는지 mock으로 확인
- [x] HTTP 524 1회 발생 후 재시도 성공 mock 테스트 확인
- [x] HTTP 524 반복 발생 시 최대 재시도 후 실패 mock 테스트 확인
- [x] 최종 실패 로그에 파일명, chunk 번호, 시도 횟수, 예외 타입/메시지가 포함되는지 확인
- [x] 실제 Colab 장시간 전사 재검증
  - 6개 과목 기준 Colab Large-v3 장시간 전사 검증 완료
  - 실행 기준: python gui_main.py
  - Google Drive 자동 업로드 OFF
  - 전 과목 TXT/JSON/SRT 생성, FILE_DONE/ALL_DONE 확인
  - DRIVE_UPLOAD 이벤트 미발생 확인

---

## 4. 실제 장시간 Colab 전사 검증 계획

- 대상: 6과목 각 1개 이상
- 권장 길이: 과목별 20~40분 이상
- Google Drive 자동 업로드는 기본 OFF로 진행

확인 항목:

- Colab 연결 유지
- chunk 분할/병합
- initial_prompt/subject 전달
- corrections 적용
- TXT/JSON/SRT 생성
- SRT 시간 순서
- FILE_DONE/ALL_DONE 신호
- 오류 발생 시 로그 수집

결과물은 5번 항목(prompt/corrections 보강)의 입력 자료로 사용한다.

---

## 5. 전체 과목 prompt/corrections 품질 보강 계획

대상 경로:

```text
prompts/
corrections/common_terms.json
corrections/과목별 JSON
```

보강 기준:

- 실제 전사 결과에서 나온 오인식을 우선 반영
- 공통 용어는 `common_terms.json`에 추가
- 과목 전용 용어는 과목별 JSON에 추가
- 과잉 치환(의도하지 않은 단어까지 바뀌는) 위험이 있는 항목은 제외
- 공통/과목별 항목 간 중복 또는 충돌 여부 점검

대상 6과목:

- 부동산학개론
- 민법
- 공인중개사법
- 부동산공법
- 부동산공시법
- 부동산세법

---

## 6. 배포본 실사용 시나리오 테스트 계획

대상:

```text
dist\전사도우미\전사도우미.exe
```

시나리오:

- 다운로드 원본명 파일 선택
- 과정/과목 선택
- 파일명 정규화 preview 확인
- 로컬 Whisper 전사
- Colab Large-v3 전사
- Google Drive OFF 전사
- Google Drive ON 전사
- 알림창 표시 확인
- prompt/corrections 적용 로그 확인
- 결과 파일 stem 일치 확인

---

## 7. 릴리즈 노트 작성 계획

포함할 항목:

- 주요 기능
- 개선 사항
- 검증 완료 내역
- 알려진 제한사항
- 보류 기능
- 사용 전 준비사항
- Google Drive 인증 안내
- Colab 사용 안내

---

## 8. 버전 태그 생성 검토 기준

- 릴리즈 노트 작성 완료 후 검토
- 배포본 실사용 시나리오 통과 후 검토

태그 후보 예:

```text
v0.9.0
```

태그 생성 전 확인 사항:

- `git status`
- credentials/token 파일 미포함 확인
- dist 실행 확인
- release notes 존재 확인

---

## 9. 보류 기능

### Google Drive 업로드 완료 후 로컬 파일 자동삭제

- 위험성 때문에 보류
- 원본 MP3 및 결과 파일 손실 위험
- 추후 구현 시 기본 OFF, 휴지통 이동, mock 테스트 선행 필요

---

## 10. 작업 순서와 커밋 기준

권장 순서:

```text
0. 최종 릴리즈 체크리스트 작성
1. 실제 장시간 Colab 전사 검증
2. 전체 과목 prompt/corrections 품질 보강
3. 배포본 실사용 시나리오 테스트
4. 릴리즈 노트 작성
5. 버전 태그 생성 검토
```

커밋 기준:

- 각 단계는 가능한 한 별도 커밋으로 분리한다 (검증 결과/보강 내용/릴리즈 노트 등을 한 커밋에 섞지 않는다)
- 코드와 문서 변경은 분리해서 커밋한다
- credentials/token, build/dist 산출물은 어떤 단계에서도 커밋 대상에 포함하지 않는다
- `git add .` 또는 `git add -A`는 사용하지 않고, 변경된 파일을 명시적으로 지정해서 스테이징한다
