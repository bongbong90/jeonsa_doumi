import os
import sys
import re
import json
import mimetypes
import argparse
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/drive']  # 기존 사용자의 Drive 폴더 검색/업로드 접근 필요
UNKNOWN_COURSE = "분류대기"
UNKNOWN_SUBJECT = "과목불명"
UNKNOWN_WEEK = "주차불명"
DRIVE_UPLOAD_BLOCKED_MESSAGE = (
    "[DRIVE_UPLOAD_BLOCKED] 표준 파일명 감지 실패: 과정/과목/주차를 확인할 수 없어 업로드를 중단합니다.\n"
    "파일명을 '과정명_과목명_N주차_N강' 형식으로 정리한 뒤 다시 시도하세요."
)

# 커스텀 예외 클래스
class DriveUploadError(Exception):
    pass

# 1. AppData 경로 함수
def get_app_data_dir() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base_dir = Path(appdata) / "전사도우미"
        else:
            base_dir = Path.home() / ".전사도우미"
    else:
        base_dir = Path.home() / ".전사도우미"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir

def get_default_credentials_path() -> Path:
    return get_app_data_dir() / "google_credentials.json"

def get_default_token_path() -> Path:
    return get_app_data_dir() / "google_drive_token.json"

# 4. 인증 함수
def build_drive_service(credentials_path: str | Path | None = None, token_path: str | Path | None = None):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as e:
        raise DriveUploadError("Google API 패키지가 설치되어 있지 않습니다. (pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib)") from e

    cred_path = Path(credentials_path) if credentials_path else get_default_credentials_path()
    tok_path = Path(token_path) if token_path else get_default_token_path()

    creds = None
    if tok_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(tok_path), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise DriveUploadError(f"토큰 갱신에 실패했습니다. 다시 로그인해주세요: {e}") from e
        else:
            if not cred_path.exists():
                raise DriveUploadError(f"Google Drive API 인증 정보 파일(credentials.json)이 없습니다: {cred_path}")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                raise DriveUploadError(f"OAuth 인증 중 오류가 발생했습니다: {e}") from e
        
        # Save the credentials for the next run
        try:
            tok_path.write_text(creds.to_json(), encoding='utf-8')
        except Exception as e:
            print(f"[Warning] 토큰 저장 실패: {e}")

    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        raise DriveUploadError(f"Drive 서비스 객체 생성에 실패했습니다: {e}") from e

# 5. Drive 폴더 찾기/생성 함수
def find_folder(service, name: str, parent_id: str | None = None) -> str | None:
    try:
        # 이스케이프: 작은따옴표 처리
        safe_name = name.replace("'", "\\'")
        query = f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        
        items = results.get('files', [])
        if not items:
            return None
        return items[0]['id']
    except Exception as e:
        print(f"[Error] find_folder 실패 ('{name}'): {e}")
        return None

def create_folder(service, name: str, parent_id: str | None = None) -> str:
    try:
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        file = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        return file.get('id')
    except Exception as e:
        raise DriveUploadError(f"폴더 생성 실패 ('{name}'): {e}") from e

def get_or_create_folder(service, name: str, parent_id: str | None = None) -> str:
    folder_id = find_folder(service, name, parent_id)
    if not folder_id:
        folder_id = create_folder(service, name, parent_id)
    return folder_id

# 6. 과정명 감지 함수
def detect_course_name(path_or_name: str) -> str:
    name = Path(path_or_name).name
    if "개념완성" in name:
        return "개념완성"
    if "기본이론" in name:
        return "기본이론"
    if "기초이론" in name:
        return "기초이론"
    return UNKNOWN_COURSE

# 7. 과목 폴더 감지 함수
def detect_subject_folder(path_or_name: str) -> str:
    name = Path(path_or_name).name
    # 공시법은 공법보다 먼저 매칭
    if any(k in name for k in ["부동산공시법", "공시법", "등기법", "지적법", "박윤모"]):
        return "[2차] 부동산공시법"
    if any(k in name for k in ["민법", "김덕수"]):
        return "[1차] 민법"
    if any(k in name for k in ["부동산학개론", "학개론", "개론", "이종호"]):
        return "[1차] 부동산학개론"
    if any(k in name for k in ["공인중개사법", "중개사법", "중개실무", "정지웅"]):
        return "[2차] 공인중개사법"
    if any(k in name for k in ["부동산공법", "공법", "김희상"]):
        return "[2차] 부동산공법"
    if any(k in name for k in ["부동산세법", "세법", "정석진"]):
        return "[2차] 부동산세법"
    return UNKNOWN_SUBJECT

# 8. 주차 폴더 감지 함수
def detect_week_folder(path_or_name: str) -> str:
    name = Path(path_or_name).stem
    # 패턴: (_숫자주차_숫자강) -> 앞부분인 (_숫자주차) 까지만 반환해야 함.
    # 예: 개념완성_민법_1주차_1강 -> 매치 그룹 1번이 개념완성_민법_1주차
    match = re.search(r"(.+?_\d+주차)_\d+강", name)
    if match:
        return match.group(1)
    
    # 만약 패턴이 일치하지 않으면 폴더명 추출 시도
    # 파일 경로에서 상위 폴더 이름이 주차 폴더 형식인지 확인 가능
    path_parts = Path(path_or_name).parts
    if len(path_parts) > 1:
        parent_name = path_parts[-2]
        if re.search(r"_\d+주차$", parent_name):
            return parent_name

    return UNKNOWN_WEEK

def classify_upload_path(audio_path: str | Path) -> dict:
    path_str = str(audio_path)
    stem = Path(audio_path).stem
    course = detect_course_name(path_str)
    subject = detect_subject_folder(path_str)
    week = detect_week_folder(path_str)
    return {
        "course": course,
        "subject": subject,
        "week": week,
        "drive_path": [
            "2026 제37회 공인중개사 자격시험",
            "전사자료",
            course,
            subject,
            week
        ],
        "has_week_marker": bool(re.search(r"\d+주차", stem)),
        "has_lecture_marker": bool(re.search(r"\d+강", stem)),
    }

def validate_upload_classification(audio_path: str | Path) -> dict:
    classification = classify_upload_path(audio_path)
    reasons = []
    if classification["course"] == UNKNOWN_COURSE:
        reasons.append("과정명 감지 실패")
    if classification["subject"] == UNKNOWN_SUBJECT:
        reasons.append("과목명 감지 실패")
    if classification["week"] == UNKNOWN_WEEK:
        reasons.append("주차 감지 실패")
    if not classification["has_week_marker"]:
        reasons.append("파일명에 N주차 패턴 없음")
    if not classification["has_lecture_marker"]:
        reasons.append("파일명에 N강 패턴 없음")

    classification["ok"] = not reasons
    classification["reasons"] = reasons
    return classification

def format_upload_blocked_message(reasons: list[str]) -> str:
    if not reasons:
        return DRIVE_UPLOAD_BLOCKED_MESSAGE
    return f"{DRIVE_UPLOAD_BLOCKED_MESSAGE}\n사유: {', '.join(reasons)}"

# 9. Drive 경로 생성 함수
def build_drive_folder_path(audio_path: str | Path) -> list[str]:
    return classify_upload_path(audio_path)["drive_path"]

# 10. 파일 업로드 함수
def upload_file(service, local_path: str | Path, parent_id: str, duplicate_policy: str = "update_or_create") -> dict:
    local_path = Path(local_path)
    result = {
        "local_path": str(local_path),
        "file_name": local_path.name,
        "status": "failed",
        "drive_file_id": None,
        "error": ""
    }
    if not local_path.exists():
        result["error"] = "File not found"
        return result

    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        result["error"] = "Google API library not found"
        return result

    try:
        mime_type, _ = mimetypes.guess_type(str(local_path))
        if mime_type is None:
            mime_type = 'application/octet-stream'

        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
        
        # 중복 파일 확인
        existing_id = None
        if duplicate_policy in ("update", "update_or_create"):
            safe_name = local_path.name.replace("'", "\\'")
            query = f"name='{safe_name}' and '{parent_id}' in parents and trashed=false"
            res = service.files().list(q=query, spaces='drive', fields='files(id)', pageSize=1).execute()
            items = res.get('files', [])
            if items:
                existing_id = items[0]['id']

        if existing_id:
            # Update
            file = service.files().update(
                fileId=existing_id,
                media_body=media,
                fields='id'
            ).execute()
            result["status"] = "updated"
            result["drive_file_id"] = file.get('id')
        else:
            # Create
            file_metadata = {
                'name': local_path.name,
                'parents': [parent_id]
            }
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            result["status"] = "uploaded"
            result["drive_file_id"] = file.get('id')

    except Exception as e:
        result["error"] = str(e)
        
    return result

# 11. 번들 업로드 함수
def upload_transcription_bundle(audio_path: str | Path, include_mp3: bool = True, service=None) -> dict:
    audio_path = Path(audio_path)
    classification = validate_upload_classification(audio_path)
    result = {
        "ok": False,
        "blocked": False,
        "drive_folder_id": None,
        "drive_path": classification["drive_path"],
        "classification": {
            "course": classification["course"],
            "subject": classification["subject"],
            "week": classification["week"],
        },
        "classification_errors": classification["reasons"],
        "files": [],
        "missing": [],
        "errors": []
    }

    if not classification["ok"]:
        result["blocked"] = True
        result["errors"].append(format_upload_blocked_message(classification["reasons"]))
        return result

    if not audio_path.exists():
        result["blocked"] = True
        result["missing"].append(audio_path.name)
        result["errors"].append(f"[DRIVE_UPLOAD_BLOCKED] 업로드 대상 MP3 파일을 찾을 수 없습니다: {audio_path}")
        return result
    
    if not service:
        result["errors"].append("Drive service not provided")
        return result

    # 파일 대상 수집
    targets = []
    if include_mp3:
        targets.append(audio_path)
    for ext in [".txt", ".json", ".srt"]:
        targets.append(audio_path.with_suffix(ext))

    # 폴더 구조 만들기
    current_parent_id = None
    try:
        for folder_name in result["drive_path"]:
            current_parent_id = get_or_create_folder(service, folder_name, current_parent_id)
        result["drive_folder_id"] = current_parent_id
    except Exception as e:
        result["errors"].append(f"Failed to create drive folder path: {e}")
        return result

    # 파일 업로드 시도
    for target in targets:
        if not target.exists():
            result["missing"].append(target.name)
            continue
        
        file_result = upload_file(service, target, current_parent_id)
        if file_result["status"] in ("uploaded", "updated"):
            result["files"].append({"file_name": target.name, "status": file_result["status"]})
        else:
            result["errors"].append(f"{target.name}: {file_result['error']}")

    if not result["errors"]:
        result["ok"] = True
    return result

# 12. CLI 테스트 인터페이스
if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Google Drive Uploader CLI")
    parser.add_argument("audio_path", help="Path to the mp3 file")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Only print the path mapping without uploading")
    parser.add_argument("--upload", action="store_true", help="Actually perform OAuth and upload to Drive")
    parser.add_argument("--credentials", help="Path to credentials.json")
    parser.add_argument("--token", help="Path to token.json")
    
    args = parser.parse_args()
    
    audio_path = Path(args.audio_path).expanduser().resolve(strict=False)
    
    print("=== Google Drive Uploader CLI ===")
    print(f"Target File: {audio_path}")

    if not audio_path.exists():
        print(f"\n[Error] 파일을 찾을 수 없습니다: {audio_path}")
        sys.exit(1)
    
    classification = validate_upload_classification(audio_path)
    course = classification["course"]
    subject = classification["subject"]
    week = classification["week"]
    drive_path = classification["drive_path"]
    
    print("\n[Detection Results]")
    print(f"Course  : {course}")
    print(f"Subject : {subject}")
    print(f"Week    : {week}")
    if classification["ok"]:
        print(f"Drive   : {' / '.join(drive_path)}")
    else:
        print("Drive   : (blocked)")
    
    print("\n[Target Files]")
    targets = [audio_path] + [audio_path.with_suffix(ext) for ext in [".txt", ".json", ".srt"]]
    for t in targets:
        print(f" - {t.name} (Exists: {t.exists()})")

    if not classification["ok"]:
        mode_name = "Upload Mode" if args.upload else "Dry Run"
        print(f"\n[{mode_name}] Upload blocked. No Drive folders or files will be created.")
        print(format_upload_blocked_message(classification["reasons"]))
        sys.exit(1)
        
    if args.upload:
        print("\n[Upload Mode] Attempting OAuth and upload...")
        try:
            service = build_drive_service(args.credentials, args.token)
            print("OAuth Success. Service created.")
            
            res = upload_transcription_bundle(audio_path, include_mp3=True, service=service)
            print("\n[Upload Result]")
            print(json.dumps(res, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"\n[Fatal Error] {e}")
    else:
        print("\n[Dry Run] Completed. Use --upload to actually upload.")
