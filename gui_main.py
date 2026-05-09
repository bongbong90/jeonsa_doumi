
import datetime
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time

from PySide6.QtCore import QProcess, QSize, QTimer, Qt, QSettings, QPoint
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
APP_DISPLAY_NAME = "\uC804\uC0AC\uB3C4\uC6B0\uBBF8"
APP_USER_MODEL_ID = "com.codex.transcribehelper"
UI_DEFAULT_FONT_SIZE = 10
SETTINGS_KEY_TARGET_DIR = "ui/target_folder"
SETTINGS_KEY_NOTIFY_EACH = "ui/notify_each_file"
SETTINGS_KEY_NOTIFY_TOTAL = "ui/notify_total"
SETTINGS_KEY_SHUTDOWN_AFTER_DONE = "ui/shutdown_after_done"
SETTINGS_KEY_SHUTDOWN_WAIT_SECONDS = "ui/shutdown_wait_seconds"
SHUTDOWN_WAIT_OPTIONS = (
    (0, "\uC989\uC2DC"),
    (15, "15\uCD08"),
    (30, "30\uCD08"),
)

QUEUE_STATUS_WAITING = "WAITING"
QUEUE_STATUS_PROCESSING = "PROCESSING"
QUEUE_STATUS_DONE = "DONE"
QUEUE_STATUS_FAILED = "FAILED"

QUEUE_STATUS_STYLE = {
    QUEUE_STATUS_WAITING: ("#f1f5f9", "#475569"),
    QUEUE_STATUS_PROCESSING: ("#dbeafe", "#1e40af"),
    QUEUE_STATUS_DONE: ("#dcfce7", "#15803d"),
    QUEUE_STATUS_FAILED: ("#fee2e2", "#b91c1c"),
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
        self.progress_bar.setFixedHeight(8)
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


class TranscribeGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("RootWindow")
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(1320, 790)
        self.setMinimumSize(1024, 680)

        self.target_folder = ""
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
        self.ui_settings = QSettings(get_ui_settings_path(), QSettings.IniFormat)
        self._status_full_text = "\uB300\uAE30 \uC911"
        self._current_file_full_text = "\uD604\uC7AC \uCC98\uB9AC \uC911 \uD30C\uC77C: \uC5C6\uC74C"
        self._session_full_text = "\uC138\uC158 \uC0C1\uD0DC: \uD655\uC778 \uC911..."
        self._output_full_text = "\uC2E4\uC2DC\uAC04 \uCD9C\uB825: GUI\uC5D0 \uC9C1\uC811 \uC5F0\uACB0\uB428"
        self._output_text_elide_mode = Qt.ElideRight
        self._status_spin_frames = ["↻", "↺", "↻", "↺"]
        self._status_spin_index = 0
        self.status_spin_timer = QTimer(self)
        self.status_spin_timer.timeout.connect(self._tick_status_icon)

        self.build_ui()
        self.apply_styles()
        self.apply_font_hierarchy()
        self.apply_typography_fit_defaults()
        self._setup_checkbox_indicator_style()
        self.load_ui_preferences()
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
        sidebar.setFixedWidth(300)
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
        side_scroll.setFixedWidth(300)
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
        settings.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sbox = QVBoxLayout(settings)
        sbox.setContentsMargins(16, 16, 16, 16)
        sbox.setSpacing(0)
        self.label_section_settings = QLabel("폴더 설정", objectName="SectionTitle")
        sbox.addWidget(self.label_section_settings)
        self.label_settings_hint = QLabel("folder_open", objectName="SectionIconText")
        self.label_settings_hint.setVisible(False)
        sbox.addWidget(self.label_settings_hint)
        sbox.addSpacing(10)

        self.label_target = QLabel("폴더를 선택하세요", objectName="PathLabel")
        self.label_target.setFixedHeight(36)
        self.label_target.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_target.setWordWrap(False)
        sbox.addWidget(self.label_target)
        sbox.addSpacing(6)
        self.btn_target = QPushButton("전사자료 폴더 선택")
        self.btn_target.setProperty("uiRole", "side")
        self.btn_target.setFixedHeight(36)
        sbox.addWidget(self.btn_target)
        sbox.addSpacing(8)

        self.btn_load_files = QPushButton("MP3 파일 목록 불러오기")
        self.btn_load_files.setProperty("uiRole", "sideOutline")
        self.btn_load_files.setFixedHeight(36)
        sbox.addWidget(self.btn_load_files)
        left.addWidget(settings, 0)
        self.group_settings = settings

        options = QGroupBox("")
        options.setObjectName("SidebarCard")
        options.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        self.log_viewer.setMinimumHeight(0)
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
        trans_layout.setSpacing(8)

        dashboard = QGroupBox("")
        dashboard.setObjectName("DashboardSection")
        dashboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        dbox = QVBoxLayout(dashboard)
        dbox.setContentsMargins(16, 16, 16, 12)
        dbox.setSpacing(8)
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
        self.total_progress_bar.setFixedHeight(8)

        self.label_total_eta = QLabel(ETA_EMPTY_TEXT)
        self.label_total_eta.setObjectName("MetricEtaValue")
        self.label_current_progress_text = QLabel("0%")
        self.label_current_progress_text.setObjectName("CurrentProgressValue")
        self.current_progress_bar = QProgressBar()
        self.current_progress_bar.setObjectName("CurrentProgressBar")
        self.current_progress_bar.setRange(0, 100)
        self.current_progress_bar.setTextVisible(False)
        self.current_progress_bar.setFixedHeight(8)
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
        self.card_progress.setMinimumHeight(0)
        progress_box = QVBoxLayout(self.card_progress)
        progress_box.setContentsMargins(14, 10, 14, 10)
        progress_box.setSpacing(6)
        progress_box.addWidget(QLabel("TOTAL PROGRESS", objectName="DashboardMicroLabel"))
        metric_header = QHBoxLayout()
        metric_header.setContentsMargins(0, 0, 0, 0)
        metric_header.setSpacing(8)
        metric_header.addWidget(self.label_total_progress_text, 1)
        metric_header.addWidget(self.label_total_done_hint, 0)
        progress_box.addLayout(metric_header)
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
        self.card_current.setMinimumHeight(0)
        current_box = QVBoxLayout(self.card_current)
        current_box.setContentsMargins(14, 12, 14, 12)
        current_box.setSpacing(8)
        current_box.addWidget(QLabel("CURRENT FILE", objectName="DashboardMicroLabel"))
        self.label_current_file.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_current_file.setMinimumHeight(24)
        current_box.addWidget(self.label_current_file)

        current_header = QHBoxLayout()
        current_header.setContentsMargins(0, 0, 0, 0)
        current_header.setSpacing(8)
        current_header.addWidget(QLabel("CURRENT PROGRESS", objectName="DashboardMicroLabel"), 1)
        self.label_current_progress_text.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        current_header.addWidget(self.label_current_progress_text, 0)
        current_box.addLayout(current_header)
        current_box.addWidget(self.current_progress_bar)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(10)
        self.label_session_counter = QLabel("SESSION: 0 / 0", objectName="MetaCompactValue")
        self.label_output_value = QLabel("OUTPUT: 미설정", objectName="MetaCompactValue")
        self.label_current_eta.setWordWrap(False)
        self.label_session_counter.setWordWrap(False)
        self.label_output_value.setWordWrap(False)
        self.label_current_eta.setMinimumHeight(24)
        self.label_session_counter.setMinimumHeight(24)
        self.label_output_value.setMinimumHeight(24)
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
        self.btn_clear_done = QPushButton("Clear Done")
        self.btn_clear_done.setObjectName("QueueHeaderButton")
        self.btn_clear_done.setFixedHeight(28)
        header_row.addWidget(self.btn_filter_all, 0)
        header_row.addWidget(self.btn_uncheck_all, 0)
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
        self.file_queue_table.verticalHeader().setVisible(False)
        self.file_queue_table.horizontalHeader().setStretchLastSection(False)
        self.file_queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.file_queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.file_queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.file_queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.file_queue_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.file_queue_table.setColumnWidth(0, 40)
        self.file_queue_table.setColumnWidth(2, 90)
        self.file_queue_table.setColumnWidth(3, 100)
        self.file_queue_table.setColumnWidth(4, 60)
        self.file_queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_queue_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.file_queue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_queue_table.setAlternatingRowColors(False)
        self.file_queue_table.setShowGrid(False)
        self.file_queue_table.setMinimumHeight(54)
        self.file_queue_table.setWordWrap(False)
        self.file_queue_table.setTextElideMode(Qt.ElideRight)
        self.file_queue_table.setFocusPolicy(Qt.NoFocus)
        fbox.addWidget(self.file_queue_table, 1)
        self.file_list_widget = self.file_queue_table

        self.label_file_empty_state = QLabel("불러온 MP3 파일이 없습니다.", objectName="FileEmptyState")
        self.label_file_empty_state.setAlignment(Qt.AlignCenter)
        self.label_file_empty_state.setMinimumHeight(40)
        fbox.addWidget(self.label_file_empty_state)
        trans_layout.addWidget(files, 1)
        self.group_files = files

        controls = QGroupBox("")
        controls.setObjectName("ControlSection")
        controls.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cbox = QVBoxLayout(controls)
        cbox.setContentsMargins(14, 14, 14, 14)
        cbox.setSpacing(8)
        self.label_section_controls = QLabel("실행 제어", objectName="SectionTitle")
        cbox.addWidget(self.label_section_controls)
        self.label_controls_helper = QLabel("", objectName="HelperText")
        self.label_controls_helper.setVisible(False)
        cbox.addWidget(self.label_controls_helper)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.btn_move_and_transcribe = QPushButton("선택한 MP3 이동 후 전사 시작")
        self.btn_move_and_transcribe.setProperty("uiRole", "controlOutlinePrimary")
        self.btn_move_and_transcribe.setFixedHeight(48)
        self.btn_move_and_transcribe.setEnabled(False)
        self.btn_transcribe_target = QPushButton("전사자료 폴더 전체 전사 시작")
        self.btn_transcribe_target.setProperty("uiRole", "controlPrimary")
        self.btn_transcribe_target.setFixedHeight(48)
        row1.addWidget(self.btn_move_and_transcribe, 1)
        row1.addWidget(self.btn_transcribe_target, 1)
        cbox.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.btn_move_files = QPushButton("선택 MP3 전사자료 폴더로 이동")
        self.btn_move_files.setProperty("uiRole", "controlOutline")
        self.btn_move_files.setFixedHeight(44)
        self.btn_stop_now = QPushButton("즉시 중지")
        self.btn_stop_now.setProperty("uiRole", "controlGhost")
        self.btn_stop_now.setFixedHeight(44)
        self.btn_stop_now.setEnabled(False)
        row2.addWidget(self.btn_move_files, 1)
        row2.addWidget(self.btn_stop_now, 1)
        cbox.addLayout(row2)
        trans_layout.addWidget(controls)
        self.group_controls = controls

        trans_scroll = QScrollArea()
        trans_scroll.setWidgetResizable(True)
        trans_scroll.setFrameShape(QFrame.NoFrame)
        trans_scroll.setWidget(trans_page)
        trans_scroll.setObjectName("TransScrollArea")
        trans_scroll.viewport().setObjectName("TransScrollViewport")
        self.main_stack.addWidget(trans_scroll)

        dash_page = QWidget()
        dash_layout = QVBoxLayout(dash_page)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_placeholder = QFrame()
        dash_placeholder.setObjectName("PlaceholderCard")
        dash_box = QVBoxLayout(dash_placeholder)
        dash_box.setContentsMargins(20, 20, 20, 20)
        dash_box.addWidget(QLabel("Dashboard 탭은 향후 확장 영역입니다.", objectName="PlaceholderText"))
        dash_layout.addWidget(dash_placeholder)
        self.main_stack.addWidget(dash_page)

        folder_page = QWidget()
        folder_layout = QVBoxLayout(folder_page)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_placeholder = QFrame()
        folder_placeholder.setObjectName("PlaceholderCard")
        folder_box = QVBoxLayout(folder_placeholder)
        folder_box.setContentsMargins(20, 20, 20, 20)
        folder_box.addWidget(QLabel("Folders 탭은 폴더 관리 전용 영역입니다.", objectName="PlaceholderText"))
        folder_layout.addWidget(folder_placeholder)
        self.main_stack.addWidget(folder_page)

        self._apply_status_and_meta_labels()
        self._refresh_path_labels()

        self.btn_target.clicked.connect(self.select_target_folder)
        self.btn_load_files.clicked.connect(self.load_mp3_files)
        self.btn_move_files.clicked.connect(self.move_selected_files)
        self.btn_move_and_transcribe.clicked.connect(self.move_selected_files_and_start_transcribe)
        self.btn_transcribe_target.clicked.connect(self.start_transcribe_on_target_folder)
        self.btn_stop_now.clicked.connect(self.request_immediate_stop)
        self.btn_filter_all.clicked.connect(self._mark_all_queue_checked)
        self.btn_uncheck_all.clicked.connect(self._uncheck_all_queue)
        self.btn_clear_done.clicked.connect(self._clear_done_queue_rows)
        self.chk_notify_each_file.stateChanged.connect(self.save_ui_preferences)
        self.chk_notify_total.stateChanged.connect(self.save_ui_preferences)
        self.shutdown_checkbox.stateChanged.connect(self._sync_shutdown_wait_combo_state)
        self.shutdown_checkbox.stateChanged.connect(self.save_ui_preferences)
        self.shutdown_wait_combo.currentIndexChanged.connect(self.save_ui_preferences)
        self.tab_transcriptions.clicked.connect(lambda: self._switch_main_tab("transcriptions"))
        self.tab_dashboard.clicked.connect(lambda: self._switch_main_tab("dashboard"))
        self.tab_folders.clicked.connect(lambda: self._switch_main_tab("folders"))

        self._sync_shutdown_wait_combo_state()
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
            QTableWidget#FileQueueTable {
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
            QTableWidget#FileQueueTable::item:focus {
                border: none;
                color: #1a1b21;
            }
            QWidget#CheckboxCell, QWidget#ActionCell, QWidget#BadgeCell {
                background: transparent;
            }
            QHeaderView::section {
                background: #ffffff;
                color: #64748b;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 8px 6px;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
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
            QProgressBar {
                background: #f1f5f9;
                border: none;
                border-radius: 6px;
                min-height: 8px;
                max-height: 8px;
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
        for cb in (self.chk_notify_each_file, self.chk_notify_total, self.shutdown_checkbox):
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
        if item is None or item.column() != 0:
            return
        row_idx = item.row()
        if row_idx < 0 or row_idx >= len(self.file_queue_rows):
            return
        self.file_queue_rows[row_idx]["checked"] = item.checkState() == Qt.Checked
        QTimer.singleShot(0, self._clear_file_queue_selection)

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
            file_item.setFlags(Qt.ItemIsEnabled)
            file_item.setToolTip(file_name)
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
            self.file_queue_table.setRowHeight(row_idx, 38)

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
                f"불러온 MP3 파일 수: {total}개 | 선택: {checked_count}개"
            )
        else:
            self.label_file_count.setText(f"불러온 MP3 파일 수: {total}개")
        self.btn_filter_all.setEnabled(has_files)
        self.btn_uncheck_all.setEnabled(has_files)
        if not self._is_transcribe_running():
            self.btn_move_and_transcribe.setEnabled(checked_count > 0)

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
            existing_paths.add(source_key)
            display_name = os.path.basename(normalized_path)
            duration = self._detect_duration_mmss(normalized_path)
            self.file_queue_rows.append(
                {
                    "filename": display_name,
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
        self.btn_move_and_transcribe.setFixedHeight(44)
        self.btn_transcribe_target.setFixedHeight(44)
        self.btn_move_files.setFixedHeight(38)
        self.btn_stop_now.setFixedHeight(38)

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

        self.current_progress_bar.setMinimumHeight(8)
        self.current_progress_bar.setMaximumHeight(8)
        self.total_progress_bar.setMinimumHeight(8)
        self.total_progress_bar.setMaximumHeight(8)

        top_card_h = 92
        for icon in (self.status_icon, self.eta_icon):
            icon.setFixedSize(40, 40)
        self.top_cards_container.setMinimumHeight(top_card_h)
        self.top_cards_container.setMaximumHeight(top_card_h)
        for card in (self.card_status, self.card_progress, self.card_eta):
            card.setMinimumHeight(top_card_h)
            card.setMaximumHeight(top_card_h)

        detail_min_h = 132
        self.card_current.setMinimumHeight(detail_min_h)
        self.card_current.setMaximumHeight(detail_min_h)
        dashboard_h = top_card_h + detail_min_h + 48
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

        for cb in (self.chk_notify_each_file, self.chk_notify_total, self.shutdown_checkbox):
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

        if self.target_folder:
            output_text = self._display_path_for_ui(self.target_folder)
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
            self.shutdown_checkbox.setChecked(
                bool(self.ui_settings.value(SETTINGS_KEY_SHUTDOWN_AFTER_DONE, False, type=bool))
            )
            shutdown_wait_seconds = int(
                self.ui_settings.value(SETTINGS_KEY_SHUTDOWN_WAIT_SECONDS, 0, type=int)
            )
            self._set_shutdown_wait_seconds(shutdown_wait_seconds)
        except Exception:
            pass
        self._sync_shutdown_wait_combo_state()
        self._refresh_path_labels()
        QTimer.singleShot(0, self._refresh_path_labels)
        self._refresh_file_list_empty_state()

    def save_ui_preferences(self):
        try:
            self.ui_settings.setValue(SETTINGS_KEY_TARGET_DIR, self.target_folder or "")
            self.ui_settings.setValue(SETTINGS_KEY_NOTIFY_EACH, self.chk_notify_each_file.isChecked())
            self.ui_settings.setValue(SETTINGS_KEY_NOTIFY_TOTAL, self.chk_notify_total.isChecked())
            self.ui_settings.setValue(SETTINGS_KEY_SHUTDOWN_AFTER_DONE, self.shutdown_checkbox.isChecked())
            self.ui_settings.setValue(SETTINGS_KEY_SHUTDOWN_WAIT_SECONDS, self._get_shutdown_wait_seconds())
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

    def _refresh_path_labels(self):
        self._set_path_label(
            self.label_target,
            "\uC804\uC0AC\uC790\uB8CC \uD3F4\uB354",
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

        settings_min = max(220, int(self.group_settings.minimumSizeHint().height()))
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
            self.show_warning_message("경고", "선택 전사 대상 파일이 없습니다.")
            return False
        runtime_parent = os.path.dirname(self.target_folder)
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
            self.show_error_message("오류", f"선택 전사 임시 폴더를 만들지 못했습니다.\n\n{e}")
            return False
        if not runtime_folder:
            self.show_error_message("오류", "선택 전사 임시 폴더 이름을 확보하지 못했습니다.")
            return False

        self.append_log_text(f"[DBG] _prepare_selected_runtime_folder: selected_run_items={len(self.selected_run_items)}개\n", force=True)
        for _dbg_item in self.selected_run_items:
            self.append_log_text(f"[DBG]   item: queue_name={_dbg_item.get('queue_name')!r}, transcribe_name={_dbg_item.get('transcribe_name')!r}\n", force=True)
        runtime_entries: list[dict] = []
        for item in self.selected_run_items:
            transcribe_name = os.path.basename(str(item.get("transcribe_name", ""))).strip()
            if not transcribe_name:
                self.append_log_text(f"[DBG]   transcribe_name 없음 → 건너뜀\n", force=True)
                continue
            # target_folder에서 먼저 찾고, 없으면 source_path로 fallback
            target_mp3 = os.path.join(self.target_folder, transcribe_name)
            if not os.path.isfile(target_mp3):
                fallback_src = str(item.get("source_path", "")).strip()
                if fallback_src and os.path.isfile(fallback_src):
                    self.append_log_text(f"[DBG]   target_folder 외부 파일 fallback: {fallback_src!r}\n", force=True)
                    target_mp3 = fallback_src
            self.append_log_text(f"[DBG]   target_mp3={target_mp3!r}, exists={os.path.isfile(target_mp3)}\n", force=True)
            if not os.path.isfile(target_mp3):
                self.append_log_text(f"[WARN] 선택 전사 대상 파일 누락: {target_mp3}\n", force=True)
                continue
            runtime_mp3 = os.path.join(runtime_folder, os.path.basename(target_mp3))
            try:
                self._link_or_copy_file(target_mp3, runtime_mp3)
                self.append_log_text(f"[DBG]   runtime 복사 완료: {runtime_mp3!r}\n", force=True)
            except Exception as e:
                self.append_log_text(f"[WARN] 선택 전사 임시 파일 준비 실패: {target_mp3} / {e}\n", force=True)
                continue

            # 기존 출력 파일(.txt/.json/.srt)을 runtime_folder에 복사하지 않음
            # 복사하면 count_pending_mp3_files()가 0을 반환해 전사가 시작되지 않음

            runtime_entries.append(
                {
                    "queue_name": item.get("queue_name", ""),
                    "target_mp3": target_mp3,
                    "runtime_mp3": runtime_mp3,
                }
            )

        if not runtime_entries:
            self._cleanup_selected_runtime_folder()
            self.show_warning_message("경고", "선택한 MP3를 전사 대상으로 준비하지 못했습니다.")
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
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(14, 12, 14, 12)
        content_layout.setSpacing(12)

        icon_label = QLabel("")
        icon_label.setObjectName("MessageIcon")
        icon_label.setFixedSize(28, 28)
        picked_icon = self._pick_message_icon(icon)
        if not picked_icon.isNull():
            icon_label.setPixmap(picked_icon.pixmap(24, 24))
        content_layout.addWidget(icon_label, 0, Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(5)

        heading = QLabel((title or "").strip() or APP_DISPLAY_NAME)
        heading.setObjectName("MessageHeading")
        heading.setWordWrap(False)
        text_col.addWidget(heading)

        body = QLabel((message or "").strip() or "\uD45C\uC2DC\uD560 \uBA54\uC2DC\uC9C0\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.")
        body.setObjectName("MessageText")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        text_col.addWidget(body)
        content_layout.addLayout(text_col, 1)
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
        if self.process is not None and self.process.state() != QProcess.NotRunning:
            if QMessageBox.question(self, "종료 확인", "전사가 진행 중입니다. 그래도 종료하시겠습니까?") != QMessageBox.Yes:
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
        self.btn_move_files.setEnabled(enabled)
        self.btn_move_and_transcribe.setEnabled(enabled)
        self.btn_transcribe_target.setEnabled(enabled)
        self.btn_stop_now.setEnabled(not enabled)
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
                "\uC2E4\uC2DC\uAC04 \uCD9C\uB825: GUI\uC5D0 \uC9C1\uC811 \uC5F0\uACB0\uB428"
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
                    "\uC2E4\uC2DC\uAC04 \uCD9C\uB825: GUI\uC5D0 \uC9C1\uC811 \uC5F0\uACB0\uB428"
                )
        except Exception:
            self._set_session_text("\uC138\uC158 \uC0C1\uD0DC: \uC77D\uAE30 \uC2E4\uD328")
            self._set_output_text_mode(Qt.ElideRight)
            self._set_output_text(
                "\uC2E4\uC2DC\uAC04 \uCD9C\uB825: GUI\uC5D0 \uC9C1\uC811 \uC5F0\uACB0\uB428"
            )

    def select_target_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "\uC804\uC0AC\uC790\uB8CC \uD3F4\uB354 \uC120\uD0DD",
        )
        if folder:
            self.target_folder = self._normalize_saved_folder_path(folder)
            self._refresh_path_labels()
            self.save_ui_preferences()
            self._refresh_path_labels()
            self.update_session_label()

    def load_mp3_files(self, show_empty_message=True):
        try:
            selected_files, _ = QFileDialog.getOpenFileNames(
                self,
                "MP3 파일 선택",
                "",
                "MP3 Files (*.mp3)",
            )
            if not selected_files:
                return
            self._rebuild_queue_from_files(sorted(selected_files), append=True)
            if not self._is_transcribe_running() and show_empty_message:
                self.total_target_mp3_files = 0
                self.completed_files.clear()
                self.last_completed_file_name = ""
                self.current_file_name = ""
                self.current_file_started_at = None
                self.update_current_file_progress(0, force=True)
                self._set_current_file_text("없음")
                self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)
                self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
                self._set_status_text("\uB300\uAE30 \uC911")
            self.update_total_progress_display()
            self._refresh_file_list_empty_state()
        except Exception as e:
            self.show_error_message("오류", f"파일 목록을 불러오지 못했습니다.\n\n{e}")

    def move_selected_files_core(self, refresh_queue: bool = True):
        self.append_log_text(f"[DBG] move_selected_files_core: target_folder={self.target_folder!r}\n", force=True)
        if not self.target_folder:
            self.show_warning_message("경고", "먼저 전사자료 폴더를 선택해 주세요.")
            return None
        selected_rows = self._get_checked_queue_rows()
        self.append_log_text(f"[DBG] move_selected_files_core: selected_rows={len(selected_rows)}개\n", force=True)
        if not selected_rows:
            self.show_warning_message("경고", "이동할 MP3 파일을 체크해 주세요.")
            return None
        moved, skipped, failed = 0, 0, []
        selected_items: list[dict] = []
        selected_target_files: list[str] = []
        seen_targets = set()
        same_folder = False
        for row in selected_rows:
            original = os.path.basename(str(row.get("filename", ""))).strip()
            src = self._normalize_saved_folder_path(row.get("source_path", ""))
            self.append_log_text(f"[DBG]   move: original={original!r}, raw_source={row.get('source_path', '(없음)')!r}, src={src!r}\n", force=True)
            if not src:
                candidate = os.path.join(self.target_folder, original)
                self.append_log_text(f"[DBG]   move: source_path 없음 → fallback candidate={candidate!r} exists={os.path.isfile(candidate)}\n", force=True)
                if os.path.isfile(candidate):
                    src = candidate
                else:
                    failed.append(f"{original} -> 원본 파일 경로가 없습니다.")
                    continue

            if not os.path.isfile(src):
                self.append_log_text(f"[DBG]   move: 파일 없음 → {src!r}\n", force=True)
                failed.append(f"{original} -> 원본 파일이 존재하지 않습니다.")
                continue

            clean = remove_page_suffix(os.path.basename(src))
            dst = os.path.join(self.target_folder, clean)
            same_src_target = self._is_same_folder(os.path.dirname(src), self.target_folder)
            same_folder = same_folder or same_src_target
            target_for_transcribe = os.path.basename(src if same_src_target else dst)
            row["transcribe_name"] = target_for_transcribe

            try:
                if same_src_target:
                    skipped += 1
                    row["source_path"] = src # 경로 유지
                elif os.path.normcase(os.path.abspath(src)) == os.path.normcase(os.path.abspath(dst)):
                    skipped += 1
                    row["source_path"] = dst
                elif os.path.exists(dst):
                    skipped += 1
                    row["source_path"] = dst # 이미 존재하면 해당 경로로 업데이트
                else:
                    shutil.move(src, dst)
                    moved += 1
                    row["source_path"] = dst
                
                target_key = target_for_transcribe.strip().lower()
                if target_key and target_key not in seen_targets:
                    seen_targets.add(target_key)
                    selected_target_files.append(target_for_transcribe)

                selected_items.append(
                    {
                        "queue_name": original,
                        "transcribe_name": target_for_transcribe,
                        "source_path": row.get("source_path", ""),
                    }
                )
            except Exception as e:
                row["transcribe_name"] = row.get("filename", original)
                failed.append(f"{original} -> {e}")
        self._refresh_file_queue_table()
        return {
            "moved_count": moved,
            "skipped_count": skipped,
            "failed_files": failed,
            "selected_items": selected_items,
            "selected_target_files": selected_target_files,
            "same_folder": same_folder,
        }

    def move_selected_files(self):
        result = self.move_selected_files_core()
        if result is None:
            return
        msg = (
            "\uC120\uD0DD\uD55C MP3 \uD30C\uC77C \uC774\uB3D9\uC774 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.\n\n"
            f"\uC774\uB3D9 \uC131\uACF5: {result['moved_count']}\uAC1C\n"
            f"\uC774\uBBF8 \uC874\uC7AC\uD558\uC5EC \uAC74\uB108\uB700: {result['skipped_count']}\uAC1C\n"
            f"\uC774\uB3D9 \uC2E4\uD328: {len(result['failed_files'])}\uAC1C"
        )
        if result["failed_files"]:
            msg += "\n\n\uC2E4\uD328 \uD30C\uC77C:\n" + "\n".join(result["failed_files"][:10])
        self.show_info_message("\uC774\uB3D9 \uACB0\uACFC", msg)

    def move_selected_files_and_start_transcribe(self):
        self.append_log_text("[DBG] move_selected_files_and_start_transcribe 진입\n", force=True)
        result = self.move_selected_files_core(refresh_queue=False)
        if result is None:
            return
        if not result["selected_items"]:
            self.show_info_message("알림", "선택한 MP3가 없어 전사를 시작하지 않습니다.")
            return
        self.selected_run_items = result["selected_items"]
        self.run_mode = "selected"
        self.run_transcribe_process()

    def start_transcribe_on_target_folder(self):
        # 대기열이 비어있으면 즉시 경고
        if not self.file_queue_rows:
            self.show_warning_message("경고", "전사할 파일이 없습니다.\n\n먼저 MP3 파일을 불러오세요.")
            return
        if not self.target_folder:
            self.show_warning_message("경고", "먼저 전사자료 폴더를 선택해 주세요.")
            return

        # 대기열 파일 중 target_folder 외부에 있는 파일을 자동 이동
        external_moved = 0
        for row in self.file_queue_rows:
            src = self._normalize_saved_folder_path(row.get("source_path", ""))
            if not src or not os.path.isfile(src):
                continue
            if not self._is_same_folder(os.path.dirname(src), self.target_folder):
                clean = remove_page_suffix(os.path.basename(src))
                dst = os.path.join(self.target_folder, clean)
                try:
                    if not os.path.exists(dst):
                        shutil.move(src, dst)
                        external_moved += 1
                    row["source_path"] = dst
                    row["transcribe_name"] = clean
                except Exception as e:
                    self.append_log_text(f"[WARN] 외부 파일 자동 이동 실패: {src} -> {e}\n", force=True)

        if external_moved > 0:
            self._refresh_file_queue_table()

        # 대기열 전체(체크 여부 무관)를 selected_run_items로 등록 → 임시 폴더 전사
        all_items = []
        for row in self.file_queue_rows:
            transcribe_name = str(row.get("transcribe_name", row.get("filename", ""))).strip()
            if not transcribe_name:
                continue
            all_items.append({
                "queue_name": str(row.get("filename", "")),
                "transcribe_name": transcribe_name,
                "source_path": str(row.get("source_path", "")),
            })

        if not all_items:
            self.show_warning_message("경고", "전사할 파일이 없습니다.")
            return

        self.selected_run_items = all_items
        self._cleanup_selected_runtime_folder()
        self.run_mode = "all"
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
            _in_progress = "선택 전사 진행 중" if self.run_mode == "selected" else "전체 전사 진행 중"
            self._set_status_text(_in_progress)
            self._append_user_log(f"{self._log_file_name(name)} 전사 시작", "normal")
            self.append_log_text(f"[GUI] 진행 파일 인덱스: {cur_idx}/{total}, 파일={name}\n")
            self._set_current_file_text(name)
            self._set_queue_status_by_name(name, QUEUE_STATUS_PROCESSING)
            self.update_current_file_progress(0, force=True)
            self._set_eta_value(self.label_current_eta, "계산 중...")
            self.update_total_eta_label()
        elif evt == "FILE_DONE":
            name = payload[0] if payload else self.current_file_name
            if name:
                self.completed_files.add(name)
                self.last_completed_file_name = name
                self._set_queue_status_by_name(name, QUEUE_STATUS_DONE)
            if self.current_file_started_at:
                d = time.time() - self.current_file_started_at
                if d > 0.4:
                    self.file_duration_history.append(d)
                    if len(self.file_duration_history) > 30:
                        self.file_duration_history.pop(0)
            self.current_file_name = ""
            self.current_file_started_at = None
            self.update_current_file_progress(100, force=True)
            if name:
                self._set_current_file_text(name)
            else:
                self._set_current_file_text("없음")
            self.update_total_progress_display()
            self.update_total_eta_label()
            self.update_session_label()
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
        elif evt == "FILE_FAIL":
            name = payload[0] if payload else "알 수 없음"
            err = payload[1] if len(payload) >= 2 else ""
            self._set_status_text("오류 발생")
            self._set_current_file_text(name)
            self._set_queue_status_by_name(name, QUEUE_STATUS_FAILED)
            self._append_user_log(f"{self._log_file_name(name)} 오류 발생", "error")
            if err:
                self.append_log_text(f"[GUI] 파일 실패: {name} / {err}\n")
        elif evt == "STOPPED":
            self._set_status_text("중지 요청됨")
        elif evt == "ALL_STOPPED":
            self._set_status_text("\uC0AC\uC6A9\uC790 \uC911\uC9C0\uB428")
            self._set_current_file_text("없음")
            self.current_file_name = ""
            self.current_file_started_at = None
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

    def run_transcribe_process(self):
        if not self.target_folder:
            self.show_warning_message("경고", "먼저 전사자료 폴더를 선택해 주세요.")
            return
        auto_path = self.get_auto_transcribe_path()
        if not os.path.exists(auto_path):
            self.show_error_message("오류", f"auto_transcribe.py 파일을 찾을 수 없습니다.\n\n확인 경로:\n{auto_path}")
            return
        if self.process is not None:
            self.show_warning_message("경고", "이미 전사 작업이 진행 중입니다.")
            return
        runtime_folder = self.target_folder
        if self.run_mode in ("selected", "all") and self.selected_run_items:
            if not self._prepare_selected_runtime_folder():
                return
            runtime_folder = self.selected_runtime_folder or self.target_folder
        else:
            self.selected_run_items = []
            self._cleanup_selected_runtime_folder()

        _pending = self.count_pending_mp3_files(runtime_folder)
        self.append_log_text(f"[DBG] run_transcribe_process: run_mode={self.run_mode!r}, runtime_folder={runtime_folder!r}, pending={_pending}\n", force=True)
        if _pending <= 0:
            self.total_target_mp3_files = 0
            self.update_total_progress_display()
            self._set_status_text("처리할 파일 없음")
            self._set_current_file_text("없음")
            self._set_eta_value(self.label_total_eta, ETA_EMPTY_TEXT)
            self._set_eta_value(self.label_current_eta, ETA_EMPTY_TEXT)
            self.show_info_message("알림", "이번 실행에서 처리할 파일이 없습니다.")
            self.notify_with_toast(
                "처리할 파일 없음",
                "이번 실행에서 처리할 파일이 없습니다.",
                progress_percent=None,
                current_file="",
                timeout_ms=7600,
                allow_open_folder=True,
            )
            self._sync_selected_runtime_outputs()
            self.selected_run_items = []
            return
        self.prepare_progress_tracking(runtime_folder=runtime_folder)
        self.set_transcribe_buttons_enabled(False)
        self.update_session_label()
        self.process = QProcess(self)
        self.process.setProgram("python" if getattr(sys, "frozen", False) else sys.executable)
        self.process.setArguments([auto_path, runtime_folder])
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
            self.show_error_message("오류", "전사 프로세스를 시작하지 못했습니다.")
            return
        _start_status = "선택 전사 진행 중" if self.run_mode == "selected" else "전체 전사 진행 중"
        self._set_status_text(_start_status)
        self._set_current_file_text("없음")
        self.append_log_text(f"[GUI] 전사 시작: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

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
        running = self.process is not None and self.process.state() != QProcess.NotRunning
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
    window.show()
    window.ensure_main_window_visible()
    QTimer.singleShot(140, window.ensure_main_window_visible)
    sys.exit(app.exec())
