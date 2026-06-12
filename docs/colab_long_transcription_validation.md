# Colab Large-v3 장시간 전사 검증 기록

검증 기준:
- 실행 방식: python gui_main.py
- 전사 방식: Colab Large-v3
- Google Drive 자동 업로드: OFF
- 과정명: 개념완성
- 검증 대상: 6개 과목별 장시간 MP3 1개 이상
- 확인 항목:
  - Colab 연결 상태
  - prompt loaded 로그
  - corrections loaded 로그
  - corrections applied 로그
  - TXT/JSON/SRT 생성
  - FILE_DONE / ALL_DONE 이벤트
  - DRIVE_UPLOAD 이벤트 미발생

| 과목 | 음원 길이 | 전사 소요 시간 | prompt | corrections loaded | corrections applied | TXT | JSON | SRT | FILE_DONE | ALL_DONE | DRIVE_UPLOAD |
|---|---:|---:|---|---:|---:|---|---|---|---|---|---|
| 민법 | 39:00 | 약 8분 | 민법_김덕수.txt chars=906 | 31 | 2 | O | O | O | O | O | 없음 |
| 부동산학개론 | 53:27 | 약 9분 | 부동산학개론_이종호.txt chars=876 | 36 | 4 | O | O | O | O | O | 없음 |
| 공인중개사법 | 50:11 | 약 8분 | 공인중개사법_정지웅.txt chars=828 | 38 | 22 | O | O | O | O | O | 없음 |
| 부동산공법 | 57:24 | 약 11분 | 부동산공법_김희상.txt chars=1038 | 40 | 14 | O | O | O | O | O | 없음 |
| 부동산공시법 | 57:54 | 약 11분 | 부동산공시법_박윤모.txt chars=992 | 41 | 12 | O | O | O | O | O | 없음 |
| 부동산세법 | 51:43 | 약 9분 | 부동산세법_정석진.txt chars=1005 | 49 | 6 | O | O | O | O | O | 없음 |

## 민법

- 과정명: 개념완성
- 원본 파일명: 4강_[1주차]_26_03_06_[교재]+[6]+양도담보+(p.324~).mp3
- 최종 표준 파일명: 개념완성_민법_1주차_4강.mp3
- 음원 길이: 39:00
- 전사 소요 시간: 약 8분
- Colab 연결 상태:
  - URL 클립보드 가져오기: O
  - 자동 연결 확인: O
  - 상태 연결됨 표시: O
- 전사 결과:
  - prompt loaded: 민법_김덕수.txt chars=906
  - corrections loaded: count=31
  - corrections applied: replacements=2
  - TXT/JSON/SRT 생성: O
  - FILE_DONE: O
  - ALL_DONE: O
  - DRIVE_UPLOAD 이벤트: 없음
- 판단: 통과

## 부동산학개론

- 과정명: 개념완성
- 원본 파일명: 부동산학개론_원본.mp3
- 최종 표준 파일명: 개념완성_부동산학개론_1주차_1강.mp3
- 음원 길이: 53:27
- 전사 소요 시간: 약 9분
- Colab 연결 상태:
  - URL 클립보드 가져오기: O
  - 자동 연결 확인: O
  - 상태 연결됨 표시: O
- 전사 결과:
  - prompt loaded: 부동산학개론_이종호.txt chars=876
  - corrections loaded: count=36
  - corrections applied: replacements=4
  - TXT/JSON/SRT 생성: O
  - FILE_DONE: O
  - ALL_DONE: O
  - DRIVE_UPLOAD 이벤트: 없음
- 판단: 통과

## 공인중개사법

- 과정명: 개념완성
- 원본 파일명: 공인중개사법_원본.mp3
- 최종 표준 파일명: 개념완성_공인중개사법_1주차_2강.mp3
- 음원 길이: 50:11
- 전사 소요 시간: 약 8분
- Colab 연결 상태:
  - URL 클립보드 가져오기: O
  - 자동 연결 확인: O
  - 상태 연결됨 표시: O
- 전사 결과:
  - prompt loaded: 공인중개사법_정지웅.txt chars=828
  - corrections loaded: count=38
  - corrections applied: replacements=22
  - TXT/JSON/SRT 생성: O
  - FILE_DONE: O
  - ALL_DONE: O
  - DRIVE_UPLOAD 이벤트: 없음
- 판단: 통과

## 부동산공법

- 과정명: 개념완성
- 원본 파일명: 부동산공법_원본.mp3
- 최종 표준 파일명: 개념완성_부동산공법_1주차_1강.mp3
- 음원 길이: 57:24
- 전사 소요 시간: 약 11분
- Colab 연결 상태:
  - URL 클립보드 가져오기: O
  - 자동 연결 확인: O
  - 상태 연결됨 표시: O
- 전사 결과:
  - prompt loaded: 부동산공법_김희상.txt chars=1038
  - corrections loaded: count=40
  - corrections applied: replacements=14
  - TXT/JSON/SRT 생성: O
  - FILE_DONE: O
  - ALL_DONE: O
  - DRIVE_UPLOAD 이벤트: 없음
- 판단: 통과

## 부동산공시법

- 과정명: 개념완성
- 원본 파일명: 부동산공시법_원본.mp3
- 최종 표준 파일명: 개념완성_부동산공시법_1주차_1강.mp3
- 음원 길이: 57:54
- 전사 소요 시간: 약 11분
- Colab 연결 상태:
  - URL 클립보드 가져오기: O
  - 자동 연결 확인: O
  - 상태 연결됨 표시: O
- 전사 결과:
  - prompt loaded: 부동산공시법_박윤모.txt chars=992
  - corrections loaded: count=41
  - corrections applied: replacements=12
  - TXT/JSON/SRT 생성: O
  - FILE_DONE: O
  - ALL_DONE: O
  - DRIVE_UPLOAD 이벤트: 없음
- 판단: 통과

## 부동산세법

- 과정명: 개념완성
- 원본 파일명: 부동산세법_원본.mp3
- 최종 표준 파일명: 개념완성_부동산세법_1주차_1강.mp3
- 음원 길이: 51:43
- 전사 소요 시간: 약 9분
- Colab 연결 상태:
  - URL 클립보드 가져오기: O
  - 자동 연결 확인: O
  - 상태 연결됨 표시: O
- 전사 결과:
  - prompt loaded: 부동산세법_정석진.txt chars=1005
  - corrections loaded: count=49
  - corrections applied: replacements=6
  - TXT/JSON/SRT 생성: O
  - FILE_DONE: O
  - ALL_DONE: O
  - DRIVE_UPLOAD 이벤트: 없음
- 판단: 통과
