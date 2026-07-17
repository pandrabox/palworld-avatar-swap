# UE工程の手順書(ぱん用) — PGF差し替えMOD

Blender工程は全自動化済み(`assets/converted/`に成果物あり)。ここからはUE 5.1.1での作業。
Pythonスクリプトで大部分を自動化してあるので、手作業は「インストール・設定・目視確認」だけ。

## 0. インストール(初回のみ、ぱんの手)

1. Epic Games Launcherを入れてログイン
2. Unreal Engine **5.1.1** をインストール(ライブラリ→エンジンバージョン→5.1.x)
3. 新規プロジェクト: Games > Blank、**Blueprint**、Desktop、Quality=Maximum、
   Starter Content/Raytracingオフ。名前例 `PGFPalMod`、場所例 `C:\UnrealProjects\`

## 1. プロジェクト設定(初回のみ)

1. Edit > Plugins で **Python Editor Script Plugin** を有効化 → 再起動
2. Edit > Project Settings:
   - Project > Packaging: **Use Pak File** ✔、**Cook everything in the project content directory** ✔、
     **Generate Chunks** ✔、**Share Material Shader Code** ✖
3. (VRM経路を使う場合のみ) ガイド同梱の
   `downloads\guide2826\02_Unreal_Engine_Files\01_VRM4U\Plugins\VRM4U` を
   プロジェクトの `Plugins\` フォルダへコピー → Pluginsで有効化。
   ※現在の自動化はFBX+簡易マテリアル経路なのでVRM4Uは不要

## 2. アセット構築(スクリプト実行)

UEエディタ下部のコンソール(Cmd▼をPythonに切替)に、以下を**1本ずつ**貼ってEnter:

```
C:\P\Work\PalMod\ue_scripts\00_setup_folders.py
C:\P\Work\PalMod\ue_scripts\01_import_and_setup.py
C:\P\Work\PalMod\ue_scripts\03_make_label.py
```

01の後に目視確認: Content Browserで
`Pal/Model/Character/Player/Outfit/SK_Player_Female_Outfit_OldCloth001` のSKを開き、
- メッシュがPGFの形をしているか
- マテリアル6スロットにM_PGF_*が割り当たっているか(EPTopaz/EPMetalは単色でOK)
- Skeletonが `Skeleton/Human/SK_PalHuman_Skeleton` を指しているか

## 3. パッケージ → 最初のゲーム内テスト

1. PowerShellで `C:\P\Work\PalMod\ue_scripts\package_mod.ps1` を実行
   (中の $UE_ROOT / $PROJECT のパスを自分の環境に合わせてから)
2. できた `PGF_PlayerSwap_P.pak` を
   `C:\Program Files (x86)\Steam\steamapps\common\Palworld\Pal\Content\Paks` へコピー
3. ゲーム起動 → **防具を全部外した状態**(=OldCloth001が出る状態)で見た目確認
   - 【重要】初回テスト前にセーブのバックアップ確認(取得済み: C:\P\Work\PalMod\backup)
   - おかしかったらpakを消せば即バニラに戻る

確認ポイント(=官能検査②。①はBlenderプレビューで実施済みの前提):
- テクスチャの乗り方(①はグレー素体なのでここが初見)
- **アニメーション時の変形**: 走り・騎乗・しゃがみ・攻撃。チビ体型ゆえ関節位置がパル骨格と
  ずれており、静止プレビューでは原理的に判定できない項目。ここが本MOD最大の未知数
- 頭・髪が二重になっていないか(ダミー化が効いているか)
- 接地、カメラ距離感

## 4. 全ティア展開(3のテストが通ってから!)

1. Pythonコンソールで `C:\P\Work\PalMod\ue_scripts\02_duplicate_tiers.py`
2. `package_mod.ps1` を再実行 → pak差し替え
3. 各防具を着てゲーム内確認

## 詰まったら

- スクリプトのエラーはOutput Logの全文をClaudeに貼る
- パッケージ失敗のログは「基本的に役に立たない」(ガイド著者談)ので、これもClaudeへ
- 見た目の色味・質感が不満 → M_PGF_* マテリアルはただの土台なので、UE上でいくらでも調整可。
  トゥーン感が欲しくなったらVRM経路(lilToon→MToon変換→VRM4U)への切替を相談
