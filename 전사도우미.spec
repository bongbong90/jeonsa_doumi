# -*- mode: python ; coding: utf-8 -*-

import shutil
from pathlib import Path


class CollectWithRootAutoTranscribe(COLLECT):
    def assemble(self):
        super().assemble()
        src = Path("auto_transcribe.py").resolve()
        dst_dir = Path(self.name).resolve()
        if not src.exists():
            print(f"[SPEC][WARN] auto_transcribe.py 소스 파일 없음: {src}")
            return
        if not dst_dir.exists():
            print(f"[SPEC][WARN] dist 출력 폴더 없음: {dst_dir}")
            return
        dst = dst_dir / "auto_transcribe.py"
        try:
            if dst.exists() and src.resolve() == dst.resolve():
                print(f"[SPEC] auto_transcribe.py 루트 배치 유지됨: {dst}")
                return
            shutil.copy2(src, dst)
            print(f"[SPEC] auto_transcribe.py 루트 배치 완료: {dst}")
        except Exception as e:
            print(f"[SPEC][WARN] auto_transcribe.py 루트 배치 실패: {e}")


a = Analysis(
    ["gui_main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets", "assets"), ("transcribe_helper.ico", "."), ("auto_transcribe.py", ".")],
    hiddenimports=[],
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
