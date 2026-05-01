#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
import os
import glob
import time
import datetime
import locale
import json
import re
import traceback
import stat
from json import JSONDecodeError

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

MODEL_SIZE = "medium"
SUPPORTED_EXTENSIONS = (".mp3", ".MP3")
SESSION_STATE_FILENAME = "transcribe_session_state.json"
STOP_FLAG_FILENAME = "stop.flag"
SESSION_SAVE_RETRY_COUNT = 5
SESSION_SAVE_BACKOFF_SECONDS = (0.2, 0.3, 0.4, 0.5, 0.5)
SESSION_SOURCE_WORKER = "worker"

STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_STOPPED_BY_USER = "stopped_by_user"
STATUS_CRASHED = "crashed"
STATUS_CORRUPT = "corrupt_session"

SESSION_STATE_PATH = None
STOP_FLAG_PATH = None
_whisper_model = None
RUN_COMPLETED_FILES: set[str] = set()


# --------------------------------------------------
# 로그 / 이벤트
# --------------------------------------------------
def log(message: str):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def emit_event(event_type: str, *parts):
    payload = "|".join(str(x) for x in parts)
    if payload:
        print(f"[EVENT] {event_type}|{payload}", flush=True)
    else:
        print(f"[EVENT] {event_type}", flush=True)


# --------------------------------------------------
# 경로 / 세션
# --------------------------------------------------
def init_runtime_paths(target_folder: str):
    global SESSION_STATE_PATH, STOP_FLAG_PATH
    parent_dir = os.path.dirname(os.path.abspath(target_folder))
    SESSION_STATE_PATH = os.path.join(parent_dir, SESSION_STATE_FILENAME)
    STOP_FLAG_PATH = os.path.join(parent_dir, STOP_FLAG_FILENAME)


def _normalize_audio_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def _is_access_denied_error(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError):
        return getattr(exc, "winerror", None) == 5
    return False


def _ensure_writable(path: str):
    if not os.path.exists(path):
        return
    try:
        mode = os.stat(path).st_mode
        if not (mode & stat.S_IWRITE):
            os.chmod(path, mode | stat.S_IWRITE)
    except Exception as e:
        log(f"[WARN] 세션 파일 속성 복구 실패: {path} ({type(e).__name__}: {e})")


def _session_tmp_path(path: str) -> str:
    return path + ".tmp"


def cleanup_stale_session_tmp_files(session_dir: str):
    if not session_dir:
        return
    tmp_path = os.path.join(session_dir, SESSION_STATE_FILENAME + ".tmp")
    if not os.path.exists(tmp_path):
        return
    try:
        age = max(0.0, time.time() - os.path.getmtime(tmp_path))
    except Exception:
        age = -1.0
    try:
        os.remove(tmp_path)
        if age >= 0:
            log(f"[INFO] 오래된 세션 tmp 파일 정리 완료: {tmp_path} (age={age:.1f}s)")
        else:
            log(f"[INFO] 오래된 세션 tmp 파일 정리 완료: {tmp_path}")
    except Exception as e:
        log(f"[WARN] 세션 tmp 파일 정리 실패: {tmp_path} ({type(e).__name__}: {e})")


def load_session_state_safely(path: str) -> tuple[dict | None, str | None]:
    if not path or not os.path.exists(path):
        return None, None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None, "session state is not dict"
        return data, None
    except (JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"{type(e).__name__}: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def save_session_state_safely(state: dict, path: str, source: str = SESSION_SOURCE_WORKER) -> bool:
    if not path:
        return False

    tmp_path = _session_tmp_path(path)
    retries = max(SESSION_SAVE_RETRY_COUNT, 5)
    parent_dir = os.path.dirname(path) or "."
    os.makedirs(parent_dir, exist_ok=True)

    for attempt in range(1, retries + 1):
        try:
            _ensure_writable(path)
            _ensure_writable(tmp_path)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
            if attempt > 1:
                log(
                    f"[INFO] 세션 상태 저장 재시도 성공 ({attempt}/{retries}): "
                    f"target={path}, tmp={tmp_path}, source={source}"
                )
            return True
        except Exception as e:
            err_type = type(e).__name__
            retriable = _is_access_denied_error(e) or isinstance(e, OSError)
            if retriable and attempt < retries:
                wait = SESSION_SAVE_BACKOFF_SECONDS[min(attempt - 1, len(SESSION_SAVE_BACKOFF_SECONDS) - 1)]
                log(
                    f"[WARN] 세션 상태 저장 실패 {attempt}/{retries}회, 재시도 예정: "
                    f"{err_type} {e} | target={path} | tmp={tmp_path} | source={source}"
                )
                time.sleep(wait)
                continue
            log(
                f"[ERROR] 세션 상태 저장 최종 실패 ({attempt}/{retries}): "
                f"{err_type} {e} | target={path} | tmp={tmp_path} | source={source}"
            )
            return False
    return False


def _restore_completed_files_from_state(state: dict | None, target_folder: str):
    global RUN_COMPLETED_FILES
    if not state:
        RUN_COMPLETED_FILES = set()
        return
    target_norm = _normalize_audio_path(target_folder)
    restored: set[str] = set()
    for raw in state.get("completed_files", []) or []:
        if not isinstance(raw, str) or not raw.strip():
            continue
        norm = _normalize_audio_path(raw)
        if norm.startswith(target_norm + os.sep) or norm == target_norm:
            restored.add(norm)
    RUN_COMPLETED_FILES = restored


def update_session_state(status: str, current_file: str = "", extra: dict | None = None):
    if not SESSION_STATE_PATH:
        return

    payload = {
        "status": status,
        "current_file": current_file,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed_files": sorted(RUN_COMPLETED_FILES),
    }
    if extra:
        payload.update(extra)

    save_session_state_safely(payload, SESSION_STATE_PATH, source=SESSION_SOURCE_WORKER)


def detect_previous_session_state(target_folder: str):
    if not SESSION_STATE_PATH:
        return

    state, err = load_session_state_safely(SESSION_STATE_PATH)
    if err:
        log(f"[WARN] 이전 세션 상태 파일 손상 또는 읽기 실패: {err}")
        emit_event("PREVIOUS_SESSION_CORRUPT")
        _restore_completed_files_from_state(None, target_folder)
        update_session_state(STATUS_CORRUPT, "", {"last_session_error": err})
        return

    _restore_completed_files_from_state(state, target_folder)
    if not state:
        return

    status = str(state.get("status", "") or "").strip().lower()
    current_file = str(state.get("current_file", "") or "")
    has_stop_flag = bool(STOP_FLAG_PATH and os.path.exists(STOP_FLAG_PATH))

    if status == STATUS_RUNNING:
        if has_stop_flag:
            log("[INFO] 이전 작업 사용자 중지 흔적 감지 (running + stop.flag)")
            emit_event("PREVIOUS_SESSION_STOPPED_BY_USER")
            update_session_state(STATUS_STOPPED_BY_USER, current_file, {"previous_status": STATUS_RUNNING})
        else:
            log("[WARN] 이전 작업 비정상 종료 흔적 감지")
            emit_event("PREVIOUS_SESSION_CRASHED")
            update_session_state(STATUS_CRASHED, current_file, {"previous_status": STATUS_RUNNING})
        return

    if status in ("stopped", STATUS_STOPPED_BY_USER):
        log("[INFO] 이전 작업 사용자 중지 이력 감지")
        emit_event("PREVIOUS_SESSION_STOPPED_BY_USER")
        if status != STATUS_STOPPED_BY_USER:
            update_session_state(STATUS_STOPPED_BY_USER, current_file, {"previous_status": status})
        return

    if status == STATUS_CRASHED:
        emit_event("PREVIOUS_SESSION_CRASHED")
        return

    if status == STATUS_CORRUPT:
        emit_event("PREVIOUS_SESSION_CORRUPT")


def clear_old_stop_flag():
    if STOP_FLAG_PATH and os.path.exists(STOP_FLAG_PATH):
        try:
            age = max(0.0, time.time() - os.path.getmtime(STOP_FLAG_PATH))
            os.remove(STOP_FLAG_PATH)
            log(f"[INFO] 오래된 stop.flag 정리 완료: {STOP_FLAG_PATH} (age={age:.1f}s)")
        except Exception as e:
            log(f"[WARN] 이전 stop.flag 정리 실패: {type(e).__name__}: {e}")


def stop_requested() -> bool:
    return bool(STOP_FLAG_PATH and os.path.exists(STOP_FLAG_PATH))


# --------------------------------------------------
# 파일명 처리
# --------------------------------------------------
def remove_page_suffix(filename: str) -> str:
    """
    파일명 정리:
    1) 끝 페이지 표기 제거
       예: (p.123), (p.123~), (p.123~456), (p.+8+~+), (p.+8~+10)
    2) + 기호를 공백으로 변환
    3) 연속 공백을 1칸으로 정리
    확장자는 유지
    """
    name, ext = os.path.splitext(filename)

    name = re.sub(
        r"\s*\(\s*p\.?[\s+]*\d+[\s+]*(?:~[\s+]*\d*[\s+]*)?\)\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    name = name.replace("+", " ")
    name = re.sub(r"\s+", " ", name)

    return name.strip() + ext


def get_clean_base_name(audio_path: str) -> str:
    original_name = os.path.basename(audio_path)
    cleaned_name = remove_page_suffix(original_name)
    base_name = os.path.splitext(cleaned_name)[0]
    return base_name


def get_output_paths(audio_path: str) -> dict:
    output_dir = os.path.dirname(audio_path)
    base_name = get_clean_base_name(audio_path)

    return {
        "txt": os.path.join(output_dir, base_name + ".txt"),
        "json": os.path.join(output_dir, base_name + ".json"),
        "srt": os.path.join(output_dir, base_name + ".srt"),
    }


def output_files_look_complete(audio_path: str) -> bool:
    paths = get_output_paths(audio_path)
    for p in paths.values():
        if not os.path.exists(p):
            return False
        try:
            if os.path.getsize(p) <= 0:
                return False
        except OSError:
            return False

    # json이 손상되어 있으면 완료로 보지 않는다.
    try:
        with open(paths["json"], "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False
    except Exception:
        return False

    return True


def is_audio_completed(audio_path: str) -> bool:
    normalized = _normalize_audio_path(audio_path)
    if normalized in RUN_COMPLETED_FILES and output_files_look_complete(audio_path):
        return True
    return output_files_look_complete(audio_path)


# --------------------------------------------------
# Whisper 로드
# --------------------------------------------------
def load_whisper_model():
    global _whisper_model

    if _whisper_model is not None:
        return _whisper_model

    log(f"[*] Whisper '{MODEL_SIZE}' 모델 로드 중.. (최초 로딩 시 시간이 다소 필요할 수 있습니다)")
    import whisper

    _whisper_model = whisper.load_model(MODEL_SIZE)
    log("[*] 모델 로드 완료.")
    return _whisper_model


# --------------------------------------------------
# SRT 저장
# --------------------------------------------------
def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0

    millis = int(round(seconds * 1000))
    hours = millis // 3600000
    millis %= 3600000
    minutes = millis // 60000
    millis %= 60000
    secs = millis // 1000
    millis %= 1000

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(result: dict, srt_path: str):
    segments = result.get("segments", []) or []

    with open(srt_path, "w", encoding="utf-8") as f:
        index = 1
        for seg in segments:
            text = (seg.get("text") or "").strip()
            if not text:
                continue

            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", 0.0))

            f.write(f"{index}\n")
            f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
            f.write(text + "\n\n")
            index += 1


# --------------------------------------------------
# 결과 저장
# --------------------------------------------------
def save_result_files(audio_path: str, result: dict):
    paths = get_output_paths(audio_path)

    with open(paths["txt"], "w", encoding="utf-8") as f:
        f.write((result.get("text") or "").strip() + "\n")

    with open(paths["json"], "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    write_srt(result, paths["srt"])


# --------------------------------------------------
# 전사
# --------------------------------------------------
def transcribe_one_file(audio_path: str, index: int, total_files: int):
    file_name = os.path.basename(audio_path)

    if stop_requested():
        log("[INFO] stop.flag 감지 - 현재 파일 처리 중단 준비")
        emit_event("STOPPED", file_name)
        update_session_state(
            STATUS_STOPPED_BY_USER,
            file_name,
            {
                "stop_reason": "pre_file_start",
                "current_index": index,
                "target_files_total": total_files,
                "completed_count": len(RUN_COMPLETED_FILES),
            },
        )
        log("[INFO] 사용자 중지 상태로 세션 기록 완료")
        return "stopped"

    model = load_whisper_model()

    log(f"[RUNNING] '{file_name}' 전사 시작...")
    emit_event("START_FILE", file_name)
    update_session_state(
        STATUS_RUNNING,
        file_name,
        {
            "current_index": index,
            "target_files_total": total_files,
            "completed_count": len(RUN_COMPLETED_FILES),
        },
    )

    # progress_callback 같은 미지원 인자는 사용하지 않음
    result = model.transcribe(
        audio_path,
        verbose=False,
        fp16=False,
        language="ko",
    )

    if stop_requested():
        log(f"[INFO] stop.flag 감지 - '{file_name}' 결과 저장 전 사용자 중지 요청 확인")
        emit_event("STOPPED", file_name)
        update_session_state(
            STATUS_STOPPED_BY_USER,
            file_name,
            {
                "stop_reason": "after_transcribe_before_save",
                "current_index": index,
                "target_files_total": total_files,
                "completed_count": len(RUN_COMPLETED_FILES),
            },
        )
        log("[INFO] 사용자 중지 상태로 세션 기록 완료")
        return "stopped"

    save_result_files(audio_path, result)

    log(f"[DONE] '{file_name}' 전사 완료")
    RUN_COMPLETED_FILES.add(_normalize_audio_path(audio_path))
    emit_event("FILE_DONE", file_name)
    update_session_state(
        STATUS_RUNNING,
        "",
        {
            "last_done_file": file_name,
            "current_index": index,
            "target_files_total": total_files,
            "completed_count": len(RUN_COMPLETED_FILES),
        },
    )
    return "done"


# --------------------------------------------------
# 메인 처리
# --------------------------------------------------
def find_mp3_files(target_folder: str) -> list[str]:
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(glob.glob(os.path.join(target_folder, f"*{ext}")))
    files = sorted(set(files))
    return files


def process_folder(target_folder: str):
    abs_target = os.path.abspath(target_folder)

    if not os.path.isdir(abs_target):
        raise FileNotFoundError(f"전사자료 폴더를 찾을 수 없습니다: {abs_target}")

    init_runtime_paths(abs_target)
    cleanup_stale_session_tmp_files(os.path.dirname(abs_target))
    detect_previous_session_state(abs_target)
    clear_old_stop_flag()

    log(f"[DEBUG] 실행 파일: {os.path.abspath(__file__)}")
    log("=" * 60)
    log(f"시작 시간: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}")
    log(f"처리 대상 입력 경로: ['{abs_target}']")
    log("-" * 60)
    log(f"[INFO] 폴더 처리 시작: '{abs_target}'")

    mp3_files = find_mp3_files(abs_target)

    skip_files: list[str] = []
    actual_target_files: list[str] = []
    for audio_path in mp3_files:
        if is_audio_completed(audio_path):
            skip_files.append(audio_path)
        else:
            actual_target_files.append(audio_path)

    log(f"[DEBUG] 발견된 전체 mp3 수: {len(mp3_files)}")
    log(f"[DEBUG] 기존 결과물 존재로 스킵할 파일 수: {len(skip_files)}")
    log(f"[DEBUG] 이번 실행 실제 처리 대상 수: {len(actual_target_files)}")
    emit_event("TOTAL_FILES", len(mp3_files), len(skip_files), len(actual_target_files))

    if not mp3_files:
        log(f"[] '{abs_target}' 에서 처리할 MP3 파일을 찾지 못했습니다.")
        update_session_state(STATUS_COMPLETED, "", {"total_discovered_files": 0, "target_files_total": 0})
        emit_event("ALL_DONE")
        return

    if not actual_target_files:
        log("[INFO] 이번 실행에서 처리할 파일이 없습니다.")
        update_session_state(
            STATUS_COMPLETED,
            "",
            {
                "total_discovered_files": len(mp3_files),
                "skipped_files": len(skip_files),
                "target_files_total": 0,
                "completed_count": len(RUN_COMPLETED_FILES),
            },
        )
        emit_event("ALL_DONE")
        return

    total_files = len(actual_target_files)
    update_session_state(
        STATUS_RUNNING,
        "",
        {
            "total_discovered_files": len(mp3_files),
            "skipped_files": len(skip_files),
            "target_files_total": total_files,
            "completed_count": len(RUN_COMPLETED_FILES),
        },
    )

    for idx, audio_path in enumerate(actual_target_files, start=1):
        file_name = os.path.basename(audio_path)

        if stop_requested():
            log("[INFO] 사용자 즉시 중지 요청 감지")
            log("[INFO] stop.flag 감지 - 현재 파일 처리 중단 준비")
            update_session_state(
                STATUS_STOPPED_BY_USER,
                file_name,
                {
                    "stop_reason": "before_file_loop",
                    "current_index": idx,
                    "target_files_total": total_files,
                    "completed_count": len(RUN_COMPLETED_FILES),
                },
            )
            emit_event("STOPPED", file_name)
            emit_event("ALL_STOPPED")
            log("[INFO] 사용자 중지 상태로 세션 기록 완료")
            return

        emit_event("FILE_INDEX", idx, total_files, file_name)
        log(f"[PROGRESS] {idx} / {total_files} | {file_name}")

        try:
            if is_audio_completed(audio_path):
                log(f"[SKIP] '{file_name}' (이미 전사 완료)")
                emit_event("FILE_SKIP", file_name)
                continue

            result = transcribe_one_file(audio_path, idx, total_files)
            if result == "stopped":
                emit_event("ALL_STOPPED")
                return

        except KeyboardInterrupt:
            log("[INFO] 사용자 즉시 중지 요청 감지 (KeyboardInterrupt)")
            update_session_state(
                STATUS_STOPPED_BY_USER,
                file_name,
                {
                    "stop_reason": "keyboard_interrupt",
                    "current_index": idx,
                    "target_files_total": total_files,
                    "completed_count": len(RUN_COMPLETED_FILES),
                },
            )
            emit_event("STOPPED", file_name)
            emit_event("ALL_STOPPED")
            log("[INFO] 사용자 중지 상태로 세션 기록 완료")
            return

        except Exception as e:
            log(f"[FAIL] '{file_name}' 처리 중 오류 발생:")
            log(str(e))
            emit_event("FILE_FAIL", file_name, str(e))
            update_session_state(
                STATUS_RUNNING,
                file_name,
                {
                    "last_error": str(e),
                    "error_type": type(e).__name__,
                    "current_index": idx,
                    "target_files_total": total_files,
                    "completed_count": len(RUN_COMPLETED_FILES),
                },
            )

    update_session_state(
        STATUS_COMPLETED,
        "",
        {
            "total_discovered_files": len(mp3_files),
            "skipped_files": len(skip_files),
            "target_files_total": total_files,
            "completed_count": len(RUN_COMPLETED_FILES),
        },
    )
    emit_event("ALL_DONE")

    log("")
    log("=" * 60)
    log(f"전체 작업 완료. 종료 시간: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}")
    log("=" * 60)


# --------------------------------------------------
# 엔트리 포인트
# --------------------------------------------------
def main():
    try:
        try:
            locale.setlocale(locale.LC_ALL, "ko_KR.UTF-8")
        except locale.Error:
            pass

        if len(sys.argv) < 2:
            print("사용법: python auto_transcribe.py <전사자료 폴더>", flush=True)
            sys.exit(1)

        target_folder = sys.argv[1]
        process_folder(target_folder)

    except Exception as e:
        log("[FATAL] 치명적 오류 발생")
        log(str(e))
        traceback.print_exc()

        if SESSION_STATE_PATH is not None:
            update_session_state(STATUS_CRASHED, "", {"fatal_error": str(e), "error_type": type(e).__name__})

        emit_event("PROCESS_CRASHED", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
