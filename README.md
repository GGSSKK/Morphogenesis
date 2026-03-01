# Morphogenesis

**胚発生型プロシージャル形態生成システム**

セルオートマトン、L-System、拡散反応パターン、遺伝的アルゴリズムを統合し、
プロシージャルに生物的形態を生成するプロジェクト。

## 起源

本プロジェクトは [GA_Playground](https://github.com/GGSSKK/GA_Playground)（2014-2015年頃、Unity 5 + PlayMaker）の
知見を最新技術で復活させる試みです。

GA_Playground では Unity PlayMaker のビジュアルスクリプティングのみで
以下の2つのプロトタイプを実装していました:

1. **物理ジョイント連鎖ヘビ型クリーチャー** — ConfigurableJoint の角度制限+減衰による波動伝播
2. **遺伝子駆動ルールベース形態生成** — 4bit条件+4bitアクションの遺伝子文字列によるセルオートマトン的パターン生成

詳細な分析は [`docs/`](docs/) を参照。

## ドキュメント

| ファイル | 内容 |
|---|---|
| [`docs/GA_PLAYGROUND_ANALYSIS.md`](docs/GA_PLAYGROUND_ANALYSIS.md) | GA_Playground 完全分析（FSMロジック、状態遷移、パラメータ値） |
| [`docs/REACTION_DIFFUSION_PATTERN.md`](docs/REACTION_DIFFUSION_PATTERN.md) | 拡散反応パターン詳細分析（条件-アクション対応表、リズム生成メカニズム） |
| [`docs/DESIGN_LINEAGE.md`](docs/DESIGN_LINEAGE.md) | 設計系譜（胚発生型GA論文からの影響、4つの理論の統合） |

## 理論的背景

本プロジェクトが統合する4つの理論:

| 理論 | 役割 |
|---|---|
| **遺伝的アルゴリズム (GA)** | 遺伝子文字列のランダム生成・選択・交叉・突然変異 |
| **セルオートマトン (CA)** | 近傍セルの状態を参照して自セルの状態を更新するルール |
| **L-System** | 文字列書き換えルールによる再帰的構造生成 |
| **拡散反応パターン (RD)** | 活性化因子と抑制因子の相互作用によるパターン形成 |

## ライセンス

MIT License
