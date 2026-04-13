
import datetime
import json
import os
import re
import shutil
import statistics
import sys
import time

from PySide6.QtCore import QProcess, QTimer, Qt
from PySide6.QtGui import QAction, QIcon, QTextCursor, QTextOption
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
APP_DISPLAY_NAME = "전사도우미"
APP_USER_MODEL_ID = "전사도우미"


def apply_windows_app_identity():
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
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
    ]
    if meipass:
        candidates.extend(
            [
                os.path.join(meipass, "transcribe_helper.ico"),
                os.path.join(meipass, "assets", "transcribe_helper.ico"),
            ]
        )
    for path in candidates:
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
    return QIcon()


class TranscribeGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(1240, 760)
        self.setMinimumSize(960, 620)

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
        self._status_full_text = "현재 상태: 대기 중"
        self._current_file_full_text = "현재 처리 중 파일: 없음"
        self._session_full_text = "세션 상태: 확인 안 됨"
        self._output_full_text = "실시간 출력: GUI에 직접 연결됨"

        self.build_ui()
        self.apply_styles()
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
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        left = QVBoxLayout()
        right = QVBoxLayout()
        left.setSpacing(10)
        right.setSpacing(10)
        root.addLayout(left, 30)
        root.addLayout(right, 70)

        title = QFrame()
        title.setObjectName("TitleCard")
        tbox = QVBoxLayout(title)
        tbox.setContentsMargins(16, 14, 16, 14)
        tbox.setSpacing(4)
        title_text = QLabel("MP3 전사도우미", objectName="TitleText")
        title_text.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        title_hint = QLabel("폴더 선택 -> 파일 준비 -> 전사 시작", objectName="TitleHint")
        title_hint.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        tbox.addWidget(title_text)
        tbox.addWidget(title_hint)
        left.addWidget(title)

        settings = QGroupBox("설정 및 옵션")
        sbox = QVBoxLayout(settings)
        sbox.setSpacing(8)
        sbox.addWidget(QLabel("전사 전에 사용할 폴더를 먼저 지정하세요.", objectName="HelperText"))

        self.label_download = QLabel("다운로드 폴더: 아직 선택 안 함")
        self.label_download.setWordWrap(True)
        self.label_download.setObjectName("PathLabel")
        sbox.addWidget(self.label_download)
        self.btn_download = QPushButton("다운로드 폴더 선택")
        sbox.addWidget(self.btn_download)

        self.label_target = QLabel("전사자료 폴더: 아직 선택 안 함")
        self.label_target.setWordWrap(True)
        self.label_target.setObjectName("PathLabel")
        sbox.addWidget(self.label_target)
        self.btn_target = QPushButton("전사자료 폴더 선택")
        sbox.addWidget(self.btn_target)

        self.btn_load_files = QPushButton("MP3 파일 목록 불러오기")
        sbox.addWidget(self.btn_load_files)
        left.addWidget(settings)

        options = QGroupBox("알림 및 종료 옵션")
        obox = QVBoxLayout(options)
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

        logs = QGroupBox("실행 로그")
        lbox = QVBoxLayout(logs)
        lbox.setSpacing(8)
        self.btn_toggle_log = QPushButton("로그창 보기")
        lbox.addWidget(self.btn_toggle_log)
        self.log_viewer = QTextEdit()
        self.log_viewer.setObjectName("LogViewer")
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setPlaceholderText("전사 진행 로그가 여기에 표시됩니다.")
        self.log_viewer.setMinimumHeight(140)
        self.log_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.log_viewer.setLineWrapMode(QTextEdit.WidgetWidth)
        self.log_viewer.setWordWrapMode(QTextOption.WrapAnywhere)
        self.log_viewer.document().setDocumentMargin(10)
        self.log_viewer.hide()
        lbox.addWidget(self.log_viewer)
        left.addWidget(logs, 1)

        dashboard = QGroupBox("진행 대시보드")
        dbox = QVBoxLayout(dashboard)
        dbox.setSpacing(8)
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
        dbox.addWidget(self.label_status)
        dbox.addWidget(self.label_current_file)
        dbox.addWidget(self.label_session)
        dbox.addWidget(self.label_output_source)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        self.label_total_progress_text = QLabel("0 / 0")
        self.label_total_progress_text.setObjectName("MetricValue")
        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setRange(0, 100)
        self.label_total_eta = QLabel("없음")
        self.label_total_eta.setObjectName("MetricValue")
        self.label_current_progress_text = QLabel("0%")
        self.label_current_progress_text.setObjectName("MetricValue")
        self.current_progress_bar = QProgressBar()
        self.current_progress_bar.setRange(0, 100)
        self.label_current_eta = QLabel("없음")
        self.label_current_eta.setObjectName("MetricValue")
        self.label_total_progress_text.setWordWrap(True)
        self.label_total_eta.setWordWrap(True)
        self.label_current_progress_text.setWordWrap(True)
        self.label_current_eta.setWordWrap(True)
        self.label_total_progress_text.setMinimumHeight(28)
        self.label_total_eta.setMinimumHeight(28)
        self.label_current_progress_text.setMinimumHeight(28)
        self.label_current_eta.setMinimumHeight(28)
        self.label_total_progress_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_total_eta.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_current_progress_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_current_eta.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        total_label = QLabel("전체 진행률")
        total_label.setObjectName("MetricTitle")
        grid.addWidget(total_label, 0, 0)
        grid.addWidget(self.label_total_progress_text, 1, 0)
        grid.addWidget(self.total_progress_bar, 2, 0)
        total_eta_label = QLabel("전체 작업 남은 시간")
        total_eta_label.setObjectName("MetricTitle")
        grid.addWidget(total_eta_label, 0, 1)
        grid.addWidget(self.label_total_eta, 1, 1, 2, 1)
        current_label = QLabel("현재 파일 진행률")
        current_label.setObjectName("MetricTitle")
        grid.addWidget(current_label, 0, 2)
        grid.addWidget(self.label_current_progress_text, 1, 2)
        grid.addWidget(self.current_progress_bar, 2, 2)
        current_eta_label = QLabel("현재 파일 남은 시간")
        current_eta_label.setObjectName("MetricTitle")
        grid.addWidget(current_eta_label, 0, 3)
        grid.addWidget(self.label_current_eta, 1, 3, 2, 1)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 2)
        grid.setColumnStretch(3, 1)
        dbox.addLayout(grid)
        right.addWidget(dashboard)

        files = QGroupBox("MP3 파일 목록")
        fbox = QVBoxLayout(files)
        fbox.setSpacing(8)
        self.label_file_count = QLabel("불러온 MP3 파일 수: 0개")
        self.label_file_count.setObjectName("SectionValue")
        fbox.addWidget(self.label_file_count)
        fbox.addWidget(QLabel("선택한 파일을 이동하거나 현재 가져온 목록을 여기에서 확인할 수 있습니다.", objectName="HelperText"))
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list_widget.setMinimumHeight(220)
        self.file_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.file_list_widget.setTextElideMode(Qt.ElideMiddle)
        self.file_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.file_list_widget.setUniformItemSizes(True)
        self.file_list_widget.setSpacing(2)
        fbox.addWidget(self.file_list_widget)
        right.addWidget(files, 1)

        controls = QGroupBox("실행 제어")
        cbox = QVBoxLayout(controls)
        cbox.setSpacing(8)
        cbox.addWidget(QLabel("시작 버튼으로 전사를 실행하고, 필요하면 즉시 중지할 수 있습니다.", objectName="HelperText"))
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.btn_move_and_transcribe = QPushButton("선택한 MP3 이동 후 전사 시작")
        self.btn_transcribe_target = QPushButton("전사자료 폴더 전체 전사 시작")
        row1.addWidget(self.btn_move_and_transcribe)
        row1.addWidget(self.btn_transcribe_target)
        cbox.addLayout(row1)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.btn_move_files = QPushButton("선택한 MP3를 전사자료 폴더로 이동")
        self.btn_stop_now = QPushButton("즉시 중지")
        self.btn_stop_now.setObjectName("Danger")
        self.btn_stop_now.setEnabled(False)
        row2.addWidget(self.btn_move_files, 2)
        row2.addWidget(self.btn_stop_now, 1)
        cbox.addLayout(row2)
        right.addWidget(controls)

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
            "bg_app": "#1e2230",
            "panel_bg": "#272d40",
            "title_bg": "#2e3650",
            "surface_bg": "#232a3d",
            "panel_border": "#3b4563",
            "soft_border": "#343d57",
            "button_bg": "#37435f",
            "button_hover": "#425172",
            "button_border": "#4b5878",
            "button_text": "#dce5fa",
            "button_disabled_bg": "#2c3348",
            "button_disabled_border": "#39425b",
            "button_disabled_text": "#8d97b8",
            "danger_bg": "#4f3a4a",
            "danger_hover": "#5d4556",
            "danger_border": "#6b5061",
            "list_select": "#3a4867",
            "progress_bg": "#242b3f",
            "progress_border": "#43506f",
            "progress_chunk": "#7598d1",
            "text_title": "#eef3ff",
            "text_section": "#d9e0f2",
            "text_label": "#b3bdd5",
            "text_body": "#aab4cb",
            "text_helper": "#8792b0",
            "text_value": "#dbe5fb",
            "text_metric_label": "#b9c6e1",
            "text_path": "#becae5",
            "text_log": "#c8d3ee",
            "title_hint": "#9caac8",
        }

        self.setStyleSheet(
            f"""
            QWidget {{
                background:{palette["bg_app"]};
                color:{palette["text_body"]};
                font-family:"Malgun Gothic","Segoe UI","Noto Sans KR",sans-serif;
                font-size:12px;
            }}
            QLabel {{
                font-size:12px;
                font-weight:400;
                color:{palette["text_label"]};
            }}
            QGroupBox {{
                border:1px solid {palette["panel_border"]};
                border-radius:10px;
                margin-top:10px;
                padding-top:12px;
                background:{palette["panel_bg"]};
                font-weight:700;
                font-size:15px;
                color:{palette["text_section"]};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left:12px;
                padding:0 6px;
                color:{palette["text_section"]};
            }}
            #TitleCard {{
                border:1px solid {palette["soft_border"]};
                border-radius:12px;
                background:{palette["title_bg"]};
            }}
            #TitleText {{
                font-size:34px;
                font-weight:900;
                color:{palette["text_title"]};
            }}
            #TitleHint {{
                color:{palette["title_hint"]};
                font-size:12px;
                font-weight:500;
            }}
            #PathLabel {{
                border:1px solid {palette["soft_border"]};
                border-radius:8px;
                padding:9px 10px;
                background:{palette["surface_bg"]};
                color:{palette["text_path"]};
                font-size:12px;
                font-weight:600;
            }}
            #HelperText {{
                color:{palette["text_helper"]};
                font-size:11px;
                font-weight:400;
            }}
            #SectionValue {{
                color:{palette["text_value"]};
                font-size:13px;
                font-weight:600;
            }}
            #StatusPrimary {{
                font-size:18px;
                font-weight:800;
                color:{palette["text_value"]};
            }}
            #StatusSecondary {{
                font-size:16px;
                font-weight:700;
                color:{palette["text_section"]};
            }}
            #MetaStatus {{
                font-size:11px;
                font-weight:500;
                color:{palette["text_helper"]};
            }}
            #MetricTitle {{
                font-size:12px;
                font-weight:700;
                color:{palette["text_metric_label"]};
            }}
            #MetricValue {{
                font-size:20px;
                font-weight:800;
                color:{palette["text_value"]};
            }}
            QPushButton {{
                border:1px solid {palette["button_border"]};
                border-radius:10px;
                padding:10px 12px;
                background:{palette["button_bg"]};
                color:{palette["button_text"]};
                font-weight:700;
                font-size:14px;
            }}
            QPushButton:hover {{ background:{palette["button_hover"]}; }}
            QPushButton:disabled {{
                background:{palette["button_disabled_bg"]};
                border-color:{palette["button_disabled_border"]};
                color:{palette["button_disabled_text"]};
            }}
            QPushButton#Danger {{
                background:{palette["danger_bg"]};
                border-color:{palette["danger_border"]};
                color:{palette["button_text"]};
            }}
            QPushButton#Danger:hover {{ background:{palette["danger_hover"]}; }}
            QListWidget {{
                border:1px solid {palette["soft_border"]};
                border-radius:10px;
                background:{palette["surface_bg"]};
                font-size:13px;
                font-weight:500;
                color:{palette["text_label"]};
                padding:4px;
            }}
            QListWidget::item {{
                padding:6px 8px;
                border-radius:6px;
            }}
            QListWidget::item:selected {{
                background:{palette["list_select"]};
                color:{palette["text_title"]};
            }}
            QTextEdit#LogViewer {{
                border:1px solid {palette["soft_border"]};
                border-radius:10px;
                background:{palette["surface_bg"]};
                font-family:"Consolas","D2Coding","Malgun Gothic",monospace;
                font-size:12px;
                color:{palette["text_log"]};
                padding:8px;
                selection-background-color:{palette["list_select"]};
            }}
            QCheckBox {{
                font-size:13px;
                font-weight:600;
                color:{palette["text_section"]};
                spacing:8px;
                padding:2px 0;
            }}
            QProgressBar {{
                border:1px solid {palette["progress_border"]};
                border-radius:8px;
                background:{palette["progress_bg"]};
                text-align:center;
                min-height:20px;
                color:{palette["text_metric_label"]};
                font-size:11px;
                font-weight:700;
            }}
            QProgressBar::chunk {{
                border-radius:7px;
                background:{palette["progress_chunk"]};
            }}
            """
        )

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

    def _apply_status_and_meta_labels(self):
        self._set_status_text(self._status_full_text)
        self._set_current_file_text(self._current_file_full_text)
        self._set_session_text(self._session_full_text)
        self._set_output_text(self._output_full_text)

    def _set_path_label(self, label: QLabel, title: str, path: str):
        if not path:
            label.setText(f"{title}: 아직 선택 안 함")
            label.setToolTip("")
            return
        available = max(220, label.width() - 22)
        elided = label.fontMetrics().elidedText(path, Qt.ElideMiddle, available)
        label.setText(f"{title}:\n{elided}")
        label.setToolTip(path)

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
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)

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
        return {"running": "진행 중", "completed": "완료", "stopped": "중지됨", "crashed": "비정상 종료"}.get(status, status or "없음")

    def update_session_label(self):
        path = self.get_session_state_path()
        if not path or not os.path.exists(path):
            self._set_session_text("세션 상태: 확인 안 됨")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
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

    def count_target_mp3_files(self) -> int:
        if not self.target_folder or not os.path.isdir(self.target_folder):
            return 0
        count = 0
        for name in os.listdir(self.target_folder):
            if not name.lower().endswith(".mp3"):
                continue
            mp3_path = os.path.join(self.target_folder, name)
            outs = self._output_triplet(mp3_path)
            if not all(os.path.exists(p) for p in outs):
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
            self.label_current_eta.setText(f"{format_seconds(self.current_eta_seconds)}")
        elif p >= 100:
            self.current_eta_seconds = 0
            self.label_current_eta.setText("없음")
        elif self.current_file_name:
            self.current_eta_seconds = None
            self.label_current_eta.setText("계산 중...")
        else:
            self.current_eta_seconds = None
            self.label_current_eta.setText("없음")
        self.update_total_eta_label()

    def update_total_eta_label(self):
        total = max(0, int(self.total_target_mp3_files))
        done = len(self.completed_files)
        if total <= 0 or (done >= total and not self.current_file_name):
            self.label_total_eta.setText("없음")
            self.total_eta_seconds = None
            return
        running = 1 if self.current_file_name else 0
        remain_files = max(0, total - done - running)
        has_avg = bool(self.file_duration_history)
        if self.current_file_name and self.current_eta_seconds is None and not has_avg:
            self.label_total_eta.setText("계산 중...")
            self.total_eta_seconds = None
            return
        if not self.current_file_name and not has_avg and remain_files > 0:
            self.label_total_eta.setText("계산 중...")
            self.total_eta_seconds = None
            return
        avg = statistics.mean(self.file_duration_history) if has_avg else 0.0
        cur = self.current_eta_seconds or 0.0
        est = cur + (remain_files * avg)
        self.total_eta_seconds = est if self.total_eta_seconds is None else self.total_eta_seconds * 0.7 + est * 0.3
        self.label_total_eta.setText(f"{format_seconds(self.total_eta_seconds)}")

    def update_eta_labels(self, initial=False):
        if initial:
            if self.total_target_mp3_files <= 0:
                self.label_total_eta.setText("없음")
                self.label_current_eta.setText("없음")
            else:
                self.label_total_eta.setText("계산 중...")
                self.label_current_eta.setText("계산 중...")
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
            self.total_target_mp3_files = int(payload[0]) if payload else 0
            self.update_total_progress_display()
            self.update_eta_labels(initial=True)
            if self.total_target_mp3_files <= 0:
                self.label_status.setText("현재 상태: 이번 실행에서 처리할 파일이 없습니다")
        elif evt == "FILE_INDEX":
            name = payload[2] if len(payload) >= 3 else "알 수 없음"
            self.current_file_name = name
            self.current_file_started_at = time.time()
            self.current_eta_seconds = None
            self.label_status.setText("현재 상태: 전사 진행 중")
            self.label_current_file.setText(f"현재 처리 중 파일: {name}")
            self.update_current_file_progress(0, force=True)
            self.label_current_eta.setText("계산 중...")
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
            self.label_status.setText("현재 상태: 중지됨")
        elif evt == "ALL_STOPPED":
            self.label_status.setText("현재 상태: 즉시 중지 완료")
            self.label_current_file.setText("현재 처리 중 파일: 없음")
            self.current_file_name = ""
            self.current_file_started_at = None
            self.label_current_eta.setText("없음")
            self.update_total_eta_label()
            self.update_session_label()
        elif evt == "ALL_DONE":
            self.label_status.setText("현재 상태: 전사 완료")
            self.label_current_file.setText("현재 처리 중 파일: 없음")
            self.current_file_name = ""
            self.current_file_started_at = None
            self.label_current_eta.setText("없음")
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
            self.label_total_eta.setText("없음")
            self.label_current_eta.setText("없음")
            QMessageBox.information(self, "알림", "이번 실행에서 처리할 파일이 없습니다.")
            return
        self.clear_old_stop_flag()
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
        self.append_log_text(f"[GUI] 프로세스 종료: exit_code={exit_code}, normal={exit_status == QProcess.NormalExit}\n")
        self.process = None
        self.set_transcribe_buttons_enabled(True)
        self.update_session_label()
        if self.pending_kill:
            self.label_status.setText("현재 상태: 강제 종료됨")
            self.pending_kill = False
            return
        if self.stop_requested:
            self.label_status.setText("현재 상태: 중지 완료")
            self.stop_requested = False
            return
        if exit_code != 0 and exit_status == QProcess.NormalExit:
            self.label_status.setText("현재 상태: 오류로 종료")

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
            self.label_status.setText("현재 상태: 중지 요청됨")
            self.append_log_text("[GUI] stop.flag 생성 완료 - 즉시 중지 요청\n")
            self.force_kill_timer.start(10000)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"중지 요청 실패\n\n{e}")

    def force_kill_process(self):
        if self.process is None or self.process.state() == QProcess.NotRunning:
            return
        self.pending_kill = True
        self.append_log_text("[GUI] terminate 후 종료되지 않아 kill() 실행\n")
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
    apply_windows_app_identity()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setDesktopFileName(APP_DISPLAY_NAME)
    icon = load_runtime_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = TranscribeGUI()
    if not icon.isNull():
        window.setWindowIcon(icon)
        window.tray_icon.setIcon(icon)
    window.show()
    sys.exit(app.exec())
