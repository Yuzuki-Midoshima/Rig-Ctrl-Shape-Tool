# Rig Controller Shape Tool

Autodesk Maya 2026向けの、リグ用NURBSカーブコントローラー編集ツールです。形状・色・トランスフォーム・接続を、元のTransformやリグ構造を壊さずに調整できます。

## Features

- Shape CVの移動・回転・スケール
- Local／World軸の切り替え
- XYZ軸の個別制御
- 操作中のプレビュー、確定、ロールバック
- Index Color／RGB Colorの編集
- Shapeのコピー＆ペースト
- Shape接続の安全な切り離し
- Maya Undo、選択状態、ウィンドウライフサイクルの管理

## Requirements

- Autodesk Maya 2026
- Python 3.11
- PySide6（Maya同梱版）

## Installation

`rig_ctrl_shape_tool`フォルダをMayaのユーザースクリプトフォルダへ配置します。

```text
<Maya userAppDir>/scripts/rig_ctrl_shape_tool/
```

## Launch

Maya Script EditorのPythonタブ、またはPythonシェルフから実行します。

```python
from rig_ctrl_shape_tool.app import show
show()
```

長時間起動しているMayaで更新後のソースを読み直す場合は、`launch.py`をシェルフコマンドとして使用できます。

## Project Structure

```text
rig_ctrl_shape_tool/
├── core/       # Maya非依存のデータ、状態、計算、例外
├── features/   # ユーザー操作単位のユースケース
├── maya/       # Maya API境界とCurveデータ変換
├── services/   # 選択、Scene、Color、Connection管理
├── ui/         # PySide6 Widgetとスタイル
├── tests/      # Domain、Maya統合、UI回帰テスト
├── app.py      # Dependency構築とWindow生成
└── launch.py   # Mayaシェルフ用エントリーポイント
```

## Architecture

UIからMaya APIを直接呼ばず、`features`が操作を調整し、`services`と`maya`がDCC固有処理を担当します。Maya非依存の状態と計算は`core`へ分離しているため、責務の境界が明確で、機能追加やテストを局所化できます。

```text
UI → Features → Services → Maya API
       ↓
      Core
```

プレビューとカラー編集はSessionとして扱い、確定前の値を保持します。選択変更、別操作、ウィンドウ終了時には明示的にCommitまたはRollbackされます。

## Testing

Maya 2026の`mayapy`から実行します。

```powershell
mayapy -m unittest rig_ctrl_shape_tool.tests.test_domain -v
mayapy -m unittest rig_ctrl_shape_tool.tests.test_maya_integration -v
mayapy -m unittest rig_ctrl_shape_tool.tests.test_ui -v
```

## Design Notes

- 変更理由ごとにパッケージを分割
- MayaオブジェクトとUI状態をTyped Domain Dataへ変換
- Preview操作をトランザクションとして管理
- ユーザー向けエラーと予期しない障害を区別
