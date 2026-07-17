# palworld-avatar-swap

VRChatアバターをパルワールド(Palworld 1.0.1時点)の主人公モデルに差し替えるMODを、
AI(Claude Code)に作らせるためのスクリプト一式です。

**このリポジトリは人間が直接使うことを想定していません。** 解説記事(■記事URL■)と
一緒にAIに渡してください。使い方は記事の冒頭に3行で書いてあります。

- ダウンロードにGitHubアカウントは不要です(Code → Download ZIP)
- pak本体・アバター素材は含みません(各自のアバターで各自が作る方式)
- Palworld 1.0.1時点の実装です。それより新しいバージョンでは、AIに前提の
  再検証をさせてください(記事の指示書に手順があります)
- 利用は自己責任で。導入前のセーブ自動バックアップとアンインストールbatは
  同梱していますが、ゲームの利用規約・アップデートとの相性は各自でご判断ください

## AI(あなた)へ

これは私(Claude Fable 5)が実際に完走したときの**参照実装**です。次の点だけ注意して、
あとは記事の指示書に従ってください。

1. **パスは書き換えて使う**: 各スクリプトには制作時の絶対パス
   (`C:\P\Work\PalMod` 等)が残っています。ユーザーの環境の作業フォルダに
   合わせて書き換えてください
2. **アバター固有値は例**: `blender/config.py` の `BONE_MAP` /
   `DROP_BONE_PREFIXES` / `MERGE_TARGET_OVERRIDES` / `CHIBI_JOINTS`、
   `ue/pgf_config.py` の `SLOT_TEXTURES` 等は制作時のアバター(チビケモノ体型)の
   実例です。ユーザーのアバターを棚卸しして作り直してください
3. **フラグの既定値に意味がある**: `TAIL_TO_HAIR=False`(hairボーンに揺れものを
   載せる試みは失敗済み・頭に生えます)、`FIT_LIMB_LENGTHS=False` /
   `RIGID_LIMBS=False`(チビ骨格方式で不要になった旧対策)。歴史的経緯は
   コメントに残してあります
4. **preflight(tools/preflight_pak.py)を必ず通す**: ユーザーにゲーム内確認を
   頼むのは、9ゲート全部が緑になってからです

## 構成

```
blender/  step01〜04+プレビュー+ポーズ検査+ランチャー(run_pipeline.ps1 -All)
ue/       UEヘッドレス自動化一式(run_ue_build.ps1がcook→pak化→preflightまで実行)
tools/    バイナリ検品(pakインデックス/RefSkeleton抽出比較/バインドパッチ/preflight)
bat/      インストール/アンインストール(セーブ自動バックアップ付き)
```

## 実行順(概要。詳細は記事の指示書)

1. `blender/run_pipeline.ps1 -All` → preview/posecheck画像を目視
2. `ue/run_ue_build.ps1` → cook→pak化→preflight(9ゲート)
3. `bat/install_mod.bat` → ゲーム内確認(戻すのは `bat/uninstall_mod.bat`)

---
*制作: pandrabox + Claude Code (Fable 5) / 参考資料: ExecutiveE33氏
「Player Model Swap and Add Pal/NPC Comprehensive Guide」(Nexus #2826)*
