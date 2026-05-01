
import datetime
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time

from PySide6.QtCore import QProcess, QTimer, Qt
from PySide6.QtGui import QAction, QFont, QFontDatabase, QFontInfo, QIcon, QTextCursor, QTextOption
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)


STOP_FLAG_FILENAME = "stop.flag"
SESSION_STATE_FILENAME = "transcribe_session_state.json"
ETA_EMPTY_TEXT = "-"
APP_DISPLAY_NAME = "전사도우미"
APP_USER_MODEL_ID = "com.codex.transcribehelper"
UI_DEFAULT_FONT_SIZE = 10


def apply_windows_app_identity():
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def get_shortcut_target_exe_path() -> str:
    if os.name != "nt":
        return ""
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    candidate = os.path.join(get_runtime_base_dir(), "dist", APP_DISPLAY_NAME, f"{APP_DISPLAY_NAME}.exe")
    if os.path.exists(candidate):
        return os.path.abspath(candidate)
    return ""


def ensure_start_menu_shortcut():
    if os.name != "nt":
        return

    exe_path = get_shortcut_target_exe_path()
    if not exe_path:
        return
    work_dir = os.path.dirname(exe_path)
    start_menu_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
    if not start_menu_dir:
        return

    try:
        os.makedirs(start_menu_dir, exist_ok=True)
    except Exception:
        return

    shortcut_path = os.path.join(start_menu_dir, f"{APP_DISPLAY_NAME}.lnk")

    def _ps_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    ps_script = "\n".join(
        [
            f"$shortcutPath = {_ps_quote(shortcut_path)}",
            f"$targetPath = {_ps_quote(exe_path)}",
            f"$workingDir = {_ps_quote(work_dir)}",
            f"$iconLocation = {_ps_quote(exe_path + ',0')}",
            "$wsh = New-Object -ComObject WScript.Shell",
            "$shortcut = $wsh.CreateShortcut($shortcutPath)",
            "$shortcut.TargetPath = $targetPath",
            "$shortcut.WorkingDirectory = $workingDir",
            "$shortcut.IconLocation = $iconLocation",
            f"$shortcut.Description = {_ps_quote(APP_DISPLAY_NAME)}",
            "$shortcut.Save()",
        ]
    )

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        pass


def remove_page_suffix(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    name = re.sub(
        r"\s*\(\s*p\.?[\s+]*\d+[\s+]*(?:~[\s+]*\d*[\s+]*)?\)\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    name = name.replace("+", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name + ext


def format_seconds(seconds: float | int) -> str:
    sec = max(0, int(round(float(seconds))))
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}시간 {m}분 {s}초"
    if m > 0:
        return f"{m}분 {s}초"
    return f"{s}초"


def get_runtime_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def load_runtime_icon() -> QIcon:
    base = get_runtime_base_dir()
    meipass = getattr(sys, "_MEIPASS", "")
    candidates = [
        os.path.join(base, "transcribe_helper.ico"),
        os.path.join(base, "assets", "transcribe_helper.ico"),
        os.path.join(base, "assets", "transcribe_helper.png"),
        os.path.join(base, "transcribe_helper.png"),
        os.path.join(base, "_internal", "transcribe_helper.ico"),
        os.path.join(base, "_internal", "assets", "transcribe_helper.ico"),
        os.path.join(base, "_internal", "assets", "transcribe_helper.png"),
        os.path.join(base, "transcribe_helper.svg"),
        os.path.join(base, "assets", "transcribe_helper.svg"),
        os.path.join(base, "_internal", "transcribe_helper.svg"),
        os.path.join(base, "_internal", "assets", "transcribe_helper.svg"),
    ]
    if meipass:
        candidates.extend(
            [
                os.path.join(meipass, "transcribe_helper.ico"),
                os.path.join(meipass, "assets", "transcribe_helper.ico"),
                os.path.join(meipass, "assets", "transcribe_helper.png"),
                os.path.join(meipass, "transcribe_helper.png"),
                os.path.join(meipass, "_internal", "transcribe_helper.ico"),
                os.path.join(meipass, "_internal", "assets", "transcribe_helper.ico"),
                os.path.join(meipass, "_internal", "assets", "transcribe_helper.png"),
                os.path.join(meipass, "transcribe_helper.svg"),
                os.path.join(meipass, "assets", "transcribe_helper.svg"),
                os.path.join(meipass, "_internal", "transcribe_helper.svg"),
                os.path.join(meipass, "_internal", "assets", "transcribe_helper.svg"),
            ]
        )
    seen = set()
    for path in candidates:
        norm = os.path.normcase(os.path.abspath(path))
        if norm in seen:
            continue
        seen.add(norm)
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
    return QIcon()


def _normalize_font_name(name: str) -> str:
    return re.sub(r"[\s\-_]", "", (name or "")).lower()


def _collect_embedded_ui_fonts() -> list[str]:
    base = get_runtime_base_dir()
    meipass = getattr(sys, "_MEIPASS", "")
    scan_dirs = [
        os.path.join(base, "assets"),
        os.path.join(base, "assets", "fonts"),
        os.path.join(base, "_internal", "assets"),
        os.path.join(base, "_internal", "assets", "fonts"),
        os.path.join(base, "fonts"),
        base,
    ]
    if meipass:
        scan_dirs.extend(
            [
                os.path.join(meipass, "assets"),
                os.path.join(meipass, "assets", "fonts"),
                os.path.join(meipass, "_internal", "assets"),
                os.path.join(meipass, "_internal", "assets", "fonts"),
                os.path.join(meipass, "fonts"),
                meipass,
            ]
        )
    paths = []
    for directory in scan_dirs:
        if not os.path.isdir(directory):
            continue
        try:
            for root, _, files in os.walk(directory):
                for name in files:
                    low = name.lower()
                    if not low.endswith((".ttf", ".otf", ".ttc")):
                        continue
                    if not any(key in low for key in ("gmarket", "wanted", "suit", "pretendard")):
                        continue
                    paths.append(os.path.join(root, name))
        except Exception:
            continue
    dedup = []
    seen = set()
    for p in paths:
        key = os.path.normcase(os.path.abspath(p))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(p)
    return dedup


def _pick_gmarket_font_files() -> dict[str, str]:
    candidates = _collect_embedded_ui_fonts()
    gmarket = sorted(
        [p for p in candidates if "gmarket" in os.path.basename(p).lower()],
        key=lambda p: os.path.basename(p).lower(),
    )

    selected = {"light": "", "medium": "", "bold": ""}

    def pick_by_keywords(role: str, includes: tuple[str, ...], excludes: tuple[str, ...] = ()):
        if selected[role]:
            return
        for path in gmarket:
            low = os.path.basename(path).lower()
            if all(k in low for k in includes) and all(e not in low for e in excludes):
                selected[role] = path
                return

    pick_by_keywords("light", ("light",))
    pick_by_keywords("medium", ("medium",))
    pick_by_keywords("bold", ("bold",), excludes=("extra", "black"))

    for path in gmarket:
        low = os.path.basename(path).lower()
        if not selected["light"] and "light" in low:
            selected["light"] = path
        if not selected["medium"] and "medium" in low:
            selected["medium"] = path
        if not selected["bold"] and ("bold" in low and "extra" not in low and "black" not in low):
            selected["bold"] = path

    # 필요 굵기가 하나라도 비면 보유 파일 중에서 보충한다.
    for key in ("light", "medium", "bold"):
        if selected[key]:
            continue
        for path in gmarket:
            if path not in selected.values():
                selected[key] = path
                break
    return selected


def apply_preferred_ui_font(app: QApplication) -> tuple[str, list[str]]:
    debug_lines: list[str] = []
    preferred_families = [
        "Malgun Gothic",
        "맑은 고딕",
        "NanumBarunGothic",
        "나눔바른고딕",
        "NanumGothic",
        "나눔고딕",
        "Segoe UI",
        "Arial",
    ]

    installed = {name.lower(): name for name in QFontDatabase.families()}
    selected = ""
    for fam in preferred_families:
        if fam.lower() in installed:
            selected = installed[fam.lower()]
            break
    if not selected:
        selected = app.font().family() or "Segoe UI"

    debug_lines.append(f"[FONT] selected_base_family={selected}")
    debug_lines.append(f"[FONT] preferred_candidates={preferred_families}")

    font = QFont(selected, UI_DEFAULT_FONT_SIZE)
    try:
        font.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
    except Exception:
        pass
    try:
        font.setStyleStrategy(QFont.StyleStrategy.PreferDefault | QFont.StyleStrategy.PreferAntialias)
    except Exception:
        pass
    try:
        font.setFamilies(["Malgun Gothic", "맑은 고딕", "NanumBarunGothic", "NanumGothic", "Segoe UI", "Arial"])
    except Exception:
        pass
    try:
        font.setKerning(True)
    except Exception:
        pass
    app.setFont(font)
    debug_lines.append(f"[FONT] app.setFont family={selected}, pointSize={font.pointSize()}")

    for line in debug_lines:
        print(line)

    return selected, debug_lines


def collect_font_application_diagnostics(window: "TranscribeGUI", expected_family: str) -> list[str]:
    lines: list[str] = []
    expected_norm = _normalize_font_name(expected_family)

    qss = window.styleSheet().lower()
    lines.append(f"[FONT-CHECK] qss_has_font_family_override={'font-family' in qss}")

    targets = [
        ("main_title", window.label_title_text),
        ("section_settings", window.group_settings),
        ("section_options", window.group_options),
        ("button_primary", window.btn_move_and_transcribe),
        ("button_side", window.btn_download),
        ("path_label", window.label_download),
        ("dashboard_label", window.label_status),
        ("helper_text", window.label_settings_hint),
        ("log_viewer", window.log_viewer),
    ]

    for name, widget in targets:
        req = widget.font()
        req_family = req.family()
        resolved_family = QFontInfo(req).family()
        req_norm = _normalize_font_name(req_family)
        resolved_norm = _normalize_font_name(resolved_family)
        matched = expected_norm in (req_norm, resolved_norm)
        lines.append(
            "[FONT-CHECK] "
            f"{name}: requested='{req_family}', resolved='{resolved_family}', "
            f"size={req.pointSize()}, weight={req.weight()}, matched_expected={matched}"
        )
    return lines


def run_font_debug_probe() -> int:
    print("[FONT-TEST] mode=font-debug")
    app = QApplication(sys.argv)
    selected_font_family, _ = apply_preferred_ui_font(app)
    app_font = app.font()
    print(
        "[FONT-TEST] app.font="
        f"family='{app_font.family()}', size={app_font.pointSize()}, weight={app_font.weight()}"
    )
    print(f"[FONT-TEST] selected_family='{selected_font_family}'")

    window = TranscribeGUI()
    for line in collect_font_application_diagnostics(window, selected_font_family):
        print(line)

    print("[FONT-TEST] done")
    window.deleteLater()
    app.quit()
    return 0


class TranscribeGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("RootWindow")
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(1380, 860)
        self.setMinimumSize(1100, 700)

        self.download_folder = ""
        self.target_folder = ""
        self.process = None
        self.log_visible = False
        self.stdout_buffer = ""
        self.stderr_buffer = ""

        self.total_target_mp3_files = 0
        self.completed_files = set()
        self.notified_success_files = set()
        self.total_complete_notified = False

        self.current_file_name = ""
        self.current_file_started_at = None
        self.current_eta_seconds = None
        self.total_eta_seconds = None
        self.file_duration_history = []
        self.last_current_percent = 0

        self.stop_requested = False
        self.pending_kill = False
        self.stop_terminate_sent = False
        self._status_full_text = "현재 상태: 대기 중"
        self._current_file_full_text = "현재 처리 중 파일: 없음"
        self._session_full_text = "세션 상태: 확인 안 됨"
        self._output_full_text = "실시간 출력: GUI에 직접 연결됨"

        self.build_ui()
        self.apply_styles()
        self.apply_font_hierarchy()
        self.apply_typography_fit_defaults()
        self.setup_tray_icon()
        self.update_total_progress_display()
        self.update_current_file_progress(0, force=True)
        self.update_eta_labels(initial=True)
        self.update_session_label()

        self.force_kill_timer = QTimer(self)
        self.force_kill_timer.setSingleShot(True)
        self.force_kill_timer.timeout.connect(self.force_kill_process)

        self.eta_timer = QTimer(self)
        self.eta_timer.timeout.connect(self.refresh_eta_tick)
        self.eta_timer.start(1000)

    def build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        sidebar = QFrame()
        sidebar.setObjectName("SidebarPane")
        sidebar.setFixedWidth(340)
        left = QVBoxLayout(sidebar)
        left.setContentsMargins(14, 14, 14, 14)
        left.setSpacing(12)

        mainpane = QFrame()
        mainpane.setObjectName("MainPane")
        right = QVBoxLayout(mainpane)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(12)

        root.addWidget(sidebar, 0)
        root.addWidget(mainpane, 1)

        title = QFrame()
        title.setObjectName("TitleCard")
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tbox = QVBoxLayout(title)
        tbox.setContentsMargins(16, 14, 16, 14)
        tbox.setSpacing(2)
        self.label_title_text = QLabel("전사도우미", objectName="TitleText")
        self.label_title_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_title_hint = QLabel("CONFIGURATION & LOGS", objectName="TitleHint")
        self.label_title_hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        tbox.addWidget(self.label_title_text)
        tbox.addWidget(self.label_title_hint)
        left.addWidget(title)
        self.group_title = title

        settings = QGroupBox("Folder Settings")
        settings.setObjectName("SidebarSection")
        settings.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sbox = QVBoxLayout(settings)
        sbox.setContentsMargins(14, 16, 14, 14)
        sbox.setSpacing(8)
        self.label_settings_hint = QLabel("전사 전에 사용할 폴더를 먼저 지정하세요.", objectName="SideHelperText")
        self.label_settings_hint.setWordWrap(True)
        sbox.addWidget(self.label_settings_hint)

        self.label_download = QLabel("다운로드 폴더: 아직 선택 안 함")
        self.label_download.setWordWrap(False)
        self.label_download.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_download.setObjectName("PathLabel")
        sbox.addWidget(self.label_download)
        self.btn_download = QPushButton("다운로드 폴더 선택")
        self.btn_download.setProperty("uiRole", "side")
        sbox.addWidget(self.btn_download)

        self.label_target = QLabel("전사자료 폴더: 아직 선택 안 함")
        self.label_target.setWordWrap(False)
        self.label_target.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_target.setObjectName("PathLabel")
        sbox.addWidget(self.label_target)
        self.btn_target = QPushButton("전사자료 폴더 선택")
        self.btn_target.setProperty("uiRole", "side")
        sbox.addWidget(self.btn_target)

        self.btn_load_files = QPushButton("MP3 파일 목록 불러오기")
        self.btn_load_files.setProperty("uiRole", "side")
        sbox.addWidget(self.btn_load_files)
        left.addWidget(settings)
        self.group_settings = settings

        options = QGroupBox("Options")
        options.setObjectName("SidebarSection")
        options.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        obox = QVBoxLayout(options)
        obox.setContentsMargins(14, 16, 14, 12)
        obox.setSpacing(6)
        self.chk_notify_each_file = QCheckBox("파일별 완료 알림 켜기")
        self.chk_notify_total = QCheckBox("전체 완료 알림 켜기")
        self.shutdown_checkbox = QCheckBox("전체 전사 완료 후 컴퓨터 종료")
        self.chk_notify_each_file.setChecked(True)
        self.chk_notify_total.setChecked(True)
        obox.addWidget(self.chk_notify_each_file)
        obox.addWidget(self.chk_notify_total)
        obox.addWidget(self.shutdown_checkbox)
        left.addWidget(options)
        self.group_options = options

        logs = QGroupBox("Execution Log")
        logs.setObjectName("LogsSection")
        logs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lbox = QVBoxLayout(logs)
        lbox.setContentsMargins(14, 16, 14, 12)
        lbox.setSpacing(9)
        self.btn_toggle_log = QPushButton("로그창 보기")
        self.btn_toggle_log.setProperty("uiRole", "logToggle")
        self.btn_toggle_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lbox.addWidget(self.btn_toggle_log)
        self.log_viewer = QTextEdit()
        self.log_viewer.setObjectName("LogViewer")
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setPlaceholderText("[14:20:11] Session started.\\n[14:21:05] Audio engine initialized.")
        self.log_viewer.setMinimumHeight(0)
        self.log_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.log_viewer.setLineWrapMode(QTextEdit.WidgetWidth)
        self.log_viewer.setWordWrapMode(QTextOption.WrapAnywhere)
        self.log_viewer.document().setDocumentMargin(12)
        self.log_viewer.hide()
        lbox.addWidget(self.log_viewer)
        left.addWidget(logs, 1)
        self.group_logs = logs

        dashboard = QGroupBox("진행 대시보드")
        dashboard.setObjectName("DashboardSection")
        dbox = QVBoxLayout(dashboard)
        dbox.setContentsMargins(14, 14, 14, 14)
        dbox.setSpacing(10)

        self.label_status = QLabel("")
        self.label_status.setObjectName("StatusPrimary")
        self.label_status.setWordWrap(False)
        self.label_current_file = QLabel("")
        self.label_current_file.setObjectName("StatusSecondary")
        self.label_current_file.setWordWrap(False)
        self.label_session = QLabel("")
        self.label_session.setObjectName("MetaStatus")
        self.label_session.setWordWrap(False)
        self.label_output_source = QLabel("")
        self.label_output_source.setObjectName("MetaStatus")
        self.label_output_source.setWordWrap(False)

        self.label_total_progress_text = QLabel("0 / 0")
        self.label_total_progress_text.setObjectName("MetricValue")
        self.label_total_progress_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setRange(0, 100)
        self.total_progress_bar.setFixedHeight(15)
        self.label_total_eta = QLabel(ETA_EMPTY_TEXT)
        self.label_total_eta.setObjectName("MetricValue")
        self.label_total_eta.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_current_progress_text = QLabel("0%")
        self.label_current_progress_text.setObjectName("CurrentProgressValue")
        self.label_current_progress_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.current_progress_bar = QProgressBar()
        self.current_progress_bar.setRange(0, 100)
        self.current_progress_bar.setFixedHeight(15)
        self.label_current_eta = QLabel(ETA_EMPTY_TEXT)
        self.label_current_eta.setObjectName("MetricValue")

        top_cards = QHBoxLayout()
        top_cards.setSpacing(10)

        card_status = QFrame()
        card_status.setObjectName("DashboardCard")
        card_status_box = QVBoxLayout(card_status)
        card_status_box.setContentsMargins(14, 12, 14, 12)
        card_status_box.setSpacing(4)
        card_status_title = QLabel("CURRENT STATUS", objectName="DashboardMicroLabel")
        card_status_box.addWidget(card_status_title)
        card_status_box.addWidget(self.label_status)
        top_cards.addWidget(card_status, 3)

        card_progress = QFrame()
        card_progress.setObjectName("DashboardCard")
        card_progress_box = QVBoxLayout(card_progress)
        card_progress_box.setContentsMargins(14, 12, 14, 12)
        card_progress_box.setSpacing(8)
        card_progress_title = QLabel("TOTAL PROGRESS", objectName="DashboardMicroLabel")
        card_progress_box.addWidget(card_progress_title)
        card_progress_box.addWidget(self.label_total_progress_text)
        card_progress_box.addSpacing(2)
        card_progress_box.addWidget(self.total_progress_bar)
        top_cards.addWidget(card_progress, 4)

        card_eta = QFrame()
        card_eta.setObjectName("DashboardCard")
        card_eta_box = QVBoxLayout(card_eta)
        card_eta_box.setContentsMargins(14, 12, 14, 12)
        card_eta_box.setSpacing(4)
        card_eta_title = QLabel("REMAINING TIME", objectName="DashboardMicroLabel")
        card_eta_box.addWidget(card_eta_title)
        card_eta_box.addWidget(self.label_total_eta)
        top_cards.addWidget(card_eta, 3)
        dbox.addLayout(top_cards)

        card_current = QFrame()
        card_current.setObjectName("DashboardCard")
        card_current_box = QVBoxLayout(card_current)
        card_current_box.setContentsMargins(14, 12, 14, 12)
        card_current_box.setSpacing(8)
        card_current_title = QLabel("CURRENT FILE", objectName="DashboardMicroLabel")
        card_current_box.addWidget(card_current_title)
        card_current_box.addWidget(self.label_current_file)

        current_row = QHBoxLayout()
        current_row.setContentsMargins(0, 2, 0, 0)
        current_row.setSpacing(12)
        current_progress_col = QVBoxLayout()
        current_progress_col.setSpacing(10)
        current_progress_label = QLabel("CURRENT PROGRESS", objectName="DashboardMicroLabel")
        current_progress_col.addWidget(current_progress_label)
        current_progress_col.addWidget(self.label_current_progress_text)
        current_progress_col.addSpacing(6)
        current_progress_col.addWidget(self.current_progress_bar)
        current_row.addLayout(current_progress_col, 3)

        current_eta_col = QVBoxLayout()
        current_eta_col.setSpacing(4)
        current_eta_label = QLabel("CURRENT ETA", objectName="DashboardMicroLabel")
        current_eta_col.addWidget(current_eta_label)
        self.label_current_eta.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        current_eta_col.addWidget(self.label_current_eta)
        current_eta_col.addStretch(1)
        current_row.addLayout(current_eta_col, 1)
        card_current_box.addLayout(current_row)
        dbox.addWidget(card_current)

        dbox.addWidget(self.label_session)
        dbox.addWidget(self.label_output_source)
        right.addWidget(dashboard)

        files = QGroupBox("MP3 파일 목록")
        files.setObjectName("FileQueueSection")
        files.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        fbox = QVBoxLayout(files)
        fbox.setContentsMargins(14, 16, 14, 14)
        fbox.setSpacing(8)
        self.label_file_count = QLabel("불러온 MP3 파일 수: 0개")
        self.label_file_count.setObjectName("SectionValue")
        fbox.addWidget(self.label_file_count)
        self.label_files_helper = QLabel("여러 파일을 선택해 이동/전사를 빠르게 시작할 수 있습니다.", objectName="HelperText")
        fbox.addWidget(self.label_files_helper)
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list_widget.setMinimumHeight(96)
        self.file_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.file_list_widget.setTextElideMode(Qt.ElideMiddle)
        self.file_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.file_list_widget.setUniformItemSizes(True)
        self.file_list_widget.setAlternatingRowColors(True)
        self.file_list_widget.setSpacing(4)
        fbox.addWidget(self.file_list_widget, 1)
        right.addWidget(files, 1)
        self.group_files = files

        controls = QGroupBox("실행 제어")
        controls.setObjectName("ControlSection")
        controls.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cbox = QVBoxLayout(controls)
        cbox.setContentsMargins(14, 14, 14, 14)
        cbox.setSpacing(8)
        self.label_controls_helper = QLabel("시작 버튼으로 전사를 실행하고, 필요하면 즉시 중지할 수 있습니다.", objectName="HelperText")
        cbox.addWidget(self.label_controls_helper)
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.btn_move_and_transcribe = QPushButton("선택한 MP3 이동 후 전사 시작")
        self.btn_move_and_transcribe.setProperty("uiRole", "controlSecondary")
        self.btn_transcribe_target = QPushButton("전사자료 폴더 전체 전사 시작")
        self.btn_transcribe_target.setProperty("uiRole", "controlPrimary")
        row1.addWidget(self.btn_move_and_transcribe)
        row1.addWidget(self.btn_transcribe_target)
        cbox.addLayout(row1)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.btn_move_files = QPushButton("선택한 MP3를 전사자료 폴더로 이동")
        self.btn_move_files.setProperty("uiRole", "controlGhost")
        self.btn_stop_now = QPushButton("즉시 중지")
        self.btn_stop_now.setProperty("uiRole", "controlDanger")
        self.btn_stop_now.setObjectName("Danger")
        self.btn_stop_now.setEnabled(False)
        row2.addWidget(self.btn_move_files, 1)
        row2.addWidget(self.btn_stop_now, 1)
        cbox.addLayout(row2)
        right.addWidget(controls)
        right.setStretch(0, 0)
        right.setStretch(1, 1)
        right.setStretch(2, 0)

        self._apply_status_and_meta_labels()
        self._refresh_path_labels()

        self.btn_download.clicked.connect(self.select_download_folder)
        self.btn_target.clicked.connect(self.select_target_folder)
        self.btn_load_files.clicked.connect(self.load_mp3_files)
        self.btn_move_files.clicked.connect(self.move_selected_files)
        self.btn_move_and_transcribe.clicked.connect(self.move_selected_files_and_start_transcribe)
        self.btn_transcribe_target.clicked.connect(self.start_transcribe_on_target_folder)
        self.btn_stop_now.clicked.connect(self.request_immediate_stop)
        self.btn_toggle_log.clicked.connect(self.toggle_log_view)

    def apply_styles(self):
        palette = {
            "background": "#faf8ff",
            "sidebar_bg": "#f4f3fa",
            "main_bg": "#faf8ff",
            "panel": "#ffffff",
            "panel_alt": "#f7f8ff",
            "panel_inner": "#eef1f8",
            "border": "#d6dcea",
            "divider": "#e7eaf2",
            "title_text": "#00236f",
            "section_text": "#1c2f53",
            "body_text": "#1a1b21",
            "muted_text": "#5a6478",
            "value_text": "#0f235a",
            "metric_label_text": "#5c6b86",
            "path_text": "#2b3c61",
            "log_bg": "#07153a",
            "log_text": "#c8d8ff",
            "log_accent": "#3de0bc",
            "button_text": "#1f2f4d",
            "accent_button": "#f4f6fd",
            "accent_button_hover": "#e8edf9",
            "button_disabled_bg": "#eceef5",
            "button_disabled_border": "#d7dce7",
            "button_disabled_text": "#9aa3b5",
            "selected_row": "#dbe5ff",
            "progress_bg": "#dae3f4",
            "progress_border": "#c4d0e6",
            "progress_chunk": "#002d8b",
            "title_hint": "#5e6c89",
            "danger_button": "#fff1f0",
            "danger_button_hover": "#ffe5e1",
            "danger_border": "#df7f74",
            "primary_button": "#002d8b",
            "primary_button_hover": "#183f9b",
            "on_primary": "#ffffff",
            "chip_bg": "#e7edfb",
        }

        self.setStyleSheet(
            f"""
            QWidget {{
                font-family:"Malgun Gothic", "맑은 고딕", "NanumBarunGothic", "NanumGothic", "Segoe UI", Arial, sans-serif;
                color:{palette["body_text"]};
                font-size:13px;
            }}
            QWidget#RootWindow {{
                background:{palette["background"]};
            }}
            QFrame#SidebarPane {{
                background:{palette["sidebar_bg"]};
                border:1px solid {palette["border"]};
                border-radius:14px;
            }}
            QFrame#MainPane {{
                background:transparent;
                border:none;
            }}
            QLabel {{
                font-size:13px;
                color:{palette["body_text"]};
                background:transparent;
            }}
            QFrame#TitleCard {{
                border:1px solid {palette["border"]};
                border-radius:12px;
                background:{palette["panel"]};
            }}
            QGroupBox {{
                border:1px solid {palette["border"]};
                border-radius:10px;
                margin-top:10px;
                padding-top:20px;
                background:{palette["panel"]};
                font-size:15px;
                color:{palette["section_text"]};
            }}
            QGroupBox::title {{
                subcontrol-origin: padding;
                subcontrol-position: top left;
                left:0px;
                padding:0 2px 4px 2px;
                color:{palette["section_text"]};
                background:transparent;
            }}
            QGroupBox#SidebarSection {{
                background:{palette["panel_alt"]};
            }}
            QGroupBox#DashboardSection,
            QGroupBox#FileQueueSection,
            QGroupBox#ControlSection {{
                background:{palette["panel"]};
            }}
            QGroupBox#LogsSection {{
                margin-top:10px;
                padding-top:22px;
                background:{palette["log_bg"]};
                border-color:#10255f;
            }}
            QGroupBox#LogsSection::title {{
                color:{palette["log_text"]};
                left:0px;
                padding:0 2px 4px 2px;
                background:transparent;
            }}
            QFrame#DashboardCard {{
                border:1px solid {palette["divider"]};
                border-radius:10px;
                background:{palette["panel_alt"]};
            }}
            #DashboardMicroLabel {{
                color:{palette["metric_label_text"]};
                font-size:12px;
                letter-spacing:0.6px;
            }}
            #TitleText {{
                font-size:31px;
                color:{palette["title_text"]};
            }}
            #TitleHint {{
                color:{palette["title_hint"]};
                font-size:12px;
                letter-spacing:1.0px;
            }}
            #PathLabel {{
                border:1px solid {palette["divider"]};
                border-radius:8px;
                padding:10px 12px 10px 12px;
                background:{palette["panel_inner"]};
                color:{palette["path_text"]};
                font-size:14px;
            }}
            #SideHelperText {{
                color:{palette["muted_text"]};
                font-size:13px;
                padding:2px 0 4px 0;
            }}
            #HelperText {{
                color:{palette["muted_text"]};
                font-size:13px;
            }}
            #SectionValue {{
                color:{palette["value_text"]};
                font-size:14px;
            }}
            #StatusPrimary {{
                font-size:24px;
                color:{palette["value_text"]};
            }}
            #StatusSecondary {{
                font-size:16px;
                color:{palette["section_text"]};
            }}
            #MetaStatus {{
                font-size:13px;
                color:{palette["muted_text"]};
            }}
            #MetricTitle {{
                font-size:13px;
                color:{palette["metric_label_text"]};
            }}
            #MetricValue {{
                font-size:29px;
                color:{palette["value_text"]};
            }}
            #CurrentProgressValue {{
                font-size:24px;
                color:{palette["value_text"]};
                padding-bottom:2px;
            }}
            QPushButton {{
                border:1px solid {palette["border"]};
                border-radius:6px;
                padding:9px 12px 10px 12px;
                background:{palette["accent_button"]};
                color:{palette["button_text"]};
                font-size:13px;
                text-align:center;
            }}
            QPushButton[uiRole="side"] {{
                padding:9px 12px 10px 12px;
            }}
            QPushButton[uiRole="controlPrimary"] {{
                min-height:40px;
                background:{palette["primary_button"]};
                color:{palette["on_primary"]};
                border-color:{palette["primary_button"]};
            }}
            QPushButton[uiRole="controlPrimary"]:hover {{
                background:{palette["primary_button_hover"]};
            }}
            QPushButton[uiRole="controlSecondary"] {{
                min-height:40px;
                background:{palette["panel"]};
                border-color:{palette["primary_button"]};
                color:{palette["primary_button"]};
            }}
            QPushButton[uiRole="controlSecondary"]:hover {{
                background:{palette["accent_button_hover"]};
            }}
            QPushButton[uiRole="controlGhost"] {{
                min-height:40px;
                background:{palette["accent_button"]};
            }}
            QPushButton[uiRole="controlDanger"] {{
                min-height:40px;
                background:{palette["danger_button"]};
                color:#9f1616;
                border-color:{palette["danger_border"]};
            }}
            QPushButton[uiRole="controlDanger"]:hover {{
                background:{palette["danger_button_hover"]};
            }}
            QPushButton[uiRole="logToggle"] {{
                padding:2px 12px 2px 12px;
                font-size:13px;
                min-height:34px;
                border-color:#263f81;
                color:{palette["log_text"]};
                background:#0d2256;
            }}
            QPushButton[uiRole="logToggle"]:hover {{
                background:#163170;
            }}
            QPushButton:hover {{ background:{palette["accent_button_hover"]}; }}
            QPushButton:disabled {{
                background:{palette["button_disabled_bg"]};
                border-color:{palette["button_disabled_border"]};
                color:#7a859a;
            }}
            QListWidget {{
                border:1px solid {palette["divider"]};
                border-radius:10px;
                background:{palette["panel"]};
                font-size:15px;
                font-weight:500;
                color:{palette["body_text"]};
                padding:6px;
                alternate-background-color:{palette["panel_alt"]};
            }}
            QListWidget::item {{
                padding:8px 10px;
                border-radius:6px;
            }}
            QListWidget::item:selected {{
                background:{palette["selected_row"]};
                color:{palette["title_text"]};
            }}
            QTextEdit#LogViewer {{
                border:1px solid #1c3472;
                border-radius:10px;
                background:#081a43;
                font-family:"Consolas", "D2Coding", "Malgun Gothic", monospace;
                font-size:14px;
                color:{palette["log_accent"]};
                padding:10px;
                selection-background-color:#1c3472;
            }}
            QCheckBox {{
                font-size:13px;
                color:{palette["section_text"]};
                font-weight:400;
                spacing:8px;
                padding:3px 0;
                background:transparent;
            }}
            QCheckBox::indicator {{
                width:16px;
                height:16px;
                border:1px solid {palette["border"]};
                border-radius:4px;
                background:{palette["panel"]};
            }}
            QCheckBox::indicator:checked {{
                background:{palette["primary_button"]};
                border-color:{palette["primary_button"]};
            }}
            QProgressBar {{
                border:1px solid {palette["progress_border"]};
                border-radius:6px;
                background:{palette["progress_bg"]};
                text-align:center;
                min-height:14px;
                color:{palette["value_text"]};
                font-size:11px;
                font-weight:600;
            }}
            QProgressBar::chunk {{
                border-radius:5px;
                background:{palette["progress_chunk"]};
            }}
            """
        )

    def apply_typography_fit_defaults(self):
        # 한글 baseline 잘림 방지를 위해 텍스트 높이에 맞춰 최소 높이를 보정한다.
        buttons = [
            self.btn_download,
            self.btn_target,
            self.btn_load_files,
            self.btn_toggle_log,
            self.btn_move_files,
            self.btn_move_and_transcribe,
            self.btn_transcribe_target,
            self.btn_stop_now,
        ]
        for btn in buttons:
            min_h = btn.fontMetrics().height() + 14
            btn.setMinimumHeight(max(btn.minimumHeight(), min_h))

        for lbl in [self.label_download, self.label_target]:
            line_h = lbl.fontMetrics().lineSpacing()
            box_h = max(48, line_h * 2 + 22, lbl.sizeHint().height())
            lbl.setMinimumHeight(box_h)
            lbl.setMaximumHeight(box_h)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        hint_min_h = self.label_settings_hint.fontMetrics().lineSpacing() + 4
        self.label_settings_hint.setMinimumHeight(max(self.label_settings_hint.minimumHeight(), hint_min_h))

        title_h = self.label_title_text.fontMetrics().lineSpacing() + 8
        self.label_title_text.setMinimumHeight(max(self.label_title_text.minimumHeight(), title_h))
        hint_h = self.label_title_hint.fontMetrics().lineSpacing() + 2
        self.label_title_hint.setMinimumHeight(max(self.label_title_hint.minimumHeight(), hint_h))

        for metric_label in (
            self.label_total_progress_text,
            self.label_total_eta,
            self.label_current_progress_text,
            self.label_current_eta,
        ):
            extra_pad = 12 if metric_label is self.label_current_progress_text else 6
            metric_h = metric_label.fontMetrics().lineSpacing() + extra_pad
            metric_label.setMinimumHeight(max(metric_label.minimumHeight(), metric_h))

        # 로그 토글 버튼은 열림/닫힘 상태 모두에서 baseline 잘림이 없도록 높이를 고정한다.
        log_btn_h = max(self.btn_toggle_log.sizeHint().height(), self.btn_toggle_log.fontMetrics().lineSpacing() + 16, 36)
        self.btn_toggle_log.setMinimumHeight(log_btn_h)
        self.btn_toggle_log.setMaximumHeight(log_btn_h)

        self.apply_left_section_layout_constraints()

    def apply_font_hierarchy(self):
        def _set_weight(widget, weight: int):
            f = QFont(widget.font())
            try:
                f.setWeight(QFont.Weight(weight))
            except Exception:
                # Qt enum 변환 실패 시 가장 가까운 표준 weight로 보정한다.
                if weight >= 800:
                    f.setWeight(QFont.Weight.ExtraBold)
                elif weight >= 700:
                    f.setWeight(QFont.Weight.Bold)
                elif weight >= 600:
                    f.setWeight(QFont.Weight.DemiBold)
                elif weight >= 500:
                    f.setWeight(QFont.Weight.Medium)
                else:
                    f.setWeight(QFont.Weight.Normal)
            widget.setFont(f)

        _set_weight(self.label_title_text, 550)
        _set_weight(self.label_title_hint, 500)

        for group in (self.group_settings, self.group_options, self.group_logs):
            _set_weight(group, 550)

        for btn in (
            self.btn_download,
            self.btn_target,
            self.btn_load_files,
            self.btn_toggle_log,
            self.btn_move_files,
            self.btn_move_and_transcribe,
            self.btn_transcribe_target,
            self.btn_stop_now,
        ):
            _set_weight(btn, 500)

        for lbl in (
            self.label_settings_hint,
            self.label_files_helper,
            self.label_controls_helper,
            self.label_session,
            self.label_output_source,
        ):
            _set_weight(lbl, 450)

        for lbl in (self.label_download, self.label_target):
            _set_weight(lbl, 500)

        _set_weight(self.label_status, 550)
        _set_weight(self.label_current_file, 550)
        _set_weight(self.label_total_progress_text, 600)
        _set_weight(self.label_total_eta, 550)
        _set_weight(self.label_current_progress_text, 600)
        _set_weight(self.label_current_eta, 550)
        _set_weight(self.label_file_count, 550)
        _set_weight(self.log_viewer, 400)
        self.log_viewer.document().setDefaultFont(self.log_viewer.font())

        for lbl in self.findChildren(QLabel):
            if lbl.objectName() == "MetricTitle":
                _set_weight(lbl, 600)

        for cb in (self.chk_notify_each_file, self.chk_notify_total, self.shutdown_checkbox):
            _set_weight(cb, 500)

        log_font = QFont(self.log_viewer.font())
        try:
            log_font.setFamilies(["Consolas", "D2Coding", "Malgun Gothic", "맑은 고딕"])
        except Exception:
            pass
        self.log_viewer.setFont(log_font)
        self.log_viewer.document().setDefaultFont(log_font)

    def apply_left_section_layout_constraints(self):
        # 설정/옵션은 안정 영역으로 고정하고, 실행 로그만 남는 공간을 쓰도록 분리한다.
        for section in (self.group_title, self.group_settings, self.group_options):
            h = section.sizeHint().height()
            section.setMinimumHeight(h)
            section.setMaximumHeight(h)

    def _elide_for_label(self, label: QLabel, text: str, mode=Qt.ElideRight) -> str:
        available = max(120, label.width() - 14)
        return label.fontMetrics().elidedText(text, mode, available)

    def _set_elided_label_text(self, label: QLabel, text: str, mode=Qt.ElideRight):
        elided = self._elide_for_label(label, text, mode)
        label.setText(elided)
        label.setToolTip(text if elided != text else "")

    def _set_status_text(self, text: str):
        self._status_full_text = text
        self._set_elided_label_text(self.label_status, text)

    def _set_current_file_text(self, text: str):
        self._current_file_full_text = text
        self._set_elided_label_text(self.label_current_file, text)

    def _set_session_text(self, text: str):
        self._session_full_text = text
        self._set_elided_label_text(self.label_session, text)

    def _set_output_text(self, text: str):
        self._output_full_text = text
        self._set_elided_label_text(self.label_output_source, text)

    def _set_eta_value(self, label: QLabel, text: str):
        # 값 유형과 무관하게 ETA 셀 중앙 정렬 기준을 고정한다.
        label.setAlignment(Qt.AlignCenter)
        label.setIndent(0)
        label.setText(text)

    def _apply_status_and_meta_labels(self):
        self._set_status_text(self._status_full_text)
        self._set_current_file_text(self._current_file_full_text)
        self._set_session_text(self._session_full_text)
        self._set_output_text(self._output_full_text)

    def _set_path_label(self, label: QLabel, title: str, path: str):
        available = max(180, label.width() - 24)
        if not path:
            value_text = "아직 선택 안 함"
            label.setToolTip("")
        else:
            value_text = label.fontMetrics().elidedText(path, Qt.ElideMiddle, available)
            label.setToolTip(path if value_text != path else "")
        label.setText(f"{title}:\n{value_text}")

    def _refresh_path_labels(self):
        self._set_path_label(self.label_download, "다운로드 폴더", self.download_folder)
        self._set_path_label(self.label_target, "전사자료 폴더", self.target_folder)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_status_and_meta_labels()
        self._refresh_path_labels()

    def get_base_dir(self) -> str:
        return get_runtime_base_dir()

    def get_auto_transcribe_path(self) -> str:
        base = self.get_base_dir()
        for path in [os.path.join(base, "auto_transcribe.py"), os.path.join(base, "_internal", "auto_transcribe.py")]:
            if os.path.exists(path):
                return path
        return os.path.join(base, "auto_transcribe.py")

    def get_stop_flag_path(self) -> str:
        if not self.target_folder:
            return ""
        return os.path.join(os.path.dirname(self.target_folder), STOP_FLAG_FILENAME)

    def get_session_state_path(self) -> str:
        if not self.target_folder:
            return ""
        return os.path.join(os.path.dirname(self.target_folder), SESSION_STATE_FILENAME)

    def clear_old_stop_flag(self):
        path = self.get_stop_flag_path()
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                self.append_log_text(f"[GUI] stop.flag 삭제 실패: {e}\n")

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = load_runtime_icon()
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.setWindowIcon(icon)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip(APP_DISPLAY_NAME)
        menu = QMenu()
        show_action = QAction("창 열기", self)
        quit_action = QAction("종료", self)
        show_action.triggered.connect(self.restore_from_tray)
        quit_action.triggered.connect(self.quit_application)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def show_tray_message(self, title, message):
        if self.tray_icon.isVisible():
            head = (title or "").strip()
            body = (message or "").strip()
            if head:
                head = f"{APP_DISPLAY_NAME} · {head}"
            else:
                head = APP_DISPLAY_NAME
            try:
                self.tray_icon.showMessage(head, body, self.tray_icon.icon(), 5000)
            except TypeError:
                self.tray_icon.showMessage(head, body, QSystemTrayIcon.Information, 5000)

    def restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore_from_tray()

    def quit_application(self):
        if self.process is not None and self.process.state() != QProcess.NotRunning:
            if QMessageBox.question(self, "종료 확인", "전사가 진행 중입니다. 그래도 종료하시겠습니까?") != QMessageBox.Yes:
                return
        self.tray_icon.hide()
        QApplication.instance().quit()

    def toggle_log_view(self):
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_viewer.show()
            self.btn_toggle_log.setText("로그창 숨기기")
        else:
            self.log_viewer.hide()
            self.btn_toggle_log.setText("로그창 보기")

    def set_transcribe_buttons_enabled(self, enabled: bool):
        self.btn_download.setEnabled(enabled)
        self.btn_target.setEnabled(enabled)
        self.btn_load_files.setEnabled(enabled)
        self.btn_move_files.setEnabled(enabled)
        self.btn_move_and_transcribe.setEnabled(enabled)
        self.btn_transcribe_target.setEnabled(enabled)
        self.btn_stop_now.setEnabled(not enabled)

    def translate_session_status(self, status: str) -> str:
        mapping = {
            "running": "진행 중",
            "completed": "완료",
            "stopped": "중지됨",
            "stopped_by_user": "사용자 중지",
            "crashed": "비정상 종료",
            "corrupt_session": "세션 손상",
        }
        return mapping.get(status, status or "없음")

    def load_session_state_safely(self, path: str):
        retries = 3
        for attempt in range(1, retries + 1):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    return json.load(f)
            except (PermissionError, json.JSONDecodeError):
                if attempt < retries:
                    time.sleep(0.1 * attempt)
                    continue
                raise

    def update_session_label(self):
        path = self.get_session_state_path()
        if not path or not os.path.exists(path):
            self._set_session_text("세션 상태: 확인 안 됨")
            return
        try:
            state = self.load_session_state_safely(path)
            status = self.translate_session_status(state.get("status", "없음"))
            cur = state.get("current_file", "")
            self._set_session_text(f"세션 상태: {status}" + (f" / 마지막 파일: {cur}" if cur else ""))
        except Exception:
            self._set_session_text("세션 상태: 읽기 실패")

    def select_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "다운로드 폴더 선택")
        if folder:
            self.download_folder = folder
            self._refresh_path_labels()
            self.file_list_widget.clear()
            self.label_file_count.setText("불러온 MP3 파일 수: 0개")

    def select_target_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "전사자료 폴더 선택")
        if folder:
            self.target_folder = folder
            self._refresh_path_labels()
            self.update_session_label()

    def load_mp3_files(self, show_empty_message=True):
        if not self.download_folder:
            QMessageBox.warning(self, "경고", "먼저 다운로드 폴더를 선택해 주세요.")
            return
        self.file_list_widget.clear()
        try:
            files = sorted([x for x in os.listdir(self.download_folder) if x.lower().endswith(".mp3")])
            for name in files:
                item = QListWidgetItem(name)
                item.setToolTip(name)
                self.file_list_widget.addItem(item)
            self.label_file_count.setText(f"불러온 MP3 파일 수: {len(files)}개")
            if not files and show_empty_message:
                QMessageBox.information(self, "알림", "선택한 폴더에서 MP3 파일을 찾지 못했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일 목록을 불러오지 못했습니다.\n\n{e}")

    def move_selected_files_core(self):
        if not self.download_folder:
            QMessageBox.warning(self, "경고", "먼저 다운로드 폴더를 선택해 주세요.")
            return None
        if not self.target_folder:
            QMessageBox.warning(self, "경고", "먼저 전사자료 폴더를 선택해 주세요.")
            return None
        items = self.file_list_widget.selectedItems()
        if not items:
            QMessageBox.warning(self, "경고", "이동할 MP3 파일을 먼저 선택해 주세요.")
            return None
        moved, skipped, failed = 0, 0, []
        for item in items:
            original = item.text()
            clean = remove_page_suffix(original)
            src = os.path.join(self.download_folder, original)
            dst = os.path.join(self.target_folder, clean)
            try:
                if os.path.exists(dst):
                    skipped += 1
                    continue
                shutil.move(src, dst)
                moved += 1
            except Exception as e:
                failed.append(f"{original} -> {e}")
        self.load_mp3_files(show_empty_message=False)
        return {"moved_count": moved, "skipped_count": skipped, "failed_files": failed}

    def move_selected_files(self):
        result = self.move_selected_files_core()
        if result is None:
            return
        msg = (
            "선택한 MP3 파일 이동이 완료되었습니다.\n\n"
            f"이동 성공: {result['moved_count']}개\n"
            f"이미 존재하여 건너뜀: {result['skipped_count']}개\n"
            f"이동 실패: {len(result['failed_files'])}개"
        )
        if result["failed_files"]:
            msg += "\n\n실패 파일:\n" + "\n".join(result["failed_files"][:10])
        QMessageBox.information(self, "이동 결과", msg)

    def move_selected_files_and_start_transcribe(self):
        result = self.move_selected_files_core()
        if result is None:
            return
        if result["moved_count"] <= 0:
            QMessageBox.information(self, "알림", "이동된 파일이 없어 전사를 시작하지 않았습니다.")
            return
        self.run_transcribe_process()

    def start_transcribe_on_target_folder(self):
        self.run_transcribe_process()

    def _output_triplet(self, mp3_path: str):
        base = os.path.splitext(remove_page_suffix(os.path.basename(mp3_path)))[0]
        parent = os.path.dirname(mp3_path)
        return [os.path.join(parent, base + ".txt"), os.path.join(parent, base + ".json"), os.path.join(parent, base + ".srt")]

    def _output_triplet_looks_complete(self, mp3_path: str) -> bool:
        txt_path, json_path, srt_path = self._output_triplet(mp3_path)
        for path in (txt_path, json_path, srt_path):
            if not os.path.exists(path):
                return False
        for path in (txt_path, json_path):
            try:
                if os.path.getsize(path) <= 0:
                    return False
            except OSError:
                return False
        try:
            with open(json_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return False
            if "text" not in data or "segments" not in data:
                return False
        except Exception:
            return False
        return True

    def count_target_mp3_files(self) -> int:
        if not self.target_folder or not os.path.isdir(self.target_folder):
            return 0
        count = 0
        for name in os.listdir(self.target_folder):
            if not name.lower().endswith(".mp3"):
                continue
            mp3_path = os.path.join(self.target_folder, name)
            if not self._output_triplet_looks_complete(mp3_path):
                count += 1
        return count

    def prepare_progress_tracking(self):
        self.stdout_buffer = ""
        self.stderr_buffer = ""
        self.notified_success_files.clear()
        self.total_complete_notified = False
        self.completed_files.clear()
        self.total_target_mp3_files = self.count_target_mp3_files()
        self.stop_requested = False
        self.pending_kill = False
        self.stop_terminate_sent = False
        self.last_current_percent = 0
        self.current_file_name = ""
        self.current_file_started_at = None
        self.current_eta_seconds = None
        self.total_eta_seconds = None
        self.file_duration_history.clear()
        self.log_viewer.clear()
        self.label_status.setText("현재 상태: 전사 시작 요청")
        self.label_current_file.setText("현재 처리 중 파일: 확인 중...")
        self.update_total_progress_display()
        self.update_current_file_progress(0, force=True)
        self.update_eta_labels(initial=True)

    def update_total_progress_display(self):
        total = max(0, int(self.total_target_mp3_files))
        done = min(len(self.completed_files), total) if total > 0 else 0
        self.label_total_progress_text.setText(f"{done} / {total}")
        self.total_progress_bar.setValue(int(done * 100 / total) if total > 0 else 0)

    def update_current_file_progress(self, percent: int, force=False):
        p = max(0, min(100, int(percent)))
        if not force and p < self.last_current_percent:
            return
        self.last_current_percent = p
        self.current_progress_bar.setValue(p)
        self.label_current_progress_text.setText(f"{p}%")
        if self.current_file_started_at and 0 < p < 100:
            elapsed = max(0.0, time.time() - self.current_file_started_at)
            est = max(0.0, (elapsed / (p / 100.0)) - elapsed)
            self.current_eta_seconds = est if self.current_eta_seconds is None else self.current_eta_seconds * 0.7 + est * 0.3
            self._set_eta_value(self.label_current_eta, f"{format_seconds(self.current_eta_seconds)}")
        elif p >= 100:
            self.current_eta_seconds = 0
            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
        elif self.current_file_name:
            self.current_eta_seconds = None
            self._set_eta_value(self.label_current_eta, "계산 중...")
        else:
            self.current_eta_seconds = None
            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
        self.update_total_eta_label()

    def update_total_eta_label(self):
        total = max(0, int(self.total_target_mp3_files))
        done = len(self.completed_files)
        if total <= 0 or (done >= total and not self.current_file_name):
            self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)
            self.total_eta_seconds = None
            return
        running = 1 if self.current_file_name else 0
        remain_files = max(0, total - done - running)
        has_avg = bool(self.file_duration_history)
        if self.current_file_name and self.current_eta_seconds is None and not has_avg:
            self._set_eta_value(self.label_total_eta, "계산 중...")
            self.total_eta_seconds = None
            return
        if not self.current_file_name and not has_avg and remain_files > 0:
            self._set_eta_value(self.label_total_eta, "계산 중...")
            self.total_eta_seconds = None
            return
        avg = statistics.mean(self.file_duration_history) if has_avg else 0.0
        cur = self.current_eta_seconds or 0.0
        est = cur + (remain_files * avg)
        self.total_eta_seconds = est if self.total_eta_seconds is None else self.total_eta_seconds * 0.7 + est * 0.3
        self._set_eta_value(self.label_total_eta, f"{format_seconds(self.total_eta_seconds)}")

    def update_eta_labels(self, initial=False):
        if initial:
            if self.total_target_mp3_files <= 0:
                self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)
                self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
            else:
                self._set_eta_value(self.label_total_eta, "계산 중...")
                self._set_eta_value(self.label_current_eta, "계산 중...")
            return
        self.update_total_eta_label()

    def refresh_eta_tick(self):
        if self.process is None or self.process.state() == QProcess.NotRunning:
            return
        if self.current_file_name:
            self.update_current_file_progress(self.last_current_percent, force=True)
        else:
            self.update_total_eta_label()

    def decode_process_data(self, raw: bytes) -> str:
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode("utf-8", errors="ignore")

    def is_progress_only_line(self, line: str) -> bool:
        return bool(re.match(r"^\d{1,3}%\|", line.strip()))

    def append_log_text(self, text: str):
        if not text:
            return
        self.log_viewer.moveCursor(QTextCursor.End)
        self.log_viewer.insertPlainText(text)
        self.log_viewer.moveCursor(QTextCursor.End)

    def parse_stdout_progress(self, text: str):
        matches = re.findall(r"(\d{1,3})%\|", text)
        if matches:
            self.update_current_file_progress(max(int(x) for x in matches))

    def _consume_chunk(self, attr: str, chunk: str, stdout: bool):
        buf = getattr(self, attr) + chunk
        lines = buf.splitlines(keepends=True)
        rem = ""
        if lines and not lines[-1].endswith(("\n", "\r")):
            rem = lines.pop()
        setattr(self, attr, rem)
        for line in lines:
            line = line.rstrip("\r\n")
            if not line:
                continue
            if stdout:
                self.parse_stdout_progress(line)
                if self.process_event_line(line):
                    continue
            if not self.is_progress_only_line(line):
                self.append_log_text(line + "\n")

    def handle_process_stdout(self):
        if self.process is None:
            return
        raw = bytes(self.process.readAllStandardOutput())
        if raw:
            self._consume_chunk("stdout_buffer", self.decode_process_data(raw), True)

    def handle_process_stderr(self):
        if self.process is None:
            return
        raw = bytes(self.process.readAllStandardError())
        if raw:
            self._consume_chunk("stderr_buffer", self.decode_process_data(raw), False)

    def process_event_line(self, line: str) -> bool:
        if not line.startswith("[EVENT] "):
            return False
        body = line[len("[EVENT] "):]
        parts = body.split("|")
        evt, payload = parts[0], parts[1:]
        if evt == "TOTAL_FILES":
            discovered = int(payload[0]) if len(payload) >= 1 and payload[0].isdigit() else 0
            skipped = int(payload[1]) if len(payload) >= 2 and payload[1].isdigit() else 0
            target = int(payload[2]) if len(payload) >= 3 and payload[2].isdigit() else 0
            self.total_target_mp3_files = target
            self.append_log_text(f"[GUI] 발견된 전체 mp3 수: {discovered}\n")
            self.append_log_text(f"[GUI] 기존 결과물 존재로 스킵할 파일 수: {skipped}\n")
            self.append_log_text(f"[GUI] 이번 실행 실제 처리 대상 수: {target}\n")
            self.update_total_progress_display()
            self.update_eta_labels(initial=True)
            if self.total_target_mp3_files <= 0:
                self.label_status.setText("현재 상태: 이번 실행에서 처리할 파일이 없습니다")
        elif evt == "FILE_INDEX":
            cur_idx = int(payload[0]) if len(payload) >= 1 and payload[0].isdigit() else 0
            total = int(payload[1]) if len(payload) >= 2 and payload[1].isdigit() else self.total_target_mp3_files
            name = payload[2] if len(payload) >= 3 else "알 수 없음"
            self.current_file_name = name
            self.current_file_started_at = time.time()
            self.current_eta_seconds = None
            if total > 0 and cur_idx > 0:
                self.label_status.setText(f"현재 상태: 전사 진행 중 ({cur_idx}/{total})")
            else:
                self.label_status.setText("현재 상태: 전사 진행 중")
            self.label_current_file.setText(f"현재 처리 중 파일: {name}")
            self.update_current_file_progress(0, force=True)
            self._set_eta_value(self.label_current_eta, "계산 중...")
            self.update_total_eta_label()
        elif evt == "FILE_DONE":
            name = payload[0] if payload else self.current_file_name
            if name:
                self.completed_files.add(name)
            if self.current_file_started_at:
                d = time.time() - self.current_file_started_at
                if d > 0.4:
                    self.file_duration_history.append(d)
                    if len(self.file_duration_history) > 30:
                        self.file_duration_history.pop(0)
            self.current_file_name = ""
            self.current_file_started_at = None
            self.update_current_file_progress(100, force=True)
            self.label_current_file.setText("현재 처리 중 파일: 없음")
            self.update_total_progress_display()
            self.update_total_eta_label()
            self.update_session_label()
            if self.chk_notify_each_file.isChecked() and name not in self.notified_success_files:
                self.show_tray_message("파일 전사 완료", f"{name} 전사가 완료되었습니다.")
                self.notified_success_files.add(name)
        elif evt == "FILE_SKIP":
            name = payload[0] if payload else "알 수 없음"
            self.label_status.setText(f"현재 상태: 기존 결과 존재로 건너뜀 ({name})")
        elif evt == "STOPPED":
            self.label_status.setText("현재 상태: 사용자 중지 요청 감지")
        elif evt == "ALL_STOPPED":
            self.label_status.setText("현재 상태: 즉시 중지 완료")
            self.label_current_file.setText("현재 처리 중 파일: 없음")
            self.current_file_name = ""
            self.current_file_started_at = None
            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
            self.update_total_eta_label()
            self.update_session_label()
        elif evt == "ALL_DONE":
            self.label_status.setText("현재 상태: 전사 완료")
            self.label_current_file.setText("현재 처리 중 파일: 없음")
            self.current_file_name = ""
            self.current_file_started_at = None
            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
            self.update_total_progress_display()
            self.update_total_eta_label()
            self.update_session_label()
            if self.chk_notify_total.isChecked() and not self.total_complete_notified:
                self.show_tray_message("전사 완료", "전사자료 폴더 전체 전사가 완료되었습니다.")
                self.total_complete_notified = True
            if self.shutdown_checkbox.isChecked():
                self.append_log_text("[GUI] 전체 완료 후 컴퓨터 종료 실행\n")
                self.shutdown_computer()
        elif evt == "PREVIOUS_SESSION_CRASHED":
            self.append_log_text("[GUI] 이전 작업 비정상 종료 흔적 감지\n")
            self.update_session_label()
        elif evt == "PREVIOUS_SESSION_STOPPED_BY_USER":
            self.append_log_text("[GUI] 이전 작업 사용자 중지 이력 감지\n")
            self.update_session_label()
        elif evt == "PREVIOUS_SESSION_CORRUPT":
            self.append_log_text("[GUI] 이전 세션 파일 손상 감지\n")
            self.update_session_label()
        return True

    def run_transcribe_process(self):
        if not self.target_folder:
            QMessageBox.warning(self, "경고", "먼저 전사자료 폴더를 선택해 주세요.")
            return
        auto_path = self.get_auto_transcribe_path()
        if not os.path.exists(auto_path):
            QMessageBox.critical(self, "오류", f"auto_transcribe.py 파일을 찾을 수 없습니다.\n\n확인 경로:\n{auto_path}")
            return
        if self.process is not None:
            QMessageBox.warning(self, "경고", "이미 전사 작업이 진행 중입니다.")
            return
        if self.count_target_mp3_files() <= 0:
            self.total_target_mp3_files = 0
            self.update_total_progress_display()
            self.label_status.setText("현재 상태: 이번 실행에서 처리할 파일이 없습니다")
            self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)
            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
            QMessageBox.information(self, "알림", "이번 실행에서 처리할 파일이 없습니다.")
            return
        self.prepare_progress_tracking()
        self.set_transcribe_buttons_enabled(False)
        self.update_session_label()
        self.process = QProcess(self)
        self.process.setProgram("python" if getattr(sys, "frozen", False) else sys.executable)
        self.process.setArguments([auto_path, self.target_folder])
        self.process.setWorkingDirectory(self.get_base_dir())
        self.process.readyReadStandardOutput.connect(self.handle_process_stdout)
        self.process.readyReadStandardError.connect(self.handle_process_stderr)
        self.process.finished.connect(self.handle_process_finished)
        self.process.start()
        if not self.process.waitForStarted(4000):
            self.process = None
            self.set_transcribe_buttons_enabled(True)
            QMessageBox.critical(self, "오류", "전사 프로세스를 시작하지 못했습니다.")
            return
        self.label_status.setText("현재 상태: 전사 시작됨")
        self.append_log_text(f"[GUI] 전사 시작: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def handle_process_finished(self, exit_code: int, exit_status):
        for name in ("stdout_buffer", "stderr_buffer"):
            tail = getattr(self, name)
            if tail:
                self.append_log_text(tail + "\n")
                setattr(self, name, "")
        self.force_kill_timer.stop()
        normal_exit = exit_status == QProcess.NormalExit
        self.append_log_text(f"[GUI] 프로세스 종료: exit_code={exit_code}, normal={normal_exit}\n")
        self.process = None
        self.set_transcribe_buttons_enabled(True)
        self.update_session_label()
        if self.stop_requested:
            if self.pending_kill:
                self.label_status.setText("현재 상태: 사용자 중지(강제 종료)")
            else:
                self.label_status.setText("현재 상태: 사용자 중지 완료")
            self.append_log_text("[INFO] 사용자 중지 상태로 종료 처리 완료\n")
            self.pending_kill = False
            self.stop_terminate_sent = False
            self.stop_requested = False
            return
        if self.pending_kill:
            self.label_status.setText("현재 상태: 강제 종료됨")
            self.pending_kill = False
            self.stop_terminate_sent = False
            return
        if exit_code != 0 and exit_status == QProcess.NormalExit:
            self.label_status.setText("현재 상태: 오류로 종료")
        self.stop_terminate_sent = False

    def request_immediate_stop(self):
        if self.process is None or self.process.state() == QProcess.NotRunning:
            QMessageBox.information(self, "알림", "진행 중인 전사 작업이 없습니다.")
            return
        stop_flag = self.get_stop_flag_path()
        if not stop_flag:
            QMessageBox.warning(self, "경고", "전사자료 폴더가 설정되지 않았습니다.")
            return
        try:
            with open(stop_flag, "w", encoding="utf-8") as f:
                f.write("stop\n")
            self.stop_requested = True
            self.pending_kill = False
            self.stop_terminate_sent = False
            self.label_status.setText("현재 상태: 중지 요청됨")
            self.append_log_text("[INFO] 사용자 즉시 중지 요청 감지\n")
            self.append_log_text("[GUI] stop.flag 생성 완료 - 즉시 중지 요청\n")
            if self.process is not None and self.process.state() != QProcess.NotRunning:
                self.append_log_text("[WARN] 사용자 중지 요청 후 정상 종료 지연 - terminate 시도\n")
                self.stop_terminate_sent = True
                self.process.terminate()
                self.force_kill_timer.start(8000)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"중지 요청 실패\n\n{e}")

    def force_kill_process(self):
        if self.process is None or self.process.state() == QProcess.NotRunning:
            return
        if not self.stop_requested:
            return
        self.pending_kill = True
        self.append_log_text("[WARN] 사용자 중지 요청 후 terminate 실패 - kill 실행\n")
        self.process.kill()

    def shutdown_computer(self):
        os.system("shutdown /s /t 0")

    def closeEvent(self, event):
        running = self.process is not None and self.process.state() != QProcess.NotRunning
        if running:
            self.hide()
            self.show_tray_message(APP_DISPLAY_NAME, "전사 작업은 계속 진행 중입니다. 프로그램은 시스템 트레이로 이동했습니다.")
            event.ignore()
            return
        self.tray_icon.hide()
        event.accept()


if __name__ == "__main__":
    if "--font-debug" in sys.argv:
        sys.exit(run_font_debug_probe())

    apply_windows_app_identity()
    ensure_start_menu_shortcut()
    try:
        # 배율이 125%/150%일 때 글자 가장자리 흐림을 줄이기 위한 라운딩 정책.
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor)
    except Exception:
        pass
    app = QApplication(sys.argv)
    selected_font_family, font_debug_lines = apply_preferred_ui_font(app)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setDesktopFileName(APP_USER_MODEL_ID)
    icon = load_runtime_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = TranscribeGUI()
    if not icon.isNull():
        window.setWindowIcon(icon)
        window.tray_icon.setIcon(icon)
    for line in font_debug_lines:
        window.append_log_text(line + "\n")
    for line in collect_font_application_diagnostics(window, selected_font_family):
        print(line)
        window.append_log_text(line + "\n")
    window.show()
    sys.exit(app.exec())
