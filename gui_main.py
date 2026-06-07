





import datetime





import json
import mimetypes





import os




from pathlib import Path





import re





import shutil





import statistics





import subprocess
import tempfile
import traceback

try:
    import filename_normalizer as filename_norm
except ImportError:
    filename_norm = None





import sys
import threading
import uuid





import time
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
import webbrowser











class _NullTextStream:
    encoding = "utf-8"
    errors = "replace"

    def write(self, text):
        return len(text) if text is not None else 0

    def flush(self):
        pass

    def isatty(self):
        return False


def _ensure_standard_streams():
    try:
        if getattr(sys, "stdout", None) is None:
            sys.stdout = _NullTextStream()
        if getattr(sys, "stderr", None) is None:
            sys.stderr = _NullTextStream()
    except Exception:
        pass


_ensure_standard_streams()

from PySide6.QtCore import QProcess, QSize, QTimer, Qt, QSettings, QPoint, QObject, Signal





from PySide6.QtGui import (





    QAction,





    QColor,





    QFont,





    QFontDatabase,





    QFontInfo,





    QIcon,





    QPainter,





    QPen,





    QPixmap,





    QTextCharFormat,





    QTextCursor,





    QTextOption,





)





from PySide6.QtWidgets import (





    QApplication,





    QAbstractItemView,





    QCheckBox,





    QComboBox,





    QDialog,





    QDialogButtonBox,





    QFileDialog,





    QFrame,





    QGraphicsDropShadowEffect,





    QGridLayout,





    QGroupBox,





    QHBoxLayout,





    QLabel,





    QLineEdit,





    QMenu,





    QMessageBox,





    QProgressBar,





    QPushButton,





    QHeaderView,





    QProxyStyle,





    QScrollArea,





    QStackedWidget,





    QStyle,





    QStyleOptionButton,





    QSystemTrayIcon,





    QTableWidget,





    QTableWidgetItem,





    QTextEdit,





    QVBoxLayout,





    QWidget,





    QSizePolicy,





)

















STOP_FLAG_FILENAME = "stop.flag"





SESSION_STATE_FILENAME = "transcribe_session_state.json"





ETA_EMPTY_TEXT = "-"
DEFAULT_WHISPER_TIME_RATIO = 0.18
COLAB_CHUNK_SECONDS = 600
COLAB_PROGRESS_FILENAME = "progress.json"





APP_DISPLAY_NAME = "\uC804\uC0AC\uB3C4\uC6B0\uBBF8"





APP_USER_MODEL_ID = "com.codex.transcribehelper"





UI_DEFAULT_FONT_SIZE = 10





SETTINGS_KEY_TARGET_DIR = "ui/target_folder"





SETTINGS_KEY_NOTIFY_EACH = "ui/notify_each_file"





SETTINGS_KEY_NOTIFY_TOTAL = "ui/notify_total"





SETTINGS_KEY_SHUTDOWN_AFTER_DONE = "ui/shutdown_after_done"





SETTINGS_KEY_SHUTDOWN_WAIT_SECONDS = "ui/shutdown_wait_seconds"
SETTINGS_KEY_UPLOAD_DRIVE = "ui/upload_drive"
SETTINGS_KEY_TRANSCRIBE_COURSE = "ui/transcribe_course"
SETTINGS_KEY_TRANSCRIBE_SUBJECT = "ui/transcribe_subject"
SETTINGS_KEY_TRANSCRIBE_COURSE = "ui/transcribe_course"
SETTINGS_KEY_TRANSCRIBE_SUBJECT = "ui/transcribe_subject"
SETTINGS_KEY_TRANSCRIPTION_ENGINE = "ui/transcription_engine"
SETTINGS_KEY_COLAB_URL = "ui/colab_url"

SETTINGS_KEY_DASH_TOTAL_DONE_FILES = "dashboard/total_done_files"
SETTINGS_KEY_DASH_TOTAL_AUDIO_SECONDS = "dashboard/total_audio_seconds"
SETTINGS_KEY_DASH_DAILY_COUNTS_JSON = "dashboard/daily_counts_json"
SETTINGS_KEY_DASH_RECENT_DONE_JSON = "dashboard/recent_done_json"
SETTINGS_KEY_DASH_OBSERVED_AUDIO_SECONDS = "dashboard/observed_audio_seconds"
SETTINGS_KEY_DASH_OBSERVED_PROCESSING_SECONDS = "dashboard/observed_processing_seconds"





SHUTDOWN_WAIT_OPTIONS = (





    (0, "\uC989\uC2DC"),





    (15, "15\uCD08"),





    (30, "30\uCD08"),





)











QUEUE_STATUS_WAITING = "WAITING"





QUEUE_STATUS_PROCESSING = "PROCESSING"





QUEUE_STATUS_DONE = "DONE"





QUEUE_STATUS_FAILED = "FAILED"
QUEUE_STATUS_MOVED = "MOVED"
QUEUE_STATUS_STOP = "STOP"

FOLDER_STATUS_COMPLETE = "완료"
FOLDER_STATUS_INCOMPLETE = "미완료"
FOLDER_STATUS_RESULT_ONLY = "결과만"











QUEUE_STATUS_STYLE = {





    QUEUE_STATUS_WAITING: ("#f1f5f9", "#475569"),





    QUEUE_STATUS_PROCESSING: ("#dbeafe", "#1e40af"),





    QUEUE_STATUS_DONE: ("#dcfce7", "#15803d"),





    QUEUE_STATUS_FAILED: ("#fee2e2", "#b91c1c"),
    QUEUE_STATUS_MOVED: ("#e0e7ff", "#3730a3"),
    QUEUE_STATUS_STOP: ("#ffedd5", "#c2410c"),





}

















class CheckboxIndicatorStyle(QProxyStyle):





    def drawPrimitive(self, element, option, painter, widget=None):





        if element != QStyle.PE_IndicatorCheckBox:





            return super().drawPrimitive(element, option, painter, widget)











        rect = option.rect.adjusted(1, 1, -1, -1)





        checked = bool(option.state & QStyle.State_On)





        enabled = bool(option.state & QStyle.State_Enabled)











        painter.save()





        painter.setRenderHint(QPainter.Antialiasing, True)





        border = QColor("#94a3b8") if enabled else QColor("#cbd5e1")





        fill = QColor("#00236f") if checked and enabled else QColor("#ffffff")





        painter.setPen(QPen(border if not checked else QColor("#00236f"), 1.5))





        painter.setBrush(fill)





        painter.drawRoundedRect(rect, 2, 2)











        if checked:





            p1 = rect.topLeft() + QPoint(rect.width() * 0.22, rect.height() * 0.56)





            p2 = rect.topLeft() + QPoint(rect.width() * 0.45, rect.height() * 0.78)





            p3 = rect.topLeft() + QPoint(rect.width() * 0.80, rect.height() * 0.28)





            pen = QPen(QColor("#ffffff"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)





            painter.setPen(pen)





            painter.drawLine(p1, p2)





            painter.drawLine(p2, p3)





        painter.restore()

















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

















def get_ui_settings_path() -> str:





    fallback_roots = []





    if os.name == "nt":





        appdata = os.environ.get("APPDATA", "").strip()





        if appdata:





            fallback_roots.append(appdata)





        public_root = os.path.join(





            os.environ.get("PUBLIC", r"C:\Users\Public"),





            "Documents",





            "ESTsoft",





            "CreatorTemp",





        )





        fallback_roots.append(public_root)





    fallback_roots.append(get_runtime_base_dir())











    for base in fallback_roots:





        if not base:





            continue





        settings_dir = os.path.join(base, APP_DISPLAY_NAME)





        try:





            os.makedirs(settings_dir, exist_ok=True)





            return os.path.join(settings_dir, "ui_settings.ini")





        except Exception:





            continue





    return os.path.join(get_runtime_base_dir(), "ui_settings.ini")

















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

















def create_brand_symbol_pixmap(size: int = 24) -> QPixmap:





    size = max(18, int(size))





    pix = QPixmap(size, size)





    pix.fill(Qt.transparent)











    p = QPainter(pix)





    p.setRenderHint(QPainter.Antialiasing, True)











    doc_margin = max(2, size // 10)





    doc_w = int(size * 0.66)





    doc_h = int(size * 0.8)





    doc_x = doc_margin + max(1, size // 16)





    doc_y = doc_margin











    p.setPen(QPen(QColor("#1f3f90"), 1.3))





    p.setBrush(QColor("#e9f0ff"))





    p.drawRoundedRect(doc_x, doc_y, doc_w, doc_h, 3, 3)











    p.setPen(QPen(QColor("#1f3f90"), 1.4, Qt.SolidLine, Qt.RoundCap))





    line_x = doc_x + max(4, size // 6)





    for idx in range(3):





        y = doc_y + max(4, size // 5) + (idx * max(4, size // 7))





        p.drawLine(line_x, y, doc_x + doc_w - max(4, size // 7), y)











    wave_x = doc_x - max(3, size // 8)





    wave_base = doc_y + max(5, size // 4)





    p.setPen(QPen(QColor("#1f3f90"), 1.7, Qt.SolidLine, Qt.RoundCap))





    p.drawLine(wave_x, wave_base + 8, wave_x, wave_base + 12)





    p.drawLine(wave_x + 3, wave_base + 5, wave_x + 3, wave_base + 15)





    p.drawLine(wave_x + 6, wave_base + 2, wave_x + 6, wave_base + 18)











    p.end()





    return pix

















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











    # 필요한 굵기가 비어 있으면 남은 파일로 보충한다.





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





        ("button_side", window.btn_target),





        ("path_label", window.label_target),





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

















class TrayToastWindow(QWidget):





    def __init__(self, parent: QWidget | None = None):





        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)





        self.setObjectName("ToastRoot")





        self.setAttribute(Qt.WA_TranslucentBackground, True)





        self.setAttribute(Qt.WA_NoSystemBackground, True)





        self.setAttribute(Qt.WA_StyledBackground, True)





        self.setAttribute(Qt.WA_ShowWithoutActivating, True)





        self.setWindowTitle(APP_DISPLAY_NAME)





        self.setFixedWidth(360)





        self._close_timer = QTimer(self)





        self._close_timer.setSingleShot(True)





        self._close_timer.timeout.connect(self.hide)





        self._build_ui()











    def _build_ui(self):





        root = QVBoxLayout(self)





        root.setContentsMargins(1, 1, 1, 1)





        root.setSpacing(0)











        self.card = QFrame()





        self.card.setObjectName("ToastCard")





        self.card.setAttribute(Qt.WA_StyledBackground, True)





        root.addWidget(self.card)





        shadow = QGraphicsDropShadowEffect(self.card)





        shadow.setBlurRadius(25)





        shadow.setOffset(0, 10)





        shadow.setColor(QColor(0, 0, 0, 13))





        self.card.setGraphicsEffect(shadow)











        body = QVBoxLayout(self.card)





        body.setContentsMargins(0, 0, 0, 0)





        body.setSpacing(10)











        header = QHBoxLayout()





        header.setContentsMargins(16, 12, 16, 10)





        header.setSpacing(7)





        self.icon_label = QLabel("")





        self.icon_label.setObjectName("ToastHeaderIcon")





        self.icon_label.setFixedSize(20, 20)





        header.addWidget(self.icon_label, 0, Qt.AlignVCenter)





        self.app_name_label = QLabel(APP_DISPLAY_NAME)





        self.app_name_label.setObjectName("ToastAppName")





        header.addWidget(self.app_name_label, 1, Qt.AlignVCenter)





        self.btn_close = QPushButton("×")





        self.btn_close.setObjectName("ToastCloseButton")





        self.btn_close.setFixedSize(18, 18)





        self.btn_close.clicked.connect(self.hide)





        header.addWidget(self.btn_close, 0, Qt.AlignRight | Qt.AlignVCenter)





        body.addLayout(header)











        content_row = QHBoxLayout()





        content_row.setContentsMargins(16, 0, 16, 0)





        content_row.setSpacing(12)











        content_col = QVBoxLayout()





        content_col.setContentsMargins(0, 0, 0, 0)





        content_col.setSpacing(3)





        self.title_label = QLabel("")





        self.title_label.setObjectName("ToastTitle")





        self.title_label.setWordWrap(False)





        content_col.addWidget(self.title_label)





        self.message_label = QLabel("")





        self.message_label.setObjectName("ToastMessage")





        self.message_label.setWordWrap(True)





        self.message_label.setMaximumHeight(52)





        content_col.addWidget(self.message_label)





        self.file_label = QLabel("")





        self.file_label.setObjectName("ToastFileName")





        self.file_label.setWordWrap(False)





        content_col.addWidget(self.file_label)





        content_row.addLayout(content_col, 1)











        self.doc_icon_label = QLabel("")





        self.doc_icon_label.setObjectName("ToastDocIcon")





        self.doc_icon_label.setFixedSize(20, 20)





        self.doc_icon_label.setText("●")





        self.doc_icon_label.setAlignment(Qt.AlignCenter)





        self.doc_icon_label.setVisible(True)





        content_row.addWidget(self.doc_icon_label, 0, Qt.AlignTop)





        body.addLayout(content_row)











        self.progress_wrap = QFrame()





        self.progress_wrap.setObjectName("ToastProgressWrap")





        progress_wrap_layout = QVBoxLayout(self.progress_wrap)





        progress_wrap_layout.setContentsMargins(16, 0, 16, 0)





        progress_wrap_layout.setSpacing(4)





        progress_meta = QHBoxLayout()





        progress_meta.setContentsMargins(0, 0, 0, 0)





        progress_meta.setSpacing(8)





        self.progress_label = QLabel("\uC804\uCCB4 \uC9C4\uD589\uB960")





        self.progress_label.setObjectName("ToastProgressLabel")





        self.progress_percent_label = QLabel("0%")





        self.progress_percent_label.setObjectName("ToastProgressPercent")





        self.progress_percent_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)





        progress_meta.addWidget(self.progress_label, 1)





        progress_meta.addWidget(self.progress_percent_label, 0)





        progress_wrap_layout.addLayout(progress_meta)





        self.progress_bar = QProgressBar()





        self.progress_bar.setObjectName("ToastProgressBar")





        self.progress_bar.setRange(0, 100)





        self.progress_bar.setValue(0)





        self.progress_bar.setTextVisible(False)





        self.progress_bar.setFixedHeight(14)





        progress_wrap_layout.addWidget(self.progress_bar)





        body.addWidget(self.progress_wrap)











        self.footer = QFrame()





        self.footer.setObjectName("ToastFooter")





        footer_box = QHBoxLayout(self.footer)





        footer_box.setContentsMargins(16, 16, 16, 16)





        footer_box.setSpacing(8)





        buttons = QHBoxLayout()





        buttons.setContentsMargins(0, 0, 0, 0)





        buttons.setSpacing(8)





        self.btn_open_folder = QPushButton("폴더 열기")





        self.btn_open_folder.setObjectName("ToastButtonSecondary")





        self.btn_open_folder.setFixedHeight(36)





        self.btn_ok = QPushButton("확인")





        self.btn_ok.setObjectName("ToastButtonPrimary")





        self.btn_ok.setFixedHeight(36)





        self.btn_ok.clicked.connect(self.hide)





        buttons.addWidget(self.btn_open_folder, 1)





        buttons.addWidget(self.btn_ok, 1)





        footer_box.addLayout(buttons, 1)





        body.addWidget(self.footer)











        self.setStyleSheet(





            """





            QWidget#ToastRoot {





                background:transparent;





                border:none;





            }





            QWidget {





                font-family:"Malgun Gothic", "맑은 고딕", "NanumBarunGothic", "Segoe UI", sans-serif;





            }





            QFrame#ToastCard {





                background:#ffffff;





                border:1px solid #c5c5d3;





                border-radius:4px;





            }





            QLabel#ToastAppName {





                color:#00236f;





                font-size:13px;





                font-weight:600;





            }





            QPushButton#ToastCloseButton {





                border:none;





                border-radius:3px;





                background:transparent;





                color:#757682;





                font-size:18px;





                padding:0;





            }





            QPushButton#ToastCloseButton:hover {





                background:#f1f5f9;





            }





            QLabel#ToastTitle {





                color:#00236f;





                font-size:20px;





                font-weight:600;





            }





            QLabel#ToastMessage {





                color:#444651;





                font-size:14px;





            }





            QLabel#ToastFileName {





                color:#444651;





                font-size:13px;





                padding-top:1px;





            }





            QLabel#ToastDocIcon {





                color:#1e3a8a;





                font-size:14px;





                font-weight:700;





            }





            QLabel#ToastProgressLabel {





                color:#38485d;





                font-size:12px;





                font-weight:700;





            }





            QLabel#ToastProgressPercent {





                color:#00236f;





                font-size:12px;





                font-weight:700;





            }





            QProgressBar#ToastProgressBar {





                border:none;





                border-radius:12px;





                background:#d3e4fe;





                min-height:8px;





                max-height:8px;





            }





            QProgressBar#ToastProgressBar::chunk {





                border-radius:12px;





                background:#00236f;





                border-right:4px solid #1e3a8a;





            }





            QFrame#ToastFooter {





                background:#f4f3fa;





                border-top:1px solid #f1f5f9;





                border-bottom-left-radius:4px;





                border-bottom-right-radius:4px;





            }





            QPushButton#ToastButtonSecondary {





                border:1px solid #757682;





                border-radius:4px;





                background:#ffffff;





                color:#444651;





                min-height:36px;





                font-size:13px;





                font-weight:500;





            }





            QPushButton#ToastButtonSecondary:hover {





                background:#f1f5f9;





            }





            QPushButton#ToastButtonPrimary {





                border:1px solid #00236f;





                border-radius:4px;





                background:#00236f;





                color:#ffffff;





                min-height:36px;





                font-size:13px;





                font-weight:600;





            }





            QPushButton#ToastButtonPrimary:hover {





                background:#1e3a8a;





            }





            """





        )











    def set_icon(self, icon: QIcon):





        if icon.isNull():





            self.icon_label.clear()





            return





        self.icon_label.setPixmap(icon.pixmap(16, 16))











    def configure(





        self,





        title: str,





        message: str,





        progress_percent: int | None = None,





        current_file: str = "",





        folder_open_enabled: bool = True,





    ):





        safe_title = (title or "").strip() or APP_DISPLAY_NAME





        safe_message = (message or "").strip()





        self.title_label.setText(safe_title)





        self.message_label.setText(safe_message)











        if current_file:





            shown = self.file_label.fontMetrics().elidedText(current_file, Qt.ElideMiddle, 292)





            self.file_label.setText(f"현재 파일: {shown}")





            self.file_label.setToolTip(current_file if shown != current_file else "")





            self.file_label.setVisible(True)





        else:





            self.file_label.clear()





            self.file_label.setToolTip("")





            self.file_label.setVisible(False)











        if progress_percent is None:





            self.progress_wrap.setVisible(False)





        else:





            percent = max(0, min(100, int(progress_percent)))





            self.progress_percent_label.setText(f"{percent}%")





            self.progress_bar.setValue(percent)





            self.progress_wrap.setVisible(True)











        self.btn_open_folder.setEnabled(folder_open_enabled)





        self.adjustSize()











    def show_at_bottom_right(self, anchor: QWidget, timeout_ms: int = 7200):





        screen = None





        if anchor and anchor.windowHandle() is not None:





            screen = anchor.windowHandle().screen()





        if screen is None:





            screen = QApplication.primaryScreen()





        self.adjustSize()





        if screen is not None:





            geo = screen.availableGeometry()





            margin = 16





            x = geo.x() + geo.width() - self.width() - margin





            y = geo.y() + geo.height() - self.height() - margin





            self.move(max(geo.x() + 8, x), max(geo.y() + 8, y))





        self._close_timer.stop()





        self.show()





        self.raise_()





        self._close_timer.start(max(3000, int(timeout_ms)))

















class ColabHealthCheckBridge(QObject):
    finished = Signal(int, str)

class ColabTranscribeRunBridge(QObject):
    event_line = Signal(str)
    log_line = Signal(str)
    finished = Signal(int, str, str)
    last_comm = Signal(str)


class TranscribeGUI(QWidget):





    def __init__(self):





        super().__init__()





        self.setObjectName("RootWindow")





        self.setWindowTitle(APP_DISPLAY_NAME)





        self.resize(1320, 760)





        self.setMinimumSize(1024, 680)











        self.target_folder = ""





        self._output_display_folder = ""





        self.process = None





        self.log_visible = False





        self.stdout_buffer = ""





        self.stderr_buffer = ""











        self.total_target_mp3_files = 0





        self.loaded_mp3_count = 0





        self.file_queue_rows: list[dict] = []





        self._queue_item_signal_bound = False





        self.completed_files = set()





        self.notified_success_files = set()





        self.total_complete_notified = False





        self.last_completed_file_name = ""





        self.current_tab_name = "transcriptions"











        self.current_file_name = ""





        self.current_file_started_at = None





        self.current_eta_seconds = None





        self.total_eta_seconds = None





        self.file_duration_history = []

        self.duration_eta_ratio = DEFAULT_WHISPER_TIME_RATIO
        self.duration_eta_ratio_calibrated = False
        self.run_total_audio_seconds = 0.0
        self.run_done_audio_seconds = 0.0
        self.run_current_audio_seconds = 0.0
        self.run_audio_seconds_by_primary_key: dict[str, float] = {}
        self.run_audio_alias_to_primary_key: dict[str, str] = {}
        self.run_audio_accounted_primary_keys: set[str] = set()





        self.last_current_percent = 0











        self.run_mode = "none"





        self.stop_requested = False





        self.pending_kill = False





        self.stop_terminate_sent = False





        self.shutdown_prompt_shown_for_run = False





        self.shutdown_prompt_pending_for_run = False





        self.toast_window: TrayToastWindow | None = None





        self.selected_runtime_folder = ""





        self.selected_runtime_entries: list[dict] = []





        self.selected_run_items: list[dict] = []

        self.moved_transcribe_items: list[dict] = []





        self.ui_settings = QSettings(get_ui_settings_path(), QSettings.IniFormat)
        self.dashboard_total_done_files = 0
        self.dashboard_total_audio_seconds = 0.0
        self.dashboard_daily_done_counts: dict[str, int] = {}
        self.dashboard_recent_done_items: list[dict] = []
        self.dashboard_observed_audio_seconds = 0.0
        self.dashboard_observed_processing_seconds = 0.0
        self.folder_tab_rows: list[dict] = []
        self.folder_tab_visible_rows: list[dict] = []
        self.folder_tab_filter_mode = "all"
        self.folder_preview_full_text = ""
        self.folder_preview_path = ""
        self.transcription_engine = "local"
        self.colab_url = ""
        self._colab_check_in_progress = False
        self._colab_check_connected = False
        self._colab_check_request_id = 0
        self._colab_health_check_bridge = ColabHealthCheckBridge()
        self._colab_health_check_bridge.finished.connect(self._on_colab_health_check_finished)
        self._colab_run_active = False
        self._colab_stop_after_current = False
        self._colab_run_request_id = 0
        self._colab_run_bridge = ColabTranscribeRunBridge()
        self._colab_run_bridge.event_line.connect(self._on_colab_transcribe_event_line)
        self._colab_run_bridge.log_line.connect(self._on_colab_transcribe_log_line)
        self._colab_run_bridge.finished.connect(self._on_colab_transcribe_finished)
        self._colab_run_bridge.last_comm.connect(self.update_colab_last_comm)
        self._colab_resume_enabled = False
        self._colab_resume_completed_keys: set[str] = set()
        self._colab_resume_session_id = ""
        self._colab_resume_progress_path_key = ""





        self._status_full_text = "\uB300\uAE30 \uC911"





        self._current_file_full_text = "\uD604\uC7AC \uCC98\uB9AC \uC911 \uD30C\uC77C: \uC5C6\uC74C"





        self._session_full_text = "\uC138\uC158 \uC0C1\uD0DC: \uD655\uC778 \uC911..."





        self._output_full_text = (self._display_path_for_ui(self._output_display_folder or self.target_folder) if (self._output_display_folder or self.target_folder) else "\uBBF8\uC124\uC815")





        self._output_text_elide_mode = Qt.ElideRight





        self._status_spin_frames = ["↻", "↺", "↻", "↺"]





        self._status_spin_index = 0





        self.status_spin_timer = QTimer(self)





        self.status_spin_timer.timeout.connect(self._tick_status_icon)











        self.build_ui()

        self._configure_folder_and_control_ui()





        self.apply_styles()





        self.apply_font_hierarchy()





        self.apply_typography_fit_defaults()





        self._setup_checkbox_indicator_style()





        self.load_ui_preferences()
        QTimer.singleShot(0, self._check_colab_progress_resume_on_startup)
        self.load_dashboard_statistics()
        self.refresh_dashboard_view()
        self._set_folder_filter_mode("all")
        self.refresh_folder_management_view()





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





        QTimer.singleShot(0, self._sync_sidebar_height)











    def build_ui(self):





        root = QVBoxLayout(self)





        root.setContentsMargins(0, 0, 0, 0)





        root.setSpacing(0)











        top_bar = QFrame()





        top_bar.setObjectName("TopAppBar")





        top_bar.setFixedHeight(64)





        top_layout = QHBoxLayout(top_bar)





        top_layout.setContentsMargins(20, 0, 20, 0)





        top_layout.setSpacing(16)











        brand_row = QHBoxLayout()





        brand_row.setContentsMargins(0, 0, 0, 0)





        brand_row.setSpacing(10)





        self.label_title_icon = QLabel("")





        self.label_title_icon.setObjectName("TopBrandIcon")





        self.label_title_icon.setFixedSize(32, 32)





        self.label_title_icon.setPixmap(create_brand_symbol_pixmap(32))





        self.label_title_text = QLabel("전사도우미")





        self.label_title_text.setObjectName("TopBrandText")





        self.label_title_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)





        brand_row.addWidget(self.label_title_icon, 0, Qt.AlignVCenter)





        brand_row.addWidget(self.label_title_text, 0, Qt.AlignVCenter)





        brand_row.addStretch(1)





        top_layout.addLayout(brand_row, 1)











        tab_row = QHBoxLayout()





        tab_row.setContentsMargins(0, 0, 0, 0)





        tab_row.setSpacing(6)





        self.tab_transcriptions = QPushButton("Transcriptions")





        self.tab_dashboard = QPushButton("Dashboard")





        self.tab_folders = QPushButton("Folders")





        for btn in (self.tab_transcriptions, self.tab_dashboard, self.tab_folders):





            btn.setObjectName("TopTabButton")





            btn.setCheckable(True)





            btn.setCursor(Qt.PointingHandCursor)





            btn.setMinimumHeight(64)





            btn.setProperty("active", False)





            tab_row.addWidget(btn, 0, Qt.AlignVCenter)





        top_layout.addLayout(tab_row, 0)





        root.addWidget(top_bar)











        content_wrap = QFrame()





        content_wrap.setObjectName("ContentWrap")





        content_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)





        content_layout = QHBoxLayout(content_wrap)





        content_layout.setContentsMargins(0, 0, 0, 0)





        content_layout.setSpacing(0)





        root.addWidget(content_wrap, 1)





        self.content_wrap = content_wrap











        sidebar = QFrame()





        sidebar.setObjectName("SidebarPane")





        sidebar.setFixedWidth(360)





        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)





        self.sidebar_pane = sidebar





        content_layout.addWidget(sidebar, 0)











        side_wrap = QVBoxLayout(sidebar)





        side_wrap.setContentsMargins(0, 0, 0, 0)





        side_wrap.setSpacing(0)











        side_scroll = QScrollArea()





        side_scroll.setObjectName("SidebarScroll")





        side_scroll.setFrameShape(QFrame.NoFrame)





        side_scroll.setWidgetResizable(True)





        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)





        side_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)





        side_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)





        side_scroll.setFixedWidth(360)





        side_wrap.addWidget(side_scroll, 1)





        self.sidebar_scroll = side_scroll











        side_content = QWidget()





        side_content.setObjectName("SidebarContent")





        side_content.setMinimumWidth(0)





        side_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)





        side_scroll.setWidget(side_content)





        left = QVBoxLayout(side_content)





        left.setContentsMargins(12, 20, 12, 20)





        left.setSpacing(8)





        self.sidebar_sections_layout = left











        self.group_title = None











        settings = QGroupBox("")





        settings.setObjectName("SidebarCard")





        settings.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)





        sbox = QVBoxLayout(settings)





        sbox.setContentsMargins(16, 0, 16, 12)





        sbox.setSpacing(0)





        self.label_section_settings = QLabel("폴더 설정", objectName="SectionTitle")





        sbox.addWidget(self.label_section_settings)





        self.label_settings_hint = QLabel("folder_open", objectName="SectionIconText")





        settings_hint_policy = self.label_settings_hint.sizePolicy()
        settings_hint_policy.setRetainSizeWhenHidden(False)
        self.label_settings_hint.setSizePolicy(settings_hint_policy)
        self.label_settings_hint.setVisible(False)





        sbox.addWidget(self.label_settings_hint)





        sbox.addSpacing(6)











        self.label_target = QLabel("폴더를 선택하세요", objectName="PathLabel")





        self.label_target.setFixedHeight(36)





        self.label_target.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)





        self.label_target.setWordWrap(False)





        sbox.addWidget(self.label_target)





        sbox.addSpacing(4)





        self.btn_target = QPushButton("전사자료 폴더 선택")





        self.btn_target.setProperty("uiRole", "side")





        self.btn_target.setFixedHeight(36)





        sbox.addWidget(self.btn_target)





        sbox.addSpacing(6)











        self.btn_load_files = QPushButton("MP3 파일 목록 불러오기")





        self.btn_load_files.setProperty("uiRole", "sideOutline")





        self.btn_load_files.setFixedHeight(36)





        sbox.addWidget(self.btn_load_files)





        left.addWidget(settings, 0)





        self.group_settings = settings











        # ── 전사 파일 분류 카드 ──
        classify_card = QGroupBox("")
        classify_card.setObjectName("SidebarCard")
        classify_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        classify_box = QVBoxLayout(classify_card)
        classify_box.setContentsMargins(16, 12, 16, 12)
        classify_box.setSpacing(6)

        self.label_section_classify = QLabel("전사 파일 분류", objectName="SectionTitle")
        classify_box.addWidget(self.label_section_classify)

        classify_desc = QLabel(
            "과정명과 과목명은 다운로드 원본 파일명을 표준 파일명으로 바꾸고, "
            "과목별 전사 보정 및 Google Drive 업로드 경로를 정하는 데 사용됩니다."
        )
        classify_desc.setWordWrap(True)
        classify_desc.setObjectName("SidebarHintLabel")
        classify_desc.setStyleSheet("color: #64748b; font-size: 11px; margin-bottom: 2px;")
        classify_box.addWidget(classify_desc)

        classify_box.addSpacing(2)

        lbl_course = QLabel("과정명")
        lbl_course.setStyleSheet("font-weight: 500; font-size: 12px;")
        classify_box.addWidget(lbl_course)
        self.combo_transcribe_course = QComboBox()
        self.combo_transcribe_course.addItems(["", "개념완성", "기본이론", "기초이론"])
        self.combo_transcribe_course.setFixedHeight(34)
        classify_box.addWidget(self.combo_transcribe_course)

        classify_box.addSpacing(4)

        lbl_subject = QLabel("과목명")
        lbl_subject.setStyleSheet("font-weight: 500; font-size: 12px;")
        classify_box.addWidget(lbl_subject)
        self.combo_transcribe_subject = QComboBox()
        self.combo_transcribe_subject.addItems(["", "부동산학개론", "민법", "공인중개사법", "부동산공법", "부동산공시법", "부동산세법"])
        self.combo_transcribe_subject.setFixedHeight(34)
        classify_box.addWidget(self.combo_transcribe_subject)

        classify_box.addSpacing(6)

        classify_warn = QLabel(
            "선택한 과정/과목은 이번 전사 대상 파일 전체에 적용됩니다.\n"
            "여러 과목 파일이 한 폴더에 섞여 있다면, 과목별로 체크해서 나누어 실행하세요."
        )
        classify_warn.setWordWrap(True)
        classify_warn.setObjectName("SidebarWarnLabel")
        classify_warn.setStyleSheet("color: #b45309; font-size: 11px; background: #fef3c7; border-radius: 4px; padding: 6px 8px;")
        classify_box.addWidget(classify_warn)

        left.addWidget(classify_card, 0)
        self.group_classify = classify_card

        # ── Google Drive 업로드 카드 ──
        drive_card = QGroupBox("")
        drive_card.setObjectName("SidebarCard")
        drive_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        drive_box = QVBoxLayout(drive_card)
        drive_box.setContentsMargins(16, 12, 16, 12)
        drive_box.setSpacing(6)

        self.label_section_drive = QLabel("Google Drive 업로드", objectName="SectionTitle")
        drive_box.addWidget(self.label_section_drive)

        self.upload_drive_checkbox = QCheckBox("Google Drive 자동 업로드")
        drive_box.addWidget(self.upload_drive_checkbox)

        drive_desc = QLabel(
            "전사 완료 후 MP3, TXT, JSON, SRT 4종 파일을 기존 Google Drive "
            "주차 폴더에 업로드합니다.\n"
            "인증 파일이 없거나 손상된 경우 전사 시작 전 안내됩니다."
        )
        drive_desc.setWordWrap(True)
        drive_desc.setObjectName("SidebarHintLabel")
        drive_desc.setStyleSheet("color: #64748b; font-size: 11px;")
        drive_box.addWidget(drive_desc)

        left.addWidget(drive_card, 0)
        self.group_drive = drive_card

        # ── 알림 및 종료 옵션 카드 ──
        options = QGroupBox("")
        options.setObjectName("SidebarCard")
        options.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        obox = QVBoxLayout(options)
        obox.setContentsMargins(16, 12, 16, 10)
        obox.setSpacing(6)

        self.label_section_options = QLabel("알림 및 종료 옵션", objectName="SectionTitle")
        obox.addWidget(self.label_section_options)

        self.chk_notify_each_file = QCheckBox("파일별 완료 알림 켜기")
        self.chk_notify_total = QCheckBox("전체 완료 알림 켜기")
        self.shutdown_checkbox = QCheckBox("전체 전사 완료 후 컴퓨터 종료")

        self.shutdown_wait_combo = QComboBox()
        self.shutdown_wait_combo.setObjectName("ShutdownWaitCombo")
        self.shutdown_wait_combo.setFixedHeight(34)
        for seconds, label in SHUTDOWN_WAIT_OPTIONS:
            self.shutdown_wait_combo.addItem(label, seconds)
        self.shutdown_wait_combo.setCurrentIndex(0)
        self.shutdown_wait_combo.setEnabled(False)

        self.chk_notify_each_file.setChecked(True)
        self.chk_notify_total.setChecked(True)

        obox.addWidget(self.chk_notify_each_file)
        obox.addWidget(self.chk_notify_total)
        obox.addWidget(self.shutdown_checkbox)
        obox.addWidget(self.shutdown_wait_combo)

        left.addWidget(options, 0)
        self.group_options = options











        logs = QGroupBox("")





        logs.setObjectName("SidebarCard")





        logs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)





        lbox = QVBoxLayout(logs)





        lbox.setContentsMargins(16, 12, 16, 12)





        lbox.setSpacing(6)





        self.label_section_logs = QLabel("실행 로그", objectName="SectionTitle")





        lbox.addWidget(self.label_section_logs)





        self.log_viewer = QTextEdit()





        self.log_viewer.setObjectName("LogViewer")





        self.log_viewer.setReadOnly(True)





        self.log_viewer.setMinimumHeight(160)
        self.log_viewer.setMaximumHeight(220)





        self.log_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)





        self.log_viewer.setLineWrapMode(QTextEdit.WidgetWidth)





        self.log_viewer.setWordWrapMode(QTextOption.WrapAnywhere)





        self.log_viewer.document().setDocumentMargin(12)





        self.log_viewer.setVisible(True)





        lbox.addWidget(self.log_viewer, 1)





        left.addWidget(logs, 1)





        self.group_logs = logs











        mainpane = QFrame()





        mainpane.setObjectName("MainPane")





        mainpane.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)





        self.main_pane = mainpane





        content_layout.addWidget(mainpane, 1)





        content_layout.setStretch(0, 0)





        content_layout.setStretch(1, 1)





        right = QVBoxLayout(mainpane)





        right.setContentsMargins(20, 20, 20, 20)





        right.setSpacing(16)











        self.main_stack = QStackedWidget()





        self.main_stack.setObjectName("MainStack")





        right.addWidget(self.main_stack, 1)











        # Transcriptions tab page





        trans_page = QWidget()





        trans_page.setObjectName("TransPage")





        trans_layout = QVBoxLayout(trans_page)





        trans_layout.setContentsMargins(0, 0, 0, 0)





        trans_layout.setSpacing(0)











        dashboard = QGroupBox("")





        dashboard.setObjectName("DashboardSection")





        dashboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)





        dbox = QVBoxLayout(dashboard)





        dbox.setContentsMargins(16, 6, 16, 4)
        dbox.setSpacing(1)





        self.label_section_dashboard = QLabel("Transcriptions", objectName="SectionTitle")





        self.label_section_dashboard.setVisible(False)





        dbox.addWidget(self.label_section_dashboard)











        self.label_status = QLabel("")





        self.label_status.setObjectName("StatusPrimary")





        self.label_status.setWordWrap(False)





        self.label_current_file = QLabel("")





        self.label_current_file.setObjectName("StatusSecondary")





        self.label_current_file.setWordWrap(False)





        self.label_session = QLabel("")





        self.label_session.setObjectName("MetaStatus")





        self.label_output_source = QLabel("")





        self.label_output_source.setObjectName("MetaStatus")











        self.label_total_progress_text = QLabel("0 / 0")





        self.label_total_progress_text.setObjectName("MetricValue")





        self.label_total_progress_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)





        self.label_total_done_hint = QLabel("0 FILES DONE", objectName="MetricDoneHint")





        self.label_total_done_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)











        self.total_progress_bar = QProgressBar()





        self.total_progress_bar.setRange(0, 100)





        self.total_progress_bar.setTextVisible(False)





        self.total_progress_bar.setFixedHeight(14)











        self.label_total_eta = QLabel(ETA_EMPTY_TEXT)





        self.label_total_eta.setObjectName("MetricEtaValue")





        self.label_current_progress_text = QLabel("0%")





        self.label_current_progress_text.setObjectName("CurrentProgressValue")





        self.current_progress_bar = QProgressBar()





        self.current_progress_bar.setObjectName("CurrentProgressBar")





        self.current_progress_bar.setRange(0, 100)





        self.current_progress_bar.setTextVisible(False)





        self.current_progress_bar.setFixedHeight(14)





        self.label_current_eta = QLabel("CURRENT ETA: -")





        self.label_current_eta.setObjectName("MetaCompactValue")











        self.top_cards_container = QWidget()





        self.top_cards_container.setObjectName("DashboardTopCards")





        self.top_cards_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)





        top_cards = QHBoxLayout(self.top_cards_container)





        top_cards.setContentsMargins(0, 0, 0, 0)





        top_cards.setSpacing(16)











        self.card_status = QFrame()





        self.card_status.setObjectName("DashboardCard")





        self.card_status.setMinimumHeight(0)





        status_box = QVBoxLayout(self.card_status)





        status_box.setContentsMargins(16, 12, 16, 12)





        status_box.setSpacing(0)





        status_row = QHBoxLayout()





        status_row.setContentsMargins(0, 0, 0, 0)





        status_row.setSpacing(12)





        status_text_col = QVBoxLayout()





        status_text_col.setContentsMargins(0, 0, 0, 0)





        status_text_col.setSpacing(4)





        self.status_icon = QLabel("↻")





        self.status_icon.setObjectName("StatusIconBubble")





        self.status_icon.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)





        self.status_icon.setFixedSize(40, 40)





        self.status_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)





        status_icon_container = QWidget()





        status_icon_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)





        status_icon_container.setFixedWidth(40)





        status_icon_col = QVBoxLayout(status_icon_container)





        status_icon_col.setContentsMargins(0, 0, 0, 0)





        status_icon_col.setSpacing(0)





        status_icon_col.addStretch(1)





        status_icon_col.addWidget(self.status_icon, 0, Qt.AlignHCenter | Qt.AlignVCenter)





        status_icon_col.addStretch(1)





        status_text_col.addStretch(1)





        status_text_col.addWidget(QLabel("CURRENT STATUS", objectName="DashboardMicroLabel"))





        self.label_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)





        status_text_col.addWidget(self.label_status)





        status_text_col.addStretch(1)





        status_row.addLayout(status_text_col, 1)





        status_row.addWidget(status_icon_container, 0, Qt.AlignVCenter | Qt.AlignRight)





        status_box.addLayout(status_row, 1)





        top_cards.addWidget(self.card_status, 1)











        self.card_progress = QFrame()





        self.card_progress.setObjectName("DashboardCard")





        self.card_progress.setMinimumHeight(130)
        progress_box = QVBoxLayout(self.card_progress)
        progress_box.setContentsMargins(14, 14, 14, 14)
        progress_box.setSpacing(2)





        lbl_tp = QLabel("TOTAL PROGRESS", objectName="DashboardMicroLabel")
        lbl_tp.setMinimumHeight(22)
        progress_box.addWidget(lbl_tp)
        progress_box.addSpacing(2)

        metric_header = QHBoxLayout()
        metric_header.setContentsMargins(0, 0, 0, 0)
        metric_header.setSpacing(10)

        self.label_total_progress_text.setMinimumHeight(36)
        self.label_total_progress_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        metric_header.addWidget(self.label_total_progress_text, 0)

        self.label_total_done_hint.setMinimumHeight(36)
        self.label_total_done_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        metric_header.addWidget(self.label_total_done_hint, 1)

        progress_box.addLayout(metric_header)
        progress_box.addSpacing(12)
        progress_box.addWidget(self.total_progress_bar)





        top_cards.addWidget(self.card_progress, 1)











        self.card_eta = QFrame()





        self.card_eta.setObjectName("DashboardCard")





        self.card_eta.setMinimumHeight(0)





        eta_box = QVBoxLayout(self.card_eta)





        eta_box.setContentsMargins(16, 12, 16, 12)





        eta_box.setSpacing(0)





        eta_row = QHBoxLayout()





        eta_row.setContentsMargins(0, 0, 0, 0)





        eta_row.setSpacing(12)





        eta_text_col = QVBoxLayout()





        eta_text_col.setContentsMargins(0, 0, 0, 0)





        eta_text_col.setSpacing(4)





        self.eta_icon = QLabel("◷")





        self.eta_icon.setObjectName("EtaIconBubble")





        self.eta_icon.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)





        self.eta_icon.setFixedSize(40, 40)





        self.eta_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)





        eta_icon_container = QWidget()





        eta_icon_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)





        eta_icon_container.setFixedWidth(40)





        eta_icon_col = QVBoxLayout(eta_icon_container)





        eta_icon_col.setContentsMargins(0, 0, 0, 0)





        eta_icon_col.setSpacing(0)





        eta_icon_col.addStretch(1)





        eta_icon_col.addWidget(self.eta_icon, 0, Qt.AlignHCenter | Qt.AlignVCenter)





        eta_icon_col.addStretch(1)





        eta_text_col.addStretch(1)





        eta_text_col.addWidget(QLabel("REMAINING TIME", objectName="DashboardMicroLabel"))





        self.label_total_eta.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)





        eta_text_col.addWidget(self.label_total_eta)





        eta_text_col.addStretch(1)





        eta_row.addLayout(eta_text_col, 1)





        eta_row.addWidget(eta_icon_container, 0, Qt.AlignVCenter | Qt.AlignRight)





        eta_box.addLayout(eta_row, 1)





        top_cards.addWidget(self.card_eta, 1)





        dbox.addWidget(self.top_cards_container)





        dbox.addSpacing(10)











        self.card_current = QFrame()





        self.card_current.setObjectName("DashboardCard")





        self.card_current.setMinimumHeight(175)
        current_box = QVBoxLayout(self.card_current)
        current_box.setContentsMargins(16, 20, 16, 20)





        current_box.setSpacing(0)
        label_cf = QLabel("CURRENT FILE", objectName="DashboardMicroLabel")
        label_cf.setMinimumHeight(22)





        current_box.addWidget(label_cf)





        self.label_current_file.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)





        self.label_current_file.setMinimumHeight(28)





        current_box.addWidget(self.label_current_file)





        current_box.addSpacing(16)











        current_header = QHBoxLayout()





        current_header.setContentsMargins(0, 0, 0, 0)





        current_header.setSpacing(8)





        label_cp = QLabel("CURRENT PROGRESS", objectName="DashboardMicroLabel")
        label_cp.setMinimumHeight(22)
        current_header.addWidget(label_cp, 1)

        self.label_current_progress_text.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.label_current_progress_text.setMinimumHeight(22)
        self.label_current_progress_text.setContentsMargins(0, 0, 6, 0)
        current_header.addWidget(self.label_current_progress_text, 0)





        current_box.addLayout(current_header)
        current_box.addSpacing(4)
        current_box.addWidget(self.current_progress_bar)
        current_box.addSpacing(18)











        meta_row = QHBoxLayout()





        meta_row.setContentsMargins(0, 0, 0, 0)





        meta_row.setSpacing(10)





        self.label_session_counter = QLabel("SESSION: 0 / 0", objectName="MetaCompactValue")





        self.label_output_value = QLabel("OUTPUT: 미설정", objectName="MetaCompactValue")





        self.label_current_eta.setWordWrap(False)





        self.label_session_counter.setWordWrap(False)





        self.label_output_value.setWordWrap(False)





        self.label_current_eta.setMinimumHeight(26)





        self.label_session_counter.setMinimumHeight(26)





        self.label_output_value.setMinimumHeight(26)





        self.label_current_eta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)





        self.label_session_counter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)





        self.label_output_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)





        meta_row.addWidget(self.label_current_eta, 2)





        meta_row.addWidget(self.label_session_counter, 2)





        meta_row.addWidget(self.label_output_value, 4)





        current_box.addLayout(meta_row)





        dbox.addWidget(self.card_current)





        self.current_progress_panel = self.card_current





        self.current_meta_panel = self.card_current











        trans_layout.addWidget(dashboard)





        self.group_dashboard = dashboard











        files = QGroupBox("")





        files.setObjectName("FileQueueSection")





        files.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)





        fbox = QVBoxLayout(files)





        fbox.setContentsMargins(14, 12, 14, 12)





        fbox.setSpacing(8)





        header_row = QHBoxLayout()





        header_row.setContentsMargins(0, 0, 0, 0)





        header_row.setSpacing(8)





        self.label_section_files = QLabel("전사 대기열", objectName="QueueTitle")





        header_row.addWidget(self.label_section_files, 1)





        self.btn_filter_all = QPushButton("전체 선택")





        self.btn_filter_all.setObjectName("QueueHeaderButton")





        self.btn_filter_all.setFixedHeight(28)





        self.btn_filter_all.setEnabled(False)





        self.btn_uncheck_all = QPushButton("전체 해제")





        self.btn_uncheck_all.setObjectName("QueueHeaderButton")





        self.btn_uncheck_all.setFixedHeight(28)





        self.btn_uncheck_all.setEnabled(False)





        self.btn_clear_all = QPushButton("전체 삭제")





        self.btn_clear_all.setObjectName("QueueHeaderButtonDanger")





        self.btn_clear_all.setFixedHeight(28)





        self.btn_clear_all.setEnabled(False)





        self.btn_clear_done = QPushButton("완료정리")





        self.btn_clear_done.setObjectName("QueueHeaderButton")





        self.btn_clear_done.setFixedHeight(28)





        header_row.addWidget(self.btn_filter_all, 0)





        header_row.addWidget(self.btn_uncheck_all, 0)





        header_row.addWidget(self.btn_clear_all, 0)





        header_row.addWidget(self.btn_clear_done, 0)





        fbox.addLayout(header_row)











        self.label_file_count = QLabel("불러온 MP3 파일 수: 0개", objectName="SectionValue")





        fbox.addWidget(self.label_file_count)





        self.label_files_helper = QLabel("", objectName="HelperText")





        self.label_files_helper.setVisible(False)





        fbox.addWidget(self.label_files_helper)











        self.file_queue_table = QTableWidget(0, 5)





        self.file_queue_table.setObjectName("FileQueueTable")





        self.file_queue_table.setHorizontalHeaderLabels(["", "Filename", "Duration", "Status", "Action"])
        self.file_queue_table.horizontalHeaderItem(2).setTextAlignment(Qt.AlignCenter)
        self.file_queue_table.horizontalHeaderItem(3).setTextAlignment(Qt.AlignCenter)
        self.file_queue_table.horizontalHeaderItem(4).setTextAlignment(Qt.AlignCenter)





        self.file_queue_table.verticalHeader().setVisible(False)





        self.file_queue_table.horizontalHeader().setStretchLastSection(False)





        self.file_queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)





        self.file_queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)





        self.file_queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)





        self.file_queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)





        self.file_queue_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)





        self.file_queue_table.setColumnWidth(0, 40)





        self.file_queue_table.setColumnWidth(2, 90)





        self.file_queue_table.setColumnWidth(3, 112)





        self.file_queue_table.setColumnWidth(4, 84)





        self.file_queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)





        self.file_queue_table.setSelectionMode(QAbstractItemView.NoSelection)





        self.file_queue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)





        self.file_queue_table.setAlternatingRowColors(False)





        self.file_queue_table.setShowGrid(False)





        self.file_queue_row_height = 36
        queue_header_h = self.file_queue_table.horizontalHeader().sizeHint().height()
        queue_frame_h = max(2, self.file_queue_table.frameWidth() * 2)
        self.file_queue_table.setMinimumHeight(
            queue_header_h + (self.file_queue_row_height * 6) + queue_frame_h + 10
        )
        self.file_queue_table.setMaximumHeight(queue_header_h + (self.file_queue_row_height * 10) + queue_frame_h)
        self.file_queue_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)





        self.file_queue_table.setWordWrap(False)





        self.file_queue_table.setTextElideMode(Qt.ElideRight)





        self.file_queue_table.setFocusPolicy(Qt.NoFocus)
        self.file_queue_table.setContextMenuPolicy(Qt.NoContextMenu)
        self.file_queue_table.viewport().setContextMenuPolicy(Qt.NoContextMenu)
        self.file_queue_table.horizontalHeader().setContextMenuPolicy(Qt.NoContextMenu)
        self.file_queue_table.verticalHeader().setContextMenuPolicy(Qt.NoContextMenu)





        fbox.addWidget(self.file_queue_table, 1)





        self.file_list_widget = self.file_queue_table











        self.label_file_empty_state = QLabel("불러온 MP3 파일이 없습니다.", objectName="FileEmptyState")





        self.label_file_empty_state.setAlignment(Qt.AlignCenter)





        self.label_file_empty_state.setMinimumHeight(40)





        fbox.addWidget(self.label_file_empty_state)





        trans_layout.addWidget(files, 100)





        self.group_files = files











        controls = QGroupBox("")





        controls.setObjectName("ControlSection")





        controls.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)





        cbox = QVBoxLayout(controls)





        cbox.setContentsMargins(10, 4, 10, 2)
        cbox.setSpacing(0)





        self.label_section_controls = QLabel("실행 제어", objectName="SectionTitle")





        cbox.addWidget(self.label_section_controls)





        self.label_controls_helper = QLabel("", objectName="HelperText")





        self.label_controls_helper.setVisible(False)





        cbox.addWidget(self.label_controls_helper)











        self.transcription_engine_panel = QWidget()
        self.transcription_engine_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        engine_box = QVBoxLayout(self.transcription_engine_panel)
        engine_box.setContentsMargins(0, 2, 0, 4)
        engine_box.setSpacing(4)

        engine_row = QHBoxLayout()
        engine_row.setContentsMargins(0, 0, 0, 0)
        engine_row.setSpacing(6)
        self.label_transcription_engine = QLabel("전사 방식", objectName="TranscriptionModeLabel")
        self.label_transcription_engine.setMinimumWidth(64)
        self.label_transcription_engine.setMaximumWidth(64)
        engine_row.addWidget(self.label_transcription_engine, 0)

        self.combo_transcription_engine = QComboBox()
        self.combo_transcription_engine.setObjectName("TranscriptionEngineCombo")
        self.combo_transcription_engine.setFixedHeight(34)
        self.combo_transcription_engine.setMaxVisibleItems(2)
        self.combo_transcription_engine.addItem("로컬 Whisper", "local")
        self.combo_transcription_engine.addItem("Colab Large-v3", "colab")
        engine_row.addWidget(self.combo_transcription_engine, 1)
        engine_box.addLayout(engine_row)

        self.colab_url_panel = QWidget()
        self.colab_url_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        colab_policy = self.colab_url_panel.sizePolicy()
        colab_policy.setRetainSizeWhenHidden(False)
        self.colab_url_panel.setSizePolicy(colab_policy)
        colab_box = QVBoxLayout(self.colab_url_panel)
        colab_box.setContentsMargins(0, 0, 0, 0)
        colab_box.setSpacing(0)

        colab_row = QHBoxLayout()
        colab_row.setContentsMargins(0, 0, 0, 0)
        colab_row.setSpacing(6)
        self.label_colab_url = QLabel("Colab URL", objectName="TranscriptionModeLabel")
        self.label_colab_url.setMinimumWidth(64)
        self.label_colab_url.setMaximumWidth(64)
        colab_row.addWidget(self.label_colab_url, 0)
        self.input_colab_url = QLineEdit()
        self.input_colab_url.setObjectName("ColabUrlInput")
        self.input_colab_url.setMinimumHeight(32)
        self.input_colab_url.setPlaceholderText("https://colab.research.google.com/...")
        colab_row.addWidget(self.input_colab_url, 1)

        self.btn_colab_check = QPushButton("연결 확인")
        self.btn_colab_check.setObjectName("ColabCheckButton")
        self.btn_colab_check.setProperty("uiRole", "controlOutline")
        self.btn_colab_check.setProperty("connected", False)
        self.btn_colab_check.setFixedHeight(32)
        self.btn_colab_check.setFixedWidth(92)
        colab_row.addWidget(self.btn_colab_check, 0)
        self.btn_colab_open = QPushButton("Colab 열기")
        self.btn_colab_open.setObjectName("ColabOpenButton")
        self.btn_colab_open.setProperty("uiRole", "controlOutline")
        self.btn_colab_open.setFixedHeight(32)
        self.btn_colab_open.setFixedWidth(92)
        self.btn_colab_open.clicked.connect(self.open_colab_notebook)
        colab_row.addWidget(self.btn_colab_open, 0)

        colab_box.addLayout(colab_row)
        self.label_colab_last_comm = QLabel("마지막 통신: --:--:--", objectName="TranscriptionModeLabel")
        self.label_colab_last_comm.setStyleSheet("color: #64748b; font-size: 11px; margin-top: 2px; margin-left: 70px;")
        colab_box.addWidget(self.label_colab_last_comm)
        engine_box.addWidget(self.colab_url_panel)
        cbox.addWidget(self.transcription_engine_panel)

        row1 = QHBoxLayout()





        row1.setSpacing(6)





        self.btn_move_and_transcribe = QPushButton("선택한 MP3 이동 후 전사 시작")





        self.btn_move_and_transcribe.setProperty("uiRole", "controlOutlinePrimary")





        self.btn_move_and_transcribe.setFixedHeight(38)





        self.btn_move_and_transcribe.setEnabled(False)





        self.btn_transcribe_target = QPushButton("전사자료 폴더 전체 전사 시작")





        self.btn_transcribe_target.setProperty("uiRole", "controlPrimary")





        self.btn_transcribe_target.setFixedHeight(38)





        row1.addWidget(self.btn_move_and_transcribe, 1)





        row1.addWidget(self.btn_transcribe_target, 1)





        cbox.addLayout(row1)











        row2 = QHBoxLayout()





        row2.setSpacing(6)





        self.btn_move_files = QPushButton("선택 MP3 전사자료 폴더로 이동")





        self.btn_move_files.setProperty("uiRole", "controlOutline")





        self.btn_move_files.setFixedHeight(34)





        self.btn_stop_now = QPushButton("전사중지")





        self.btn_stop_now.setProperty("uiRole", "controlGhost")





        self.btn_stop_now.setFixedHeight(34)





        self.btn_stop_now.setEnabled(False)





        row2.addWidget(self.btn_move_files, 1)





        row2.addWidget(self.btn_stop_now, 1)





        cbox.addLayout(row2)





        trans_layout.addWidget(controls)





        self.group_controls = controls











        trans_scroll = QScrollArea()





        trans_scroll.setWidgetResizable(True)
        trans_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)





        trans_scroll.setFrameShape(QFrame.NoFrame)





        trans_scroll.setWidget(trans_page)





        trans_scroll.setObjectName("TransScrollArea")





        trans_scroll.viewport().setObjectName("TransScrollViewport")





        self.main_stack.addWidget(trans_scroll)











        dash_page = QWidget()





        dash_layout = QVBoxLayout(dash_page)





        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(10)

        dash_cards = QFrame()
        dash_cards.setObjectName("DashboardTopCards")
        dash_cards_grid = QGridLayout(dash_cards)
        dash_cards_grid.setContentsMargins(0, 0, 0, 0)
        dash_cards_grid.setHorizontalSpacing(10)
        dash_cards_grid.setVerticalSpacing(10)

        self.card_dash_total_done = QFrame()
        self.card_dash_total_done.setObjectName("DashboardCard")
        card_total_done_box = QVBoxLayout(self.card_dash_total_done)
        card_total_done_box.setContentsMargins(14, 12, 14, 12)
        card_total_done_box.setSpacing(6)
        card_total_done_box.addWidget(QLabel("TOTAL DONE FILES", objectName="DashboardMicroLabel"))
        self.label_dash_total_done = QLabel("0")
        self.label_dash_total_done.setObjectName("MetricValue")
        self.label_dash_total_done.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        card_total_done_box.addWidget(self.label_dash_total_done, 1)
        dash_cards_grid.addWidget(self.card_dash_total_done, 0, 0)

        self.card_dash_total_audio = QFrame()
        self.card_dash_total_audio.setObjectName("DashboardCard")
        card_total_audio_box = QVBoxLayout(self.card_dash_total_audio)
        card_total_audio_box.setContentsMargins(14, 12, 14, 12)
        card_total_audio_box.setSpacing(6)
        card_total_audio_box.addWidget(QLabel("TOTAL AUDIO TIME", objectName="DashboardMicroLabel"))
        self.label_dash_total_audio = QLabel("0분")
        self.label_dash_total_audio.setObjectName("MetricValue")
        self.label_dash_total_audio.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        card_total_audio_box.addWidget(self.label_dash_total_audio, 1)
        dash_cards_grid.addWidget(self.card_dash_total_audio, 0, 1)

        self.card_dash_today_done = QFrame()
        self.card_dash_today_done.setObjectName("DashboardCard")
        card_today_done_box = QVBoxLayout(self.card_dash_today_done)
        card_today_done_box.setContentsMargins(14, 12, 14, 12)
        card_today_done_box.setSpacing(6)
        card_today_done_box.addWidget(QLabel("DONE TODAY", objectName="DashboardMicroLabel"))
        self.label_dash_today_done = QLabel("0")
        self.label_dash_today_done.setObjectName("MetricValue")
        self.label_dash_today_done.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        card_today_done_box.addWidget(self.label_dash_today_done, 1)
        dash_cards_grid.addWidget(self.card_dash_today_done, 1, 0)

        self.card_dash_speed = QFrame()
        self.card_dash_speed.setObjectName("DashboardCard")
        card_speed_box = QVBoxLayout(self.card_dash_speed)
        card_speed_box.setContentsMargins(14, 12, 14, 12)
        card_speed_box.setSpacing(6)
        card_speed_box.addWidget(QLabel("AVG TRANSCRIBE SPEED", objectName="DashboardMicroLabel"))
        self.label_dash_speed = QLabel("오디오 1분 -> 약 -")
        self.label_dash_speed.setObjectName("DashboardSpeedValue")
        self.label_dash_speed.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_dash_speed.setWordWrap(True)
        card_speed_box.addWidget(self.label_dash_speed, 1)
        dash_cards_grid.addWidget(self.card_dash_speed, 1, 1)

        dash_layout.addWidget(dash_cards, 0)

        self.dashboard_recent_card = QFrame()
        self.dashboard_recent_card.setObjectName("DashboardCard")
        recent_box = QVBoxLayout(self.dashboard_recent_card)
        recent_box.setContentsMargins(14, 12, 14, 12)
        recent_box.setSpacing(8)
        recent_box.addWidget(QLabel("RECENT COMPLETIONS", objectName="DashboardMicroLabel"))

        self.dashboard_recent_table = QTableWidget(0, 2)
        self.dashboard_recent_table.setObjectName("DashboardRecentTable")
        self.dashboard_recent_table.setHorizontalHeaderLabels(["파일명", "완료 시각"])
        self.dashboard_recent_table.verticalHeader().setVisible(False)
        self.dashboard_recent_table.horizontalHeader().setStretchLastSection(False)
        self.dashboard_recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.dashboard_recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.dashboard_recent_table.setColumnWidth(1, 170)
        self.dashboard_recent_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.dashboard_recent_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dashboard_recent_table.setShowGrid(False)
        self.dashboard_recent_table.setFocusPolicy(Qt.NoFocus)
        self.dashboard_recent_table.setAlternatingRowColors(False)
        self.dashboard_recent_table.setWordWrap(False)
        self.dashboard_recent_table.setTextElideMode(Qt.ElideRight)
        recent_box.addWidget(self.dashboard_recent_table, 1)

        dash_layout.addWidget(self.dashboard_recent_card, 1)





        self.main_stack.addWidget(dash_page)











        folder_page = QWidget()
        folder_layout = QVBoxLayout(folder_page)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(10)

        folder_top_card = QFrame()
        folder_top_card.setObjectName("DashboardCard")
        folder_top_box = QVBoxLayout(folder_top_card)
        folder_top_box.setContentsMargins(14, 12, 14, 12)
        folder_top_box.setSpacing(8)
        folder_top_box.addWidget(QLabel("CURRENT FOLDER", objectName="DashboardMicroLabel"))

        folder_path_row = QHBoxLayout()
        folder_path_row.setContentsMargins(0, 0, 0, 0)
        folder_path_row.setSpacing(8)
        self.label_folders_current_path = QLabel("미설정")
        self.label_folders_current_path.setObjectName("PathLabel")
        self.label_folders_current_path.setMinimumHeight(34)
        self.label_folders_current_path.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        folder_path_row.addWidget(self.label_folders_current_path, 1)

        self.btn_folders_open = QPushButton("폴더 열기")
        self.btn_folders_open.setProperty("uiRole", "controlOutline")
        self.btn_folders_open.setFixedHeight(34)
        folder_path_row.addWidget(self.btn_folders_open, 0)

        self.btn_folders_refresh = QPushButton("새로고침")
        self.btn_folders_refresh.setProperty("uiRole", "controlOutline")
        self.btn_folders_refresh.setFixedHeight(34)
        folder_path_row.addWidget(self.btn_folders_refresh, 0)

        folder_top_box.addLayout(folder_path_row)
        folder_layout.addWidget(folder_top_card, 0)

        folder_table_card = QFrame()
        folder_table_card.setObjectName("DashboardCard")
        folder_table_box = QVBoxLayout(folder_table_card)
        folder_table_box.setContentsMargins(14, 12, 14, 12)
        folder_table_box.setSpacing(8)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)

        self.btn_folders_filter_all = QPushButton("전체")
        self.btn_folders_filter_done = QPushButton("완료")
        self.btn_folders_filter_pending = QPushButton("미완료")
        self.btn_folders_filter_result_only = QPushButton("결과만")
        for _btn in (
            self.btn_folders_filter_all,
            self.btn_folders_filter_done,
            self.btn_folders_filter_pending,
            self.btn_folders_filter_result_only,
        ):
            _btn.setProperty("uiRole", "controlOutline")
            _btn.setFixedHeight(34)
            _btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            _btn.setMinimumWidth(_btn.fontMetrics().horizontalAdvance(_btn.text()) + 26)
            filter_row.addWidget(_btn, 0)
        filter_row.addStretch(1)
        folder_table_box.addLayout(filter_row)

        self.folders_table = QTableWidget(0, 4)
        self.folders_table.setObjectName("FolderFilesTable")
        self.folders_table.setHorizontalHeaderLabels(["파일명", "유형", "전사 상태", "수정일"])
        self.folders_table.verticalHeader().setVisible(False)
        self.folders_table.horizontalHeader().setStretchLastSection(False)
        self.folders_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.folders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.folders_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.folders_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.folders_table.setColumnWidth(1, 90)
        self.folders_table.setColumnWidth(2, 100)
        self.folders_table.setColumnWidth(3, 160)
        self.folders_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.folders_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.folders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.folders_table.setAlternatingRowColors(False)
        self.folders_table.setShowGrid(False)
        self.folders_table.setWordWrap(False)
        self.folders_table.setTextElideMode(Qt.ElideRight)
        self.folders_table.setFocusPolicy(Qt.NoFocus)
        self.folders_table.setSortingEnabled(False)
        folders_header = self.folders_table.horizontalHeader()
        folders_header.setSortIndicatorShown(True)
        folders_header.setSectionsClickable(True)
        folders_header.setSortIndicator(0, Qt.AscendingOrder)
        folder_table_box.addWidget(self.folders_table, 1)

        folder_layout.addWidget(folder_table_card, 1)

        folder_preview_card = QFrame()
        folder_preview_card.setObjectName("DashboardCard")
        folder_preview_box = QVBoxLayout(folder_preview_card)
        folder_preview_box.setContentsMargins(14, 12, 14, 12)
        folder_preview_box.setSpacing(8)

        preview_header = QHBoxLayout()
        preview_header.setContentsMargins(0, 0, 0, 0)
        preview_header.setSpacing(8)
        preview_header.addWidget(QLabel("TXT PREVIEW", objectName="DashboardMicroLabel"), 1)
        preview_header.addStretch(1)

        self.btn_folders_preview_full = QPushButton("전체 보기")
        preview_btn_width = max(96, self.btn_folders_preview_full.fontMetrics().horizontalAdvance("전체 보기") + 32)
        self.btn_folders_preview_full.setFixedWidth(preview_btn_width)
        self.btn_folders_preview_full.setFixedHeight(34)
        preview_header.addWidget(self.btn_folders_preview_full, 0)
        folder_preview_box.addLayout(preview_header)

        self.text_folders_preview = QTextEdit()
        self.text_folders_preview.setObjectName("FolderPreviewText")
        self.text_folders_preview.setReadOnly(True)
        self.text_folders_preview.setPlaceholderText("TXT 파일을 선택하면 미리보기가 표시됩니다.")
        self.text_folders_preview.setMinimumHeight(150)
        folder_preview_box.addWidget(self.text_folders_preview, 1)

        folder_layout.addWidget(folder_preview_card, 0)

        self.main_stack.addWidget(folder_page)











        self._apply_status_and_meta_labels()





        self._refresh_path_labels()











        self.btn_target.clicked.connect(self.select_target_folder)





        self.btn_load_files.clicked.connect(self.load_mp3_files)





        self.btn_move_files.clicked.connect(self.move_selected_files)





        self.btn_move_and_transcribe.clicked.connect(self.move_selected_files_and_start_transcribe)





        self.btn_transcribe_target.clicked.connect(self.start_transcribe_on_target_folder)





        self.btn_stop_now.clicked.connect(self.request_immediate_stop)





        self.file_queue_table.cellDoubleClicked.connect(self._on_filename_double_clicked)





        self.btn_filter_all.clicked.connect(self._mark_all_queue_checked)





        self.btn_uncheck_all.clicked.connect(self._uncheck_all_queue)





        self.btn_clear_all.clicked.connect(self._clear_all_queue_rows)





        self.btn_clear_done.clicked.connect(self._clear_done_queue_rows)

        self.btn_folders_open.clicked.connect(self.open_preferred_folder)
        self.btn_folders_refresh.clicked.connect(self.refresh_folder_management_view)
        self.btn_folders_filter_all.clicked.connect(lambda: self._set_folder_filter_mode("all"))
        self.btn_folders_filter_done.clicked.connect(lambda: self._set_folder_filter_mode("complete"))
        self.btn_folders_filter_pending.clicked.connect(lambda: self._set_folder_filter_mode("incomplete"))
        self.btn_folders_filter_result_only.clicked.connect(lambda: self._set_folder_filter_mode("result_only"))
        self.folders_table.horizontalHeader().sectionClicked.connect(self._handle_folders_table_header_clicked)
        self.folders_table.itemSelectionChanged.connect(self._handle_folders_table_selection_changed)
        self.folders_table.cellClicked.connect(self._handle_folders_table_cell_clicked)
        self.folders_table.itemClicked.connect(self._handle_folders_table_item_clicked)
        self.btn_folders_preview_full.clicked.connect(self._show_folders_preview_full_text)





        self.chk_notify_each_file.stateChanged.connect(self.save_ui_preferences)





        self.chk_notify_total.stateChanged.connect(self.save_ui_preferences)

        self.upload_drive_checkbox.stateChanged.connect(self.save_ui_preferences)
        self.combo_transcribe_course.currentTextChanged.connect(self.save_ui_preferences)
        self.combo_transcribe_subject.currentTextChanged.connect(self.save_ui_preferences)
        self.combo_transcribe_course.currentTextChanged.connect(self.save_ui_preferences)
        self.combo_transcribe_subject.currentTextChanged.connect(self.save_ui_preferences)





        self.shutdown_checkbox.stateChanged.connect(self._sync_shutdown_wait_combo_state)





        self.shutdown_checkbox.stateChanged.connect(self.save_ui_preferences)





        self.shutdown_wait_combo.currentIndexChanged.connect(self.save_ui_preferences)
        self.combo_transcription_engine.currentIndexChanged.connect(self._on_transcription_engine_changed)
        self.input_colab_url.textChanged.connect(self._on_colab_url_text_changed)
        self.btn_colab_check.clicked.connect(self._handle_colab_connection_check)





        self.tab_transcriptions.clicked.connect(lambda: self._switch_main_tab("transcriptions"))





        self.tab_dashboard.clicked.connect(lambda: self._switch_main_tab("dashboard"))





        self.tab_folders.clicked.connect(lambda: self._switch_main_tab("folders"))











        self._sync_shutdown_wait_combo_state()
        self._sync_transcription_engine_ui_state()





        self._switch_main_tab("transcriptions")





        self._sync_log_panel_state()





        self._refresh_file_list_empty_state()











    def apply_styles(self):





        self.setStyleSheet(





            """





            QWidget {





                font-family: "Malgun Gothic", "Segoe UI", "NanumGothic", sans-serif;





                color: #1a1b21;





                font-size: 13px;





            }





            QWidget#RootWindow {





                background: #f8fafc;





            }





            QFrame#ContentWrap,





            QFrame#MainPane {





                background: #f8fafc;





            }





            QWidget#TransPage,





            QWidget#TransScrollViewport,





            QWidget#DashboardTopCards {





                background: #f8fafc;





            }





            QFrame#TopAppBar {





                background: #ffffff;





                border-bottom: 1px solid #e2e8f0;





            }





            QLabel#TopBrandText {





                color: #00236f;





                font-size: 20px;





                font-weight: 700;





            }





            QPushButton#TopTabButton {





                border: none;





                border-bottom: 2px solid transparent;





                border-radius: 0px;





                padding: 0 12px;





                color: #64748b;





                background: transparent;





                font-size: 14px;





                font-weight: 600;





            }





            QPushButton#TopTabButton:hover {





                background: #f8fafc;





            }





            QPushButton#TopTabButton[active="true"] {





                color: #1d4ed8;





                border-bottom: 2px solid #1d4ed8;





            }





            QFrame#SidebarPane {





                background: #f8fafc;





                border-right: 1px solid #e2e8f0;





            }





            QWidget#SidebarContent {





                background: #f8fafc;





            }





            QScrollArea#SidebarScroll,





            QScrollArea#TransScrollArea {





                background: transparent;





                border: none;





            }





            QFrame#SidebarCard,





            QGroupBox#SidebarCard {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





            }





            QLabel#SectionTitle {





                color: #334155;





                font-size: 14px;





                font-weight: 700;





            }





            QLabel#PathTitle {





                color: #64748b;





                font-size: 11px;





                font-weight: 700;





                letter-spacing: 0.8px;





            }





            QLabel#PathLabel {





                background: #f8fafc;





                border: 1px solid #f1f5f9;





                border-radius: 2px;





                padding: 0 8px;





                color: #475569;





                font-size: 12px;





            }





            QLabel#PathLabel[empty="true"] {





                color: #94a3b8;





            }





            QPushButton {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





                color: #334155;





                padding: 8px 12px;





                font-size: 13px;





            }





            QPushButton[uiRole="side"] {





                border-color: #e2e8f0;





            }





            QPushButton[uiRole="sideOutline"] {





                border: 1px solid #00236f;





                color: #00236f;





                background: #ffffff;





            }





            QPushButton[uiRole="sideOutline"]:hover {





                background: #eff6ff;





            }





            QPushButton[uiRole="logToggle"] {





                background: #1e3a8a;





                color: #ffffff;





                border: 1px solid #1e3a8a;





            }





            QPushButton[uiRole="logToggle"]:hover {





                background: #1d4ed8;





            }





            QLabel#LogCollapsedHint {





                color: #64748b;





                font-size: 12px;





            }





            QLabel#LogCollapsedSubHint {





                color: #64748b;





                font-size: 12px;





            }





            QTextEdit#LogViewer {





                border: 1px solid #0f172a;





                border-radius: 2px;





                background: #0f172a;





                color: rgba(255,255,255,0.6);





                font-size: 12px;





                line-height: 28px;





                selection-background-color: #1e293b;





            }





            QGroupBox#DashboardSection,





            QGroupBox#FileQueueSection,





            QGroupBox#ControlSection {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





            }





            QFrame#DashboardCard {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





            }





            QLabel#StatusIconBubble {





                background: #eff6ff;





                border-radius: 20px;





                color: #00236f;





                font-size: 24px;





                font-weight: 600;





            }





            QLabel#EtaIconBubble {





                background: #fff7ed;





                border-radius: 20px;





                color: #f39461;





                font-size: 24px;





                font-weight: 600;





            }





            QLabel#DashboardMicroLabel {





                color: #64748b;





                font-size: 11px;





                font-weight: 700;





                letter-spacing: 0.6px;





            }





            QLabel#StatusPrimary {





                color: #1e3a8a;





                font-size: 20px;





                font-weight: 700;





            }





            QLabel#StatusSecondary {





                color: #1e293b;





                font-size: 14px;





                font-weight: 600;





            }





            QLabel#MetricValue {





                color: #1e3a8a;





                font-size: 28px;





                font-weight: 700;





            }





            QLabel#MetricDoneHint {





                color: #94a3b8;





                font-size: 11px;





                font-weight: 700;





                letter-spacing: 0.6px;





            }





            QLabel#MetricEtaValue {





                color: #1e293b;





                font-size: 20px;





                font-weight: 700;





            }





            QLabel#DashboardSpeedValue {
                color: #1e3a8a;
                font-size: 18px;
                font-weight: 700;
            }

            QLabel#CurrentProgressValue {





                color: #00236f;





                font-size: 12px;





                font-weight: 700;





            }





            QLabel#MetaCompactValue {





                color: #1e293b;





                font-size: 12px;





                font-weight: 600;





            }





            QLabel#QueueTitle {





                color: #1e293b;





                font-size: 20px;





                font-weight: 600;





            }





            QPushButton#QueueHeaderButton {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





                color: #334155;





                font-size: 12px;





                padding: 2px 10px;





            }





            QPushButton#QueueHeaderButton:hover {





                background: #f8fafc;





            }





            QPushButton#QueueHeaderButtonDanger {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





                color: #ba1a1a;





                font-size: 12px;





                padding: 2px 10px;





            }





            QPushButton#QueueHeaderButtonDanger:hover {





                background: #fff0f0;





            }





            QPushButton#QueueHeaderButtonDanger:disabled {





                color: #e2b4b4;





                border-color: #f1f5f9;





            }





            QPushButton#QueueRemoveButton {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





                color: #64748b;





                padding: 0;





                font-size: 11px;





                font-weight: 700;





            }





            QPushButton#QueueRemoveButton:hover {





                background: #f8fafc;





            }





            QTableWidget#FileQueueTable,
            QTableWidget#DashboardRecentTable,
            QTableWidget#FolderFilesTable {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





                gridline-color: #f8fafc;





                selection-background-color: #ffffff;





                selection-color: #1a1b21;





                outline: 0;





            }





            QTableWidget#FileQueueTable::item,
            QTableWidget#FileQueueTable::item:selected,
            QTableWidget#FileQueueTable::item:focus,
            QTableWidget#DashboardRecentTable::item,
            QTableWidget#DashboardRecentTable::item:selected,
            QTableWidget#DashboardRecentTable::item:focus,
            QTableWidget#FolderFilesTable::item,
            QTableWidget#FolderFilesTable::item:focus {





                border: none;





                color: #1a1b21;





            }

            QTableWidget#FolderFilesTable::item:selected,
            QTableWidget#FolderFilesTable::item:selected:active,
            QTableWidget#FolderFilesTable::item:selected:!active {
                background: #eff6ff;
                color: #1a1b21;
                border: none;
                outline: 0;
            }





            QTableWidget#FileQueueTable QLineEdit {





                background: #ffffff;





                color: #1a1b21;





                border: 1px solid #cbd5e1;





                selection-background-color: #dbeafe;





                selection-color: #1a1b21;





                padding: 2px 6px;





            }

            QTextEdit#FolderPreviewText {
                border: 1px solid #e2e8f0;
                border-radius: 2px;
                background: #ffffff;
                color: #1a1b21;
                selection-background-color: #dbeafe;
                selection-color: #1a1b21;
                font-size: 12px;
            }





            QWidget#CheckboxCell, QWidget#ActionCell, QWidget#BadgeCell {





                background: transparent;





            }





            QHeaderView::section {





                background: #ffffff;





                color: #64748b;





                border: none;





                border-bottom: 1px solid #e2e8f0;





                padding: 8px 22px 8px 6px;
                margin: 0;





                font-size: 11px;





                font-weight: 700;





                text-transform: uppercase;


            }

            QHeaderView::up-arrow,
            QHeaderView::down-arrow {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 10px;
                height: 10px;
                right: 6px;
            }

            QTableWidget#FileQueueTable QHeaderView::section {
                padding: 8px 6px;
            }





            QLabel#FileEmptyState {





                color: #94a3b8;





                font-size: 14px;





                border: none;





                background: transparent;





            }





            QPushButton[uiRole="controlPrimary"] {





                border: 1px solid #00236f;





                background: #00236f;





                color: #ffffff;





            }





            QPushButton[uiRole="controlPrimary"]:hover {





                background: #1e3a8a;





            }





            QPushButton[uiRole="controlOutlinePrimary"],





            QPushButton[uiRole="controlOutline"] {





                border: 1px solid #00236f;





                background: #ffffff;





                color: #00236f;





            }





            QPushButton[uiRole="controlOutlinePrimary"]:hover,





            QPushButton[uiRole="controlOutline"]:hover {





                background: #eff6ff;





            }





            QPushButton[uiRole="controlGhost"] {





                border: 1px solid #e2e8f0;





                background: #f1f5f9;





                color: #94a3b8;





            }





            QPushButton:disabled {





                border: 1px solid #cbd5e1;





                background: #f1f5f9;





                color: #64748b;





            }





            QCheckBox {





                spacing: 8px;





                color: #334155;





                font-size: 13px;





            }





            QCheckBox::indicator {





                width: 16px;





                height: 16px;





            }





            QComboBox#ShutdownWaitCombo {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





                color: #334155;





                padding: 0 10px;





                min-height: 34px;





            }





            QComboBox#ShutdownWaitCombo::drop-down {





                border: none;





                width: 24px;





            }





            QComboBox#ShutdownWaitCombo QAbstractItemView {





                border: 1px solid #e2e8f0;





                background: #ffffff;





                color: #334155;





                selection-background-color: #eff6ff;





                selection-color: #1e40af;





            }





            QComboBox#ShutdownWaitCombo:disabled {





                border: 1px solid #cbd5e1;





                background: #f1f5f9;





                color: #94a3b8;





            }

            QComboBox#TranscriptionEngineCombo,
            QLineEdit#ColabUrlInput {
                border: 1px solid #94a3b8;
                border-radius: 2px;
                background: #ffffff;
                color: #334155;
                padding: 0 8px;
                min-height: 32px;
            }

            QComboBox#TranscriptionEngineCombo:hover,
            QLineEdit#ColabUrlInput:hover {
                border: 1px solid #94a3b8;
            }

            QComboBox#TranscriptionEngineCombo:focus,
            QLineEdit#ColabUrlInput:focus {
                border: 1px solid #334155;
            }

            QComboBox#TranscriptionEngineCombo::drop-down {
                border: none;
                width: 24px;
            }

            QComboBox#TranscriptionEngineCombo QAbstractItemView {
                border: 1px solid #cbd5e1;
                background: #ffffff;
                color: #334155;
                outline: 0;
                padding: 2px 0;
                selection-background-color: #e2e8f0;
                selection-color: #1e293b;
            }

            QComboBox#TranscriptionEngineCombo QAbstractItemView::item {
                min-height: 28px;
                padding: 4px 10px;
                border: none;
                background: #ffffff;
                color: #334155;
            }

            QComboBox#TranscriptionEngineCombo QAbstractItemView::item:hover {
                background: #f1f5f9;
                color: #0f172a;
            }

            QComboBox#TranscriptionEngineCombo QAbstractItemView::item:selected {
                background: #e2e8f0;
                color: #0f172a;
            }

            QComboBox#TranscriptionEngineCombo QAbstractItemView::item:selected:hover {
                background: #cbd5e1;
                color: #0f172a;
            }

            QComboBox#TranscriptionEngineCombo:disabled,
            QLineEdit#ColabUrlInput:disabled {
                border: 1px solid #e2e8f0;
                background: #f8fafc;
                color: #94a3b8;
            }

            QLabel#TranscriptionModeLabel {
                color: #334155;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.2px;
            }

            QPushButton#ColabCheckButton[connected="true"] {
                border: 1px solid #16a34a;
                background: #dcfce7;
                color: #166534;
                font-weight: 600;
            }

            QPushButton#ColabCheckButton[connected="true"]:hover {
                border: 1px solid #15803d;
                background: #bbf7d0;
                color: #14532d;
            }





            QProgressBar {





                background: #f1f5f9;





                border: none;





                border-radius: 7px;





                min-height: 14px;





                max-height: 14px;





            }





            QProgressBar::chunk {





                background: #00236f;





                border-radius: 6px;





            }





            QFrame#PlaceholderCard {





                border: 1px solid #e2e8f0;





                border-radius: 2px;





                background: #ffffff;





            }





            QLabel#PlaceholderText {





                color: #64748b;





                font-size: 14px;





            }





            """





        )











    def _setup_checkbox_indicator_style(self):





        self.checkbox_indicator_style = CheckboxIndicatorStyle(self.style())





        for cb in (self.chk_notify_each_file, self.chk_notify_total, self.upload_drive_checkbox, self.shutdown_checkbox):





            cb.setStyle(self.checkbox_indicator_style)











    def _switch_main_tab(self, tab_name: str):





        mapping = {





            "transcriptions": 0,





            "dashboard": 1,





            "folders": 2,





        }





        if tab_name not in mapping:





            tab_name = "transcriptions"





        self.current_tab_name = tab_name





        self.main_stack.setCurrentIndex(mapping[tab_name])
        if tab_name == "dashboard":
            self.refresh_dashboard_view()
        elif tab_name == "folders":
            self.refresh_folder_management_view()











        state_map = {





            "transcriptions": self.tab_transcriptions,





            "dashboard": self.tab_dashboard,





            "folders": self.tab_folders,





        }





        for name, btn in state_map.items():





            active = name == tab_name





            btn.setProperty("active", active)





            btn.setChecked(active)





            btn.style().unpolish(btn)





            btn.style().polish(btn)





            btn.update()











    def _detect_duration_mmss(self, file_path: str) -> str:





        duration_sec = None





        try:





            from mutagen.mp3 import MP3  # type: ignore





            duration_sec = float(MP3(file_path).info.length)





        except Exception:





            pass











        if not duration_sec or duration_sec <= 0:





            try:





                from tinytag import TinyTag  # type: ignore





                val = TinyTag.get(file_path).duration





                if val:





                    duration_sec = float(val)





            except Exception:





                pass











        if duration_sec and duration_sec > 0:





            total = int(round(duration_sec))





            m, s = divmod(total, 60)





            return f"{m:02d}:{s:02d}"











        return self._detect_duration_raw_mp3(file_path)











    def _detect_duration_raw_mp3(self, file_path: str) -> str:





        """MP3 프레임 헤더 직접 파싱으로 재생 시간 추정 (외부 라이브러리 불필요)."""





        BITRATE_IDX = {





            (3, 1): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],





            (2, 1): [0,  8, 16, 24, 32, 40, 48, 56,  64,  80,  96, 112, 128, 144, 160, 0],





            (0, 1): [0,  8, 16, 24, 32, 40, 48, 56,  64,  80,  96, 112, 128, 144, 160, 0],





        }





        SAMPLE_RATE = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}





        try:





            file_size = os.path.getsize(file_path)





            with open(file_path, "rb") as f:





                head = f.read(10)





                audio_start = 0





                if head[:3] == b"ID3":





                    sz = head[6:10]





                    id3_size = (





                        (sz[0] & 0x7F) << 21 | (sz[1] & 0x7F) << 14 |





                        (sz[2] & 0x7F) << 7  | (sz[3] & 0x7F)





                    )





                    audio_start = 10 + id3_size





                    f.seek(audio_start)





                else:





                    f.seek(0)





                chunk = f.read(8192)





            sync = -1





            for i in range(len(chunk) - 3):





                if chunk[i] == 0xFF and (chunk[i + 1] & 0xE0) == 0xE0:





                    sync = i





                    break





            if sync < 0:





                return "-"





            b = chunk[sync: sync + 4]





            ver   = (b[1] >> 3) & 0x3   # 3=MPEG1, 2=MPEG2, 0=MPEG2.5





            layer = (b[1] >> 1) & 0x3   # 1=LayerIII(MP3)





            if layer != 1:





                return "-"





            bi  = (b[2] >> 4) & 0xF





            sri = (b[2] >> 2) & 0x3





            bitrates   = BITRATE_IDX.get((ver, layer))





            sample_rates = SAMPLE_RATE.get(ver)





            if not bitrates or bi >= len(bitrates) or bitrates[bi] == 0:





                return "-"





            if not sample_rates or sri >= len(sample_rates):





                return "-"





            bitrate_kbps = bitrates[bi]





            audio_bytes  = file_size - audio_start





            dur = (audio_bytes * 8) / (bitrate_kbps * 1000)





            if dur <= 0:





                return "-"





            m, s = divmod(int(round(dur)), 60)





            return f"{m:02d}:{s:02d}"





        except Exception:





            return "-"











    def _status_badge_widget(self, status: str) -> QWidget:





        shown = status if status in QUEUE_STATUS_STYLE else QUEUE_STATUS_WAITING





        bg, fg = QUEUE_STATUS_STYLE[shown]





        badge = QLabel(shown)





        badge.setAlignment(Qt.AlignCenter)





        badge.setFixedSize(88, 26)





        badge.setStyleSheet(





            f"""





            QLabel {{





                background: {bg};





                color: {fg};





                border-radius: 4px;





                padding: 0px 6px;





                font-size: 10px;





                font-weight: 700;





            }}





            """





        )





        container = QWidget()





        container.setObjectName("BadgeCell")





        lay = QHBoxLayout(container)





        lay.setContentsMargins(0, 0, 0, 0)





        lay.addStretch()





        lay.addWidget(badge)





        lay.addStretch()





        return container











    def _on_queue_item_changed(self, item: QTableWidgetItem):





        if item is None:





            return





        row_idx = item.row()





        if row_idx < 0 or row_idx >= len(self.file_queue_rows):





            return





        col = item.column()





        if col == 0:





            self.file_queue_rows[row_idx]["checked"] = item.checkState() == Qt.Checked





            QTimer.singleShot(0, self._clear_file_queue_selection)





        elif col == 1:





            self._handle_filename_item_changed(row_idx, item)











    def _clear_file_queue_selection(self):





        self.file_queue_table.clearSelection()





        self.file_queue_table.setCurrentCell(-1, -1)





        self.file_queue_table.viewport().update()











    def _refresh_file_queue_table(self):





        self.file_queue_table.blockSignals(True)





        if self._queue_item_signal_bound:





            self.file_queue_table.itemChanged.disconnect(self._on_queue_item_changed)





            self._queue_item_signal_bound = False





        self.file_queue_table.setRowCount(len(self.file_queue_rows))





        mono = QFont("Consolas", 10)





        if mono.family().lower() != "consolas":





            mono = QFont("Courier New", 10)











        for row_idx, row_data in enumerate(self.file_queue_rows):





            is_checked = row_data.get("checked", False)





            row_bg = self._row_bg(row_data)











            # 컬럼 0: 체크박스 셀 위젯 (커스텀 스타일 적용)





            cb = QCheckBox()





            cb.setChecked(is_checked)





            cb.setStyle(self.checkbox_indicator_style)





            cb.setFixedSize(18, 18)





            cb.stateChanged.connect(





                lambda state, r=row_idx: self._on_cell_checkbox_changed(r, state)





            )





            cb_container = QWidget()





            cb_container.setObjectName("CheckboxCell")





            cb_lay = QHBoxLayout(cb_container)





            cb_lay.setContentsMargins(0, 0, 0, 0)





            cb_lay.addStretch()





            cb_lay.addWidget(cb)





            cb_lay.addStretch()





            self.file_queue_table.setCellWidget(row_idx, 0, cb_container)











            # 컬럼 1: 파일명





            file_name = row_data.get("filename", "")





            file_item = QTableWidgetItem(file_name)





            file_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)





            original_fname = str(row_data.get("original_filename", file_name))





            file_item.setToolTip(f"\uC6D0\uBCF8: {original_fname}" if original_fname != file_name else file_name)





            file_item.setBackground(QColor(row_bg))





            self.file_queue_table.setItem(row_idx, 1, file_item)











            # 컬럼 2: Duration





            duration = row_data.get("duration", "-")





            duration_item = QTableWidgetItem(duration)





            duration_item.setFlags(Qt.ItemIsEnabled)





            duration_item.setTextAlignment(Qt.AlignCenter)





            duration_item.setFont(mono)





            duration_item.setBackground(QColor(row_bg))





            self.file_queue_table.setItem(row_idx, 2, duration_item)











            # 컬럼 3: 상태 배지





            status = row_data.get("status", QUEUE_STATUS_WAITING)





            badge_widget = self._status_badge_widget(status)





            self.file_queue_table.setCellWidget(row_idx, 3, badge_widget)











            # 컬럼 4: 제거 버튼 (중앙 정렬 컨테이너)





            remove_btn = QPushButton("✕")





            remove_btn.setObjectName("QueueRemoveButton")





            remove_btn.setFixedSize(28, 28)





            remove_btn.clicked.connect(





                lambda _checked=False, fn=file_name: self._remove_queue_row(fn)





            )





            btn_container = QWidget()





            btn_container.setObjectName("ActionCell")





            btn_lay = QHBoxLayout(btn_container)





            btn_lay.setContentsMargins(0, 0, 0, 0)





            btn_lay.addStretch()





            btn_lay.addWidget(remove_btn)





            btn_lay.addStretch()





            self.file_queue_table.setCellWidget(row_idx, 4, btn_container)





            self.file_queue_table.setRowHeight(
                row_idx, int(getattr(self, "file_queue_row_height", 36))
            )











        self.file_queue_table.blockSignals(False)





        self.file_queue_table.itemChanged.connect(self._on_queue_item_changed)





        self._queue_item_signal_bound = True





        self._clear_file_queue_selection()





        self._refresh_file_list_empty_state()





        self._update_checked_state()











    def _row_bg(self, row_data: dict) -> str:





        if row_data.get("status") == QUEUE_STATUS_DONE:





            return "#f0fdf4"





        return "#eff6ff" if row_data.get("checked", False) else "#ffffff"











    def _on_cell_checkbox_changed(self, row_idx: int, state: int):





        if row_idx < 0 or row_idx >= len(self.file_queue_rows):





            return





        is_checked = bool(state)





        self.file_queue_rows[row_idx]["checked"] = is_checked





        row_bg = self._row_bg(self.file_queue_rows[row_idx])





        for col in (1, 2):





            item = self.file_queue_table.item(row_idx, col)





            if item:





                item.setBackground(QColor(row_bg))





        self._update_checked_state()











    def _update_checked_state(self):
        checked_count = sum(1 for r in self.file_queue_rows if r.get("checked", False))
        total = self.loaded_mp3_count
        has_files = bool(self.file_queue_rows)

        if checked_count > 0:
            self.label_file_count.setText(
                f"\uBD88\uB7EC\uC628 MP3 \uD30C\uC77C \uC218: {total}\uAC1C | \uC120\uD0DD: {checked_count}\uAC1C"
            )
        else:
            self.label_file_count.setText(f"\uBD88\uB7EC\uC628 MP3 \uD30C\uC77C \uC218: {total}\uAC1C")

        running = self._is_transcribe_running()

        self.btn_filter_all.setEnabled(has_files and not running)
        self.btn_uncheck_all.setEnabled(has_files and not running)
        self.btn_clear_all.setEnabled(has_files and not running)
        self.btn_transcribe_target.setEnabled(has_files and not running)
        self.btn_move_files.setEnabled(checked_count > 0 and not running)
        self.btn_move_and_transcribe.setEnabled(bool(self.moved_transcribe_items) and not running)

    def _remove_queue_row(self, file_name: str):





        target = os.path.basename(file_name).lower()





        self.file_queue_rows = [





            row





            for row in self.file_queue_rows





            if os.path.basename(str(row.get("filename", ""))).lower() != target





        ]





        self.loaded_mp3_count = len(self.file_queue_rows)





        self.label_file_count.setText(f"불러온 MP3 파일 수: {self.loaded_mp3_count}개")





        self._refresh_file_queue_table()





        self.update_total_progress_display()











    def _set_queue_status_by_name(self, file_name: str, status: str):





        target_keys = self._queue_name_keys(file_name)





        if not target_keys:





            return





        if status == QUEUE_STATUS_PROCESSING:





            for row in self.file_queue_rows:





                if row.get("status") == QUEUE_STATUS_PROCESSING:





                    row["status"] = QUEUE_STATUS_WAITING





        updated = False





        for row in self.file_queue_rows:





            row_keys = set()





            row_keys.update(self._queue_name_keys(str(row.get("filename", ""))))





            row_keys.update(self._queue_name_keys(str(row.get("transcribe_name", ""))))





            if row_keys & target_keys:





                row["status"] = status





                updated = True





                break





        if updated:





            self._refresh_file_queue_table()

    def _mark_processing_rows_as_stop(self):
        updated = False
        for row in self.file_queue_rows:
            if row.get("status") == QUEUE_STATUS_PROCESSING:
                row["status"] = QUEUE_STATUS_STOP
                updated = True
        if updated:
            self._refresh_file_queue_table()











    def _queue_name_keys(self, file_name: str) -> set[str]:





        base = os.path.basename(str(file_name or "")).strip()





        if not base:





            return set()





        keys = {base.lower()}





        keys.add(os.path.basename(remove_page_suffix(base)).strip().lower())





        return {k for k in keys if k}











    def _find_queue_row_by_filename(self, file_name: str):





        target = os.path.basename(str(file_name or "")).strip().lower()





        if not target:





            return None





        for row in self.file_queue_rows:





            current = os.path.basename(str(row.get("filename", ""))).strip().lower()





            if current == target:





                return row





        return None











    def _mark_all_queue_checked(self):





        for row in self.file_queue_rows:





            row["checked"] = True





        self._refresh_file_queue_table()











    def _uncheck_all_queue(self):





        for row in self.file_queue_rows:





            row["checked"] = False





        self._refresh_file_queue_table()











    def _clear_done_queue_rows(self):





        self.file_queue_rows = [row for row in self.file_queue_rows if row.get("status") != QUEUE_STATUS_DONE]





        self.loaded_mp3_count = len(self.file_queue_rows)





        self.label_file_count.setText(f"불러온 MP3 파일 수: {self.loaded_mp3_count}개")





        self._refresh_file_queue_table()





        self.update_total_progress_display()











    def _clear_all_queue_rows(self):





        self.file_queue_rows = []





        self.loaded_mp3_count = 0





        self.label_file_count.setText("불러온 MP3 파일 수: 0개")





        self._refresh_file_queue_table()





        self.update_total_progress_display()











    def _on_filename_double_clicked(self, row: int, col: int):





        if col != 1 or self._is_transcribe_running():





            return





        if row < 0 or row >= len(self.file_queue_rows):





            return





        item = self.file_queue_table.item(row, col)





        if item is None:





            return





        self.file_queue_table.editItem(item)
        QTimer.singleShot(0, self._disable_filename_editor_context_menu)

    def _disable_filename_editor_context_menu(self):
        for editor in self.file_queue_table.findChildren(QLineEdit):
            editor.setContextMenuPolicy(Qt.NoContextMenu)











    def _handle_filename_item_changed(self, row_idx: int, item: QTableWidgetItem):





        new_text = item.text().strip()





        row_data = self.file_queue_rows[row_idx]





        old_name = str(row_data.get("filename", "")).strip()





        if not new_text or new_text == old_name:





            self.file_queue_table.blockSignals(True)





            item.setText(old_name)





            self.file_queue_table.blockSignals(False)





            QTimer.singleShot(0, self._refresh_file_queue_table)





            return





        if not new_text.lower().endswith(".mp3"):





            new_text += ".mp3"





        row_data["filename"] = new_text





        row_data["transcribe_name"] = new_text





        original_fname = str(row_data.get("original_filename", new_text)).strip()





        self.file_queue_table.blockSignals(True)





        item.setText(new_text)





        item.setToolTip(f"\uC6D0\uBCF8: {original_fname}" if original_fname != new_text else new_text)





        self.file_queue_table.blockSignals(False)





        self.file_queue_table.viewport().update()





        QTimer.singleShot(0, self._refresh_file_queue_table)











    def _normalize_mp3_name(self, value: str, fallback: str = "") -> str:





        name = os.path.basename(str(value or "").strip())





        if not name:





            name = os.path.basename(str(fallback or "").strip())





        if not name:





            return ""





        if not name.lower().endswith(".mp3"):





            name += ".mp3"





        return name











    def _resolve_transcribe_name_by_priority(self, row: dict, source_path: str = "") -> str:
        source_base = os.path.basename(source_path) if source_path else ""
        stored_original = self._normalize_mp3_name(
            str(row.get("original_filename", "")),
            source_base or str(row.get("filename", "")),
        )
        source_name = self._normalize_mp3_name(source_base, stored_original)
        edited_name = self._normalize_mp3_name(str(row.get("filename", "")), source_name)

        if edited_name and stored_original and edited_name.lower() != stored_original.lower():
            return edited_name

        return source_name or edited_name or stored_original

    def _collect_filename_change_previews(self, rows: list[dict]) -> list[tuple[str, str]]:
        previews: list[tuple[str, str]] = []

        for row in rows:
            src = self._normalize_saved_folder_path(row.get("source_path", ""))
            current_name = self._normalize_mp3_name(
                os.path.basename(src) if src else "",
                str(row.get("original_filename", "")) or str(row.get("filename", "")),
            )
            desired_name = self._resolve_transcribe_name_by_priority(row, src)
            original_name = self._normalize_mp3_name(
                str(row.get("original_filename", "")),
                current_name,
            )
            edited_name = self._normalize_mp3_name(
                str(row.get("filename", "")),
                current_name,
            )

            changed_by_edit = bool(
                edited_name
                and original_name
                and edited_name.lower() != original_name.lower()
            )

            if changed_by_edit and desired_name and current_name and desired_name.lower() != current_name.lower():
                previews.append((current_name, desired_name))

        return previews

    def _confirm_filename_changes(self, rows: list[dict]) -> bool:
        changed = self._collect_filename_change_previews(rows)
        if not changed:
            return True

        dialog = QDialog(self)
        dialog.setWindowTitle("\uD30C\uC77C\uBA85 \uBCC0\uACBD \uD655\uC778")
        dialog.setWindowIcon(self.windowIcon())
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet(
            """
            QDialog {
                background: #ffffff;
            }
            QLabel {
                color: #1a1b21;
            }
            QTextEdit {
                border: 1px solid #e2e8f0;
                border-radius: 2px;
                background: #ffffff;
                color: #1a1b21;
                selection-background-color: #dbeafe;
                selection-color: #1a1b21;
            }
            """
        )

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QLabel("\uC544\uB798 \uD30C\uC77C\uBA85\uC774 \uC2E4\uC81C \uD30C\uC77C\uBA85\uC73C\uB85C \uBCC0\uACBD\uB429\uB2C8\uB2E4.")
        header.setObjectName("DialogMessage")
        header.setStyleSheet("color: #1a1b21;")
        layout.addWidget(header)

        list_edit = QTextEdit()
        list_edit.setReadOnly(True)
        list_edit.setFixedHeight(min(len(changed) * 52 + 16, 280))

        def _escape_html(value: str) -> str:
            return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        preview_blocks: list[str] = []
        for orig_name, curr_name in changed:
            orig = _escape_html(orig_name)
            curr = _escape_html(curr_name)
            preview_blocks.append(
                "<div style='margin:0 0 10px 0;'>"
                f"<div style='color:#757682;'>\uC6D0\uBCF8\uBA85: {orig}</div>"
                f"<div style='color:#00236f;font-weight:700;'>\uBCC0\uACBD\uBA85: {curr}</div>"
                "</div>"
            )

        list_edit.setHtml("".join(preview_blocks))
        layout.addWidget(list_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("\uCDE8\uC18C")
        cancel_btn.setObjectName("DialogSecondaryButton")
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(dialog.reject)

        ok_btn = QPushButton("\uBCC0\uACBD \uC801\uC6A9")
        ok_btn.setObjectName("DialogPrimaryButton")
        ok_btn.setFixedHeight(36)
        ok_btn.clicked.connect(dialog.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        return dialog.exec() == QDialog.Accepted

    def _get_checked_queue_rows(self) -> list[dict]:





        checked: list[dict] = []





        self.append_log_text(f"[DBG] _get_checked_queue_rows: file_queue_rows={len(self.file_queue_rows)}개, table rows={self.file_queue_table.rowCount()}개\n", force=True)





        for row_idx, row_data in enumerate(self.file_queue_rows):





            container = self.file_queue_table.cellWidget(row_idx, 0)





            is_checked = False





            if container:





                cb = container.findChild(QCheckBox)





                if cb:





                    is_checked = cb.isChecked()





                else:





                    self.append_log_text(f"[DBG]   row {row_idx}: QCheckBox child 없음\n", force=True)





            else:





                self.append_log_text(f"[DBG]   row {row_idx}: cellWidget(0) 없음\n", force=True)





            row_data["checked"] = is_checked





            src = row_data.get("source_path", "(없음)")





            self.append_log_text(f"[DBG]   row {row_idx}: checked={is_checked}, source_path={src}\n", force=True)





            if is_checked:





                checked.append(row_data)





        self.append_log_text(f"[DBG] _get_checked_queue_rows 결과: {len(checked)}개 선택됨\n", force=True)





        return checked





    def _rebuild_queue_from_files(self, file_paths: list[str], append: bool = False):





        if not append:





            self.file_queue_rows = []





        existing_paths = set()





        for row in self.file_queue_rows:





            src = str(row.get("source_path", "")).strip()





            if not src:





                continue





            existing_paths.add(os.path.normcase(os.path.abspath(src)))





        for file_path in file_paths:





            normalized_path = self._normalize_saved_folder_path(file_path)





            if not normalized_path or not normalized_path.lower().endswith(".mp3"):





                continue





            source_key = os.path.normcase(os.path.abspath(normalized_path))





            if source_key in existing_paths:





                continue





            if self._has_existing_output_triplet(normalized_path):





                continue





            existing_paths.add(source_key)





            display_name = os.path.basename(normalized_path)





            duration = self._detect_duration_mmss(normalized_path)





            self.file_queue_rows.append(





                {





                    "filename": display_name,





                    "original_filename": display_name,





                    "source_path": normalized_path,





                    "transcribe_name": display_name,





                    "duration": duration,





                    "status": QUEUE_STATUS_WAITING,





                    "checked": False,





                }





            )





        self.loaded_mp3_count = len(self.file_queue_rows)





        self.label_file_count.setText(f"불러온 MP3 파일 수: {self.loaded_mp3_count}개")





        self._refresh_file_queue_table()











    def apply_typography_fit_defaults(self):





        # 주요 고정 높이 토큰을 강제해 1366x768에서 잘림을 방지한다.





        side_widgets = (





            self.group_settings,





            self.group_options,





            self.group_logs,





            self.label_target,





            self.btn_target,





            self.btn_load_files,





            self.chk_notify_each_file,
            self.upload_drive_checkbox,





            self.chk_notify_total,





            self.shutdown_checkbox,





        )





        for widget in side_widgets:





            widget.setMinimumWidth(0)











        for lbl in [self.label_target]:





            lbl.setMinimumHeight(36)





            lbl.setMaximumHeight(36)





            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)











        self.btn_target.setFixedHeight(36)





        self.btn_load_files.setFixedHeight(36)





        self.btn_move_and_transcribe.setFixedHeight(38)





        self.btn_transcribe_target.setFixedHeight(38)





        self.btn_move_files.setFixedHeight(34)





        self.btn_stop_now.setFixedHeight(34)











        for metric_label in (





            self.label_total_progress_text,





            self.label_total_eta,





            self.label_current_eta,





            self.label_session,





            self.label_output_source,





            self.label_session_counter,





            self.label_output_value,





        ):





            extra_pad = 6





            metric_h = metric_label.fontMetrics().lineSpacing() + extra_pad





            metric_label.setMinimumHeight(max(metric_label.minimumHeight(), metric_h))











        self.current_progress_bar.setMinimumHeight(14)





        self.current_progress_bar.setMaximumHeight(14)





        self.total_progress_bar.setMinimumHeight(14)





        self.total_progress_bar.setMaximumHeight(14)











        top_card_h = 130





        for icon in (self.status_icon, self.eta_icon):





            icon.setFixedSize(40, 40)





        self.top_cards_container.setMinimumHeight(top_card_h)





        self.top_cards_container.setMaximumHeight(top_card_h)





        for card in (self.card_status, self.card_progress, self.card_eta):





            card.setMinimumHeight(top_card_h)





            card.setMaximumHeight(top_card_h)











        detail_min_h = 175





        self.card_current.setMinimumHeight(detail_min_h)





        self.card_current.setMaximumHeight(detail_min_h)





        dashboard_h = top_card_h + detail_min_h + 34





        self.group_dashboard.setMinimumHeight(dashboard_h)





        self.group_dashboard.setMaximumHeight(dashboard_h)











        self.apply_left_section_layout_constraints()











    def apply_font_hierarchy(self):





        def _set_weight(widget, weight: int):





            f = QFont(widget.font())





            try:





                f.setWeight(QFont.Weight(weight))





            except Exception:





                # Fallback when enum conversion fails.





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











        for group in (self.group_settings, self.group_options, self.group_logs, self.group_dashboard, self.group_files, self.group_controls):





            _set_weight(group, 550)











        for lbl in (





            self.label_section_settings,





            self.label_section_options,





            self.label_section_logs,





            self.label_section_dashboard,





            self.label_section_files,





            self.label_section_controls,





        ):





            _set_weight(lbl, 600)











        for btn in (





            self.btn_target,





            self.btn_load_files,





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





            self.label_session_counter,





            self.label_output_value,





        ):





            _set_weight(lbl, 450)











        for lbl in (self.label_target,):





            _set_weight(lbl, 500)











        _set_weight(self.label_status, 550)





        _set_weight(self.label_current_file, 550)





        _set_weight(self.label_total_progress_text, 600)





        _set_weight(self.label_total_eta, 550)





        _set_weight(self.label_current_progress_text, 600)





        _set_weight(self.label_current_eta, 550)





        _set_weight(self.label_session_counter, 600)





        _set_weight(self.label_output_value, 560)





        _set_weight(self.label_file_count, 550)





        _set_weight(self.log_viewer, 400)





        self.log_viewer.document().setDefaultFont(self.log_viewer.font())











        for lbl in self.findChildren(QLabel):





            if lbl.objectName() == "MetricTitle":





                _set_weight(lbl, 600)











        for cb in (self.chk_notify_each_file, self.chk_notify_total, self.upload_drive_checkbox, self.shutdown_checkbox):





            _set_weight(cb, 500)











        log_font = QFont(self.log_viewer.font())





        try:





            log_font.setFamilies(["Malgun Gothic", "Segoe UI", "NanumGothic", "맑은 고딕"])





        except Exception:





            pass





        log_font.setPointSize(max(11, log_font.pointSize()))





        self.log_viewer.setFont(log_font)





        self.log_viewer.document().setDefaultFont(log_font)











    def apply_left_section_layout_constraints(self):





        for section in (self.group_settings, self.group_options):





            section.setMinimumHeight(0)





            section.setMaximumHeight(16777215)





            section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)





        self.group_logs.setMinimumHeight(0)





        self.group_logs.setMaximumHeight(16777215)





        self.group_logs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)











    def _elide_for_label(self, label: QLabel, text: str, mode=Qt.ElideRight) -> str:





        available = max(120, label.width() - 14)





        return label.fontMetrics().elidedText(text, mode, available)











    def _set_elided_label_text(self, label: QLabel, text: str, mode=Qt.ElideRight):





        elided = self._elide_for_label(label, text, mode)





        label.setText(elided)





        label.setToolTip(text if elided != text else "")











    def _normalize_status_value(self, text: str) -> str:





        raw = (text or "").replace("\n", " ").strip()





        if not raw:





            return "\uB300\uAE30 \uC911"











        value = raw





        _mode_statuses = ("선택 전사 완료", "전체 전사 완료", "선택 전사 진행 중", "전체 전사 진행 중")





        if raw in _mode_statuses:





            return raw











        if value.startswith("\uD604\uC7AC \uC0C1\uD0DC"):





            if ":" in value:





                value = value.split(":", 1)[1].strip()





            else:





                value = value.replace("\uD604\uC7AC \uC0C1\uD0DC", "").strip()











        value = re.sub(r"\s*\([^)]*\)\s*$", "", value).strip()











        if "\uCC98\uB9AC\uD560 \uD30C\uC77C" in value and "\uC5C6" in value:





            return "\uCC98\uB9AC\uD560 \uD30C\uC77C \uC5C6\uC74C"





        if "\uC804\uC0AC \uC644\uB8CC" in value or value == "\uC644\uB8CC":





            return "\uC804\uC0AC \uC644\uB8CC"





        if (





            "\uC0AC\uC6A9\uC790 \uC911\uC9C0" in value





            or "\uC911\uC9C0 \uC694\uCCAD" in value





            or "\uC989\uC2DC \uC911\uC9C0" in value





        ):





            return "\uC0AC\uC6A9\uC790 \uC911\uC9C0\uB428"





        if (





            "\uC624\uB958" in value





            or "\uAC15\uC81C \uC885\uB8CC" in value





            or "\uBE44\uC815\uC0C1" in value





        ):





            return "\uC624\uB958 \uBC1C\uC0DD"





        if (





            "\uC804\uC0AC \uC9C4\uD589" in value





            or "\uC804\uC0AC \uC900\uBE44" in value





            or "\uC804\uC0AC \uC2DC\uC791" in value





            or "\uD30C\uC77C \uAC74\uB108\uB700" in value





        ):





            return "\uC804\uC0AC \uC9C4\uD589 \uC911"





        if "\uB300\uAE30" in value:





            return "\uB300\uAE30 \uC911"





        return "\uB300\uAE30 \uC911"











    def _set_status_text(self, text: str):





        normalized = self._normalize_status_value(text)





        self._status_full_text = normalized





        self.label_status.setText(normalized)





        self.label_status.setToolTip("")





        if hasattr(self, "status_icon"):





            if normalized in ("전사 진행 중", "선택 전사 진행 중", "전체 전사 진행 중"):





                if not self.status_spin_timer.isActive():





                    self.status_spin_timer.start(240)





            else:





                self.status_spin_timer.stop()





                self.status_icon.setText("↻")











    def _tick_status_icon(self):





        if not hasattr(self, "status_icon"):





            return





        self._status_spin_index = (self._status_spin_index + 1) % len(self._status_spin_frames)





        self.status_icon.setText(self._status_spin_frames[self._status_spin_index])











    def _set_current_file_text(self, text: str):





        raw = (text or "").strip()





        for marker in ("현재 처리 중 파일:", "전사 완료 파일:", "현재 파일:"):





            if raw.startswith(marker):





                raw = raw.split(":", 1)[1].strip()





                break





        if not raw or "없음" in raw or "확인 중" in raw:





            shown = "없음"





        else:





            shown = os.path.basename(raw)





        self._current_file_full_text = shown





        self._set_elided_label_text(self.label_current_file, shown)











    def _set_session_text(self, text: str):





        self._session_full_text = text





        self._set_elided_label_text(self.label_session, text)





        self._refresh_meta_summary()











    def _set_output_text(self, text: str):





        self._output_full_text = text





        self._set_elided_label_text(self.label_output_source, text, self._output_text_elide_mode)





        self._refresh_meta_summary()











    def _set_output_text_mode(self, mode):





        self._output_text_elide_mode = mode





        self._set_elided_label_text(self.label_output_source, self._output_full_text, mode)





        self._refresh_meta_summary()











    def _display_path_for_ui(self, path: str) -> str:





        shown = str(path or "").replace("\\", "/").strip()





        if not shown:





            return shown





        drive = ""





        rest = shown





        m = re.match(r"^([A-Za-z]:)(/.*)?$", shown)





        if m:





            drive = m.group(1)





            rest = m.group(2) or ""





        rest = re.sub(r"/{2,}", "/", rest)





        if drive:





            return f"{drive}{rest or '/'}".rstrip("/")





        return re.sub(r"/{2,}", "/", shown)











    def _elide_path_for_label(self, label: QLabel, path: str, available: int) -> str:





        shown = self._display_path_for_ui(path)





        if not shown:





            return shown











        fm = label.fontMetrics()





        if fm.horizontalAdvance(shown) <= available:





            return shown











        parts = [segment for segment in shown.split("/") if segment]





        if len(parts) >= 2:





            drive = parts[0] if ":" in parts[0] else ""





            tail_two = "/".join(parts[-2:])





            candidate = f"{drive}/.../{tail_two}" if drive else f".../{tail_two}"





            if fm.horizontalAdvance(candidate) <= available:





                return candidate











            tail_one = f".../{parts[-1]}"





            if fm.horizontalAdvance(tail_one) <= available:





                return tail_one











        return fm.elidedText(shown, Qt.ElideMiddle, available)











    def _is_transcribe_running(self) -> bool:





        if self._colab_run_active:
            return True
        return self.process is not None and self.process.state() != QProcess.NotRunning











    def _refresh_meta_summary(self):





        if not hasattr(self, "label_session_counter") or not hasattr(self, "label_output_value"):





            return











        running = self._is_transcribe_running()





        if running or self.total_target_mp3_files > 0 or self.completed_files:





            total = max(0, int(self.total_target_mp3_files))





            if total <= 0 and self.completed_files:





                total = len(self.completed_files)





            done = min(len(self.completed_files), total) if total > 0 else 0





        elif self.loaded_mp3_count > 0:





            total = int(self.loaded_mp3_count)





            done = 0





        else:





            total = 0





            done = 0











        session_text = f"{done} / {total}"





        self.label_session_counter.setText(f"SESSION: {session_text}")





        self.label_session_counter.setToolTip(session_text)











        _out_folder = self._output_display_folder or self.target_folder
        if _out_folder:
            output_text = self._display_path_for_ui(_out_folder)





        else:





            output_text = "\uBBF8\uC124\uC815"





        self._set_compact_output_meta_text(output_text)











    def _refresh_file_list_empty_state(self):





        has_items = bool(self.file_queue_rows)





        self.file_queue_table.setVisible(has_items)





        self.label_file_empty_state.setVisible(not has_items)





        self._refresh_meta_summary()











    def _set_eta_value(self, label: QLabel, text: str):





        # 현재 파일 ETA는 좌측 정렬, 전체 ETA는 기존 좌측 정렬을 유지한다.





        if label is self.label_current_eta:





            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)





            shown = text if text else ETA_EMPTY_TEXT





            label.setText(f"CURRENT ETA: {shown}")





            label.setToolTip(shown)





        else:





            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)





            label.setText(text)





        label.setIndent(0)











    def _format_remaining_minutes(self, seconds: float | int) -> str:





        sec = max(0, int(round(float(seconds))))





        minutes = max(1, int(round(sec / 60.0))) if sec > 0 else 0





        return f"{minutes} 분" if minutes > 0 else ETA_EMPTY_TEXT

    def _format_approx_remaining_minutes(self, seconds: float | int) -> str:
        sec = max(0, int(round(float(seconds))))
        minutes = max(1, int(round(sec / 60.0))) if sec > 0 else 0
        return f"약 {minutes}분" if minutes > 0 else ETA_EMPTY_TEXT

    def _duration_text_to_seconds(self, duration_value) -> float:
        if isinstance(duration_value, (int, float)):
            return max(0.0, float(duration_value))

        text = str(duration_value or "").strip()
        if not text or text == ETA_EMPTY_TEXT:
            return 0.0

        parts = text.split(":")
        if len(parts) not in (2, 3):
            return 0.0

        try:
            nums = [int(p) for p in parts]
        except ValueError:
            return 0.0

        if any(n < 0 for n in nums):
            return 0.0

        if len(nums) == 2:
            mm, ss = nums
            return float(mm * 60 + ss)

        hh, mm, ss = nums
        return float(hh * 3600 + mm * 60 + ss)

    def _eta_primary_name_key(self, file_name: str) -> str:
        return os.path.basename(str(file_name or "")).strip().lower()

    def _build_run_duration_estimate_state(self):
        self.run_total_audio_seconds = 0.0
        self.run_done_audio_seconds = 0.0
        self.run_current_audio_seconds = 0.0
        self.run_audio_seconds_by_primary_key.clear()
        self.run_audio_alias_to_primary_key.clear()
        self.run_audio_accounted_primary_keys.clear()

        run_items = self.selected_run_items if self.selected_run_items else self.file_queue_rows
        for item in run_items:
            duration_seconds = self._duration_text_to_seconds(item.get("duration_seconds", 0))
            if duration_seconds <= 0:
                duration_seconds = self._duration_text_to_seconds(item.get("duration", ""))
            if duration_seconds <= 0:
                for ref_name in (
                    str(item.get("transcribe_name", "")),
                    str(item.get("queue_name", "")),
                    str(item.get("filename", "")),
                    os.path.basename(str(item.get("source_path", ""))),
                ):
                    row = self._find_queue_row_by_filename(ref_name)
                    if not row:
                        continue
                    duration_seconds = self._duration_text_to_seconds(row.get("duration", ""))
                    if duration_seconds > 0:
                        break
            if duration_seconds <= 0:
                continue

            primary_name = (
                str(item.get("transcribe_name", ""))
                or str(item.get("filename", ""))
                or str(item.get("queue_name", ""))
                or os.path.basename(str(item.get("source_path", "")))
            )
            primary_key = self._eta_primary_name_key(primary_name)
            if not primary_key:
                continue

            self.run_total_audio_seconds += duration_seconds
            self.run_audio_seconds_by_primary_key[primary_key] = duration_seconds

            alias_keys = set()
            for alias_name in (
                primary_name,
                str(item.get("queue_name", "")),
                str(item.get("filename", "")),
                os.path.basename(str(item.get("source_path", ""))),
            ):
                alias_keys.update(self._queue_name_keys(alias_name))
            alias_keys.add(primary_key)

            for alias_key in alias_keys:
                if alias_key and alias_key not in self.run_audio_alias_to_primary_key:
                    self.run_audio_alias_to_primary_key[alias_key] = primary_key

    def _resolve_run_audio_primary_key(self, file_name: str) -> str:
        for alias_key in self._queue_name_keys(file_name):
            primary_key = self.run_audio_alias_to_primary_key.get(alias_key, "")
            if primary_key:
                return primary_key
        return ""

    def _lookup_run_audio_seconds(self, file_name: str) -> float:
        primary_key = self._resolve_run_audio_primary_key(file_name)
        if not primary_key:
            return 0.0
        return float(self.run_audio_seconds_by_primary_key.get(primary_key, 0.0))

    def _consume_run_audio_seconds(self, file_name: str) -> float:
        primary_key = self._resolve_run_audio_primary_key(file_name)
        if not primary_key or primary_key in self.run_audio_accounted_primary_keys:
            return 0.0
        self.run_audio_accounted_primary_keys.add(primary_key)
        duration_seconds = float(self.run_audio_seconds_by_primary_key.get(primary_key, 0.0))
        if duration_seconds > 0:
            self.run_done_audio_seconds += duration_seconds
        return duration_seconds

    def _dashboard_today_key(self) -> str:
        return datetime.date.today().isoformat()

    def _format_dashboard_total_audio_time(self, total_seconds: float | int) -> str:
        safe_seconds = max(0.0, float(total_seconds))
        total_minutes = 0 if safe_seconds <= 0 else max(1, int(round(safe_seconds / 60.0)))
        if total_minutes <= 0:
            return "0분"
        hours, minutes = divmod(total_minutes, 60)
        if hours > 0:
            return f"{hours}시간 {minutes}분"
        return f"{minutes}분"

    def _format_dashboard_avg_speed_text(self) -> str:
        if self.dashboard_observed_audio_seconds > 0 and self.dashboard_observed_processing_seconds > 0:
            ratio = self.dashboard_observed_processing_seconds / self.dashboard_observed_audio_seconds
            ratio = max(0.05, min(5.0, ratio))
            minutes_text = f"{ratio:.1f}".rstrip("0").rstrip(".")
            return f"오디오 1분 -> 약 {minutes_text}분"
        return "오디오 1분 -> 약 -"

    def _sanitize_dashboard_daily_counts(self, raw_obj) -> dict[str, int]:
        if not isinstance(raw_obj, dict):
            return {}
        cleaned: dict[str, int] = {}
        for key, value in raw_obj.items():
            day_key = str(key or "").strip()
            if not day_key:
                continue
            try:
                count = int(value)
            except Exception:
                continue
            if count > 0:
                cleaned[day_key] = count
        return cleaned

    def _sanitize_dashboard_recent_items(self, raw_obj) -> list[dict]:
        if not isinstance(raw_obj, list):
            return []
        cleaned: list[dict] = []
        for item in raw_obj:
            if not isinstance(item, dict):
                continue
            file_name = os.path.basename(str(item.get("file_name", "")).strip()) or "알 수 없음"
            completed_at = str(item.get("completed_at", "")).strip()
            try:
                timestamp = float(item.get("timestamp", 0.0))
            except Exception:
                timestamp = 0.0
            if not completed_at and timestamp > 0:
                completed_at = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            if not completed_at:
                completed_at = "-"
            cleaned.append(
                {
                    "file_name": file_name,
                    "completed_at": completed_at,
                    "timestamp": max(0.0, timestamp),
                }
            )
        cleaned.sort(key=lambda x: float(x.get("timestamp", 0.0)), reverse=True)
        return cleaned[:10]

    def _resolve_done_duration_seconds(self, file_name: str, preferred_seconds: float | int = 0.0) -> float:
        duration_seconds = max(0.0, float(preferred_seconds))
        if duration_seconds > 0:
            return duration_seconds

        candidate_names: list[str] = []
        for candidate in (file_name, self.current_file_name):
            name = str(candidate or "").strip()
            if name and name not in candidate_names:
                candidate_names.append(name)

        for candidate_name in candidate_names:
            duration_seconds = self._lookup_run_audio_seconds(candidate_name)
            if duration_seconds > 0:
                return duration_seconds

        target_keys: set[str] = set()
        for candidate_name in candidate_names:
            target_keys.update(self._queue_name_keys(candidate_name))

        matched_row = None
        if target_keys:
            for row in self.file_queue_rows:
                row_keys: set[str] = set()
                row_keys.update(self._queue_name_keys(str(row.get("filename", ""))))
                row_keys.update(self._queue_name_keys(str(row.get("transcribe_name", ""))))
                if row_keys & target_keys:
                    matched_row = row
                    break

        if matched_row is not None:
            duration_seconds = self._duration_text_to_seconds(matched_row.get("duration", ""))
            if duration_seconds > 0:
                return duration_seconds

            src = self._normalize_saved_folder_path(matched_row.get("source_path", ""))
            if src and os.path.isfile(src):
                redetected = self._detect_duration_mmss(src)
                duration_seconds = self._duration_text_to_seconds(redetected)
                if duration_seconds > 0:
                    matched_row["duration"] = redetected
                    return duration_seconds

        return 0.0

    def load_dashboard_statistics(self):
        try:
            self.dashboard_total_done_files = max(
                0, int(self.ui_settings.value(SETTINGS_KEY_DASH_TOTAL_DONE_FILES, 0, type=int))
            )
            self.dashboard_total_audio_seconds = max(
                0.0, float(self.ui_settings.value(SETTINGS_KEY_DASH_TOTAL_AUDIO_SECONDS, 0.0, type=float))
            )

            raw_daily = self.ui_settings.value(SETTINGS_KEY_DASH_DAILY_COUNTS_JSON, "{}")
            parsed_daily = json.loads(str(raw_daily or "{}"))
            self.dashboard_daily_done_counts = self._sanitize_dashboard_daily_counts(parsed_daily)

            raw_recent = self.ui_settings.value(SETTINGS_KEY_DASH_RECENT_DONE_JSON, "[]")
            parsed_recent = json.loads(str(raw_recent or "[]"))
            self.dashboard_recent_done_items = self._sanitize_dashboard_recent_items(parsed_recent)

            self.dashboard_observed_audio_seconds = max(
                0.0, float(self.ui_settings.value(SETTINGS_KEY_DASH_OBSERVED_AUDIO_SECONDS, 0.0, type=float))
            )
            self.dashboard_observed_processing_seconds = max(
                0.0, float(self.ui_settings.value(SETTINGS_KEY_DASH_OBSERVED_PROCESSING_SECONDS, 0.0, type=float))
            )
        except Exception:
            self.dashboard_total_done_files = 0
            self.dashboard_total_audio_seconds = 0.0
            self.dashboard_daily_done_counts = {}
            self.dashboard_recent_done_items = []
            self.dashboard_observed_audio_seconds = 0.0
            self.dashboard_observed_processing_seconds = 0.0

    def save_dashboard_statistics(self):
        try:
            self.ui_settings.setValue(SETTINGS_KEY_DASH_TOTAL_DONE_FILES, int(max(0, self.dashboard_total_done_files)))
            self.ui_settings.setValue(
                SETTINGS_KEY_DASH_TOTAL_AUDIO_SECONDS, float(max(0.0, self.dashboard_total_audio_seconds))
            )
            self.ui_settings.setValue(
                SETTINGS_KEY_DASH_DAILY_COUNTS_JSON,
                json.dumps(self.dashboard_daily_done_counts, ensure_ascii=False),
            )
            self.ui_settings.setValue(
                SETTINGS_KEY_DASH_RECENT_DONE_JSON,
                json.dumps(self.dashboard_recent_done_items[:10], ensure_ascii=False),
            )
            self.ui_settings.setValue(
                SETTINGS_KEY_DASH_OBSERVED_AUDIO_SECONDS, float(max(0.0, self.dashboard_observed_audio_seconds))
            )
            self.ui_settings.setValue(
                SETTINGS_KEY_DASH_OBSERVED_PROCESSING_SECONDS,
                float(max(0.0, self.dashboard_observed_processing_seconds)),
            )
            self.ui_settings.sync()
        except Exception:
            pass

    def refresh_dashboard_view(self):
        if not hasattr(self, "label_dash_total_done"):
            return

        self.label_dash_total_done.setText(str(int(max(0, self.dashboard_total_done_files))))
        self.label_dash_total_audio.setText(
            self._format_dashboard_total_audio_time(self.dashboard_total_audio_seconds)
        )
        today_count = int(max(0, self.dashboard_daily_done_counts.get(self._dashboard_today_key(), 0)))
        self.label_dash_today_done.setText(str(today_count))
        self.label_dash_speed.setText(self._format_dashboard_avg_speed_text())

        items = self.dashboard_recent_done_items[:10]
        self.dashboard_recent_table.setRowCount(len(items))
        for row_idx, item in enumerate(items):
            file_item = QTableWidgetItem(str(item.get("file_name", "알 수 없음")))
            file_item.setFlags(Qt.ItemIsEnabled)
            file_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.dashboard_recent_table.setItem(row_idx, 0, file_item)

            time_item = QTableWidgetItem(str(item.get("completed_at", "-")))
            time_item.setFlags(Qt.ItemIsEnabled)
            time_item.setTextAlignment(Qt.AlignCenter)
            self.dashboard_recent_table.setItem(row_idx, 1, time_item)
            self.dashboard_recent_table.setRowHeight(row_idx, 34)

    def record_dashboard_done(
        self,
        file_name: str,
        duration_seconds: float | int,
        processing_seconds: float | int | None = None,
    ):
        safe_name = os.path.basename(str(file_name or "").strip()) or "알 수 없음"
        safe_duration = max(0.0, float(duration_seconds))
        self.dashboard_total_done_files += 1
        self.dashboard_total_audio_seconds += safe_duration

        today_key = self._dashboard_today_key()
        today_count = int(self.dashboard_daily_done_counts.get(today_key, 0))
        self.dashboard_daily_done_counts[today_key] = today_count + 1

        completed_at = datetime.datetime.now()
        self.dashboard_recent_done_items.append(
            {
                "file_name": safe_name,
                "completed_at": completed_at.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": completed_at.timestamp(),
            }
        )
        self.dashboard_recent_done_items = self._sanitize_dashboard_recent_items(
            self.dashboard_recent_done_items
        )

        if processing_seconds is not None and safe_duration > 0:
            safe_processing = max(0.0, float(processing_seconds))
            if safe_processing > 0:
                self.dashboard_observed_audio_seconds += safe_duration
                self.dashboard_observed_processing_seconds += safe_processing

        self.save_dashboard_statistics()
        self.refresh_dashboard_view()

    def _folder_status_colors(self, status_text: str) -> tuple[str, str]:
        if status_text == FOLDER_STATUS_COMPLETE:
            return "#dcfce7", "#15803d"
        if status_text == FOLDER_STATUS_INCOMPLETE:
            return "#fee2e2", "#b91c1c"
        return "#fff7ed", "#c2410c"

    def _folder_group_key(self, file_name: str) -> str:
        cleaned = os.path.splitext(remove_page_suffix(os.path.basename(str(file_name or ""))))[0].strip().lower()
        if cleaned:
            return cleaned
        return os.path.splitext(os.path.basename(str(file_name or "")))[0].strip().lower()

    def _folder_type_text(self, ext: str) -> str:
        mapping = {
            ".mp3": "MP3",
            ".txt": "TXT",
            ".json": "JSON",
            ".srt": "SRT",
        }
        return mapping.get(ext.lower(), ext.upper().lstrip("."))

    def _folder_status_from_group(self, group_info: dict) -> str:
        has_mp3 = bool(group_info.get("mp3"))
        has_txt = bool(group_info.get("txt"))
        has_json = bool(group_info.get("json"))
        has_srt = bool(group_info.get("srt"))
        if has_mp3 and has_txt and has_json and has_srt:
            return FOLDER_STATUS_COMPLETE
        if has_mp3:
            return FOLDER_STATUS_INCOMPLETE
        return FOLDER_STATUS_RESULT_ONLY

    def _scan_folder_tab_rows(self, folder_path: str) -> list[dict]:
        rows: list[dict] = []
        allowed_exts = {".mp3", ".txt", ".json", ".srt"}
        if not folder_path or not os.path.isdir(folder_path):
            return rows

        group_map: dict[str, dict] = {}
        raw_files: list[dict] = []
        for name in os.listdir(folder_path):
            full_path = os.path.join(folder_path, name)
            if not os.path.isfile(full_path):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in allowed_exts:
                continue
            group_key = self._folder_group_key(name)
            if not group_key:
                continue

            if group_key not in group_map:
                group_map[group_key] = {"mp3": False, "txt": False, "json": False, "srt": False}
            key_name = ext.lstrip(".")
            if key_name in group_map[group_key]:
                group_map[group_key][key_name] = True

            try:
                modified_ts = float(os.path.getmtime(full_path))
            except OSError:
                modified_ts = 0.0
            raw_files.append(
                {
                    "file_name": name,
                    "path": full_path,
                    "ext": ext,
                    "group_key": group_key,
                    "modified_ts": modified_ts,
                }
            )

        for file_info in raw_files:
            status_text = self._folder_status_from_group(group_map.get(file_info["group_key"], {}))
            modified_text = (
                datetime.datetime.fromtimestamp(file_info["modified_ts"]).strftime("%Y-%m-%d %H:%M")
                if file_info["modified_ts"] > 0
                else "-"
            )
            rows.append(
                {
                    "file_name": file_info["file_name"],
                    "path": file_info["path"],
                    "ext": file_info["ext"],
                    "type_text": self._folder_type_text(file_info["ext"]),
                    "status_text": status_text,
                    "modified_text": modified_text,
                    "modified_ts": file_info["modified_ts"],
                }
            )

        rows.sort(key=lambda x: (-float(x.get("modified_ts", 0.0)), str(x.get("file_name", "")).lower()))
        return rows

    def _read_text_file_with_fallback(self, file_path: str) -> str:
        for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except Exception:
                continue
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _set_folder_filter_mode(self, mode: str):
        if mode not in ("all", "complete", "incomplete", "result_only"):
            mode = "all"
        self.folder_tab_filter_mode = mode

        button_map = {
            "all": self.btn_folders_filter_all,
            "complete": self.btn_folders_filter_done,
            "incomplete": self.btn_folders_filter_pending,
            "result_only": self.btn_folders_filter_result_only,
        }
        for key, btn in button_map.items():
            btn.setEnabled(key != mode)

        self._render_folder_tab_rows()

    def _filtered_folder_rows(self) -> list[dict]:
        mode = self.folder_tab_filter_mode
        if mode == "complete":
            return [r for r in self.folder_tab_rows if r.get("status_text") == FOLDER_STATUS_COMPLETE]
        if mode == "incomplete":
            return [r for r in self.folder_tab_rows if r.get("status_text") == FOLDER_STATUS_INCOMPLETE]
        if mode == "result_only":
            return [r for r in self.folder_tab_rows if r.get("status_text") == FOLDER_STATUS_RESULT_ONLY]
        return list(self.folder_tab_rows)

    def _render_folder_tab_rows(self):
        rows = self._filtered_folder_rows()
        self.folder_tab_visible_rows = list(rows)
        self.folders_table.blockSignals(True)
        self.folders_table.setSortingEnabled(False)
        self.folders_table.clearSelection()
        self.folders_table.setRowCount(len(rows))

        for row_idx, row_data in enumerate(rows):
            file_item = QTableWidgetItem(str(row_data.get("file_name", "")))
            file_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            file_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            file_item.setData(Qt.UserRole, str(row_data.get("path", "")))
            file_item.setData(Qt.UserRole + 1, str(row_data.get("ext", "")))
            self.folders_table.setItem(row_idx, 0, file_item)

            type_item = QTableWidgetItem(str(row_data.get("type_text", "")))
            type_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            type_item.setTextAlignment(Qt.AlignCenter)
            self.folders_table.setItem(row_idx, 1, type_item)

            status_text = str(row_data.get("status_text", FOLDER_STATUS_INCOMPLETE))
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            status_item.setTextAlignment(Qt.AlignCenter)
            bg, fg = self._folder_status_colors(status_text)
            status_item.setBackground(QColor(bg))
            status_item.setForeground(QColor(fg))
            self.folders_table.setItem(row_idx, 2, status_item)

            modified_item = QTableWidgetItem(str(row_data.get("modified_text", "-")))
            modified_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            modified_item.setTextAlignment(Qt.AlignCenter)
            self.folders_table.setItem(row_idx, 3, modified_item)

            self.folders_table.setRowHeight(row_idx, 34)

        header = self.folders_table.horizontalHeader()
        sort_section = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        if sort_section in (0, 1):
            self.folders_table.sortItems(sort_section, sort_order)
        self.folders_table.setSortingEnabled(False)
        self.folders_table.horizontalHeader().setSortIndicatorShown(True)
        self.folders_table.blockSignals(False)
        self._handle_folders_table_selection_changed()

    def _handle_folders_table_header_clicked(self, section: int):
        if section not in (0, 1):
            return

        header = self.folders_table.horizontalHeader()
        current_section = header.sortIndicatorSection()
        current_order = header.sortIndicatorOrder()
        if current_section == section:
            next_order = Qt.DescendingOrder if current_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            next_order = Qt.AscendingOrder

        header.setSortIndicator(section, next_order)
        self.folders_table.sortItems(section, next_order)
        self._handle_folders_table_selection_changed()

    def _reset_folders_preview(self, message: str = "TXT 파일을 선택하면 미리보기가 표시됩니다."):
        self.folder_preview_full_text = ""
        self.folder_preview_path = ""
        self.text_folders_preview.setPlainText(message)
        self.btn_folders_preview_full.setEnabled(False)

    def _update_folders_preview_for_row(self, row: int):
        if row < 0 or row >= self.folders_table.rowCount():
            self._reset_folders_preview()
            return

        # sorting 호환성을 위해 table item에서 직접 데이터를 가져오는 것을 우선시함
        file_path = ""
        file_ext = ""
        name_item = self.folders_table.item(row, 0)
        if name_item is not None:
            file_path = str(name_item.data(Qt.UserRole) or "")
            file_ext = str(name_item.data(Qt.UserRole + 1) or "").lower()

        # fallback: UserRole 데이터가 없는 경우 (만약의 경우를 대비)
        if not file_path and row < len(self.folder_tab_visible_rows):
            row_data = self.folder_tab_visible_rows[row]
            file_path = str(row_data.get("path", ""))
            file_ext = str(row_data.get("ext", "")).lower()

        if file_ext != ".txt" or not file_path:
            self._reset_folders_preview()
            return

        try:
            full_text = self._read_text_file_with_fallback(file_path)
        except Exception:
            self._reset_folders_preview("파일을 읽을 수 없습니다.")
            return

        if not full_text:
            full_text = "(내용 없음)"
        preview_text = full_text[:500]
        if len(full_text) > 500:
            preview_text += "\n\n... (전체 보기 버튼으로 나머지 내용을 확인하세요)"

        self.folder_preview_full_text = full_text
        self.folder_preview_path = file_path
        self.text_folders_preview.setPlainText(preview_text)
        self.btn_folders_preview_full.setEnabled(True)

    def _handle_folders_table_selection_changed(self):
        row = self.folders_table.currentRow()
        if row < 0:
            current_item = self.folders_table.currentItem()
            if current_item is not None:
                row = current_item.row()
            else:
                selected_items = self.folders_table.selectedItems()
                if selected_items:
                    row = selected_items[0].row()
        self._update_folders_preview_for_row(row)

    def _handle_folders_table_cell_clicked(self, row: int, col: int):
        if row >= 0:
            self.folders_table.setCurrentCell(row, 0)
        self._update_folders_preview_for_row(row)

    def _handle_folders_table_item_clicked(self, item: QTableWidgetItem):
        if item is None:
            self._reset_folders_preview()
            return
        row = item.row()
        if row >= 0:
            self.folders_table.setCurrentCell(row, 0)
        self._update_folders_preview_for_row(row)

    def _show_folders_preview_full_text(self):
        if not self.folder_preview_full_text:
            self.show_info_message("알림", "전체 보기 가능한 TXT 미리보기가 없습니다.")
            return

        title_name = os.path.basename(self.folder_preview_path) if self.folder_preview_path else "텍스트 미리보기"
        dialog = QDialog(self)
        dialog.setWindowTitle(f"전체 보기 - {title_name}")
        dialog.setWindowIcon(self.windowIcon())
        dialog.resize(760, 520)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(self.folder_preview_full_text)
        viewer.setObjectName("FolderPreviewText")
        layout.addWidget(viewer, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons, 0)

        dialog.exec()

    def refresh_folder_management_view(self):
        folder = self._normalize_saved_folder_path(self.target_folder)
        folder_exists = bool(folder and os.path.isdir(folder))
        shown_path = self._display_path_for_ui(folder) if folder_exists else "미설정"
        self.label_folders_current_path.setText(shown_path)
        self.label_folders_current_path.setToolTip(shown_path)

        self.btn_folders_open.setEnabled(folder_exists)
        self.btn_folders_refresh.setEnabled(folder_exists)

        if not folder_exists:
            self.folder_tab_rows = []
            self._render_folder_tab_rows()
            self.text_folders_preview.setPlainText("전사자료 폴더를 먼저 설정하세요.")
            self.btn_folders_preview_full.setEnabled(False)
            return

        try:
            self.folder_tab_rows = self._scan_folder_tab_rows(folder)
        except Exception as e:
            self.folder_tab_rows = []
            self._render_folder_tab_rows()
            self.text_folders_preview.setPlainText(f"폴더 스캔 실패: {e}")
            self.btn_folders_preview_full.setEnabled(False)
            return

        self._render_folder_tab_rows()











    def _set_compact_output_meta_text(self, output_text: str):





        prefix = "OUTPUT: "





        raw_value = output_text or "미설정"





        label = self.label_output_value





        full_text = f"{prefix}{raw_value}"





        available = max(120, label.width() - 12)





        fm = label.fontMetrics()





        if fm.horizontalAdvance(full_text) <= available:





            shown = full_text





        else:





            value_available = max(64, available - fm.horizontalAdvance(prefix))





            shown = prefix + fm.elidedText(raw_value, Qt.ElideMiddle, value_available)





        label.setText(shown)





        label.setToolTip(raw_value if shown != full_text else "")











    def _apply_status_and_meta_labels(self):





        self._set_status_text(self._status_full_text)





        self._set_current_file_text(self._current_file_full_text)





        self._set_session_text(self._session_full_text)





        self._set_output_text(self._output_full_text)





        self._refresh_meta_summary()











    def _normalize_saved_folder_path(self, value) -> str:





        text = str(value or "").strip().strip('"')





        if not text:





            return ""





        return os.path.normpath(text)











    def _normalize_transcription_engine(self, value) -> str:
        normalized = str(value or "").strip().lower()
        if normalized == "colab":
            return "colab"
        return "local"

    def _set_transcription_engine_value(self, engine: str):
        normalized = self._normalize_transcription_engine(engine)
        idx = self.combo_transcription_engine.findData(normalized)
        if idx < 0:
            idx = 0
        if self.combo_transcription_engine.currentIndex() != idx:
            self.combo_transcription_engine.setCurrentIndex(idx)
        self.transcription_engine = normalized

    def _current_transcription_engine(self) -> str:
        return self._normalize_transcription_engine(self.combo_transcription_engine.currentData())

    def _sync_transcription_engine_ui_state(self):
        is_colab = self._current_transcription_engine() == "colab"
        self.colab_url_panel.setVisible(is_colab)
        self.input_colab_url.setEnabled(is_colab)
        self._update_colab_check_button_state()

    def _on_transcription_engine_changed(self, _index: int = -1):
        self.transcription_engine = self._current_transcription_engine()
        self._sync_transcription_engine_ui_state()
        self.save_ui_preferences()

    def _refresh_widget_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _set_colab_check_button_connected_style(self, connected: bool):
        current_value = bool(self.btn_colab_check.property("connected"))
        target_value = bool(connected)
        if current_value == target_value:
            return
        self.btn_colab_check.setProperty("connected", target_value)
        self._refresh_widget_style(self.btn_colab_check)

    def _update_colab_check_button_state(self):
        is_colab = self._current_transcription_engine() == "colab"
        if self._colab_check_in_progress:
            self._set_colab_check_button_connected_style(False)
            self.btn_colab_check.setText("확인 중...")
            self.btn_colab_check.setEnabled(False)
            return
        if self._colab_check_connected:
            self._set_colab_check_button_connected_style(True)
            self.btn_colab_check.setText("연결됨 ✓")
            self.btn_colab_check.setEnabled(is_colab)
            return
        self._set_colab_check_button_connected_style(False)
        self.btn_colab_check.setText("연결 확인")
        self.btn_colab_check.setEnabled(is_colab)

    def _build_colab_health_url(self, raw_url: str) -> str:
        return self._build_colab_endpoint_url(raw_url, "/health")

    def _build_colab_endpoint_url(self, raw_url: str, endpoint_path: str) -> str:
        candidate = str(raw_url or "").strip()
        if not candidate:
            return ""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidate):
            candidate = f"https://{candidate}"
        try:
            parsed = urllib_parse.urlsplit(candidate)
        except Exception:
            return ""
        if not parsed.scheme or not parsed.netloc:
            return ""

        endpoint = "/" + str(endpoint_path or "").strip().lstrip("/")
        base_path = parsed.path.rstrip("/")
        for known_suffix in ("/health", "/transcribe"):
            if base_path.lower().endswith(known_suffix):
                base_path = base_path[: -len(known_suffix)]
                break
        target_path = f"{base_path}{endpoint}" if base_path else endpoint
        normalized = parsed._replace(path=target_path, query="", fragment="")
        return normalized.geturl()

    def _perform_colab_health_check(self, request_id: int, health_url: str):
        result_code = "connection_error"
        try:
            req = urllib_request.Request(
                health_url,
                headers={"Accept": "application/json", "Cache-Control": "no-cache"},
                method="GET",
            )
            with urllib_request.urlopen(req, timeout=10) as response:
                payload_bytes = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
            try:
                payload = json.loads(payload_bytes.decode(charset, errors="replace"))
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and str(payload.get("status", "")).strip().lower() == "ok":
                result_code = "success"
            else:
                result_code = "invalid_response"
        except urllib_error.HTTPError:
            result_code = "invalid_response"
        except (TimeoutError, urllib_error.URLError, OSError, ValueError):
            result_code = "connection_error"
        except Exception:
            result_code = "connection_error"
        self._colab_health_check_bridge.finished.emit(int(request_id), str(result_code))

    def _build_colab_transcribe_url(self, raw_url: str) -> str:
        return self._build_colab_endpoint_url(raw_url, "/transcribe")

    def _colab_path_key(self, path: str) -> str:
        normalized = self._normalize_saved_folder_path(path)
        if not normalized:
            return ""
        try:
            normalized = os.path.abspath(normalized)
        except Exception:
            pass
        return os.path.normcase(normalized)

    def _colab_now_text(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _colab_progress_path_for_runtime(self, runtime_folder: str = "") -> str:
        base_folder = self._normalize_saved_folder_path(self.target_folder)
        if not base_folder:
            base_folder = self._normalize_saved_folder_path(runtime_folder)
        if not base_folder or not os.path.isdir(base_folder):
            return ""
        return os.path.join(base_folder, COLAB_PROGRESS_FILENAME)

    def _load_colab_progress_payload_safely(self, progress_path: str):
        if not progress_path or not os.path.isfile(progress_path):
            return None
        try:
            with open(progress_path, "r", encoding="utf-8-sig") as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                return payload
        except Exception:
            return None
        return None

    def _extract_colab_progress_completed_items(self, payload) -> list[dict]:
        if not isinstance(payload, dict):
            return []
        raw_items = payload.get("completed_files", [])
        if not isinstance(raw_items, list):
            return []
        items: list[dict] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            mp3_path = self._normalize_saved_folder_path(raw.get("mp3_path", ""))
            if not mp3_path:
                continue
            items.append(
                {
                    "mp3_path": mp3_path,
                    "txt_path": str(raw.get("txt_path", "") or ""),
                    "json_path": str(raw.get("json_path", "") or ""),
                    "srt_path": str(raw.get("srt_path", "") or ""),
                    "completed_at": str(raw.get("completed_at", "") or ""),
                }
            )
        return items

    def _save_colab_progress_payload_safely(self, progress_path: str, payload: dict):
        if not progress_path or not isinstance(payload, dict):
            return
        try:
            parent = os.path.dirname(progress_path)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _remove_colab_progress_file_safely(self, progress_path: str):
        if not progress_path:
            return
        try:
            if os.path.isfile(progress_path):
                os.remove(progress_path)
        except Exception:
            pass

    def _clear_colab_resume_state(self):
        self._colab_resume_enabled = False
        self._colab_resume_completed_keys.clear()
        self._colab_resume_session_id = ""
        self._colab_resume_progress_path_key = ""

    def _confirm_colab_resume_progress_dialog(self) -> bool:
        dialog, button_box = self._build_message_box(
            "이전 전사 작업",
            "이전 전사 작업이 있습니다. 이어서 진행할까요?",
            QMessageBox.Question,
            parent_override=self,
        )
        yes_btn = button_box.addButton("예", QDialogButtonBox.AcceptRole)
        yes_btn.setObjectName("DialogPrimaryButton")
        no_btn = button_box.addButton("아니오", QDialogButtonBox.RejectRole)
        no_btn.setObjectName("DialogSecondaryButton")
        yes_btn.clicked.connect(dialog.accept)
        no_btn.clicked.connect(dialog.reject)
        return dialog.exec() == QDialog.Accepted

    def _check_colab_progress_resume_on_startup(self):
        progress_path = self._colab_progress_path_for_runtime(self.target_folder)
        payload = self._load_colab_progress_payload_safely(progress_path)
        if not payload:
            return
        engine = str(payload.get("engine", "colab") or "").strip().lower()
        if engine and engine != "colab":
            return

        completed_items = self._extract_colab_progress_completed_items(payload)
        progress_key = self._colab_path_key(progress_path)
        if not progress_key:
            return

        if self._confirm_colab_resume_progress_dialog():
            session_id = str(payload.get("session_id", "") or "").strip()
            if not session_id:
                session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            completed_keys: set[str] = set()
            for item in completed_items:
                item_key = self._colab_path_key(item.get("mp3_path", ""))
                if item_key:
                    completed_keys.add(item_key)
            self._colab_resume_enabled = True
            self._colab_resume_completed_keys = completed_keys
            self._colab_resume_session_id = session_id
            self._colab_resume_progress_path_key = progress_key
            self.append_log_text(
                f"[GUI] Colab 이어하기 준비 완료: 완료 파일 {len(completed_keys)}개, 세션={session_id}\n",
                force=True,
            )
            return

        self._remove_colab_progress_file_safely(progress_path)
        self._clear_colab_resume_state()

    def _is_colab_resume_active_for_runtime(self, runtime_folder: str) -> bool:
        if not self._colab_resume_enabled:
            return False
        progress_path = self._colab_progress_path_for_runtime(runtime_folder)
        progress_key = self._colab_path_key(progress_path)
        if not progress_key:
            return False
        return progress_key == self._colab_resume_progress_path_key

    def _build_colab_progress_state(self, runtime_folder: str, run_targets: list[dict]) -> dict:
        progress_path = self._colab_progress_path_for_runtime(runtime_folder)
        resume_active = self._is_colab_resume_active_for_runtime(runtime_folder)
        completed_map: dict[str, dict] = {}
        session_id = ""
        total_files = len(run_targets)

        payload = self._load_colab_progress_payload_safely(progress_path) if resume_active else None
        if payload:
            session_id = str(payload.get("session_id", "") or "").strip()
            try:
                total_files = int(payload.get("total_files", total_files))
            except (TypeError, ValueError):
                total_files = len(run_targets)
            for item in self._extract_colab_progress_completed_items(payload):
                item_key = self._colab_path_key(item.get("mp3_path", ""))
                if item_key:
                    completed_map[item_key] = item

        if not session_id:
            session_id = self._colab_resume_session_id if resume_active else ""
        if not session_id:
            session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        total_files = max(int(total_files), len(run_targets) + len(completed_map))
        if total_files <= 0:
            total_files = len(run_targets)

        state = {
            "path": progress_path,
            "session_id": session_id,
            "total_files": total_files,
            "completed_map": completed_map,
        }

        payload_to_save = {
            "session_id": session_id,
            "engine": "colab",
            "total_files": int(total_files),
            "completed_files": list(completed_map.values()),
            "last_updated": self._colab_now_text(),
        }
        self._save_colab_progress_payload_safely(progress_path, payload_to_save)

        self._colab_resume_enabled = True
        self._colab_resume_session_id = session_id
        self._colab_resume_progress_path_key = self._colab_path_key(progress_path)
        self._colab_resume_completed_keys = set(completed_map.keys())
        return state

    def _record_colab_progress_completion(
        self,
        progress_state: dict,
        mp3_path: str,
        txt_path: str,
        json_path: str,
        srt_path: str,
    ):
        if not isinstance(progress_state, dict):
            return
        item_key = self._colab_path_key(mp3_path)
        if not item_key:
            return
        completed_map = progress_state.setdefault("completed_map", {})
        completed_map[item_key] = {
            "mp3_path": self._normalize_saved_folder_path(mp3_path),
            "txt_path": str(txt_path or ""),
            "json_path": str(json_path or ""),
            "srt_path": str(srt_path or ""),
            "completed_at": self._colab_now_text(),
        }
        self._colab_resume_completed_keys.add(item_key)
        payload = {
            "session_id": str(progress_state.get("session_id", "") or ""),
            "engine": "colab",
            "total_files": int(progress_state.get("total_files", 0) or 0),
            "completed_files": list(completed_map.values()),
            "last_updated": self._colab_now_text(),
        }
        self._save_colab_progress_payload_safely(str(progress_state.get("path", "") or ""), payload)

    def _collect_colab_runtime_targets(self, runtime_folder: str) -> list[dict]:
        targets: list[dict] = []
        resume_active = self._is_colab_resume_active_for_runtime(runtime_folder)
        resume_completed = self._colab_resume_completed_keys if resume_active else set()
        for entry in self.selected_runtime_entries:
            runtime_mp3 = self._normalize_saved_folder_path(entry.get("runtime_mp3", ""))
            if not runtime_mp3 or not os.path.isfile(runtime_mp3):
                continue
            source_mp3 = self._normalize_saved_folder_path(entry.get("target_mp3", "")) or runtime_mp3
            source_key = self._colab_path_key(source_mp3)
            if resume_active and source_key and source_key in resume_completed:
                continue
            queue_name = str(entry.get("queue_name", "")).strip() or os.path.basename(runtime_mp3)
            targets.append(
                {
                    "runtime_mp3": runtime_mp3,
                    "event_name": queue_name,
                    "source_mp3": source_mp3,
                }
            )

        if targets:
            return targets

        normalized_runtime = self._normalize_saved_folder_path(runtime_folder)
        if not normalized_runtime or not os.path.isdir(normalized_runtime):
            return []

        for name in sorted(os.listdir(normalized_runtime)):
            if not name.lower().endswith(".mp3"):
                continue
            runtime_mp3 = os.path.join(normalized_runtime, name)
            if os.path.isfile(runtime_mp3):
                source_key = self._colab_path_key(runtime_mp3)
                if resume_active and source_key and source_key in resume_completed:
                    continue
                targets.append({"runtime_mp3": runtime_mp3, "event_name": name, "source_mp3": runtime_mp3})
        return targets

    def _colab_safe_seconds(self, value, default: float = 0.0) -> float:
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            return float(default)
        if seconds != seconds:
            return float(default)
        return max(0.0, seconds)

    def _colab_format_timestamp(self, seconds: float) -> str:
        safe_seconds = self._colab_safe_seconds(seconds, default=0.0)
        millis = int(round(safe_seconds * 1000))
        hours = millis // 3600000
        millis %= 3600000
        minutes = millis // 60000
        millis %= 60000
        secs = millis // 1000
        millis %= 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _write_colab_srt(self, result: dict, srt_path: str):
        segments = result.get("segments", []) or []
        with open(srt_path, "w", encoding="utf-8") as f:
            index = 1
            for seg in segments:
                if not isinstance(seg, dict):
                    continue
                text = str(seg.get("text", "") or "").strip()
                if not text:
                    continue
                start = self._colab_safe_seconds(seg.get("start", 0.0), default=0.0)
                end = self._colab_safe_seconds(seg.get("end", 0.0), default=start)
                if end < start:
                    end = start
                f.write(f"{index}\n")
                f.write(f"{self._colab_format_timestamp(start)} --> {self._colab_format_timestamp(end)}\n")
                f.write(text + "\n\n")
                index += 1

    def _save_colab_result_files(self, audio_path: str, result: dict):
        txt_path, json_path, srt_path = self._output_triplet(audio_path)
        for output_path in (txt_path, json_path, srt_path):
            parent = os.path.dirname(output_path)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)

        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(str(result.get("text", "") or "").strip() + "\n")
        except Exception as exc:
            raise OSError(f"TXT 저장 실패: {txt_path} ({type(exc).__name__}: {exc})") from exc

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            raise OSError(f"JSON 저장 실패: {json_path} ({type(exc).__name__}: {exc})") from exc

        try:
            self._write_colab_srt(result, srt_path)
        except Exception as exc:
            raise OSError(f"SRT 저장 실패: {srt_path} ({type(exc).__name__}: {exc})") from exc

        return txt_path, json_path, srt_path

    def _encode_colab_multipart_file(self, file_path: str) -> tuple[bytes, str]:
        boundary = f"----TranscribeHelperBoundary{uuid.uuid4().hex}"
        boundary_bytes = boundary.encode("ascii")
        crlf = b"\r\n"
        file_name = os.path.basename(file_path)
        mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        body = bytearray()
        body.extend(b"--" + boundary_bytes + crlf)
        body.extend(b'Content-Disposition: form-data; name="language"' + crlf + crlf)
        body.extend(b"ko" + crlf)
        body.extend(b"--" + boundary_bytes + crlf)
        body.extend(
            (
                f'Content-Disposition: form-data; name="file"; filename="{file_name}"'
            ).encode("utf-8")
            + crlf
        )
        body.extend((f"Content-Type: {mime_type}").encode("utf-8") + crlf + crlf)
        body.extend(file_bytes + crlf)
        body.extend(b"--" + boundary_bytes + b"--" + crlf)

        content_type = f"multipart/form-data; boundary={boundary}"
        return bytes(body), content_type

    def _get_ffmpeg_executable(self) -> str:
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path
        raise RuntimeError(
            "ffmpeg를 찾을 수 없습니다. Colab 분할 전송을 위해 ffmpeg 설치 후 PATH에 등록해 주세요."
        )

    def _split_mp3_for_colab_chunks(
        self, source_mp3: str, chunk_seconds: int = COLAB_CHUNK_SECONDS
    ) -> tuple[list[dict], str]:
        if not source_mp3 or not os.path.isfile(source_mp3):
            raise FileNotFoundError(f"분할 대상 파일이 없습니다: {source_mp3}")

        ffmpeg_path = self._get_ffmpeg_executable()
        parent_dir = os.path.dirname(source_mp3) or os.getcwd()
        chunk_dir = tempfile.mkdtemp(prefix="colab_chunks_", dir=parent_dir)
        chunk_pattern = os.path.join(chunk_dir, "chunk_%04d.mp3")

        cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            source_mp3,
            "-f",
            "segment",
            "-segment_time",
            str(max(60, int(chunk_seconds))),
            "-c",
            "copy",
            "-reset_timestamps",
            "1",
            chunk_pattern,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"MP3 분할 실패(ffmpeg): {err or 'unknown error'}")

        chunk_names = sorted(
            [
                name
                for name in os.listdir(chunk_dir)
                if name.lower().endswith(".mp3") and name.lower().startswith("chunk_")
            ]
        )
        if not chunk_names:
            raise RuntimeError("MP3 분할 실패: 생성된 조각 파일이 없습니다.")

        chunk_infos: list[dict] = []
        offset_seconds = 0.0
        for idx, name in enumerate(chunk_names):
            chunk_path = os.path.join(chunk_dir, name)
            duration_text = self._detect_duration_mmss(chunk_path)
            duration_seconds = self._duration_text_to_seconds(duration_text)
            if duration_seconds <= 0:
                duration_seconds = float(max(60, int(chunk_seconds)))

            chunk_infos.append(
                {
                    "path": chunk_path,
                    "offset": float(offset_seconds),
                    "duration": float(duration_seconds),
                    "index": idx + 1,
                }
            )
            offset_seconds += max(0.0, float(duration_seconds))

        return chunk_infos, chunk_dir

    def _post_colab_transcribe(self, transcribe_url: str, file_path: str) -> dict:
        body, content_type = self._encode_colab_multipart_file(file_path)
        req = urllib_request.Request(
            transcribe_url,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": content_type,
                "Cache-Control": "no-cache",
            },
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=1800) as response:
            payload_bytes = response.read()
            charset = response.headers.get_content_charset() or "utf-8"

        try:
            payload = json.loads(payload_bytes.decode(charset, errors="replace"))
        except json.JSONDecodeError as exc:
            raise ValueError("Colab 서버 응답이 JSON 형식이 아닙니다.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Colab 서버 응답 형식이 올바르지 않습니다.")

        if str(payload.get("error", "") or "").strip():
            raise RuntimeError(str(payload.get("error")).strip())

        text_value = str(payload.get("text", "") or "").strip()
        raw_segments = payload.get("segments", [])
        if not isinstance(raw_segments, list):
            raw_segments = []

        normalized_segments: list[dict] = []
        for idx, seg in enumerate(raw_segments):
            if not isinstance(seg, dict):
                continue
            seg_text = str(seg.get("text", "") or "").strip()
            start = self._colab_safe_seconds(seg.get("start", 0.0), default=0.0)
            end = self._colab_safe_seconds(seg.get("end", 0.0), default=start)
            if end < start:
                end = start
            seg_id = seg.get("id", idx)
            try:
                seg_id = int(seg_id)
            except (TypeError, ValueError):
                seg_id = idx
            normalized_segments.append(
                {
                    "id": seg_id,
                    "start": max(0.0, start),
                    "end": max(0.0, end),
                    "text": seg_text,
                }
            )

        normalized_payload = dict(payload)
        normalized_payload["text"] = text_value
        normalized_payload["segments"] = normalized_segments
        normalized_payload["language"] = str(payload.get("language", "") or "").strip() or "ko"
        return normalized_payload

    def _start_colab_transcribe_run(self, runtime_folder: str) -> bool:
        colab_url = str(self.input_colab_url.text() or "").strip()
        transcribe_url = self._build_colab_transcribe_url(colab_url)
        if not self.btn_colab_check.property("connected"):
            self.show_info_message("알림", "Colab 연결을 먼저 확인해 주세요.")
            self.set_transcribe_buttons_enabled(True)
            self._sync_selected_runtime_outputs()
            self.selected_run_items = []
            return False

        if not transcribe_url:
            self.show_info_message("알림", "Colab URL을 먼저 입력하고 연결을 확인해 주세요.")
            self.set_transcribe_buttons_enabled(True)
            self._sync_selected_runtime_outputs()
            self.selected_run_items = []
            return False

        try:
            _ffmpeg_path = self._get_ffmpeg_executable()
            self.append_log_text(f"[GUI] ffmpeg 확인 완료: {_ffmpeg_path}\n")
        except Exception as exc:
            self.append_log_text(f"[GUI] Colab 분할 전송 준비 실패: {exc}\n", force=True)
            self.show_warning_message("경고", str(exc))
            self.set_transcribe_buttons_enabled(True)
            self._sync_selected_runtime_outputs()
            self.selected_run_items = []
            return False

        run_targets = self._collect_colab_runtime_targets(runtime_folder)
        if not run_targets:
            self.set_transcribe_buttons_enabled(True)
            self._sync_selected_runtime_outputs()
            self.selected_run_items = []
            self.show_info_message("알림", "이번 실행에서 처리할 파일이 없습니다.")
            return False
        progress_state = self._build_colab_progress_state(runtime_folder, run_targets)

        self.total_target_mp3_files = len(run_targets)
        self.update_total_progress_display()
        self.update_eta_labels(initial=True)

        self._colab_run_active = True
        self._colab_stop_after_current = False
        self._colab_run_request_id += 1
        request_id = self._colab_run_request_id
        self._set_status_text(self._run_mode_in_progress_text())
        self._set_current_file_text("없음")
        self.append_log_text(f"[GUI] Colab 전사 시작: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        worker = threading.Thread(
            target=self._run_colab_transcribe_worker,
            args=(request_id, transcribe_url, run_targets, progress_state),
            daemon=True,
        )
        worker.start()
        return True

    def _run_colab_transcribe_worker(
        self,
        request_id: int,
        transcribe_url: str,
        run_targets: list[dict],
        progress_state: dict | None = None,
    ):
        def _emit_comm_time():
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            self._colab_run_bridge.last_comm.emit(now_str)

        def _safe_token(value) -> str:
            return str(value or "").replace("\r", " ").replace("\n", " ").replace("|", "/").strip()

        def _emit_event(evt: str, *payload):
            parts = [str(evt)] + [_safe_token(v) for v in payload]
            line = "[EVENT] " + "|".join(parts)
            self._colab_run_bridge.event_line.emit(line)

        def _emit_log(text: str):
            self._colab_run_bridge.log_line.emit(str(text or ""))

        try:
            total = len(run_targets)
            _emit_event("TOTAL_FILES", total, 0, total)

            if total <= 0:
                _emit_event("ALL_DONE")
                self._colab_run_bridge.finished.emit(int(request_id), "done", "")
                return

            stopped = False
            for idx, target in enumerate(run_targets, start=1):
                if int(request_id) != int(self._colab_run_request_id):
                    return
                if self._colab_stop_after_current:
                    stopped = True
                    break

                runtime_mp3 = str(target.get("runtime_mp3", "") or "").strip()
                event_name = _safe_token(target.get("event_name", os.path.basename(runtime_mp3)))
                if not runtime_mp3 or not os.path.isfile(runtime_mp3):
                    _emit_event("FILE_FAIL", event_name, "파일을 찾을 수 없습니다.")
                    _emit_log(f"[GUI] Colab 전사 실패 상세: 파일={event_name}, 단계=파일 확인, 경로={runtime_mp3}\n")
                    if self._colab_stop_after_current:
                        stopped = True
                        break
                    continue

                _emit_event("FILE_INDEX", idx, total, event_name)
                stage = "분할 준비"
                chunk_dir = ""
                try:
                    try:
                        file_size = os.path.getsize(runtime_mp3)
                    except OSError:
                        file_size = 0
                    _emit_log(f"[GUI] Colab 요청 시작: {event_name} ({file_size} bytes)\n")

                    stage = "MP3 분할"
                    chunk_infos, chunk_dir = self._split_mp3_for_colab_chunks(
                        runtime_mp3, chunk_seconds=COLAB_CHUNK_SECONDS
                    )
                    chunk_total = len(chunk_infos)
                    if chunk_total <= 0:
                        raise RuntimeError("분할 조각이 생성되지 않았습니다.")
                    _emit_log(
                        f"[GUI] MP3 분할 완료: {event_name} / 조각 {chunk_total}개 (단위 {int(COLAB_CHUNK_SECONDS)}초)\n"
                    )

                    merged_segments: list[dict] = []
                    merged_text_parts: list[str] = []
                    merged_language = ""

                    for chunk_idx, chunk in enumerate(chunk_infos, start=1):
                        if int(request_id) != int(self._colab_run_request_id):
                            return
                        if self._colab_stop_after_current:
                            _emit_log(
                                f"[GUI] 중지 요청 감지: 다음 조각 시작 전 중단 ({event_name}, {chunk_idx}/{chunk_total})\n"
                            )
                            stopped = True
                            break

                        chunk_path = str(chunk.get("path", "") or "").strip()
                        chunk_offset = self._colab_safe_seconds(chunk.get("offset", 0.0), default=0.0)
                        stage = f"조각 전송 {chunk_idx}/{chunk_total}"

                        chunk_result = self._post_colab_transcribe(transcribe_url, chunk_path)
                        _emit_comm_time()

                        if not merged_language:
                            merged_language = str(chunk_result.get("language", "") or "").strip() or "ko"

                        chunk_text = str(chunk_result.get("text", "") or "").strip()
                        if chunk_text:
                            merged_text_parts.append(chunk_text)

                        for seg in (chunk_result.get("segments", []) or []):
                            if not isinstance(seg, dict):
                                continue
                            seg_text = str(seg.get("text", "") or "").strip()
                            if not seg_text:
                                continue
                            seg_start = self._colab_safe_seconds(seg.get("start", 0.0), default=0.0) + chunk_offset
                            seg_end = self._colab_safe_seconds(seg.get("end", 0.0), default=seg_start) + chunk_offset
                            if seg_end < seg_start:
                                seg_end = seg_start
                            merged_segments.append(
                                {
                                    "id": len(merged_segments),
                                    "start": seg_start,
                                    "end": seg_end,
                                    "text": seg_text,
                                }
                            )

                        _emit_event("FILE_PROGRESS", event_name, chunk_idx, chunk_total)
                        _emit_log(f"[GUI] Colab 조각 완료: {event_name} ({chunk_idx}/{chunk_total})\n")

                        if self._colab_stop_after_current:
                            _emit_log(
                                f"[GUI] 중지 요청 감지: 현재 조각 완료 후 중단 ({event_name}, {chunk_idx}/{chunk_total})\n"
                            )
                            stopped = True
                            break

                    if stopped:
                        break

                    stage = "결과 병합"
                    merged_result = {
                        "text": " ".join(merged_text_parts).strip(),
                        "segments": merged_segments,
                        "language": merged_language or "ko",
                    }

                    stage = "결과 파일 저장"
                    txt_path, json_path, srt_path = self._save_colab_result_files(runtime_mp3, merged_result)
                    source_mp3 = self._normalize_saved_folder_path(target.get("source_mp3", "")) or runtime_mp3
                    self._record_colab_progress_completion(
                        progress_state or {},
                        source_mp3,
                        txt_path,
                        json_path,
                        srt_path,
                    )
                    _emit_log(f"[GUI] Colab 결과 저장 완료: {event_name}\n")
                    _emit_log(f"[GUI] 저장 경로: TXT={txt_path}\n")
                    _emit_log(f"[GUI] 저장 경로: JSON={json_path}\n")
                    _emit_log(f"[GUI] 저장 경로: SRT={srt_path}\n")
                    _emit_event("FILE_DONE", event_name)
                    _emit_log(f"[GUI] Colab 전사 완료: {event_name}\n")
                except urllib_error.HTTPError as exc:
                    err_text = f"HTTP {getattr(exc, 'code', '?')} {str(getattr(exc, 'reason', '') or '').strip()}".strip()
                    _emit_event("FILE_FAIL", event_name, err_text or "HTTP 오류")
                    _emit_log(f"[GUI] Colab 전사 실패: {event_name} / {err_text}\n")
                    try:
                        body_bytes = exc.read()
                        body_text = body_bytes.decode("utf-8", errors="replace").strip() if body_bytes else ""
                    except Exception:
                        body_text = ""
                    if body_text:
                        _emit_log(f"[GUI] Colab HTTP 응답 본문: {body_text[:400]}\n")
                    _emit_log(
                        f"[GUI] Colab 전사 실패 상세: 파일={event_name}, 단계={stage}, 예외={type(exc).__name__}, 메시지={err_text}\n"
                    )
                    _emit_log(f"[GUI] Colab traceback:\n{traceback.format_exc()}\n")
                except (TimeoutError, urllib_error.URLError, OSError, ValueError, RuntimeError) as exc:
                    raw_error = str(exc) or "요청 실패"
                    err_text = _safe_token(raw_error)
                    _emit_event("FILE_FAIL", event_name, err_text)
                    _emit_log(f"[GUI] Colab 전사 실패: {event_name} / {err_text}\n")
                    _emit_log(
                        f"[GUI] Colab 전사 실패 상세: 파일={event_name}, 단계={stage}, 예외={type(exc).__name__}, 메시지={raw_error}\n"
                    )
                    _emit_log(f"[GUI] Colab traceback:\n{traceback.format_exc()}\n")
                except Exception as exc:
                    raw_error = str(exc) or "알 수 없는 오류"
                    err_text = _safe_token(raw_error)
                    _emit_event("FILE_FAIL", event_name, err_text)
                    _emit_log(f"[GUI] Colab 전사 실패: {event_name} / {err_text}\n")
                    _emit_log(
                        f"[GUI] Colab 전사 실패 상세: 파일={event_name}, 단계={stage}, 예외={type(exc).__name__}, 메시지={raw_error}\n"
                    )
                    _emit_log(f"[GUI] Colab traceback:\n{traceback.format_exc()}\n")
                finally:
                    if chunk_dir and os.path.isdir(chunk_dir):
                        try:
                            shutil.rmtree(chunk_dir, ignore_errors=True)
                        except Exception as cleanup_exc:
                            _emit_log(
                                f"[GUI] Colab 임시 조각 폴더 정리 실패: {chunk_dir} ({type(cleanup_exc).__name__}: {cleanup_exc})\n"
                            )

                if self._colab_stop_after_current:
                    stopped = True
                    break

            if stopped:
                _emit_event("ALL_STOPPED")
                self._colab_run_bridge.finished.emit(int(request_id), "stopped", "")
                return

            self._remove_colab_progress_file_safely(str((progress_state or {}).get("path", "") or ""))
            _emit_event("ALL_DONE")
            self._colab_run_bridge.finished.emit(int(request_id), "done", "")
        except Exception as exc:
            _emit_log(
                f"[GUI] Colab 워커 치명 오류: 단계=워커 루프, 예외={type(exc).__name__}, 메시지={str(exc)}\n"
            )
            _emit_log(f"[GUI] Colab 워커 traceback:\n{traceback.format_exc()}\n")
            self._colab_run_bridge.finished.emit(int(request_id), "error", str(exc))

    def _on_colab_transcribe_event_line(self, line: str):
        try:
            self.process_event_line(str(line or ""))
        except Exception:
            pass

    def _on_colab_transcribe_log_line(self, text: str):
        if not text:
            return
        message = str(text)
        if not message.endswith("\n"):
            message += "\n"
        stripped = message.strip()
        if stripped.startswith("[GUI] "):
            display = stripped[len("[GUI] "):] + "\n"
        else:
            display = message
        self.append_log_text(display, force=True)

    def _on_colab_transcribe_finished(self, request_id: int, outcome: str, detail: str):
        if int(request_id) != int(self._colab_run_request_id):
            return

        self._colab_run_active = False
        self._colab_stop_after_current = False
        self.set_transcribe_buttons_enabled(True)
        self._sync_selected_runtime_outputs()
        self.selected_run_items = []
        self.update_session_label()

        if outcome == "done":
            progress_path = self._colab_progress_path_for_runtime(self.target_folder)
            self._remove_colab_progress_file_safely(progress_path)
            self._clear_colab_resume_state()

        if outcome == "error":
            self._set_status_text("오류 발생")
            if detail:
                self.append_log_text(f"[GUI] Colab 전사 런타임 오류: {detail}\n")
            self.show_error_message("오류", f"Colab 전사 처리 중 오류가 발생했습니다.\n\n{detail or '-'}")

        self.stop_requested = False
        self.pending_kill = False
        self.stop_terminate_sent = False


    def open_colab_notebook(self):
        url = "https://colab.research.google.com/github/bongbong90/jeonsa_doumi/blob/main/colab_transcribe.ipynb"
        webbrowser.open(url)

    def update_colab_last_comm(self, timestamp_str):
        self.label_colab_last_comm.setText(f"마지막 통신: {timestamp_str}")
    def _on_colab_url_text_changed(self, text: str):
        self.colab_url = str(text or "").strip()
        if self._colab_check_connected:
            self._colab_check_connected = False
            self._update_colab_check_button_state()
        self.save_ui_preferences()

    def _handle_colab_connection_check(self):
        colab_url = str(self.input_colab_url.text() or "").strip()
        if not colab_url:
            self.show_info_message("알림", "Colab URL을 입력해 주세요.")
            return
        health_url = self._build_colab_health_url(colab_url)
        if not health_url:
            self.show_info_message("알림", "Colab 서버에 연결할 수 없습니다. URL을 확인해 주세요.")
            return
        if self._colab_check_in_progress:
            return

        self._colab_check_in_progress = True
        self._colab_check_connected = False
        self._colab_check_request_id += 1
        request_id = self._colab_check_request_id
        self._update_colab_check_button_state()

        worker = threading.Thread(
            target=self._perform_colab_health_check,
            args=(request_id, health_url),
            daemon=True,
        )
        worker.start()

    def _on_colab_health_check_finished(self, request_id: int, result_code: str):
        if int(request_id) != int(self._colab_check_request_id):
            return
        self._colab_check_in_progress = False
        if result_code == "success":
            self._colab_check_connected = True
            self._update_colab_check_button_state()
            self.show_info_message("알림", "Colab 연결 성공")
            return

        self._colab_check_connected = False
        self._update_colab_check_button_state()
        if result_code == "invalid_response":
            self.show_info_message("알림", "Colab 서버 응답이 올바르지 않습니다.")
            return
        self.show_info_message("알림", "Colab 서버에 연결할 수 없습니다. URL을 확인해 주세요.")

    def load_ui_preferences(self):
        try:
            self.target_folder = self._normalize_saved_folder_path(
                self.ui_settings.value(SETTINGS_KEY_TARGET_DIR, "")
            )
            self.chk_notify_each_file.setChecked(
                bool(self.ui_settings.value(SETTINGS_KEY_NOTIFY_EACH, True, type=bool))
            )
            self.chk_notify_total.setChecked(
                bool(self.ui_settings.value(SETTINGS_KEY_NOTIFY_TOTAL, True, type=bool))
            )
            self.upload_drive_checkbox.setChecked(
                bool(self.ui_settings.value(SETTINGS_KEY_UPLOAD_DRIVE, False, type=bool))
            )
            saved_course = str(self.ui_settings.value(SETTINGS_KEY_TRANSCRIBE_COURSE, "") or "").strip()
            self.combo_transcribe_course.setCurrentText(saved_course)
            saved_subject = str(self.ui_settings.value(SETTINGS_KEY_TRANSCRIBE_SUBJECT, "") or "").strip()
            self.combo_transcribe_subject.setCurrentText(saved_subject)
            self.shutdown_checkbox.setChecked(
                bool(self.ui_settings.value(SETTINGS_KEY_SHUTDOWN_AFTER_DONE, False, type=bool))
            )
            shutdown_wait_seconds = int(
                self.ui_settings.value(SETTINGS_KEY_SHUTDOWN_WAIT_SECONDS, 0, type=int)
            )
            self._set_shutdown_wait_seconds(shutdown_wait_seconds)
            saved_engine = self._normalize_transcription_engine(
                self.ui_settings.value(SETTINGS_KEY_TRANSCRIPTION_ENGINE, "local")
            )
            self._set_transcription_engine_value(saved_engine)
            saved_colab_url = str(self.ui_settings.value(SETTINGS_KEY_COLAB_URL, "") or "").strip()
            self.colab_url = saved_colab_url
            self.input_colab_url.setText(saved_colab_url)
        except Exception:
            pass

        self._sync_shutdown_wait_combo_state()
        self._sync_transcription_engine_ui_state()
        self._refresh_path_labels()
        QTimer.singleShot(0, self._refresh_path_labels)

        if self.target_folder and os.path.isdir(self.target_folder):
            self._load_mp3_files_from_folder(self.target_folder, append=False, show_empty_message=False)

        self._refresh_file_list_empty_state()
        self._update_checked_state()

    def save_ui_preferences(self):





        try:





            self.ui_settings.setValue(SETTINGS_KEY_TARGET_DIR, self.target_folder or "")





            self.ui_settings.setValue(SETTINGS_KEY_NOTIFY_EACH, self.chk_notify_each_file.isChecked())





            self.ui_settings.setValue(SETTINGS_KEY_NOTIFY_TOTAL, self.chk_notify_total.isChecked())

            self.ui_settings.setValue(SETTINGS_KEY_UPLOAD_DRIVE, self.upload_drive_checkbox.isChecked())
            self.ui_settings.setValue(SETTINGS_KEY_TRANSCRIBE_COURSE, self.combo_transcribe_course.currentText())
            self.ui_settings.setValue(SETTINGS_KEY_TRANSCRIBE_SUBJECT, self.combo_transcribe_subject.currentText())

            self.ui_settings.setValue(SETTINGS_KEY_SHUTDOWN_AFTER_DONE, self.shutdown_checkbox.isChecked())





            self.ui_settings.setValue(SETTINGS_KEY_SHUTDOWN_WAIT_SECONDS, self._get_shutdown_wait_seconds())
            self.ui_settings.setValue(
                SETTINGS_KEY_TRANSCRIPTION_ENGINE, self._current_transcription_engine()
            )
            self.ui_settings.setValue(
                SETTINGS_KEY_COLAB_URL, str(self.input_colab_url.text() or "").strip()
            )
            self.transcription_engine = self._current_transcription_engine()
            self.colab_url = str(self.input_colab_url.text() or "").strip()





            self.ui_settings.sync()





        except Exception:





            pass











    def _set_shutdown_wait_seconds(self, seconds: int):





        safe_seconds = max(0, int(seconds))





        idx = self.shutdown_wait_combo.findData(safe_seconds)





        if idx < 0:





            idx = 0





        if self.shutdown_wait_combo.currentIndex() != idx:





            self.shutdown_wait_combo.setCurrentIndex(idx)











    def _get_shutdown_wait_seconds(self) -> int:





        value = self.shutdown_wait_combo.currentData()





        try:





            return max(0, int(value))





        except Exception:





            return 0











    def _sync_shutdown_wait_combo_state(self):





        enabled = self.shutdown_checkbox.isChecked()





        if self.shutdown_wait_combo.isEnabled() != enabled:





            self.shutdown_wait_combo.setEnabled(enabled)











    def _set_path_label(self, label: QLabel, title: str, path: str):





        if not path:





            value_text = "폴더를 선택하세요"





            label.setToolTip("")





            label.setProperty("empty", True)





        else:





            label_width = label.width() if label.width() > 0 else label.sizeHint().width()





            available = max(120, label_width - 16)





            value_text = self._elide_path_for_label(label, path, available)





            label.setToolTip(self._display_path_for_ui(path))





            label.setProperty("empty", False)





        label.setText(value_text)





        label.style().unpolish(label)





        label.style().polish(label)





        label.update()











    def _configure_folder_and_control_ui(self):
        self.label_target.setText("\uD3F4\uB354\uB97C \uC120\uD0DD\uD558\uC138\uC694")

        self.btn_target.setText("\uD3F4\uB354 \uC120\uD0DD")
        self.btn_load_files.setText("\uD30C\uC77C \uC120\uD0DD")

        self.btn_transcribe_target.setText("\uC804\uC0AC\uC2DC\uC791")
        self.btn_stop_now.setText("\uC804\uC0AC\uC911\uC9C0")
        self.btn_move_files.setText("\uD30C\uC77C\uC774\uB3D9")
        self.btn_move_and_transcribe.setText("\uC774\uB3D9\uC804\uC0AC")

        self.btn_transcribe_target.setProperty("uiRole", "controlPrimary")
        self.btn_stop_now.setProperty("uiRole", "controlGhost")
        self.btn_move_files.setProperty("uiRole", "controlOutline")
        self.btn_move_and_transcribe.setProperty("uiRole", "controlOutlinePrimary")

        self.btn_move_and_transcribe.setEnabled(False)


        cbox = self.group_controls.layout() if hasattr(self, "group_controls") else None
        if cbox is not None:
            row_layouts = []
            for i in range(cbox.count()):
                item = cbox.itemAt(i)
                lay = item.layout() if item is not None else None
                if isinstance(lay, QHBoxLayout):
                    row_layouts.append(lay)
            if len(row_layouts) >= 2:
                row1, row2 = row_layouts[0], row_layouts[1]

                def _clear(layout: QHBoxLayout):
                    while layout.count():
                        child = layout.takeAt(0)
                        w = child.widget()
                        if w is not None:
                            w.setParent(None)

                _clear(row1)
                _clear(row2)

                row1.addWidget(self.btn_transcribe_target, 1)
                row1.addWidget(self.btn_stop_now, 1)

                row2.addWidget(self.btn_move_files, 1)
                row2.addWidget(self.btn_move_and_transcribe, 1)

    def _build_material_symbol_icon(self, symbol_name: str, size_px: int = 18, color: QColor | None = None) -> QIcon:
        material_codepoints = {
            "play_circle": "\ue1c4",
            "stop_circle": "\uef71",
            "drive_file_move": "\ue675",
            "play_arrow": "\ue037",
        }
        fallback_glyphs = {
            "play_circle": "?",
            "stop_circle": "?",
            "drive_file_move": "?",
            "play_arrow": "?",
        }

        families = [
            "Material Symbols Outlined",
            "Material Symbols Rounded",
            "Material Symbols Sharp",
        ]
        installed = set(QFontDatabase.families())
        family = ""
        for candidate in families:
            if candidate in installed:
                family = candidate
                break

        glyph = material_codepoints.get(symbol_name, "")
        if not family:
            family = self.font().family()
            glyph = fallback_glyphs.get(symbol_name, "?")

        if not glyph:
            return QIcon()

        pix = QPixmap(size_px, size_px)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        font = QFont(family)
        font.setPixelSize(size_px)
        painter.setFont(font)
        painter.setPen(color if color is not None else QColor("#1a1b21"))
        painter.drawText(pix.rect(), Qt.AlignCenter, glyph)
        painter.end()

        return QIcon(pix)

    def _set_button_material_icon(self, button: QPushButton, symbol_name: str, color: QColor | None = None):
        icon = self._build_material_symbol_icon(symbol_name, size_px=18, color=color)
        if icon.isNull():
            return
        button.setIcon(icon)
        button.setIconSize(QSize(18, 18))

    def _reset_idle_progress_state(self):
        if self._is_transcribe_running():
            return
        self.total_target_mp3_files = 0
        self.completed_files.clear()
        self.last_completed_file_name = ""
        self.current_file_name = ""
        self.current_file_started_at = None
        self.duration_eta_ratio = DEFAULT_WHISPER_TIME_RATIO
        self.duration_eta_ratio_calibrated = False
        self.run_total_audio_seconds = 0.0
        self.run_done_audio_seconds = 0.0
        self.run_current_audio_seconds = 0.0
        self.run_audio_seconds_by_primary_key.clear()
        self.run_audio_alias_to_primary_key.clear()
        self.run_audio_accounted_primary_keys.clear()
        self.update_current_file_progress(0, force=True)
        self._set_current_file_text("\uC5C6\uC74C")
        self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)
        self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
        self._set_status_text("\uB300\uAE30 \uC911")

    def _load_mp3_files_from_folder(self, folder: str, append: bool = False, show_empty_message: bool = True) -> bool:
        normalized = self._normalize_saved_folder_path(folder)
        if not normalized or not os.path.isdir(normalized):
            if show_empty_message:
                self.show_warning_message("\uACBD\uACE0", "\uC120\uD0DD\uD55C \uD3F4\uB354\uB97C \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.")
            return False

        mp3_paths = []
        for name in sorted(os.listdir(normalized)):
            if not name.lower().endswith(".mp3"):
                continue
            mp3_paths.append(os.path.join(normalized, name))

        self._rebuild_queue_from_files(mp3_paths, append=append)
        self._reset_idle_progress_state()
        self.update_total_progress_display()
        self._refresh_file_list_empty_state()

        if show_empty_message and not mp3_paths:
            self.show_warning_message(
                "MP3 파일을 찾을 수 없어요",
                "선택한 폴더에 전사할 MP3 파일이 없습니다.\n다른 폴더를 선택하거나 MP3 파일을 추가한 뒤 다시 시도해 주세요."
            )

        return True

    def _runtime_parent_for_selected_items(self) -> str:
        if self.target_folder:
            target = self._normalize_saved_folder_path(self.target_folder)
            if target:
                parent = os.path.dirname(target)
                if parent:
                    return parent
                return target

        for item in self.selected_run_items:
            src = self._normalize_saved_folder_path(item.get("source_path", ""))
            if src:
                parent = os.path.dirname(src)
                if parent:
                    return parent

        return self.get_base_dir()

    def _run_mode_in_progress_text(self) -> str:
        if self.run_mode == "selected":
            return "\uC120\uD0DD \uC804\uC0AC \uC9C4\uD589 \uC911"
        if self.run_mode == "moved":
            return "\uC774\uB3D9\uC804\uC0AC \uC9C4\uD589 \uC911"
        return "\uC804\uCCB4 \uC804\uC0AC \uC9C4\uD589 \uC911"

    def _run_mode_done_texts(self) -> tuple[str, str, str]:
        if self.run_mode == "selected":
            return (
                "\uC120\uD0DD \uC804\uC0AC \uC644\uB8CC",
                "\uC120\uD0DD \uC804\uC0AC \uC644\uB8CC",
                "\uC120\uD0DD\uD55C MP3 \uC804\uC0AC\uAC00 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.",
            )
        if self.run_mode == "moved":
            return (
                "\uC774\uB3D9\uC804\uC0AC \uC644\uB8CC",
                "\uC774\uB3D9\uC804\uC0AC \uC644\uB8CC",
                "\uC774\uB3D9\uD55C MP3 \uC804\uC0AC\uAC00 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.",
            )
        return (
            "\uC804\uCCB4 \uC804\uC0AC \uC644\uB8CC",
            "\uC804\uCCB4 \uC804\uC0AC \uC644\uB8CC",
            "\uC804\uCCB4 \uC804\uC0AC\uAC00 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.",
        )

    def _prepare_transcribe_items_with_rename(self, rows: list[dict], log_key: str) -> tuple[list[dict], int, int]:
        rename_success = 0
        rename_failed = 0
        run_items: list[dict] = []

        for row in rows:
            src = self._normalize_saved_folder_path(row.get("source_path", ""))
            if not src or not os.path.isfile(src):
                continue

            current_name = os.path.basename(src)
            desired_name = self._resolve_transcribe_name_by_priority(row, src)
            final_name = current_name

            if desired_name and desired_name.lower() != current_name.lower():
                dst = os.path.join(os.path.dirname(src), desired_name)
                try:
                    src_abs = os.path.normcase(os.path.abspath(src))
                    dst_abs = os.path.normcase(os.path.abspath(dst))
                    if src_abs != dst_abs:
                        if os.path.exists(dst):
                            raise FileExistsError(f"\uB3D9\uC77C\uD55C \uC774\uB984\uC758 \uD30C\uC77C\uC774 \uC774\uBBF8 \uC874\uC7AC\uD569\uB2C8\uB2E4: {desired_name}")
                        os.replace(src, dst)
                        src = dst
                        final_name = os.path.basename(src)
                        row["filename"] = final_name
                        row["original_filename"] = final_name
                        rename_success += 1
                        self.append_log_text(f"[DBG] {log_key} rename success: {current_name!r} -> {final_name!r}\\n", force=True)
                except Exception as e:
                    rename_failed += 1
                    final_name = current_name
                    self.append_log_text(f"[WARN] {log_key} rename failed: {src} -> {desired_name} ({e})\\n", force=True)

            row["source_path"] = src
            row["transcribe_name"] = final_name
            duration_text = str(row.get("duration", ""))
            duration_seconds = self._duration_text_to_seconds(duration_text)

            run_items.append(
                {
                    "queue_name": str(row.get("filename", final_name)),
                    "transcribe_name": final_name,
                    "source_path": src,
                    "duration": duration_text,
                    "duration_seconds": duration_seconds,
                }
            )

        return run_items, rename_success, rename_failed

    def _refresh_path_labels(self):
        self._set_path_label(
            self.label_target,
            "\uC120\uD0DD \uD3F4\uB354",
            self.target_folder,
        )
        self._refresh_meta_summary()

    def resizeEvent(self, event):





        super().resizeEvent(event)





        self._apply_status_and_meta_labels()





        self._refresh_path_labels()





        QTimer.singleShot(0, self._sync_sidebar_height)











    def _sync_sidebar_height(self):





        sidebar = getattr(self, "sidebar_pane", None)





        mainpane = getattr(self, "main_pane", None)





        if sidebar is None or mainpane is None:





            return





        target_h = max(0, int(mainpane.height()))





        if target_h <= 0:





            return





        if sidebar.minimumHeight() != target_h:





            sidebar.setMinimumHeight(target_h)





        if sidebar.maximumHeight() != target_h:





            sidebar.setMaximumHeight(target_h)





        self._sync_sidebar_panel_heights()











    def _sync_sidebar_panel_heights(self):





        sidebar = getattr(self, "sidebar_pane", None)





        left = getattr(self, "sidebar_sections_layout", None)





        if sidebar is None or left is None:





            return





        if not all(hasattr(self, name) for name in ("group_settings", "group_options", "group_logs")):





            return











        margins = left.contentsMargins()





        spacing = max(0, left.spacing())





        available = int(sidebar.height()) - margins.top() - margins.bottom() - (spacing * 2)





        if available <= 0:





            return











        settings_min = max(156, int(self.group_settings.minimumSizeHint().height()) + 8)





        options_min = max(118, int(self.group_options.minimumSizeHint().height()))





        logs_min = max(





            220,





            int(self.group_logs.minimumSizeHint().height()),





        )











        settings_h = settings_min





        options_h = options_min





        logs_h = max(logs_min, available - settings_h - options_h)











        if settings_h + options_h + logs_h > available:





            # Keep each card's natural height and allow sidebar scrolling on overflow.





            logs_h = logs_min











        self.group_settings.setFixedHeight(settings_h)





        self.group_options.setFixedHeight(options_h)





        self.group_logs.setFixedHeight(logs_h)











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





                self.append_log_text(f"[GUI] stop.flag 제거 실패: {e}\n")











    def _is_same_folder(self, left: str, right: str) -> bool:





        if not left or not right:





            return False





        try:





            return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))





        except Exception:





            return False











    def _link_or_copy_file(self, src: str, dst: str):





        parent = os.path.dirname(dst)





        if parent:





            os.makedirs(parent, exist_ok=True)





        try:





            os.link(src, dst)





            return





        except Exception:





            shutil.copy2(src, dst)











    def _cleanup_selected_runtime_folder(self):





        runtime = self.selected_runtime_folder





        self.selected_runtime_folder = ""





        self.selected_runtime_entries = []





        if not runtime:





            return





        try:





            shutil.rmtree(runtime, ignore_errors=True)





        except Exception as e:





            self.append_log_text(f"[GUI] 선택 전사용 임시 폴더 정리 실패: {e}\n")











    def _prepare_selected_runtime_folder(self) -> bool:
        self._cleanup_selected_runtime_folder()

        if not self.selected_run_items:
            self.show_warning_message("\uACBD\uACE0", "\uC120\uD0DD \uC804\uC0AC \uB300\uC0C1 \uD30C\uC77C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.")
            return False

        runtime_parent = self._runtime_parent_for_selected_items()
        runtime_folder = ""

        try:
            stamp = int(time.time() * 1000)
            for seq in range(100):
                candidate = os.path.join(runtime_parent, f"selected_transcribe_{stamp}_{seq}")
                if os.path.exists(candidate):
                    continue
                os.makedirs(candidate, exist_ok=False)
                runtime_folder = candidate
                break
        except Exception as e:
            self.show_error_message("\uC624\uB958", f"\uC120\uD0DD \uC804\uC0AC \uC784\uC2DC \uD3F4\uB354\uB97C \uB9CC\uB4E4\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.\\n\\n{e}")
            return False

        if not runtime_folder:
            self.show_error_message("\uC624\uB958", "\uC120\uD0DD \uC804\uC0AC \uC784\uC2DC \uD3F4\uB354 \uC774\uB984\uC744 \uD655\uBCF4\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.")
            return False

        self.append_log_text(f"[DBG] _prepare_selected_runtime_folder: selected_run_items={len(self.selected_run_items)}\uAC1C\\n", force=True)
        for _dbg_item in self.selected_run_items:
            self.append_log_text(
                f"[DBG]   item: queue_name={_dbg_item.get('queue_name')!r}, transcribe_name={_dbg_item.get('transcribe_name')!r}\\n",
                force=True,
            )

        runtime_entries: list[dict] = []

        for item in self.selected_run_items:
            transcribe_name = os.path.basename(str(item.get("transcribe_name", ""))).strip()
            if not transcribe_name:
                self.append_log_text("[DBG]   transcribe_name \uC5C6\uC74C -> \uAC74\uB108\uB700\\n", force=True)
                continue

            source_mp3 = self._normalize_saved_folder_path(item.get("source_path", ""))
            target_mp3 = ""

            if source_mp3 and os.path.isfile(source_mp3):
                target_mp3 = source_mp3
                self.append_log_text(f"[DBG]   source_path primary file used: {target_mp3!r}\\n", force=True)
            else:
                if source_mp3:
                    self.append_log_text(f"[DBG]   source_path missing file fallback: {source_mp3!r}\\n", force=True)
                continue

            self.append_log_text(f"[DBG]   target_mp3={target_mp3!r}, exists={os.path.isfile(target_mp3)}\\n", force=True)
            if not os.path.isfile(target_mp3):
                self.append_log_text(f"[WARN] selected transcribe source missing: {target_mp3}\\n", force=True)
                continue

            runtime_mp3 = os.path.join(runtime_folder, transcribe_name)
            try:
                self._link_or_copy_file(target_mp3, runtime_mp3)
                self.append_log_text(f"[DBG]   runtime \uBCF5\uC0AC \uC644\uB8CC: {runtime_mp3!r}\\n", force=True)
            except Exception as e:
                self.append_log_text(f"[WARN] \uC120\uD0DD \uC804\uC0AC \uC784\uC2DC \uD30C\uC77C \uC900\uBE44 \uC2E4\uD328: {target_mp3} / {e}\\n", force=True)
                continue

            runtime_entries.append(
                {
                    "queue_name": item.get("queue_name", ""),
                    "target_mp3": target_mp3,
                    "runtime_mp3": runtime_mp3,
                }
            )

        if not runtime_entries:
            self._cleanup_selected_runtime_folder()
            self.show_warning_message("\uACBD\uACE0", "\uC120\uD0DD\uD55C MP3\uB97C \uC804\uC0AC \uB300\uC0C1\uC73C\uB85C \uC900\uBE44\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.")
            return False

        self.selected_runtime_folder = runtime_folder
        self.selected_runtime_entries = runtime_entries
        return True

    def _sync_selected_runtime_outputs(self):





        if not self.selected_runtime_entries:





            self._cleanup_selected_runtime_folder()





            return





        for entry in self.selected_runtime_entries:





            runtime_mp3 = str(entry.get("runtime_mp3", ""))





            target_mp3 = str(entry.get("target_mp3", ""))





            if not runtime_mp3 or not target_mp3:





                continue





            runtime_outputs = self._output_triplet(runtime_mp3)





            target_outputs = self._output_triplet(target_mp3)





            for src_out, dst_out in zip(runtime_outputs, target_outputs):





                if not os.path.exists(src_out):





                    continue





                try:





                    shutil.copy2(src_out, dst_out)





                except Exception as e:





                    self.append_log_text(f"[WARN] 선택 전사 결과 동기화 실패: {src_out} -> {dst_out} ({e})\n")





        self._cleanup_selected_runtime_folder()











    def _queue_shutdown_prompt_after_completion(self, reason: str):





        if not self.shutdown_checkbox.isChecked():





            return





        if self.shutdown_prompt_shown_for_run or self.shutdown_prompt_pending_for_run:





            return





        self.shutdown_prompt_pending_for_run = True





        self.append_log_text(f"[GUI] 종료 확인 팝업 예약 ({reason})\n")





        QTimer.singleShot(120, self._consume_shutdown_prompt_queue)











    def _consume_shutdown_prompt_queue(self):





        self.shutdown_prompt_pending_for_run = False





        self.request_shutdown_after_completion()











    def setup_tray_icon(self):





        self.tray_icon = QSystemTrayIcon(self)





        icon = load_runtime_icon()





        if icon.isNull():





            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)





        self.setWindowIcon(icon)





        self.tray_icon.setIcon(icon)





        self.tray_icon.setToolTip(APP_DISPLAY_NAME)





        menu = QMenu()





        show_action = QAction("열기", self)





        quit_action = QAction("종료", self)





        show_action.triggered.connect(self.restore_from_tray)





        quit_action.triggered.connect(self.quit_application)





        menu.addAction(show_action)





        menu.addAction(quit_action)





        self.tray_icon.setContextMenu(menu)





        self.tray_icon.activated.connect(self.on_tray_icon_activated)





        self.tray_icon.show()











    def _create_toast_window(self) -> TrayToastWindow:





        if self.toast_window is None:





            self.toast_window = TrayToastWindow(self)





            self.toast_window.btn_open_folder.clicked.connect(self.open_preferred_folder)





        icon = self.tray_icon.icon() if hasattr(self, "tray_icon") else self.windowIcon()





        self.toast_window.set_icon(icon)





        return self.toast_window











    def get_preferred_folder_path(self) -> str:





        path = self.target_folder





        if path and os.path.isdir(path):





            return path





        return ""











    def open_preferred_folder(self):





        folder = self.get_preferred_folder_path()





        if not folder:





            return





        try:





            if os.name == "nt":





                os.startfile(folder)





            elif sys.platform == "darwin":





                subprocess.Popen(["open", folder])





            else:





                subprocess.Popen(["xdg-open", folder])





        except Exception as e:





            self.append_log_text(f"[WARN] 폴더 열기 실패: {e}\n")











    def show_custom_toast(





        self,





        title: str,





        message: str,





        progress_percent: int | None = None,





        current_file: str = "",





        timeout_ms: int = 7200,





        allow_open_folder: bool = True,





    ) -> bool:





        try:





            toast = self._create_toast_window()





            if toast.isVisible():





                toast.hide()





            folder_ok = allow_open_folder and bool(self.get_preferred_folder_path())





            toast.configure(





                title=title,





                message=message,





                progress_percent=progress_percent,





                current_file=current_file,





                folder_open_enabled=folder_ok,





            )





            toast.show_at_bottom_right(self, timeout_ms=timeout_ms)





            return True





        except Exception as e:





            self.append_log_text(f"[WARN] 커스텀 토스트 표시 실패: {e}\n")





            return False











    def notify_with_toast(





        self,





        title: str,





        message: str,





        progress_percent: int | None = None,





        current_file: str = "",





        timeout_ms: int = 7200,





        allow_open_folder: bool = True,





    ):





        shown = self.show_custom_toast(





            title=title,





            message=message,





            progress_percent=progress_percent,





            current_file=current_file,





            timeout_ms=timeout_ms,





            allow_open_folder=allow_open_folder,





        )





        if not shown:





            self.show_tray_message(title, message)











    def show_tray_message(self, title, message):





        if self.tray_icon.isVisible():





            head = (title or "").strip() or APP_DISPLAY_NAME





            body = (message or "").strip()





            try:





                self.tray_icon.showMessage(head, body, self.tray_icon.icon(), 5000)





            except TypeError:





                self.tray_icon.showMessage(head, body, QSystemTrayIcon.Information, 5000)











    def _pick_message_icon(self, icon):





        icon_map = {





            QMessageBox.Information: QStyle.StandardPixmap.SP_MessageBoxInformation,





            QMessageBox.Warning: QStyle.StandardPixmap.SP_MessageBoxWarning,





            QMessageBox.Critical: QStyle.StandardPixmap.SP_MessageBoxCritical,





            QMessageBox.Question: QStyle.StandardPixmap.SP_MessageBoxQuestion,





        }





        std_pix = icon_map.get(icon, QStyle.StandardPixmap.SP_MessageBoxInformation)





        return self.style().standardIcon(std_pix)











    def _build_message_box(self, title: str, message: str, icon, parent_override=None) -> tuple[QDialog, QDialogButtonBox]:





        owner = parent_override





        if owner is None:





            owner = self if self.isVisible() else None





        dialog = QDialog(owner)





        dialog.setObjectName("CommonMessageDialog")





        dialog.setWindowTitle((title or "").strip() or APP_DISPLAY_NAME)





        dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)





        dialog.setModal(True)





        dialog.setMinimumSize(430, 188)











        root = QVBoxLayout(dialog)





        root.setContentsMargins(18, 16, 18, 14)





        root.setSpacing(12)











        content = QFrame()





        content.setObjectName("MessageBody")





        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 12, 14, 12)
        content_layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        icon_label = QLabel("")
        icon_label.setObjectName("MessageIcon")
        icon_label.setFixedSize(28, 28)
        picked_icon = self._pick_message_icon(icon)
        if not picked_icon.isNull():
            icon_label.setPixmap(picked_icon.pixmap(24, 24))
        header_row.addWidget(icon_label, 0, Qt.AlignVCenter)

        heading = QLabel((title or "").strip() or APP_DISPLAY_NAME)
        heading.setObjectName("MessageHeading")
        heading.setWordWrap(True)
        heading.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_row.addWidget(heading, 1, Qt.AlignVCenter)

        content_layout.addLayout(header_row)

        body = QLabel((message or "").strip() or "표시할 메시지가 없습니다.")
        body.setObjectName("MessageText")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        content_layout.addWidget(body)





        root.addWidget(content)











        button_row = QHBoxLayout()





        button_row.setContentsMargins(0, 0, 0, 0)





        button_row.setSpacing(8)





        button_row.addStretch(1)





        button_box = QDialogButtonBox(Qt.Horizontal)





        button_box.setObjectName("CommonDialogButtons")





        button_row.addWidget(button_box, 0, Qt.AlignRight)





        root.addLayout(button_row)











        dialog.setStyleSheet(





            """





            QDialog#CommonMessageDialog {





                background:#ffffff;





            }





            QFrame#MessageBody {





                border:1px solid #e2e8f0;





                border-radius:8px;





                background:#ffffff;





            }





            QLabel#MessageHeading {





                color:#0f235a;





                font-size:17px;





                font-weight:700;





            }





            QLabel#MessageText {





                color:#334155;





                font-size:13px;





                min-width:300px;





                max-width:420px;





                padding:2px 0;





            }





            QPushButton#DialogPrimaryButton {





                min-width:102px;





                min-height:36px;





                padding:5px 14px;





                border:1px solid #002d8b;





                border-radius:6px;





                background:#002d8b;





                color:#ffffff;





                font-size:13px;





                font-weight:600;





            }





            QPushButton#DialogPrimaryButton:hover {





                background:#163f9a;





            }





            QPushButton#DialogSecondaryButton {





                min-width:102px;





                min-height:36px;





                padding:5px 14px;





                border:1px solid #cbd5e1;





                border-radius:6px;





                background:#ffffff;





                color:#1e293b;





                font-size:13px;





                font-weight:500;





            }





            QPushButton#DialogSecondaryButton:hover {





                background:#f6f8fc;





            }





            """





        )





        return dialog, button_box











    def show_info_message(self, title: str, message: str):





        dialog, button_box = self._build_message_box(title, message, QMessageBox.Information)





        ok_btn = button_box.addButton("확인", QDialogButtonBox.AcceptRole)





        ok_btn.setObjectName("DialogPrimaryButton")





        ok_btn.clicked.connect(dialog.accept)





        dialog.exec()











    def show_warning_message(self, title: str, message: str):





        dialog, button_box = self._build_message_box(title, message, QMessageBox.Warning)





        ok_btn = button_box.addButton("확인", QDialogButtonBox.AcceptRole)





        ok_btn.setObjectName("DialogPrimaryButton")





        ok_btn.clicked.connect(dialog.accept)





        dialog.exec()











    def show_error_message(self, title: str, message: str):





        dialog, button_box = self._build_message_box(title, message, QMessageBox.Critical)





        ok_btn = button_box.addButton("확인", QDialogButtonBox.AcceptRole)





        ok_btn.setObjectName("DialogPrimaryButton")





        ok_btn.clicked.connect(dialog.accept)





        dialog.exec()

    def show_question_message(self, title: str, message: str, yes_text: str = "예", no_text: str = "아니오") -> bool:
        dialog, button_box = self._build_message_box(title, message, QMessageBox.Question)
        yes_btn = button_box.addButton(yes_text, QDialogButtonBox.YesRole)
        no_btn = button_box.addButton(no_text, QDialogButtonBox.NoRole)
        yes_btn.setObjectName("DialogPrimaryButton")
        yes_btn.clicked.connect(dialog.accept)
        no_btn.clicked.connect(dialog.reject)
        return dialog.exec() == QDialog.Accepted











    def confirm_shutdown_after_completion(self, wait_seconds: int = 0) -> bool:





        wait_seconds = max(0, int(wait_seconds))





        if wait_seconds <= 0:





            return True





        if self.toast_window is not None and self.toast_window.isVisible():





            self.toast_window.hide()





        if self.isHidden():





            self.showNormal()





        self.raise_()





        self.activateWindow()











        dialog, button_box = self._build_message_box(





            "\uC804\uC0AC \uC644\uB8CC",





            "\uC804\uCCB4 \uC804\uC0AC\uAC00 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uCEF4\uD4E8\uD130\uB97C \uC885\uB8CC\uD560\uAE4C\uC694?",





            QMessageBox.Question,





            parent_override=self,





        )





        dialog.setWindowFlag(Qt.WindowStaysOnTopHint, True)





        dialog.setWindowModality(Qt.ApplicationModal)





        shutdown_btn = button_box.addButton(





            f"\uC9C0\uAE08 \uC885\uB8CC ({wait_seconds})",





            QDialogButtonBox.AcceptRole,





        )





        shutdown_btn.setObjectName("DialogPrimaryButton")





        cancel_btn = button_box.addButton("\uCDE8\uC18C", QDialogButtonBox.RejectRole)





        cancel_btn.setObjectName("DialogSecondaryButton")











        countdown_timer = QTimer(dialog)





        countdown_timer.setInterval(1000)





        remaining_seconds = wait_seconds











        def _stop_countdown():





            if countdown_timer.isActive():





                countdown_timer.stop()











        def _tick_shutdown_countdown():





            nonlocal remaining_seconds





            remaining_seconds -= 1





            if remaining_seconds <= 0:





                _stop_countdown()





                dialog.done(1)





                return





            shutdown_btn.setText(f"\uC9C0\uAE08 \uC885\uB8CC ({remaining_seconds})")











        shutdown_btn.clicked.connect(lambda: dialog.done(1))





        cancel_btn.clicked.connect(lambda: dialog.done(0))





        dialog.finished.connect(lambda _result: _stop_countdown())





        countdown_timer.timeout.connect(_tick_shutdown_countdown)





        countdown_timer.start()





        cancel_btn.setDefault(True)





        cancel_btn.setAutoDefault(True)





        dialog.raise_()





        dialog.activateWindow()





        result = dialog.exec()





        _stop_countdown()





        print(f"[DEBUG-POPUP] dialog.exec() returned {result}", flush=True)





        return result == 1











    def request_shutdown_after_completion(self):





        self.shutdown_prompt_pending_for_run = False





        self.append_log_text(f"[GUI] \uC885\uB8CC \uC635\uC158={self.shutdown_checkbox.isChecked()}, run_mode={self.run_mode}\n")





        if not self.shutdown_checkbox.isChecked():





            return





        if self.shutdown_prompt_shown_for_run:





            return





        self.shutdown_prompt_shown_for_run = True











        shutdown_wait_seconds = self._get_shutdown_wait_seconds()





        if shutdown_wait_seconds <= 0:





            self.append_log_text("[GUI] \uC885\uB8CC \uB300\uAE30\uC2DC\uAC04=\uC989\uC2DC, \uD31D\uC5C5 \uC5C6\uC774 \uC885\uB8CC \uC2E4\uD589\n")





            self.shutdown_computer()





            return











        self.append_log_text(f"[GUI] \uC885\uB8CC \uB300\uAE30\uC2DC\uAC04={shutdown_wait_seconds}\uCD08 \uCE74\uC6B4\uD2B8\uB2E4\uC6B4 \uC2DC\uC791\n")





        if self.confirm_shutdown_after_completion(shutdown_wait_seconds):





            self.append_log_text("[GUI] \uC0AC\uC6A9\uC790 \uD655\uC778\uC73C\uB85C \uCEF4\uD4E8\uD130 \uC885\uB8CC \uC2E4\uD589\n")





            self.shutdown_computer()





        else:





            self.append_log_text("[GUI] \uC0AC\uC6A9\uC790 \uCDE8\uC18C\uB85C \uCEF4\uD4E8\uD130 \uC885\uB8CC \uCDE8\uC18C\n")











    def ensure_main_window_visible(self):





        try:





            if self.windowState() & Qt.WindowMinimized:





                self.setWindowState(self.windowState() & ~Qt.WindowMinimized)





            if self.isHidden():





                self.show()





            self.showNormal()





            self.raise_()





            self.activateWindow()





        except Exception:





            self.show()











    def restore_from_tray(self):





        self.ensure_main_window_visible()











    def on_tray_icon_activated(self, reason):





        if reason == QSystemTrayIcon.DoubleClick:





            self.restore_from_tray()











    def quit_application(self):





        if self._is_transcribe_running():
            dialog, button_box = self._build_message_box(
                "\uC885\uB8CC \uD655\uC778",
                "\uC804\uC0AC\uAC00 \uC9C4\uD589 \uC911\uC785\uB2C8\uB2E4. \uADF8\uB798\uB3C4 \uC885\uB8CC\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?",
                QMessageBox.Question,
                parent_override=self,
            )
            quit_btn = button_box.addButton("\uC885\uB8CC", QDialogButtonBox.AcceptRole)
            quit_btn.setObjectName("DialogPrimaryButton")
            cancel_btn = button_box.addButton("\uCDE8\uC18C", QDialogButtonBox.RejectRole)
            cancel_btn.setObjectName("DialogSecondaryButton")
            quit_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            if dialog.exec() != QDialog.Accepted:
                return





        self.tray_icon.hide()





        QApplication.instance().quit()











    def toggle_log_view(self):





        self._sync_log_panel_state()











    def _sync_log_panel_state(self):





        self.log_visible = True





        self.log_viewer.setVisible(True)





        self.log_viewer.setMinimumHeight(164)





        self.log_viewer.setMaximumHeight(16777215)





        QTimer.singleShot(0, self._sync_sidebar_panel_heights)











    def set_transcribe_buttons_enabled(self, enabled: bool):
        self.btn_target.setEnabled(enabled)
        self.btn_load_files.setEnabled(enabled)

        if enabled:
            self.btn_stop_now.setEnabled(False)
            self._update_checked_state()
        else:
            self.btn_filter_all.setEnabled(False)
            self.btn_uncheck_all.setEnabled(False)
            self.btn_clear_all.setEnabled(False)
            self.btn_transcribe_target.setEnabled(False)
            self.btn_move_files.setEnabled(False)
            self.btn_move_and_transcribe.setEnabled(False)
            self.btn_stop_now.setEnabled(True)

        self._refresh_path_labels()

    def translate_session_status(self, status: str) -> str:





        mapping = {





            "running": "\uC9C4\uD589 \uC911",





            "completed": "\uC644\uB8CC",





            "stopped": "\uC911\uC9C0\uB428",





            "stopped_by_user": "\uC0AC\uC6A9\uC790 \uC911\uC9C0",





            "crashed": "\uBE44\uC815\uC0C1 \uC885\uB8CC",





            "corrupt_session": "\uC138\uC158 \uC190\uC0C1",





        }





        return mapping.get(status, status or "\uC5C6\uC74C")











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





            self._set_session_text("\uC138\uC158 \uC0C1\uD0DC: \uD655\uC778 \uC911...")





            self._set_output_text_mode(Qt.ElideRight)





            self._set_output_text(





                (self._display_path_for_ui(self._output_display_folder or self.target_folder) if (self._output_display_folder or self.target_folder) else "\uBBF8\uC124\uC815")





            )





            return





        try:





            state = self.load_session_state_safely(path)





            status = self.translate_session_status(state.get("status", "\uC5C6\uC74C"))





            cur = state.get("current_file", "")





            self._set_session_text(f"\uC138\uC158 \uC0C1\uD0DC: {status}")





            if cur:





                self._set_output_text_mode(Qt.ElideMiddle)





                self._set_output_text(f"\uB9C8\uC9C0\uB9C9 \uD30C\uC77C: {cur}")





            else:





                self._set_output_text_mode(Qt.ElideRight)





                self._set_output_text(





                    (self._display_path_for_ui(self._output_display_folder or self.target_folder) if (self._output_display_folder or self.target_folder) else "\uBBF8\uC124\uC815")





                )





        except Exception:





            self._set_session_text("\uC138\uC158 \uC0C1\uD0DC: \uC77D\uAE30 \uC2E4\uD328")





            self._set_output_text_mode(Qt.ElideRight)





            self._set_output_text(





                (self._display_path_for_ui(self._output_display_folder or self.target_folder) if (self._output_display_folder or self.target_folder) else "\uBBF8\uC124\uC815")





            )











    def select_target_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "\uD3F4\uB354 \uC120\uD0DD",
            self.target_folder or "",
        )
        if folder:
            self.target_folder = self._normalize_saved_folder_path(folder)
            self._refresh_path_labels()
            self.save_ui_preferences()
            self.update_session_label()

            self.moved_transcribe_items = []
            self._load_mp3_files_from_folder(self.target_folder, append=False, show_empty_message=True)
            self._update_checked_state()
            if hasattr(self, "folders_table"):
                self.refresh_folder_management_view()

    def load_mp3_files(self, show_empty_message=True):
        try:
            selected_files, _ = QFileDialog.getOpenFileNames(
                self,
                "MP3 \uD30C\uC77C \uC120\uD0DD",
                self.target_folder or "",
                "MP3 Files (*.mp3)",
            )
            if not selected_files:
                return

            self._rebuild_queue_from_files(sorted(selected_files), append=True)
            self._reset_idle_progress_state()
            self.update_total_progress_display()
            self._refresh_file_list_empty_state()
        except Exception as e:
            self.show_error_message("\uC624\uB958", f"\uD30C\uC77C \uBAA9\uB85D\uC744 \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.\\n\\n{e}")

    def move_selected_files_core(self, destination_folder: str, refresh_queue: bool = True):
        dst_root = self._normalize_saved_folder_path(destination_folder)
        self.append_log_text(f"[DBG] move_selected_files_core: destination_folder={dst_root!r}\\n", force=True)

        if not dst_root:
            self.show_warning_message("\uACBD\uACE0", "\uC774\uB3D9 \uB300\uC0C1 \uD3F4\uB354\uB97C \uC120\uD0DD\uD574 \uC8FC\uC138\uC694.")
            return None

        selected_rows = self._get_checked_queue_rows()
        self.append_log_text(f"[DBG] move_selected_files_core: selected_rows={len(selected_rows)}\\n", force=True)

        if not selected_rows:
            self.show_warning_message("\uACBD\uACE0", "\uC120\uD0DD\uB41C MP3 \uD30C\uC77C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.")
            return None

        moved, skipped, failed = 0, 0, []
        moved_rows: list[dict] = []
        moved_items: list[dict] = []

        for row in selected_rows:
            original_label = os.path.basename(str(row.get("filename", ""))).strip()
            src = self._normalize_saved_folder_path(row.get("source_path", ""))

            if not src or not os.path.isfile(src):
                failed.append(f"{original_label} -> \uC6D0\uBCF8 \uD30C\uC77C\uC744 \uCC3E\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.")
                continue

            actual_name = os.path.basename(src)
            dst = os.path.join(dst_root, actual_name)

            try:
                src_abs = os.path.normcase(os.path.abspath(src))
                dst_abs = os.path.normcase(os.path.abspath(dst))

                if src_abs == dst_abs:
                    skipped += 1
                else:
                    if os.path.exists(dst):
                        failed.append(f"{actual_name} -> \uC774\uB3D9 \uB300\uC0C1 \uC774\uB984 \uCDA9\uB3CC: {actual_name}")
                        continue
                    shutil.move(src, dst)
                    moved += 1

                moved_rows.append(row)
                moved_items.append(
                    {
                        "filename": str(row.get("filename", actual_name)),
                        "original_filename": str(row.get("original_filename", actual_name)),
                        "source_path": dst,
                        "transcribe_name": os.path.basename(dst),
                        "duration": str(row.get("duration", "")),
                        "duration_seconds": self._duration_text_to_seconds(row.get("duration", "")),
                    }
                )
            except Exception as e:
                failed.append(f"{actual_name} -> {e}")

        for _r in moved_rows:
            _r["status"] = QUEUE_STATUS_MOVED

        if refresh_queue:
            self._refresh_file_queue_table()

        return {
            "moved_count": moved,
            "skipped_count": skipped,
            "failed_files": failed,
            "moved_items": moved_items,
            "destination_folder": dst_root,
        }

    def move_selected_files(self):
        destination_folder = QFileDialog.getExistingDirectory(
            self,
            "\uC774\uB3D9 \uB300\uC0C1 \uD3F4\uB354 \uC120\uD0DD",
            self.target_folder or "",
        )
        if not destination_folder:
            return

        result = self.move_selected_files_core(destination_folder=destination_folder)
        if result is None:
            return

        moved_items = result.get("moved_items", [])
        if moved_items:
            merged: dict[str, dict] = {}
            for item in self.moved_transcribe_items:
                src = self._normalize_saved_folder_path(item.get("source_path", ""))
                if src:
                    merged[os.path.normcase(os.path.abspath(src))] = item
            for item in moved_items:
                src = self._normalize_saved_folder_path(item.get("source_path", ""))
                if src:
                    merged[os.path.normcase(os.path.abspath(src))] = item
            self.moved_transcribe_items = list(merged.values())

        self._update_checked_state()

        msg = (
            "\uC120\uD0DD\uD55C MP3 \uD30C\uC77C \uC774\uB3D9\uC774 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.\\n\\n"
            f"\uC774\uB3D9 \uC131\uACF5: {result['moved_count']}\uAC1C\\n"
            f"\uC774\uBBF8 \uB3D9\uC77C \uC704\uCE58: {result['skipped_count']}\uAC1C\\n"
            f"\uC774\uB3D9 \uC2E4\uD328: {len(result['failed_files'])}\uAC1C"
        )
        if result["failed_files"]:
            msg += "\\n\\n\uC2E4\uD328 \uD30C\uC77C:\\n" + "\\n".join(result["failed_files"][:10])
        self.show_info_message("\uC774\uB3D9 \uACB0\uACFC", msg)

    def move_selected_files_and_start_transcribe(self):
        self.append_log_text("[DBG] move_selected_files_and_start_transcribe \uC9C4\uC785\\n", force=True)

        if not self.moved_transcribe_items:
            self.show_warning_message("\uACBD\uACE0", "\uBA3C\uC800 \uD30C\uC77C\uC774\uB3D9\uC744 \uC2E4\uD589\uD574 \uC8FC\uC138\uC694.")
            return

        if not self._confirm_filename_changes(self.moved_transcribe_items):
            return

        run_items, rename_success, rename_failed = self._prepare_transcribe_items_with_rename(
            self.moved_transcribe_items,
            "moved",
        )

        if rename_success > 0 or rename_failed > 0:
            self.append_log_text(f"[GUI] moved-mode rename result: success {rename_success} / failed {rename_failed}\\n")

        if not run_items:
            self.show_warning_message("\uACBD\uACE0", "\uC774\uB3D9\uC804\uC0AC\uD560 \uD30C\uC77C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.")
            return

        self.selected_run_items = run_items
        self.run_mode = "moved"
        self.run_transcribe_process()

    def _detect_filename_normalization_hints(self, row: dict, source_path: str) -> dict:
        selected_course = getattr(self, "combo_transcribe_course", None)
        selected_subject = getattr(self, "combo_transcribe_subject", None)
        c_val = selected_course.currentText().strip() if selected_course else ""
        s_val = selected_subject.currentText().strip() if selected_subject else ""
        hints = {
            "course_hint": c_val or row.get("course"),
            "subject_hint": s_val or row.get("subject"),
            "week_hint": row.get("week")
        }
        
        path_str = source_path.replace(os.sep, "_").replace("/", "_")
        
        if not hints["course_hint"]:
            c = filename_norm.detect_course_name(path_str)
            if c != "분류대기":
                hints["course_hint"] = c
                
        if not hints["subject_hint"]:
            s = filename_norm.detect_subject_name(path_str)
            if s != "과목불명":
                hints["subject_hint"] = s
                
        if not hints["week_hint"]:
            w, _, _ = filename_norm.detect_week_lesson(os.path.basename(source_path))
            if w is not None:
                hints["week_hint"] = w
            else:
                w, _, _ = filename_norm.detect_week_lesson(path_str)
                if w is not None:
                    hints["week_hint"] = w
                    
        return hints

    def _build_filename_normalize_plans_for_rows(self, rows: list[dict]) -> list:
        if filename_norm is None:
            return []
        plans = []
        folders = {}
        for row in rows:
            src = self._normalize_saved_folder_path(row.get("source_path", ""))
            if not src or not os.path.isfile(src):
                continue
            parent = os.path.dirname(src)
            folders.setdefault(parent, []).append((row, src))

        for parent, items in folders.items():
            common_course = None
            common_subject = None
            common_week = None
            for row, src in items:
                hints = self._detect_filename_normalization_hints(row, src)
                if not common_course and hints["course_hint"]:
                    common_course = hints["course_hint"]
                if not common_subject and hints["subject_hint"]:
                    common_subject = hints["subject_hint"]
                if not common_week and hints["week_hint"]:
                    common_week = hints["week_hint"]

            folder_plans = filename_norm.preview_folder_renames(
                parent,
                course_hint=common_course,
                subject_hint=common_subject,
                week_hint=common_week
            )
            plan_map = {p.original_name: p for p in folder_plans}
            for row, src in items:
                orig_name = os.path.basename(src)
                if orig_name in plan_map:
                    plans.append((row, src, plan_map[orig_name]))
                else:
                    hints = self._detect_filename_normalization_hints(row, src)
                    p = filename_norm.build_normalize_plan(
                        src,
                        course_hint=hints["course_hint"] or common_course,
                        subject_hint=hints["subject_hint"] or common_subject,
                        week_hint=hints["week_hint"] or common_week
                    )
                    plans.append((row, src, p))
        return plans

    def _confirm_auto_filename_normalization(self, plans: list) -> bool:
        if not plans:
            return True

        errors = [p for row, src, p in plans if p.error]
        conflicts = [p for row, src, p in plans if p.conflict]
        rename_needed = [p for row, src, p in plans if p.needs_rename and not p.error and not p.conflict]

        if errors or conflicts:
            if errors:
                title = "파일명을 정리할 수 없어요"
                msg = "일부 파일의 과정명, 과목명 또는 주차 정보를 확인하지 못했습니다.\n파일명을 확인하거나 과정명/과목명을 선택한 뒤 다시 시도해 주세요.\n\n"
                msg += f"오류 예: {errors[0].original_name} -> {errors[0].error}\n"
            else:
                title = "같은 이름의 파일이 이미 있어요"
                msg = "변경하려는 파일명과 같은 파일이 이미 존재합니다.\n기존 파일을 확인한 뒤 다시 시도해 주세요.\n\n"
                msg += f"충돌 예: {conflicts[0].original_name} -> 대상 파일 이미 존재\n"
            self.show_warning_message(title, msg.strip())
            return False

        if not rename_needed:
            return True

        sel_c = self.combo_transcribe_course.currentText().strip()
        sel_s = self.combo_transcribe_subject.currentText().strip()
        msg = "아래 파일명이 전사 시작 전에 표준 형식으로 변경됩니다.\n"
        msg += "표준 형식: 과정명_과목명_N주차_N강\n"
        if sel_c or sel_s:
            msg += f"적용 과정명: {sel_c or '(자동)'}\n"
            msg += f"적용 과목명: {sel_s or '(자동)'}\n"
        msg += "\n"
        
        display_count = 0
        for p in rename_needed:
            if display_count >= 10:
                msg += f"...외 {len(rename_needed) - 10}개\n"
                break
            msg += f"{p.original_name}\n→ {p.standard_name}\n\n"
            display_count += 1

        msg += "이대로 파일명을 변경하고 전사를 시작하시겠습니까?"
        
        return self.show_question_message("파일명 정규화 확인", msg.strip(), "변경 적용", "취소")

    def _apply_filename_normalization_plans(self, rows: list[dict], plans: list) -> bool:
        for row, src, p in plans:
            if not p.needs_rename or p.error or p.conflict:
                continue
            
            dst = p.target_path
            if not dst or dst == p.original_path:
                continue

            try:
                os.replace(src, dst)
                base_orig = os.path.splitext(src)[0]
                base_dst = os.path.splitext(dst)[0]
                for ext in [".txt", ".json", ".srt"]:
                    if os.path.exists(base_orig + ext):
                        try:
                            os.replace(base_orig + ext, base_dst + ext)
                        except Exception as ex:
                            self.append_log_text(f"[WARN] 관련 파일 변경 실패: {base_orig+ext} -> {ex}\n", force=True)

                final_name = os.path.basename(dst)
                row["source_path"] = str(dst)
                row["filename"] = final_name
                row["original_filename"] = final_name
                row["transcribe_name"] = final_name
            except Exception as e:
                self.show_warning_message("파일명 정규화 오류", f"파일 이름 변경 중 오류가 발생했습니다.\n{src}\n{e}")
                return False
        
        return True

    def start_transcribe_on_target_folder(self):
        if not self.file_queue_rows:
            self.show_warning_message("\uACBD\uACE0", "\uC804\uC0AC\uD560 \uD30C\uC77C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.\\n\\n\uBA3C\uC800 MP3 \uD30C\uC77C\uC744 \uBD88\uB7EC\uC624\uC138\uC694.")
            return

        checked_rows = self._get_checked_queue_rows()
        rows_to_run = checked_rows if checked_rows else self.file_queue_rows
        run_scope = "checked" if checked_rows else "all"

        if not self._confirm_filename_changes(rows_to_run):
            return

        if filename_norm is not None:
            plans = self._build_filename_normalize_plans_for_rows(rows_to_run)
            if not self._confirm_auto_filename_normalization(plans):
                return
            if not self._apply_filename_normalization_plans(rows_to_run, plans):
                return

        all_items, rename_success, rename_failed = self._prepare_transcribe_items_with_rename(
            rows_to_run,
            run_scope,
        )

        if rename_success > 0 or rename_failed > 0:
            self.append_log_text(
                f"[GUI] {run_scope}-mode rename result: success {rename_success} / failed {rename_failed}\\n"
            )

        if not all_items:
            self.show_warning_message("\uACBD\uACE0", "\uC804\uC0AC\uD560 \uD30C\uC77C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.")
            return

        self._refresh_file_queue_table()

        self.selected_run_items = all_items
        self._cleanup_selected_runtime_folder()
        self.run_mode = "selected" if checked_rows else "all"
        self.run_transcribe_process()

    def _output_triplet(self, mp3_path: str):





        base = os.path.splitext(remove_page_suffix(os.path.basename(mp3_path)))[0]





        parent = os.path.dirname(mp3_path)





        return [os.path.join(parent, base + ".txt"), os.path.join(parent, base + ".json"), os.path.join(parent, base + ".srt")]

    def _has_existing_output_triplet(self, mp3_path: str) -> bool:
        base_path = os.path.splitext(mp3_path)[0]
        txt_path = base_path + ".txt"
        json_path = base_path + ".json"
        srt_path = base_path + ".srt"
        return all(os.path.exists(path) for path in (txt_path, json_path, srt_path))











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











    def count_pending_mp3_files(self, folder: str) -> int:





        if not folder or not os.path.isdir(folder):





            return 0





        count = 0





        for name in os.listdir(folder):





            if not name.lower().endswith(".mp3"):





                continue





            mp3_path = os.path.join(folder, name)





            if not self._output_triplet_looks_complete(mp3_path):





                count += 1





        return count











    def count_target_mp3_files(self) -> int:





        return self.count_pending_mp3_files(self.target_folder)











    def prepare_progress_tracking(self, runtime_folder: str | None = None):





        self.stdout_buffer = ""





        self.stderr_buffer = ""





        self.notified_success_files.clear()





        self.total_complete_notified = False





        self.completed_files.clear()





        self.last_completed_file_name = ""





        self.total_target_mp3_files = self.count_pending_mp3_files(runtime_folder or self.target_folder)





        self.stop_requested = False





        self.pending_kill = False





        self.stop_terminate_sent = False





        self.shutdown_prompt_shown_for_run = False





        self.shutdown_prompt_pending_for_run = False





        self.last_current_percent = 0





        self.current_file_name = ""





        self.current_file_started_at = None





        self.current_eta_seconds = None





        self.total_eta_seconds = None





        self.file_duration_history.clear()
        self.duration_eta_ratio = DEFAULT_WHISPER_TIME_RATIO
        self.duration_eta_ratio_calibrated = False
        self._build_run_duration_estimate_state()





        self.log_viewer.clear()





        for row in self.file_queue_rows:





            row["status"] = QUEUE_STATUS_WAITING





        self._refresh_file_queue_table()





        self._set_status_text("\uD604\uC7AC \uC0C1\uD0DC: \uC804\uC0AC \uC900\uBE44 \uC911")





        self._set_current_file_text("\uD604\uC7AC \uCC98\uB9AC \uC911 \uD30C\uC77C: \uD655\uC778 \uC911...")





        self.update_total_progress_display()





        self.update_current_file_progress(0, force=True)





        self.update_eta_labels(initial=True)











    def update_total_progress_display(self):





        if self._is_transcribe_running() or self.total_target_mp3_files > 0 or self.completed_files:





            total = max(0, int(self.total_target_mp3_files))





            if total <= 0 and self.completed_files:





                total = len(self.completed_files)





            done = min(len(self.completed_files), total) if total > 0 else 0





        elif self.loaded_mp3_count > 0:





            total = int(self.loaded_mp3_count)





            done = 0





        else:





            total = 0





            done = 0





        self.label_total_progress_text.setText(f"{done} / {total}")





        self.total_progress_bar.setValue(int(done * 100 / total) if total > 0 else 0)





        if hasattr(self, "label_total_done_hint"):





            self.label_total_done_hint.setText(f"{done} FILES DONE")





        self._refresh_meta_summary()











    def update_current_file_progress(self, percent: int, force=False):





        p = max(0, min(100, int(percent)))





        if not force and p < self.last_current_percent:





            return





        self.last_current_percent = p





        self.current_progress_bar.setValue(p)





        self.label_current_progress_text.setText(f"{p}%")





        if self.toast_window is not None and self.toast_window.isVisible():
            if self.toast_window.progress_wrap.isVisible():
                self.toast_window.progress_percent_label.setText(f"{p}%")
                self.toast_window.progress_bar.setValue(p)





        if self.current_file_started_at and 0 < p < 100:





            elapsed = max(0.0, time.time() - self.current_file_started_at)
            
            if self.run_current_audio_seconds > 0:
                ratio = float(self.duration_eta_ratio) if self.duration_eta_ratio else DEFAULT_WHISPER_TIME_RATIO
                ratio = max(0.05, min(1.0, ratio))
                remaining_audio = self.run_current_audio_seconds * (1.0 - (p / 100.0))
                est = max(0.0, remaining_audio * ratio)
            else:
                est = max(0.0, (elapsed / (p / 100.0)) - elapsed)

            self.current_eta_seconds = est if self.current_eta_seconds is None else self.current_eta_seconds * 0.7 + est * 0.3





            self._set_eta_value(self.label_current_eta, f"{format_seconds(self.current_eta_seconds)}")





        elif p >= 100:





            self.current_eta_seconds = 0





            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)





        elif self.current_file_name:





            self.current_eta_seconds = None
            if self.run_current_audio_seconds <= 0:
                self.run_current_audio_seconds = self._lookup_run_audio_seconds(self.current_file_name)
            ratio = float(self.duration_eta_ratio) if self.duration_eta_ratio else DEFAULT_WHISPER_TIME_RATIO
            ratio = max(0.05, min(5.0, ratio))
            predicted_seconds = max(0.0, self.run_current_audio_seconds * ratio)
            if predicted_seconds > 0:
                self._set_eta_value(self.label_current_eta, self._format_approx_remaining_minutes(predicted_seconds))
            else:
                self._set_eta_value(self.label_current_eta, "계산 중...")





        else:





            self.current_eta_seconds = None





            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)





        self.update_total_eta_label()











    def update_total_eta_label(self):





        total = max(0, int(self.total_target_mp3_files))





        done = len(self.completed_files)





        if total <= 0:





            self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)





            self.total_eta_seconds = None





            return





        if done >= total and not self.current_file_name:





            if self._status_full_text in ("전사 완료", "선택 전사 완료", "전체 전사 완료"):





                self._set_eta_value(self.label_total_eta, "완료")





                self.total_eta_seconds = 0





            else:





                self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)





                self.total_eta_seconds = None





            return





        if self.run_total_audio_seconds > 0:
            progress_ratio = max(0.0, min(1.0, self.last_current_percent / 100.0)) if self.current_file_name else 0.0
            current_audio = max(0.0, self.run_current_audio_seconds if self.current_file_name else 0.0)
            completed_audio = max(0.0, self.run_done_audio_seconds)
            waiting_audio = max(0.0, self.run_total_audio_seconds - completed_audio - current_audio)
            remaining_current_audio = current_audio * (1.0 - progress_ratio)

            ratio = float(self.duration_eta_ratio) if self.duration_eta_ratio else DEFAULT_WHISPER_TIME_RATIO
            ratio = max(0.05, min(1.0, ratio))

            if self.current_file_name and self.current_eta_seconds is not None:
                current_est = max(0.0, float(self.current_eta_seconds))
            else:
                current_est = remaining_current_audio * ratio

            est = current_est + (waiting_audio * ratio)
            self.total_eta_seconds = est if self.total_eta_seconds is None else self.total_eta_seconds * 0.7 + est * 0.3

            shown = (
                self._format_remaining_minutes(self.total_eta_seconds)
                if self.duration_eta_ratio_calibrated
                else self._format_approx_remaining_minutes(self.total_eta_seconds)
            )
            self._set_eta_value(self.label_total_eta, shown)
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
        self._set_eta_value(self.label_total_eta, self._format_remaining_minutes(self.total_eta_seconds))











    def update_eta_labels(self, initial=False):





        if initial:





            if self.total_target_mp3_files <= 0:





                self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)





                self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)





            else:





                self.update_total_eta_label()
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











    def _log_time_hhmm(self) -> str:





        return datetime.datetime.now().strftime("%H:%M")











    def _log_file_name(self, name: str) -> str:





        base = os.path.basename(str(name or "")).strip()





        return base if base else "unknown.mp3"











    def _append_user_log(self, message: str, kind: str = "normal"):





        color_map = {





            "normal": QColor(255, 255, 255, 204),  # rgba(255,255,255,0.8)





            "done": QColor("#4ade80"),





            "error": QColor("#f87171"),





        }





        color = color_map.get(kind, color_map["normal"])





        self.append_log_text(f"{self._log_time_hhmm()} {message}\n", color=color, force=True)











    def append_log_text(self, text: str, color: QColor | None = None, force: bool = False):





        if not text:





            return





        stripped = text.strip()





        if (





            stripped.startswith("[FONT]")





            or stripped.startswith("[FONT-CHECK]")





            or stripped.startswith("[GUI]")





        ):





            return





        compact = stripped.replace(" ", "")





        if compact and compact[0] in "=*-" and all(ch == compact[0] for ch in compact):





            return





        if not force:





            return











        self.log_viewer.moveCursor(QTextCursor.End)





        current_fmt = QTextCharFormat()





        current_fmt.setForeground(color if color is not None else QColor(255, 255, 255, 204))





        cursor = self.log_viewer.textCursor()





        cursor.setCharFormat(current_fmt)





        cursor.insertText(text)





        self.log_viewer.setTextCursor(cursor)





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





            self.append_log_text(f"[GUI] 발견된 전체 MP3 수: {discovered}\n")





            self.append_log_text(f"[GUI] 기존 결과 존재로 스킵될 파일 수: {skipped}\n")





            self.append_log_text(f"[GUI] 이번 실행 처리 대상 수: {target}\n")





            self.update_total_progress_display()





            self.update_eta_labels(initial=True)





            if self.total_target_mp3_files <= 0:





                self._set_status_text("처리할 파일 없음")





        elif evt == "FILE_INDEX":





            cur_idx = int(payload[0]) if len(payload) >= 1 and payload[0].isdigit() else 0





            total = int(payload[1]) if len(payload) >= 2 and payload[1].isdigit() else self.total_target_mp3_files





            name = payload[2] if len(payload) >= 3 else "알 수 없음"





            self.current_file_name = name





            self.current_file_started_at = time.time()





            self.current_eta_seconds = None
            self.run_current_audio_seconds = self._lookup_run_audio_seconds(name)





            _in_progress = "선택 전사 진행 중" if self.run_mode == "selected" else "전체 전사 진행 중"





            self._set_status_text(_in_progress)





            self._append_user_log(f"{self._log_file_name(name)} 전사 시작", "normal")





            self.append_log_text(f"[GUI] 진행 파일 인덱스: {cur_idx}/{total}, 파일={name}\n")





            self._set_current_file_text(name)





            self._set_queue_status_by_name(name, QUEUE_STATUS_PROCESSING)





            self.update_current_file_progress(0, force=True)





            self.update_total_eta_label()





        elif evt == "FILE_PROGRESS":
            name = payload[0] if payload else self.current_file_name
            if len(payload) >= 3 and not payload[2].isdigit():
                percent_val = int(payload[1]) if payload[1].isdigit() else 0
                percent = max(0, min(100, percent_val))
                if name:
                    self._set_current_file_text(name)
                self.update_current_file_progress(percent, force=True)
                self.update_total_eta_label()
            else:
                done_chunks = int(payload[1]) if len(payload) >= 2 and payload[1].isdigit() else 0
                total_chunks = int(payload[2]) if len(payload) >= 3 and payload[2].isdigit() else 0
                if name:
                    self._set_current_file_text(name)
                if total_chunks > 0:
                    percent = max(0, min(100, int(round(done_chunks * 100.0 / total_chunks))))
                    self.update_current_file_progress(percent, force=True)
                    self.update_total_eta_label()

        elif evt == "START_FILE":
            name = payload[0] if payload else self.current_file_name
            if name:
                self._set_current_file_text(name)
            self.update_current_file_progress(5, force=True)

        elif evt == "DRIVE_UPLOAD_START":
            name = payload[0] if payload else "unknown"
            self.append_log_text(f"[GUI] Google Drive 업로드 시작: {name}\n")
            
        elif evt == "DRIVE_UPLOAD_DONE":
            name = payload[0] if payload else "unknown"
            count = payload[1] if len(payload) > 1 else "알 수 없음"
            self.append_log_text(f"[GUI] Google Drive 업로드 완료: {name} ({count}개 파일)\n")
            
        elif evt == "DRIVE_UPLOAD_BLOCKED":
            name = payload[0] if payload else "unknown"
            msg = payload[1] if len(payload) > 1 else ""
            self.append_log_text(f"[GUI] Google Drive 업로드 차단: {name} - {msg}\n")
            
        elif evt == "DRIVE_UPLOAD_FAIL":
            name = payload[0] if payload else "unknown"
            msg = payload[1] if len(payload) > 1 else ""
            self.append_log_text(f"[GUI] Google Drive 업로드 실패: {name} - {msg}\n")





        elif evt == "FILE_DONE":





            name = payload[0] if payload else self.current_file_name





            if name:





                self.completed_files.add(name)





                self.last_completed_file_name = name





                self._set_queue_status_by_name(name, QUEUE_STATUS_DONE)

            audio_seconds = self._consume_run_audio_seconds(name)
            if audio_seconds <= 0 and self.current_file_name:
                audio_seconds = self._consume_run_audio_seconds(self.current_file_name)
            processing_seconds = None
            self.run_current_audio_seconds = 0.0





            if self.current_file_started_at:





                d = time.time() - self.current_file_started_at
                processing_seconds = d





                if d > 0.4:





                    self.file_duration_history.append(d)





                    if len(self.file_duration_history) > 30:





                        self.file_duration_history.pop(0)

                    if audio_seconds > 0:
                        observed_ratio = max(0.05, min(1.0, d / audio_seconds))
                        if self.duration_eta_ratio_calibrated:
                            self.duration_eta_ratio = self.duration_eta_ratio * 0.7 + observed_ratio * 0.3
                        else:
                            self.duration_eta_ratio = observed_ratio
                            self.duration_eta_ratio_calibrated = True





            self.current_file_name = ""





            self.current_file_started_at = None
            self.run_current_audio_seconds = 0.0





            self.update_current_file_progress(100, force=True)





            if name:





                self._set_current_file_text(name)





            else:





                self._set_current_file_text("없음")





            self.update_total_progress_display()





            self.update_total_eta_label()





            self.update_session_label()
            done_duration_seconds = self._resolve_done_duration_seconds(name, audio_seconds)
            measured_processing = (
                processing_seconds
                if processing_seconds is not None and processing_seconds > 0.4 and done_duration_seconds > 0
                else None
            )
            self.record_dashboard_done(name, done_duration_seconds, processing_seconds=measured_processing)





            if name:





                self._append_user_log(f"{self._log_file_name(name)} 전사 완료", "done")





            if self.chk_notify_each_file.isChecked() and name not in self.notified_success_files:





                self.notify_with_toast(





                    "파일 전사 완료",





                    f"{name} 전사가 완료되었습니다.",





                    progress_percent=self.total_progress_bar.value(),





                    current_file=name,





                    timeout_ms=7200,





                )





                self.notified_success_files.add(name)





        elif evt == "FILE_SKIP":





            name = payload[0] if payload else "알 수 없음"





            self._set_status_text("선택 전사 진행 중" if self.run_mode == "selected" else "전체 전사 진행 중")





            self._set_current_file_text(name)





            self._set_queue_status_by_name(name, QUEUE_STATUS_DONE)
            skip_audio_seconds = self._consume_run_audio_seconds(name)
            skip_audio_seconds = self._resolve_done_duration_seconds(name, skip_audio_seconds)
            self.record_dashboard_done(name, skip_audio_seconds, processing_seconds=None)
            self.run_current_audio_seconds = 0.0
            self.update_total_eta_label()





        elif evt == "FILE_FAIL":





            name = payload[0] if payload else "알 수 없음"





            err = payload[1] if len(payload) >= 2 else ""





            self._set_status_text("오류 발생")





            self._set_current_file_text(name)





            self._set_queue_status_by_name(name, QUEUE_STATUS_FAILED)
            self._consume_run_audio_seconds(name)
            self.run_current_audio_seconds = 0.0





            self._append_user_log(f"{self._log_file_name(name)} 오류 발생", "error")





            if err:





                self.append_log_text(f"전사 실패 원인: {err}\n", force=True)

            self.update_total_eta_label()





        elif evt == "STOPPED":





            self._set_status_text("중지 요청됨")
            self._mark_processing_rows_as_stop()





        elif evt == "ALL_STOPPED":





            self._set_status_text("\uC0AC\uC6A9\uC790 \uC911\uC9C0\uB428")
            self._mark_processing_rows_as_stop()





            self._set_current_file_text("없음")





            self.current_file_name = ""





            self.current_file_started_at = None
            self.run_current_audio_seconds = 0.0





            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)





            self.update_total_eta_label()





            self.update_session_label()





        elif evt == "ALL_DONE":





            self.append_log_text(f"[GUI] ALL_DONE 감지, run_mode={self.run_mode}\n")





            _is_selected = self.run_mode == "selected"





            _done_status = "선택 전사 완료" if _is_selected else "전체 전사 완료"





            _done_title = "선택 전사 완료" if _is_selected else "전체 전사 완료"





            _done_msg = "선택한 MP3 전사가 완료되었습니다." if _is_selected else "전체 전사가 완료되었습니다."





            self._append_user_log("선택 전사 완료" if _is_selected else "전체 전사 완료", "done")





            self._set_status_text(_done_status)





            if self.last_completed_file_name:





                self._set_current_file_text(self.last_completed_file_name)





            else:





                self._set_current_file_text("없음")





            self.current_file_name = ""





            self.current_file_started_at = None
            self.run_current_audio_seconds = 0.0





            self._set_eta_value(self.label_current_eta, "완료")





            self._set_eta_value(self.label_total_eta, "완료")





            self.update_total_progress_display()





            self.update_session_label()





            if self.chk_notify_total.isChecked() and not self.total_complete_notified:





                self.notify_with_toast(





                    _done_title,





                    _done_msg,





                    progress_percent=100,





                    current_file="",





                    timeout_ms=7600,





                )





                self.total_complete_notified = True





            





            self._queue_shutdown_prompt_after_completion("ALL_DONE")





        elif evt == "PREVIOUS_SESSION_CRASHED":





            self.append_log_text("[GUI] 이전 작업 비정상 종료 이력이 감지되었습니다.\n")





            self.update_session_label()





        elif evt == "PREVIOUS_SESSION_STOPPED_BY_USER":





            self.append_log_text("[GUI] 이전 작업 사용자 중지 이력이 감지되었습니다.\n")





            self.update_session_label()





        elif evt == "PREVIOUS_SESSION_CORRUPT":





            self.append_log_text("[GUI] 이전 세션 파일 손상이 감지되었습니다.\n")





            self.update_session_label()





        return True











    def _get_google_drive_auth_paths(self) -> tuple[str, str]:
        appdata = os.environ.get("APPDATA")
        if appdata:
            base_dir = os.path.join(appdata, "전사도우미")
        else:
            base_dir = os.path.join(os.path.expanduser("~"), ".전사도우미")
        return (
            os.path.join(base_dir, "google_credentials.json"),
            os.path.join(base_dir, "google_drive_token.json"),
        )

    def _is_valid_google_credentials_file(self, path: str) -> bool:
        try:
            file_path = Path(path)
            if not file_path.exists() or file_path.stat().st_size < 20:
                return False
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("installed") or data.get("web"))
        except Exception:
            return False

    def _is_valid_google_token_file(self, path: str) -> bool:
        try:
            file_path = Path(path)
            if not file_path.exists() or file_path.stat().st_size < 20:
                return False
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            required_keys = ("token", "refresh_token", "client_id", "client_secret", "scopes")
            return all(key in data for key in required_keys)
        except Exception:
            return False

    def _has_google_drive_auth_files(self) -> bool:
        cred_path, token_path = self._get_google_drive_auth_paths()
        return (
            self._is_valid_google_credentials_file(cred_path)
            and self._is_valid_google_token_file(token_path)
        )

    def _show_google_drive_auth_warning(self):
        cred_path, token_path = self._get_google_drive_auth_paths()
        self.show_warning_message(
            "Google Drive 인증이 필요해요",
            "자동 업로드를 사용하려면 Google Drive 인증 파일이 필요합니다.\n"
            "인증 파일을 확인한 뒤 다시 시도해 주세요."
        )





    def run_transcribe_process(self):
        selected_course = self.combo_transcribe_course.currentText().strip()
        selected_subject = self.combo_transcribe_subject.currentText().strip()
        if not selected_course or not selected_subject:
            self.show_warning_message(
                "과정명과 과목명을 선택해 주세요",
                "다운로드 원본 파일명에는 과목명이 포함되지 않는 경우가 많아,\n"
                "정확한 파일명 정리와 과목별 전사 보정을 위해 선택이 필요합니다."
            )
            return

        has_selected_runtime_items = self.run_mode in ("selected", "all", "moved") and bool(self.selected_run_items)
        if not has_selected_runtime_items and self.target_folder:
            _file_count = len(self.file_queue_rows) if self.file_queue_rows else 0
            msg = (
                f"현재 선택한 과정/과목이 이번 전사 대상 전체에 적용됩니다.\n\n"
                f"과정명: {selected_course}\n"
                f"과목명: {selected_subject}\n"
                f"대상 파일 수: {_file_count}개\n\n"
                f"여러 과목 파일이 섞여 있다면 [취소]를 누르고,\n"
                f"과목별로 파일을 체크해서 나누어 실행해 주세요.\n\n"
                f"계속 진행할까요?"
            )
            if not self.show_question_message("전사 대상 전체에 같은 과정/과목이 적용됩니다", msg, "계속 진행", "취소"):
                return

        engine = self._current_transcription_engine()
        if not self.target_folder and not has_selected_runtime_items:
            self.show_warning_message("\uACBD\uACE0", "\uBA3C\uC800 \uC804\uC0AC \uD3F4\uB354 \uB610\uB294 \uD30C\uC77C \uBAA9\uB85D\uC744 \uC900\uBE44\uD574 \uC8FC\uC138\uC694.")
            return

        if self._is_transcribe_running():
            self.show_warning_message("\uACBD\uACE0", "\uC774\uBBF8 \uC804\uC0AC \uC791\uC5C5\uC774 \uC9C4\uD589 \uC911\uC785\uB2C8\uB2E4.")
            return

        if engine == "colab":
            colab_url = str(self.input_colab_url.text() or "").strip()
            if not colab_url or not self._colab_check_connected:
                self.show_info_message("알림", "Colab URL을 먼저 입력하고 연결을 확인해 주세요.")
                return
        else:
            auto_path = self.get_auto_transcribe_path()
            if not os.path.exists(auto_path):
                self.show_error_message("\uC624\uB958", f"auto_transcribe.py \uD30C\uC77C\uC744 \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.\\n\\n\uD655\uC778 \uACBD\uB85C:\\n{auto_path}")
                return

        runtime_folder = self.target_folder if self.target_folder else self.get_base_dir()

        if has_selected_runtime_items:
            if not self._prepare_selected_runtime_folder():
                return
            runtime_folder = self.selected_runtime_folder or runtime_folder
        else:
            self.selected_run_items = []
            self._cleanup_selected_runtime_folder()

        if engine == "colab":
            _pending = len(self._collect_colab_runtime_targets(runtime_folder))
        else:
            _pending = self.count_pending_mp3_files(runtime_folder)
        self.append_log_text(f"[DBG] run_transcribe_process: run_mode={self.run_mode!r}, runtime_folder={runtime_folder!r}, pending={_pending}\\n", force=True)

        if _pending <= 0:
            self.total_target_mp3_files = 0
            self.update_total_progress_display()
            self._set_status_text("\uCC98\uB9AC\uD560 \uD30C\uC77C \uC5C6\uC74C")
            self._set_current_file_text("\uC5C6\uC74C")
            self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)
            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
            self.show_info_message("\uC54C\uB9BC", "\uC774\uBC88 \uC2E4\uD589\uC5D0\uC11C \uCC98\uB9AC\uD560 \uD30C\uC77C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.")
            self.notify_with_toast(
                "\uCC98\uB9AC\uD560 \uD30C\uC77C \uC5C6\uC74C",
                "\uC774\uBC88 \uC2E4\uD589\uC5D0\uC11C \uCC98\uB9AC\uD560 \uD30C\uC77C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.",
                progress_percent=None,
                current_file="",
                timeout_ms=7600,
                allow_open_folder=True,
            )
            self._sync_selected_runtime_outputs()
            self.selected_run_items = []
            return

        self._output_display_folder = self.target_folder
        for _item in (self.selected_run_items or []):
            _src = str(_item.get("source_path", "")).strip()
            if _src:
                _folder = os.path.dirname(self._normalize_saved_folder_path(_src))
                if _folder:
                    self._output_display_folder = _folder
                    break
        self.prepare_progress_tracking(runtime_folder=runtime_folder)
        self.set_transcribe_buttons_enabled(False)
        self.update_session_label()

        if engine == "colab":
            if not self._start_colab_transcribe_run(runtime_folder):
                return
            return

        if self.upload_drive_checkbox.isChecked():
            if not self._has_google_drive_auth_files():
                self._show_google_drive_auth_warning()
                self.set_transcribe_buttons_enabled(True)
                self._sync_selected_runtime_outputs()
                self.selected_run_items = []
                return

        self.process = QProcess(self)
        self.process.setProgram("python" if getattr(sys, "frozen", False) else sys.executable)
        
        args = [auto_path, runtime_folder]
        if self.upload_drive_checkbox.isChecked():
            args.append("--upload-drive")
            
        self.process.setArguments(args)
        self.process.setWorkingDirectory(self.get_base_dir())
        self.process.readyReadStandardOutput.connect(self.handle_process_stdout)
        self.process.readyReadStandardError.connect(self.handle_process_stderr)
        self.process.finished.connect(self.handle_process_finished)
        self.process.start()

        if not self.process.waitForStarted(4000):
            self.process = None
            self.set_transcribe_buttons_enabled(True)
            self._sync_selected_runtime_outputs()
            self.selected_run_items = []
            self.show_error_message("전사를 시작하지 못했어요", "전사 실행 중 문제가 발생했습니다.\n잠시 후 다시 시도하거나 실행 로그를 확인해 주세요.")
            return

        self._set_status_text(self._run_mode_in_progress_text())
        self._set_current_file_text("\uC5C6\uC74C")
        self.append_log_text(f"[GUI] \uC804\uC0AC \uC2DC\uC791: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")

    def handle_process_finished(self, exit_code: int, exit_status):





        # Qt에서 readyReadStandardOutput 보장이 있더라도, 파이프에 남은 데이터를 명시적으로 플러시





        if self.process is not None:





            _remaining_out = bytes(self.process.readAllStandardOutput())





            if _remaining_out:





                self._consume_chunk("stdout_buffer", self.decode_process_data(_remaining_out), True)





            _remaining_err = bytes(self.process.readAllStandardError())





            if _remaining_err:





                self._consume_chunk("stderr_buffer", self.decode_process_data(_remaining_err), False)





        for name in ("stdout_buffer", "stderr_buffer"):





            tail = getattr(self, name)





            if tail:





                self.append_log_text(tail + "\n")





                setattr(self, name, "")





        self.force_kill_timer.stop()





        normal_exit = exit_status == QProcess.NormalExit





        self.append_log_text(f"[GUI] 프로세스 종료: exit_code={exit_code}, normal={normal_exit}\n")





        self.process = None





        self._sync_selected_runtime_outputs()





        self.selected_run_items = []





        self.set_transcribe_buttons_enabled(True)





        self.update_session_label()





        if self.stop_requested:
            self._mark_processing_rows_as_stop()





            if self.pending_kill:





                self._set_status_text("현재 상태: 사용자 중지됨")





            else:





                self._set_status_text("현재 상태: 사용자 중지됨")





            self._set_current_file_text("없음")





            self.append_log_text("[INFO] 사용자 중지 상태 종료 처리 완료\n")





            self.notify_with_toast(





                "사용자 중지됨",





                "사용자 요청으로 전사 작업이 중지되었습니다.",





                progress_percent=self.total_progress_bar.value(),





                current_file="",





                timeout_ms=7200,





            )





            self.pending_kill = False





            self.stop_terminate_sent = False





            self.stop_requested = False





            return





        if self.pending_kill:





            self._set_status_text("현재 상태: 강제 종료됨")





            self._set_current_file_text("없음")





            self.pending_kill = False





            self.stop_terminate_sent = False





            return





        if exit_code != 0 and exit_status == QProcess.NormalExit:





            self._set_status_text("오류 발생")





        self.stop_terminate_sent = False





        # 폴백: ALL_DONE 이벤트가 누락된 경우를 대비해 전사 완료 시 종료 옵션 확인





        if (





            exit_code == 0





            and exit_status == QProcess.NormalExit





            and not self.shutdown_prompt_shown_for_run





        ):





            self.append_log_text(f"[GUI] handle_process_finished 폴백: 종료 옵션 확인 (run_mode={self.run_mode})\n")





            self._queue_shutdown_prompt_after_completion("handle_process_finished_fallback")











    def request_immediate_stop(self):





        if self._colab_run_active and (self.process is None or self.process.state() == QProcess.NotRunning):
            self.stop_requested = True
            self._colab_stop_after_current = True
            self.pending_kill = False
            self.stop_terminate_sent = False
            self._set_status_text("\uD604\uC7AC \uC0C1\uD0DC: \uC911\uC9C0 \uC694\uCCAD\uB428")
            self._append_user_log("\uC804\uC0AC \uC911\uC9C0 \uC694\uCCAD")
            self.append_log_text("[INFO] Colab 전사 중지 요청 감지 - 현재 파일 완료 후 중단\n")
            return

        if self.process is None or self.process.state() == QProcess.NotRunning:





            self.show_info_message("알림", "진행 중인 전사 작업이 없습니다.")





            return





        stop_flag = self.get_stop_flag_path()





        if not stop_flag:





            self.show_warning_message("경고", "전사자료 폴더가 설정되지 않았습니다.")





            return





        try:





            with open(stop_flag, "w", encoding="utf-8") as f:





                f.write("stop\n")





            self.stop_requested = True





            self.pending_kill = False





            self.stop_terminate_sent = False





            self._set_status_text("\uD604\uC7AC \uC0C1\uD0DC: \uC911\uC9C0 \uC694\uCCAD\uB428")





            self._append_user_log("전사 중지됨")





            self.append_log_text("[INFO] 사용자 즉시 중지 요청 감지\n")





            self.append_log_text("[GUI] stop.flag 생성 완료 - 즉시 중지 요청\n")





            if self.process is not None and self.process.state() != QProcess.NotRunning:





                self.append_log_text("[WARN] 중지 요청 후 정상 종료 지연 - terminate 시도\n")





                self.stop_terminate_sent = True





                self.process.terminate()





                self.force_kill_timer.start(8000)





        except Exception as e:





            self.show_error_message("오류", f"중지 요청 실패\n\n{e}")











    def force_kill_process(self):





        if self.process is None or self.process.state() == QProcess.NotRunning:





            return





        if not self.stop_requested:





            return





        self.pending_kill = True





        self.append_log_text("[WARN] terminate 실패 - kill 실행\n")





        self.process.kill()











    def shutdown_computer(self):





        dry_run_flag = (os.environ.get("TRANSCRIBE_HELPER_SHUTDOWN_DRY_RUN", "") or "").strip().lower()





        if dry_run_flag in {"1", "true", "yes", "on"}:





            self.append_log_text("[GUI] [DRY-RUN] shutdown /s /t 0 호출 생략\n")





            return





        os.system("shutdown /s /t 0")











    def closeEvent(self, event):





        running = self._is_transcribe_running()





        if running:





            self.hide()





            self.notify_with_toast(





                "\uC804\uC0AC \uC9C4\uD589 \uC911",





                "전사 작업은 계속 진행 중입니다. 프로그램은 트레이로 이동합니다.",





                progress_percent=self.total_progress_bar.value(),





                current_file=self.current_file_name,





                timeout_ms=7600,





            )





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





        # Reduce high-DPI text blur on Windows.





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





        print(line)





    for line in collect_font_application_diagnostics(window, selected_font_family):





        print(line)





    window.showMaximized()





    window.ensure_main_window_visible()





    QTimer.singleShot(140, window.ensure_main_window_visible)





    sys.exit(app.exec())
