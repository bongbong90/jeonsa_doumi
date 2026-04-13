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

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

MODEL_SIZE = "medium"
SUPPORTED_EXTENSIONS = (".mp3", ".MP3")
SESSION_STATE_FILENAME = "transcribe_session_state.json"
STOP_FLAG_FILENAME = "stop.flag"

SESSION_STATE_PATH = None
STOP_FLAG_PATH = None
_whisper_model = None


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


def safe_json_dump(path: str, data: dict):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def update_session_state(status: str, current_file: str = "", extra: dict | None = None):
    if not SESSION_STATE_PATH:
        return

    payload = {
        "status": status,
        "current_file": current_file,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if extra:
        payload.update(extra)

    try:
        safe_json_dump(SESSION_STATE_PATH, payload)
    except Exception as e:
        log(f"[WARN] 세션 상태 저장 실패: {e}")


def detect_previous_crash():
    if not SESSION_STATE_PATH or not os.path.exists(SESSION_STATE_PATH):
        return

    try:
        with open(SESSION_STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)

        if state.get("status") == "running":
            log("[WARN] 이전 작업 비정상 종료 흔적 감지")
            emit_event("PREVIOUS_SESSION_CRASHED")
            update_session_state("crashed", state.get("current_file", ""))

    except Exception as e:
        log(f"[WARN] 이전 세션 상태 확인 실패: {e}")


def clear_old_stop_flag():
    if STOP_FLAG_PATH and os.path.exists(STOP_FLAG_PATH):
        try:
            os.remove(STOP_FLAG_PATH)
        except Exception as e:
            log(f"[WARN] 이전 stop.flag 삭제 실패: {e}")


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

    # 끝의 페이지 표기 제거
    name = re.sub(
        r"\s*\(\s*p\.?[\s+]*\d+[\s+]*(?:~[\s+]*\d*[\s+]*)?\)\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    # + 기호를 공백으로 변환
    name = name.replace("+", " ")

    # 연속 공백 정리
    name = re.sub(r"\s+", " ", name)

    return name.strip() + ext


def get_clean_base_name(audio_path: str) -> str:
    """
    파일명 정리 규칙:
    1) basename 추출
    2) 끝 페이지 표기 제거
    3) 확장자 제거
    4) 중간의 점(.)은 유지

    예:
    21강_[6주차]_26_02_09_[교재] 2. 포상금 제도.mp3
    -> 21강_[6주차]_26_02_09_[교재] 2. 포상금 제도
    """
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


def all_output_files_exist(audio_path: str) -> bool:
    paths = get_output_paths(audio_path)
    return all(os.path.exists(p) for p in paths.values())


# --------------------------------------------------
# Whisper 로드
# --------------------------------------------------
def load_whisper_model():
    global _whisper_model

    if _whisper_model is not None:
        return _whisper_model

    log(f"[*] Whisper '{MODEL_SIZE}' 모델 로드 중... (최초 로딩 시 시간이 다소 소요될 수 있습니다)")
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
def transcribe_one_file(audio_path: str):
    model = load_whisper_model()
    file_name = os.path.basename(audio_path)

    log(f"[RUNNING] '{file_name}' 전사 시작...")
    emit_event("START_FILE", file_name)
    update_session_state("running", file_name)

    # 원래 흐름 최대한 유지:
    # verbose=False / fp16=False / language='ko'
    # progress_callback 같은 미지원 인자는 사용하지 않음
    result = model.transcribe(
        audio_path,
        verbose=False,
        fp16=False,
        language="ko",
    )

    if stop_requested():
        log(f"[STOP] '{file_name}' 저장 전 중지 요청 감지")
        emit_event("STOPPED", file_name)
        update_session_state("stopped", file_name)
        return "stopped"

    save_result_files(audio_path, result)

    log(f"[DONE] '{file_name}' 전사 완료")
    emit_event("FILE_DONE", file_name)
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
    detect_previous_crash()
    clear_old_stop_flag()

    log(f"[DEBUG] 실행 파일: {os.path.abspath(__file__)}")
    log("=" * 60)
    log(f"시작 시간: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}")
    log(f"처리할 입력 경로: ['{abs_target}']")
    log("-" * 60)
    log(f"[INFO] 폴더 처리 시작: '{abs_target}'")

    mp3_files = find_mp3_files(abs_target)
    actual_target_files = [
        audio_path for audio_path in mp3_files if not all_output_files_exist(audio_path)
    ]
    log(f"[DEBUG] 발견된 mp3 수: {len(mp3_files)}")
    emit_event("TOTAL_FILES", len(actual_target_files), len(actual_target_files))

    if not mp3_files:
        log(f"[] '{abs_target}' 에서 처리할 MP3 파일을 찾지 못했습니다.")
        update_session_state("completed", "")
        emit_event("ALL_DONE")
        return

    if not actual_target_files:
        log("[INFO] 이번 실행에서 처리할 파일이 없습니다.")
        update_session_state("completed", "")
        emit_event("ALL_DONE")
        return

    update_session_state("running", "")

    total_files = len(actual_target_files)

    for idx, audio_path in enumerate(actual_target_files, start=1):
        file_name = os.path.basename(audio_path)

        if stop_requested():
            log("[STOP] stop.flag 감지 - 작업을 중지합니다.")
            update_session_state("stopped", file_name)
            emit_event("STOPPED", file_name)
            emit_event("ALL_STOPPED")
            return

        emit_event("FILE_INDEX", idx, total_files, file_name)

        try:
            if all_output_files_exist(audio_path):
                log(f"[SKIP] '{file_name}' (이미 전사 완료)")
                emit_event("FILE_SKIP", file_name)
                continue

            result = transcribe_one_file(audio_path)

            if result == "stopped":
                emit_event("ALL_STOPPED")
                return

        except KeyboardInterrupt:
            log("[STOP] KeyboardInterrupt 감지 - 작업 중지")
            update_session_state("stopped", file_name)
            emit_event("STOPPED", file_name)
            emit_event("ALL_STOPPED")
            return

        except Exception as e:
            log(f"[FAIL] '{file_name}' 처리 중 오류 발생:")
            log(str(e))
            emit_event("FILE_FAIL", file_name, str(e))
            update_session_state("running", file_name, {"last_error": str(e)})

    update_session_state("completed", "")
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
            update_session_state("crashed", "", {"fatal_error": str(e)})

        emit_event("PROCESS_CRASHED", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
