# Rig Controller Shape Tool

MayaのNURBS Curveコントローラを非破壊Previewしながら編集するTA向けツールです。Uniform Scale、Scale、Rotate、Move、Line Width、Color、Copy/Paste Replace/Add、Disconnectを提供します。

## Environment

- Autodesk Maya 2026
- Python 3
- PySide6（Maya同梱版）

## Install

フォルダを次の位置へ配置します。

```text
<Maya userAppDir>/scripts/rig_ctrl_shape_tool/
```

通常起動：

```python
from rig_ctrl_shape_tool.app import show
show()
```

### Shelf command

```python
import os
import runpy
import maya.cmds as cmds

maya_dir = os.path.normpath(cmds.internalVar(userAppDir=True))
launch_file = os.path.join(maya_dir, "scripts", "rig_ctrl_shape_tool", "launch.py")
runpy.run_path(launch_file, run_name="__main__")
```

`launch.py`は通常起動専用です。開発中にモジュールを再読込する場合だけ`dev_launch.py`を実行してください。

## Architecture

```text
UI (PySide6)
    ↓ Featureの公開API / Domain View Data
Feature（Use Case）
    ↓ Serviceの公開API / Domain Model
Service（Maya境界）
    ↓
Maya API（maya.cmds / OpenMaya）
```

依存方向は常に上から下です。UIとFeatureは`maya.cmds`、`maya_utils`、OpenMayaをimportしません。`app.py`だけがComposition Rootとして具象Serviceを生成し、FeatureとWindowへ注入します。

```text
rig_ctrl_shape_tool/
├─ launch.py                 通常起動
├─ dev_launch.py             開発時の再読込起動
├─ app.py                    Composition Root
├─ state.py                  アプリケーション実行時状態
├─ domain.py                 Maya／Qt非依存の値オブジェクト
├─ sessions.py               編集Session状態遷移
├─ logic.py                  Maya非依存の計算
├─ maya_utils.py             Maya共通Query／Context Manager
├─ curve_io.py               Curve永続化Adapter
├─ connections.py            Connection Adapter
├─ features/                 Use Case
├─ services/                 Maya境界Facade
├─ ui/                       Widget／Layout／Signal
└─ tests/                    Pure／Maya統合／UI回帰テスト
```

`curve_io.py`と`connections.py`は低水準のMaya Adapterです。Featureはこれらを直接呼ばず、`CurveService`と`ConnectionService`を通して利用します。

## Domain

| 型 | 表現するもの |
|---|---|
| `TransformValues` | Uniform、Scale、Rotate、Move、Line Widthの入力値 |
| `CurveShapeData` | CV、Weight、Knot、Degree、Form、Rational、Dimension、Spanを含むCurve定義 |
| `DisplaySettings` | Shapeに実在した表示属性のスナップショット |
| `ColorValue` | Index／RGBの表示色 |
| `ColorOverrideState` | Maya Override Colorの完全な復元状態 |
| `ColorViewData` | UIへ渡す初期色とCurrent Colors |
| `PlugConnection` | Source PlugとDestination Plugの接続 |
| `SessionStatus` | Idle／Active／Committed／Rolled Backの状態 |

`DisplaySettings`は固定フィールドではなく、`(attribute, value)`の不変スナップショットです。Mayaのノード種別、バージョン、プラグインによって利用可能な表示属性が異なるため、存在して読み取れた属性だけを保存します。これにより、新しい表示属性を追加してもDomain型とFeatureを変更せず、Adapter側の属性一覧だけを拡張できます。

## Features

| Feature | 責務 | 主な公開API |
|---|---|---|
| `TransformFeature` | CV座標編集、Line Width適用、+90操作 | `apply()`, `apply_value()`, `rotate_x_90()`など |
| `PreviewFeature` | 非破壊PreviewとSession管理 | `begin()`, `update_preview()`, `commit()`, `rollback()` |
| `ColorFeature` | Color Preview、確定、復元 | `begin_edit()`, `update_preview()`, `commit()`, `rollback()`, `reset()` |
| `CopyPasteFeature` | Copy Buffer、Replace、Add | `copy()`, `paste_replace()`, `paste_add()` |
| `DisconnectFeature` | Connection取得、解除、復元 | `disconnect_selected()`, `restore_connections()` |
| `ControlsFeature` | 数値状態の更新とReset | `update()`, `reset()`, `reset_axis()`, `reset_all()` |

Featureは操作順序、選択検証、Session、Undo境界を担当します。Mayaノードの具体的な読書きはServiceへ委譲し、WidgetやDialogの終了処理は知りません。

## Design Decisions

### UIからMaya APIを呼ばない

UIはWidget生成、Layout、Signal接続、Qt値への変換だけを担当します。Maya APIを呼ばないことで、画面構築をoffscreenで検証でき、UI変更がシーン編集を壊す範囲を限定できます。

### Featureを機能単位に分ける

Transform、Preview、Color、Copy/Paste、Disconnectは、選択条件、Undo単位、失敗時の復元方法が異なります。Featureを分けることで、それぞれのUse Caseを独立して変更・テストできます。Feature同士は実装を呼び合わず、共有するMaya操作はServiceを利用します。

### Typed domain data

Curve、表示設定、Color、Connectionを匿名辞書で運ばず、不変Domain Modelで表現します。レイヤー間の契約が明確になり、Maya APIの戻り値形式やQt型がFeatureへ漏れません。`QColor`との変換はUI境界だけで行います。

### Stateを独立させる

入力値、Preview Capture、Color Session、Copy Buffer、Window Jobは`ToolState`が所有します。モジュールグローバルを使わないため、Window再生成時に状態を破棄でき、テストごとに独立したStateを注入できます。

### Serviceを挟む

ServiceはFeatureが必要とする操作語彙へMaya APIを変換する薄いFacadeです。FeatureはDAG Long Name、Curve Shape Query、Selection復元、Undo実装の詳細を意識しません。抽象InterfaceやRepository基底クラスは設けず、小規模ツールに必要な具象Serviceだけを使用しています。

### Edit sessions

PreviewとColorは同じ`EditSessionLifecycle`を正式採用しています。

```text
Idle / Committed / Rolled Back
            ↓ begin
          Active
       ↙           ↘
   commit         rollback
      ↓               ↓
 Committed        Rolled Back
```

Close、別編集開始、例外時にはActive SessionをRollbackし、Undo Chunkを必ず閉じます。ColorとTransform Previewは同時にActiveにしません。Featureは状態遷移だけを通知し、Dialogを閉じる責務はUIが持ちます。

### Undo and selection

短い編集は`MayaSceneService.undo_chunk()`を使用します。Context Manager化により、途中で例外が発生してもUndo Chunkを閉じ忘れません。Copy/PasteはService経由の`preserve_selection()`で既存選択を可能な限り復元します。Preview／Colorの長時間Sessionだけは、ユーザー操作をまたぐため明示的にUndoをOpen／Closeします。

### Error boundary

ユーザー操作で回復できる問題は`RigCtrlShapeToolError`派生例外で表現し、Window境界でWarningへ変換します。予期しない例外をFeatureで一括して握り潰しません。

### 過剰設計を避ける

DI Container、Factory、抽象Repository、Interface階層、イベントバスは採用していません。Composition Rootで具象依存を明示的に組み立て、共通化はPreview／Colorで実際に共有するSession遷移に限定しています。小規模なMayaツールとして追跡しやすさを優先した構成です。

## Extension

### Mirror

Mirror計算を`logic.py`、選択検証と操作順序を`MirrorFeature`、CV書込みを`MayaSceneService`へ配置します。UIはFeatureの公開APIへSignalを接続します。

### Preset

Curve定義と表示設定の保存形式をDomainとして追加し、ファイルI/Oを新しい`PresetService`へ配置します。適用手順は`PresetFeature`が担当します。UIから直接JSONやMayaノードを操作しません。

### Constraint

Constraint作成・Queryを専用Serviceへ、選択条件とUndo単位を`ConstraintFeature`へ配置します。既存`ConnectionService`は一般Plug接続だけを担当させ、Constraint固有処理を混在させません。

## Tests

Maya付属Pythonで実行する例：

```powershell
mayapy -m unittest rig_ctrl_shape_tool.tests.test_domain -v
mayapy -m unittest rig_ctrl_shape_tool.tests.test_maya_integration -v
mayapy -m unittest rig_ctrl_shape_tool.tests.test_ui -v
```

純粋テスト対象：Color Clamp、項目単位Transform値、Edit Sessionの二重開始、Inactive Commit防止。

Maya統合テスト対象：複数Shape、Periodic／Rational Curve、Replace、Add Connection移行、Referenced拒否、Locked失敗Rollback、Selection復元、Preview／Color Commit・Rollback、Undo／Redo。

UI回帰テスト対象：右クリック対象表示、項目単位Apply・Reset表記、カーソル桁別ステップ、Color DialogのCurrent Colors・Apply・Cancel、複数Window検出、Close通知ライフサイクル。

## Preserved behavior

- Real Time Preview、Preview ON/OFF
- Applyまで未確定、CloseでRollback
- Uniform／Scale XYZ／Rotate XYZ／Move XYZ／+90
- Shape中心を一時PivotにしたCV Scale／Rotate
- 数値欄右クリックの項目別Apply／Reset
- Copy、Paste Replace、Paste Add
- Color Preview／Apply／Cancel／Preset
- Override Color／Display設定／Connection移行
- Disconnect、Undo、Selection復元
- 多重Window防止

## Maya GUIで確認する項目

Viewport上の操作感、Current ColorsのUndo／Redo直後の再描画、Color Dialogの配置、Shelfからの通常起動、複数Windowの視覚確認をMaya 2026 GUIで確認してください。Scene処理はMaya統合テストで自動検証されています。
