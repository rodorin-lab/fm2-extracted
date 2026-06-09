# 🔧 Front Mission 2 Remake — アセット抽出ツール

![Status](https://img.shields.io/badge/status-%E5%AE%8C%E6%88%90-brightgreen) ![Game](https://img.shields.io/badge/target-Front%20Mission%202%20Remake-red)

**フロントミッション2 リメイク** のUnityアセットから **Wanzer（ヴァンツァー）3Dモデルを抽出** するツール群だよ！

## 🎯 できること

- 🔍 **フェーズ1: スキャン** — 2,313個の `.bundle` ファイルを全走査
  - Meshを含むbundleを特定
  - Wanzer関連ファイルを自動分類
  - メモリ監視 + GC で安全処理
- 📦 **フェーズ2: 抽出** — 特定したbundleからアセット抽出
- 🎨 **フェーズ3: テクスチャ** — テクスチャファイルの分離・変換

## 🚀 使い方

```bash
# フェーズ1: スキャン
python3 phase1_scan.py

# フェーズ2: 抽出
python3 phase2_extract.py

# フェーズ3: テクスチャ
python3 phase3_textures.py
```

## 📊 スキャン結果

`scans/` ディレクトリにチェックポイント付きJSONで保存。
途中で止めても再開可能！

```
scans/
├── phase1_summary.json       # 全体サマリー
├── phase1_wanzers_final.json # Wanzer最終リスト
└── phase1_wanzers_chk_*.json # チェックポイント
```

## ⚠️ 注意

- Unityアセットの抽出は個人利用・研究目的に限定
- `BUNDLE_DIR` のパスを環境に合わせて変更してください

## 🛠 技術

- Python 3 + JSON
- Unity Bundle構造解析
- メモリ効率化（GC + 分割処理）

## 📝 作者

- **ロドリン** & **シンクロ（グラム）** 💎🛸
- rodorin-lab © 2026
