# -*- mode: python ; coding: utf-8 -*-

import shutil
from pathlib import Path


class CollectWithRootAutoTranscribe(COLLECT):
    def assemble(self):
        super().assemble()
        src = Path("auto_transcribe.py").resolve()
        dst_dir = Path(self.name).resolve()
        
        # Copy auto_transcribe.py
        if not src.exists():
            print(f"[SPEC][WARN] auto_transcribe.py 소스 파일 없음: {src}")
        elif not dst_dir.exists():
            print(f"[SPEC][WARN] dist 출력 폴더 없음: {dst_dir}")
        else:
            dst = dst_dir / "auto_transcribe.py"
            try:
                if not (dst.exists() and src.resolve() == dst.resolve()):
                    shutil.copy2(src, dst)
                    print(f"[SPEC] auto_transcribe.py 루트 배치 완료: {dst}")
                else:
                    print(f"[SPEC] auto_transcribe.py 루트 배치 유지됨: {dst}")
            except Exception as e:
                print(f"[SPEC][WARN] auto_transcribe.py 루트 배치 실패: {e}")

        # Copy google_drive_uploader.py
        src2 = Path("google_drive_uploader.py").resolve()
        if src2.exists() and dst_dir.exists():
            dst2 = dst_dir / "google_drive_uploader.py"
            try:
                if not (dst2.exists() and src2.resolve() == dst2.resolve()):
                    shutil.copy2(src2, dst2)
                    print(f"[SPEC] google_drive_uploader.py 루트 배치 완료: {dst2}")
                else:
                    print(f"[SPEC] google_drive_uploader.py 루트 배치 유지됨: {dst2}")
            except Exception as e:
                print(f"[SPEC][WARN] google_drive_uploader.py 루트 배치 실패: {e}")


a = Analysis(
    ["gui_main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets", "assets"), ("transcribe_helper.ico", "."), ("auto_transcribe.py", "."), ("prompts", "prompts"), ("corrections", "corrections")],
    hiddenimports=[
        "google_drive_uploader",
        "googleapiclient",
        "googleapiclient.discovery",
        "googleapiclient.http",
        "google_auth_oauthlib",
        "google_auth_oauthlib.flow",
        "google.auth",
        "google.auth.transport.requests",
        "google.oauth2.credentials",
        "httplib2",
        "oauthlib",
        "requests_oauthlib",
        "uritemplate",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="전사도우미",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["transcribe_helper.ico"],
)

coll = CollectWithRootAutoTranscribe(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="전사도우미",
)
