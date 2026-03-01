# GA_Playground 完全分析

**対象リポジトリ**: https://github.com/GGSSKK/GA_Playground
**プラットフォーム**: Unity 5 系（2014-2015年頃）
**ビジュアルスクリプティング**: PlayMaker + PlayMaker ArrayMaker

---

## 1. リポジトリ概要

プロシージャルなクリーチャー（生物体）生成システムの初期プロトタイプ。
2つのシーンでそれぞれ異なるアプローチを実験している。

## 2. アセット構成

### プレファブ

| プレファブ | コンポーネント | 用途 |
|---|---|---|
| **SegmentCube** | MeshFilter(Cube), MeshRenderer, CapsuleCollider, Rigidbody(mass=0.1, useGravity=false), ConfigurableJoint, PlayMakerFSM("Mover") | 物理ジョイントで連結する体節パーツ |
| **SegmentCube_Simple** | MeshFilter(Cube), MeshRenderer, BoxCollider | 見た目だけの体節（物理なし） |

**SegmentCube の ConfigurableJoint 設定**:
- XYZ移動: Locked
- 角度回転: Limited (±60° XY, ±20° Z)
- AngularDamper: 0.1
- 体節間で自然なうねりが出る設定

### カスタム PlayMaker アクション

**DrawLine.cs** — LineRenderer で2点間にラインを描画。実際の FSM では未使用（デバッグ用）。

---

## 3. 01Test.unity — 物理ジョイント連鎖ヘビ型クリーチャー

### シーン構成

- **Main Camera** — Generator FSM
- **SegmentCube 1 Head** — HeadController FSM + PlayMakerArrayListProxy("Segments")
- **SegmentCube 2~4** — 初期配置済み体節
- **Plane** — 地面（MeshCollider）

### FSM 1: Generator（Main Camera 上）

**意図**: SegmentCube プレファブを動的に生成し、ConfigurableJoint で数珠つなぎにして蛇/ミミズ型の物理連鎖体を構築する。

#### 変数

| 変数名 | 型 | 初期値 | Inspector公開 | 説明 |
|---|---|---|---|---|
| `segmentNum` | int | 20 | ✓ | 生成する体節数 |
| `segmentScale` | Vector3 | (1, 0.5, 0.15) | ✓ | 各体節のスケール |
| `headPosition` | Vector3 | (0, 10, 0) | ✓ | 頭部初期位置 |
| `segmentsArrayName` | string | "segmentsArray" | | ArrayListProxy参照名 |
| `currentSegment` | GameObject | — | | 現在処理中の体節 |
| `headSegment` | GameObject | — | | 頭部体節 |
| `prevSegment` | GameObject | — | | 一つ前の体節 |
| `positionOffset` | float | 0 | | Y方向配置オフセット |
| `segmentScaleY` | float | 0 | | segmentScaleのY成分 |

#### 状態遷移フロー

```
[Create Head] → [init] → [Count Segments] ←LOOP→ [Create Body]
                               ↓ FINISHED              ↓
                          [Wait 0.1s]           [Get Prev Segment Info]
                               ↓                       ↓
                        [ActivateLoop]           [Set Transform]
                          ↓ LOOP    ↓ FINISHED          ↓
               [Deactivate     [Done]            [Setup Joint]
                Kinematic]                             ↓
                    ↓                            [Count Segments]
              [Set Next Segment]
                    ↓
              [ActivateLoop]
```

#### 各ステートの詳細

1. **Create Head** — 頭を生成し管理用配列を付与
   - SegmentCube プレファブをインスタンス化 → `headSegment`
   - Kinematic = true（物理抑制）
   - ArrayList "segmentsArray" を headSegment 上に作成
   - headSegment 自身を配列に追加
   - segmentScale (1, 0.5, 0.15) を適用
   - ConfigurableJoint を削除（頭は接続先不要）
   - "head" と命名

2. **init** — 一度でいい計算
   - segmentScale の Y 成分 → segmentScaleY
   - segmentScaleY × -1.0 → positionOffset（下方向オフセット）

3. **Count Segments** — セグメント数カウント → 分岐
   - segmentsArray の要素数を取得
   - segmentNum(20) と比較
   - 等しい → Wait（完了） / 小さい → Create Body（続行）

4. **Create Body** — 新体節を生成
   - SegmentCube プレファブをインスタンス化 → `currentSegment`
   - Kinematic = true
   - segmentsArray に追加
   - segmentScale を適用

5. **Get Prev Segment Info** — 前体節の位置を取得
   - currentSegmentNum - 1 → prevSegmentIndex
   - segmentsArray[prevSegmentIndex] → prevSegment
   - prevSegment の位置を取得

6. **Set Transform** — スケールと発生位置を調整
   - prevSegment の位置に positionOffset を加算（Y方向にずらす）
   - currentSegment をその位置に配置

7. **Setup Joint** — Joint へ一つ前の体節を設定
   - prevSegment から Rigidbody を取得
   - currentSegment から ConfigurableJoint を取得
   - joint.connectedBody = prevSegment の Rigidbody

8. **Wait** — 物理よ落ち着け
   - 0.1秒待機（全体節生成後の物理安定化）

9. **ActivateLoop** — 全体節をイテレーション
   - ArrayListGetNext で順次処理
   - 全完了 → Done

10. **Deactivate Kinematic** — Kinematic 解除
    - currentSegment の Kinematic = false（物理有効化）

11. **Set Next Segment** — 各体節の Mover FSM に隣接参照を注入
    - currentSegmentIndex + 1 → nextSegmentIndex
    - segmentsArray[nextSegmentIndex] → nextSegment
    - currentSegment の "Mover" FSM の `nextSegment` 変数に設定

12. **Done** — 頭部の自律行動を起動
    - headSegment の "Mover" FSM を有効化
    - headSegment に "ACTIVATE" イベントを送信

**Generator の全体ロジック要約**:
1. 頭部生成 → 管理用ArrayList作成
2. Y方向オフセット計算（体節間距離）
3. 20体節をループ生成: 新体節 → 前体節の直下に配置 → ConfigurableJoint で連結
4. 0.1秒待機 → 全体節の Kinematic 解除（物理シミュレーション開始）
5. 各体節の Mover FSM に nextSegment 参照を注入
6. 頭部の Mover FSM 起動

---

### FSM 2: HeadController（SegmentCube 1 Head 上）

**意図**: 頭部体節を Easing 関数でX方向に左右往復移動させ、ジョイント連鎖で全身がうねる蛇運動を生む。

#### 変数

| 変数名 | 型 | 初期値 | Inspector公開 | 説明 |
|---|---|---|---|---|
| `_pos` | float | 0 | ✓ | 現在の Ease 位置 |
| `delay` | float | 0.5 | ✓ | 往復間の待機時間 |
| `moveAmount` | float | 0.5 | ✓ | X方向移動量 |
| `moveAmountMinus` | float | 0 | | 逆方向移動量（計算で求める） |
| `moveTime` | float | 1.0 | ✓ | Ease の所要時間 |

#### 状態遷移フロー

```
[init] → [List Joints] ←LOOP→ [Create Joints Array]
              ↓ FINISHED
        [initialize] → [State 1: 右移動] ←→ [State 2: 左移動]
```

#### 各ステートの詳細

1. **init** — "segmentsJointArray" を作成
2. **List Joints** — "Segments" 配列を順次イテレーション → Create Joints Array
3. **Create Joints Array** — 各体節の ConfigurableJoint を "segmentsJointArray" に収集
4. **Pulsar** — 空ステート（未使用パス）
5. **Delay** — 0.5秒待機
6. **initialize** — moveAmountMinus = moveAmount × -1.0
7. **State 1** — EaseFloat: -0.5 → +0.5（EaseType=14: EaseInOutSine）、毎フレーム SetPosition(X)
8. **State 2** — EaseFloat: +0.5 → -0.5（逆方向）、毎フレーム SetPosition(X)
9. **State 3** — 孤立ステート（未使用）

**HeadController の全体ロジック要約**:
- 全体節の ConfigurableJoint を配列に収集
- EaseInOutSine で頭部を X: -0.5 ↔ +0.5 で滑らかに往復
- ConfigurableJoint の角度制限(±60°)+減衰(0.1)が波動的に後方伝播 → 蛇のうねり

---

## 4. 02Test.unity — 遺伝子駆動ルールベース形態生成

### シーン構成

- **Main Camera** — FSM なし
- **CreatorObj** — SegmentCreator FSM（SphereCollider + Rigidbody）

### FSM: SegmentCreator（CreatorObj 上）— 32ステート

**意図**: L-System に着想を得た遺伝子文字列に基づくルールベースのプロシージャル形態生成。
4bit バイナリコードの「条件」と「アクション」のペアからなるルール列を解釈し、
条件に基づいて体節の形状（スケール）・位置・マテリアルを決定する。

**FSM 内メモ（原文）**:
> TODO:
> - 付属肢の生成を考えると、実際の細胞のように各節それぞれに次節生成機構を持たせた方が良いかも。
> - 上記: 節クラスターの発生機構、クラスターの頭は親節を見る

#### 変数

| 変数名 | 型 | 初期値 | Inspector公開 | 説明 |
|---|---|---|---|---|
| `ruleNum` | int | 20 | ✓ | 1体あたりのルール数 |
| `segmentsMaxNum` | int | 30 | ✓ | 最大体節数 |
| `segmentCount` | int | 0 | | 生成済み体節数 |
| `ruleNumCurrent` | int | 0 | | 現在のルール番号 |
| `segmentN-1Index` | int | 0 | | N-1体節のインデックス |
| `segmentN-2Index` | int | 0 | | N-2体節のインデックス |
| `segmentN-1PosX` | float | 0 | | N-1体節のX座標 |
| `segmentN-1X` | float | 0 | | N-1体節のXスケール |
| `segmentN-2X` | float | 0 | | N-2体節のXスケール |
| `segmentNPosX` | float | 0 | | 現体節のX座標 |
| `segmentNX` | float | 0 | | 現体節のXスケール |
| `gene` | string | "" | ✓ | 遺伝子文字列 |
| `currentRule` | string | "" | | 現在処理中のルール |
| `currentCondition` | string | "" | | 条件部分（4bit） |
| `currentAction` | string | "" | | アクション部分（4bit） |

#### 遺伝子フォーマット

```
[条件4bit][アクション4bit] / [条件4bit][アクション4bit] / ...  (20ルール)

例: 00010100/01110000/00001111/...
```

遺伝子はランダム生成される（`random gene generator` ステート）。
条件・アクション共に8種の中から均等確率（weight = 1.0）で選択。

#### 状態遷移フロー

```
[Init] → [Reset] → [random gene generator] ←→ [Count Rules] ←→ [Add Separator]
                                                    ↓ 全ルール生成完了
           [Show Gene] → [Create Holder] → [Setup Arrays] → [Create Head Segment]
                                                                    ↓
     ┌──────────────────────── [Apply Next Rule] ←───────────────────┐
     ↓ 次ルールあり                    ↓ 全ルール消化               │
[Rule m Condition]              [Count Segments Num]                 │
  ↓ is0000〜is0111               ↓ < max         ↓ = max           │
[Condition 1〜8]            [Create Next]    [All Segments Created]  │
  ↓ TRUE      ↓ FALSE         → [SetName]                           │
[Rule m Action]  ──→             → [Check Prev Exists]              │
  ↓ is0000〜is1111                 → [Set Scale & Position] ────────┘
[Action 1〜8] ──────────────────────────────────────────────────────┘
```

#### 詳細は [REACTION_DIFFUSION_PATTERN.md](REACTION_DIFFUSION_PATTERN.md) を参照

02Test の核心は拡散反応パターン的な条件-アクションシステムにある。
全8条件・全8アクションのパラメータ値と相互作用の分析は別ドキュメントに記載。

---

## 5. 二つのシーンの比較

| 項目 | 01Test | 02Test |
|---|---|---|
| **アプローチ** | 固定数ループ（線形連鎖） | 遺伝子駆動ルールベース |
| **プレファブ** | SegmentCube（物理あり） | SegmentCube_Simple（物理なし） |
| **物理** | ConfigurableJoint 連鎖 | なし |
| **動的挙動** | Ease 往復 → 全身うねり | 生成のみ（動きなし） |
| **FSM数 / ステート数** | 2 FSM / 計21ステート | 1 FSM / 32ステート |
| **ランダム要素** | パラメータのみ | 遺伝子文字列全体 |
| **データ構造** | ArrayList（体節配列） | ArrayList×2（ルール配列+体節配列） |

## 6. 使用プラグイン

- **PlayMaker** — ビジュアルスクリプティングエンジン
- **PlayMaker ArrayMaker** — ArrayList/HashTable データ構造
- **PlayMaker Quaternion Actions** — Quaternion 操作カスタムアクション群
- **PlayMaker Utils** — ユーティリティ（イベント送受信等）
- **iTween for PlayMaker** — iTween Easing 統合
- **Candlelight Custom Handles** — エディタカスタムハンドル
