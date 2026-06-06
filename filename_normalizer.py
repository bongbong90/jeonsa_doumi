import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple, List

def remove_page_markers(text: str) -> str:
    """
    파일명에 포함된 다양한 형태의 페이지 표기를 제거합니다.
    예: (p.40), (p. 40), (p.+40), (p.70~), (p.+70+~+), (p.123~456)
    """
    pattern = r'\(p\.[+\s]*\d+[+\s]*(?:~[+\s]*\d*[+\s]*)?\)'
    return re.sub(pattern, '', text)

def clean_download_stem(stem: str) -> str:
    """
    다운로드한 파일명(stem)을 제목형으로 정리합니다.
    """
    # 1. '+'를 공백으로 변환
    s = stem.replace('+', ' ')
    # 2. 페이지 표기 제거
    s = remove_page_markers(s)
    # 3. Windows 파일명 금지 문자 제거
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    # 4. 연속된 공백을 하나로 축소
    s = re.sub(r'\s+', ' ', s)
    # 5. '_' 주변 공백 정리
    s = re.sub(r'\s*_\s*', '_', s)
    # 6. 연속된 '_' 정리
    s = re.sub(r'_+', '_', s)
    # 7. 앞뒤 공백 및 '_' 제거
    s = s.strip(' _')
    return s

def natural_sort_key(value: str) -> list:
    """
    문자열 내의 숫자를 인식하여 자연스러운 정렬을 할 수 있도록 key를 반환합니다.
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', value)]

def detect_course_name(path_or_name: str, default: str = "분류대기") -> str:
    name = Path(path_or_name).name
    courses = ["개념완성", "기본이론", "기초이론"]
    for c in courses:
        if c in name:
            return c
    return default

def detect_subject_name(path_or_name: str, default: str = "과목불명") -> str:
    name = Path(path_or_name).name
    # 주의: 부동산공시법이 부동산공법보다 먼저 매칭되도록 순서를 배치
    subject_map = {
        "민법": ["민법", "김덕수"],
        "부동산학개론": ["부동산학개론", "학개론", "개론", "이종호"],
        "공인중개사법": ["공인중개사법", "중개사법", "중개실무", "정지웅"],
        "부동산공시법": ["부동산공시법", "공시법", "등기법", "지적법", "박윤모"],
        "부동산공법": ["부동산공법", "공법", "김희상"],
        "부동산세법": ["부동산세법", "세법", "정석진"]
    }
    for subject, keywords in subject_map.items():
        for kw in keywords:
            if kw in name:
                return subject
    return default

def detect_drive_subject_folder(path_or_name: str, default: str = "과목불명") -> str:
    subject = detect_subject_name(path_or_name, default)
    if subject in ["민법", "부동산학개론"]:
        return f"[1차] {subject}"
    elif subject in ["공인중개사법", "부동산공법", "부동산공시법", "부동산세법"]:
        return f"[2차] {subject}"
    return default

def detect_week_lesson(path_or_name: str) -> Tuple[Optional[int], Optional[int], str]:
    name = Path(path_or_name).name
    
    # 1. [N-M] 패턴 (예: 13강_[4-1] 시장론 4.mp3)
    m = re.search(r'\[(\d+)-(\d+)\]', name)
    if m:
        return int(m.group(1)), int(m.group(2)), "bracket_week_lesson"
    
    # 2. 일반 N주차_M강 패턴 (예: 개념완성_민법_4주차_3강.mp3)
    m = re.search(r'(\d+)주차[^\d]*(\d+)강', name)
    if m:
        return int(m.group(1)), int(m.group(2)), "normal"
    
    # 3. 일반 N주차 패턴 (예: 12강_[4주차]_...)
    m = re.search(r'(\d+)주차', name)
    if m:
        return int(m.group(1)), None, "week_only"
    
    return None, None, "unknown"

def build_standard_stem(course: str, subject: str, week: int, lesson: int) -> str:
    return f"{course}_{subject}_{week}주차_{lesson}강"

@dataclass
class NormalizePlan:
    original_path: Path
    original_name: str
    original_stem: str
    clean_title_stem: str
    course: str
    subject: str
    week: Optional[int]
    lesson: Optional[int]
    standard_stem: Optional[str]
    standard_name: Optional[str]
    target_path: Optional[Path]
    reason: str
    needs_rename: bool
    conflict: bool
    error: str

def build_normalize_plan(path: str | Path, course_hint: str | None = None, subject_hint: str | None = None, week_hint: int | None = None, lesson_hint: int | None = None) -> NormalizePlan:
    p = Path(path)
    original_name = p.name
    original_stem = p.stem
    ext = p.suffix

    clean_stem = clean_download_stem(original_stem)
    
    course = course_hint if course_hint else detect_course_name(original_name)
    subject = subject_hint if subject_hint else detect_subject_name(original_name)
    
    detected_week, detected_lesson, _ = detect_week_lesson(original_name)
    week = week_hint if week_hint is not None else detected_week
    lesson = lesson_hint if lesson_hint is not None else detected_lesson

    standard_stem = None
    standard_name = None
    target_path = None
    reason = ""
    needs_rename = False
    conflict = False
    error = ""

    if course == "분류대기":
        error = "과정명 감지 실패"
    elif subject == "과목불명":
        error = "과목명 감지 실패"
    elif week is None:
        error = "주차 감지 실패"
    elif lesson is None:
        error = "강 번호 감지 실패"
    else:
        standard_stem = build_standard_stem(course, subject, week, lesson)
        standard_name = f"{standard_stem}{ext}"
        target_path = p.parent / standard_name
        
        if original_name != standard_name:
            needs_rename = True
            reason = "파일명 표준화 필요"
        else:
            reason = "이미 표준 파일명"

        if target_path and target_path.exists() and target_path != p:
            conflict = True
            error = f"대상 파일이 이미 존재합니다: {standard_name}"

    return NormalizePlan(
        original_path=p,
        original_name=original_name,
        original_stem=original_stem,
        clean_title_stem=clean_stem,
        course=course,
        subject=subject,
        week=week,
        lesson=lesson,
        standard_stem=standard_stem,
        standard_name=standard_name,
        target_path=target_path,
        reason=reason,
        needs_rename=needs_rename,
        conflict=conflict,
        error=error
    )

def preview_folder_renames(folder: str | Path, course_hint: str | None = None, subject_hint: str | None = None, week_hint: int | None = None) -> List[NormalizePlan]:
    fpath = Path(folder)
    plans = []
    
    if not fpath.is_dir():
        return plans

    mp3_files = [p for p in fpath.iterdir() if p.suffix.lower() == '.mp3']
    mp3_files.sort(key=lambda p: natural_sort_key(p.name))

    temp_plans = []
    for p in mp3_files:
        w, l, _ = detect_week_lesson(p.name)
        wk = week_hint if week_hint is not None else w
        temp_plans.append((p, wk, l))
    
    week_lesson_counters = {}
    
    for p, wk, ls in temp_plans:
        final_lesson = ls
        if wk is not None:
            if wk not in week_lesson_counters:
                week_lesson_counters[wk] = 1
            if final_lesson is None:
                final_lesson = week_lesson_counters[wk]
            
            week_lesson_counters[wk] = max(week_lesson_counters[wk], final_lesson) + 1
            
        plan = build_normalize_plan(
            p, 
            course_hint=course_hint, 
            subject_hint=subject_hint, 
            week_hint=wk, 
            lesson_hint=final_lesson
        )
        plans.append(plan)
        
    return plans

def apply_rename_plan(plans: List[NormalizePlan], dry_run: bool = True) -> List[dict]:
    results = []
    for p in plans:
        res = {
            "original": p.original_name,
            "target": p.standard_name,
            "status": "skipped",
            "message": p.reason
        }
        if p.error:
            res["status"] = "error"
            res["message"] = p.error
        elif p.conflict:
            res["status"] = "conflict"
            res["message"] = "충돌 발생"
        elif not p.needs_rename:
            res["status"] = "ok"
            res["message"] = "변경 불필요"
        elif not dry_run:
            # 실제 rename
            try:
                # os.rename(p.original_path, p.target_path)
                # res["status"] = "renamed"
                # res["message"] = "변경 완료"
                pass # 이번 단계에서는 파일 수정하지 않음
            except Exception as e:
                res["status"] = "error"
                res["message"] = str(e)
        else:
            res["status"] = "dry_run"
            res["message"] = "dry-run (변경됨)"
            
        results.append(res)
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="파일명 정규화 모듈")
    parser.add_argument("path", help="대상 파일 또는 폴더 경로")
    parser.add_argument("--dry-run", action="store_true", default=True, help="실제 변경 없이 결과만 출력 (기본값)")
    parser.add_argument("--apply", action="store_true", help="실제 변경 수행 (이번 단계에서는 무시됨)")
    parser.add_argument("--course", help="과정명 힌트 (예: 개념완성)")
    parser.add_argument("--subject", help="과목명 힌트 (예: 부동산학개론)")
    parser.add_argument("--week", type=int, help="주차 힌트")
    parser.add_argument("--lesson", type=int, help="강 힌트 (단일 파일용)")
    
    args = parser.parse_args()
    
    target_path = Path(args.path)
    
    if target_path.is_file() or not target_path.exists():
        plan = build_normalize_plan(
            args.path, 
            course_hint=args.course,
            subject_hint=args.subject,
            week_hint=args.week,
            lesson_hint=args.lesson
        )
        plans = [plan]
    else:
        plans = preview_folder_renames(
            target_path,
            course_hint=args.course,
            subject_hint=args.subject,
            week_hint=args.week
        )
        
    for p in plans:
        print(f"원본 파일명: {p.original_name}")
        print(f"제목형 정리명: {p.clean_title_stem}")
        print(f"감지된 과정명: {p.course}")
        print(f"감지된 과목명: {p.subject}")
        print(f"감지된 주차/강: {p.week}주차 {p.lesson}강")
        print(f"표준 파일명: {p.standard_name}")
        print(f"충돌 여부: {p.conflict}")
        print(f"rename 필요 여부: {p.needs_rename}")
        if p.error:
            print(f"오류/알림: {p.error}")
        print("-" * 40)
