# -*- coding: utf-8 -*-
"""ヘッドレス実行用ランナー: 00→01→03を1回のエディタ起動で順に流す。
UnrealEditor-Cmd.exe <proj> -ExecutePythonScript=このファイル で呼ばれる。"""

import traceback

import unreal

# 2026-07-17改訂: 掃除→取込→NeverStream→全ティア複製→ラベルの順
SCRIPTS = [
    r"C:\P\Work\PalMod\ue_scripts\06_clean_for_reimport.py",
    r"C:\P\Work\PalMod\ue_scripts\00_setup_folders.py",
    r"C:\P\Work\PalMod\ue_scripts\01_import_and_setup.py",
    r"C:\P\Work\PalMod\ue_scripts\07_never_stream_textures.py",
    r"C:\P\Work\PalMod\ue_scripts\02_duplicate_tiers.py",
    r"C:\P\Work\PalMod\ue_scripts\03_make_label.py",
]

for path in SCRIPTS:
    unreal.log(f"===== RUN {path} =====")
    try:
        with open(path, encoding="utf-8") as f:
            code = f.read()
        exec(compile(code, path, "exec"), {"__name__": "__main__", "__file__": path})
        unreal.log(f"===== OK {path} =====")
    except Exception:
        unreal.log_error(f"===== FAILED {path} =====")
        unreal.log_error(traceback.format_exc())
        raise SystemExit(1)

unreal.log("===== ALL_SCRIPTS_DONE =====")
