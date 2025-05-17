# ros2-mcp-server

`ros2-mcp-server` is a Python-based server that integrates the Model Context Protocol (MCP) with ROS 2, enabling AI assistants to control robots via ROS 2 topics. It processes commands through FastMCP and runs as a ROS 2 node, publishing `geometry_msgs/Twist` messages to the `/cmd_vel` topic to control robot movement.

This implementation supports commands like "move forward at 0.2 m/s for 5 seconds and stop," with the `/cmd_vel` publisher named `pub_cmd_vel`.

## Features
- **MCP Integration**: Uses FastMCP to handle commands from MCP clients (e.g., Claude).
- **ROS 2 Native**: Operates as a ROS 2 node, directly publishing to `/cmd_vel`.
- **Time-Based Control**: Supports duration-based movement commands (e.g., move for a specified time and stop).
- **Asynchronous Processing**: Combines FastMCP's `asyncio` with ROS 2's event loop for efficient operation.

## Prerequisites
- **ROS 2**: Humble distribution installed and sourced.
- **Python**: Version 3.10 (required for compatibility with ROS 2 Humble).
- **uv**: Python package manager for dependency management.
- **Dependencies**:
  - `rclpy`: ROS 2 Python client library (installed with ROS 2).
  - `fastmcp`: FastMCP framework for MCP server implementation.
  - `numpy`: Required by ROS 2 message types.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/kakimochi/ros2-mcp-server.git
   cd ros2-mcp-server
   ```

2. **Python Version Configuration**:
   This project uses Python 3.10 as required by ROS 2 Humble. The `.python-version` file is already configured:
   ```bash
   # .python-version content
   3.10
   ```

3. **Project Dependencies**:
   The `pyproject.toml` file is configured with the necessary dependencies:
   ```toml
   # pyproject.toml content
   [project]
   name = "ros2-mcp-server"
   version = "0.1.0"
   description = "ROS 2 MCP Server"
   readme = "README.md"
   requires-python = ">=3.10"
   dependencies = [
       "fastmcp",
       "numpy",
   ]
   ```

4. **Create uv Environment**:
   ```bash
   uv venv --python /usr/bin/python3.10
   ```

5. **Activate the Virtual Environment**:
   ```bash
   source .venv/bin/activate
   ```
   You'll see `(.venv)` appear at the beginning of your command prompt, indicating that the virtual environment is active.

6. **Install Dependencies**:
   ```bash
   uv pip install -e .
   ```

## MCP Server Configuration

To use this server with Claude or other MCP clients, you need to configure it as an MCP server. Here's how to set it up:

### For Claude Desktop

1. Open Claude Desktop settings and navigate to the MCP servers section.
2. Add a new MCP server with the following configuration:
   ```json
   "ros2-mcp-server": {
     "autoApprove": [],
     "disabled": false,
     "timeout": 60,
     "command": "uv",
     "args": [
       "--directory",
       "/path/to/ros2-mcp-server",
       "run",
       "bash",
       "-c",
       "export ROS_LOG_DIR=/tmp && source /opt/ros/humble/setup.bash && python3 /path/to/ros2-mcp-server/ros2-mcp-server.py"
     ],
     "transportType": "stdio"
   }
   ```
   
   **Important**: Replace `/path/to/ros2-mcp-server` with the actual path to your repository. For example, if you cloned the repository to `/home/user/projects/ros2-mcp-server`, you would use that path instead.

3. Save the configuration and restart Claude.

### For Cline (VSCode Extension)

1. In VSCode, open the Cline extension settings by clicking on the Cline icon in the sidebar.
2. Navigate to the MCP servers configuration section.
3. Add a new MCP server with the following configuration:
   ```json
   "ros2-mcp-server": {
     "autoApprove": [],
     "disabled": false,
     "timeout": 60,
     "command": "uv",
     "args": [
       "--directory",
       "/path/to/ros2-mcp-server",
       "run",
       "bash",
       "-c",
       "export ROS_LOG_DIR=/tmp && source /opt/ros/humble/setup.bash && python3 /path/to/ros2-mcp-server/ros2-mcp-server.py"
     ],
     "transportType": "stdio"
   }
   ```
   
   **Important**: Replace `/path/to/ros2-mcp-server` with the actual path to your repository, as in the Claude Desktop example.

4. You can immediately toggle the server on/off and verify the connection directly from the Cline MCP settings interface without needing to restart VSCode or reload the extension.

## Usage

Once the MCP server is configured, you can use Claude to send commands to the robot:

1. **Example Command**:
   Ask Claude to move the robot forward at 0.2 m/s for 5 seconds:
   ```
   Please make the robot move forward at 0.2 m/s for 5 seconds.
   ```

2. **Direct Tool Usage**:
   You can also use the `move_robot` tool directly:
   ```json
   {
     "linear": [0.2, 0.0, 0.0],
     "angular": [0.0, 0.0, 0.0],
     "duration": 5.0
   }
   ```

3. **Monitor ROS 2 Topics**:
   Verify the `/cmd_vel` topic output:
   ```bash
   ros2 topic echo /cmd_vel
   ```

## Testing

1. **With a Simulator**:
   - Launch a ROS 2-compatible simulator (e.g., Gazebo with TurtleBot3):
     ```bash
     export TURTLEBOT3_MODEL=burger
     ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
     ```
   - Use Claude to send movement commands.
   - Observe the robot moving in Gazebo.

2. **With a Real Robot**:
   - Ensure your robot is properly set up to subscribe to the `/cmd_vel` topic.
   - Use Claude to send movement commands.
   - The robot should move according to the commands.

3. **Expected Output**:
   - The server logs movement commands and stop commands.
   - Claude receives a response like: `"Successfully moved for 5.0 seconds and stopped"`.

## Troubleshooting

- **ROS 2 Logging Errors**: If you encounter logging directory errors, ensure the `ROS_LOG_DIR` environment variable is set to a writable directory (e.g., `/tmp`).
- **Python Version Mismatch**: Ensure you're using Python 3.10, as ROS 2 Humble is built for this version.
- **Connection Errors**: If Claude reports "Connection closed" errors, check that the MCP server configuration is correct and that all dependencies are installed.

## Directory Structure
```
ros2-mcp-server/
├── ros2-mcp-server.py  # Main server script integrating FastMCP and ROS 2
├── pyproject.toml      # Project dependencies and metadata
├── .python-version     # Python version specification
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## Limitations
- **Single Topic**: Currently supports `/cmd_vel` with `Twist` messages. Extend `ros2-mcp-server.py` for other topics or services.
- **Basic Commands**: Currently supports simple movement commands. More complex behaviors would require additional implementation.

## License

```
MIT License

Copyright (c) 2025 kakimochi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Note that this project uses [FastMCP](https://github.com/jlowin/fastmcp), which is licensed under the Apache License 2.0. The terms of that license also apply to the use of FastMCP components.

## Acknowledgments
- Built with [FastMCP](https://github.com/jlowin/fastmcp) and [ROS 2](https://docs.ros.org).

---

# ros2-mcp-server

`ros2-mcp-server`は、Model Context Protocol（MCP）とROS 2を統合するPythonベースのサーバーで、AIアシスタントがROS 2トピックを介してロボットを制御できるようにします。FastMCPを通じてコマンドを処理し、ROS 2ノードとして実行され、ロボットの動きを制御するために`geometry_msgs/Twist`メッセージを`/cmd_vel`トピックに発行します。

この実装では、「0.2 m/sで5秒間前進して停止する」などのコマンドをサポートし、`/cmd_vel`パブリッシャーは`pub_cmd_vel`という名前で動作します。

## 機能
- **MCP統合**: FastMCPを使用してMCPクライアント（Claude等）からのコマンドを処理します。
- **ROS 2ネイティブ**: ROS 2ノードとして動作し、`/cmd_vel`に直接発行します。
- **時間ベースの制御**: 時間指定の移動コマンド（例：指定時間移動して停止）をサポートします。
- **非同期処理**: FastMCPの`asyncio`とROS 2のイベントループを組み合わせて効率的に動作します。

## 前提条件
- **ROS 2**: Humbleディストリビューションがインストールされ、ソースされていること。
- **Python**: バージョン3.10（ROS 2 Humbleとの互換性のために必要）。
- **uv**: 依存関係管理のためのPythonパッケージマネージャー。
- **依存関係**:
  - `rclpy`: ROS 2 Pythonクライアントライブラリ（ROS 2と共にインストール）。
  - `fastmcp`: MCPサーバー実装のためのFastMCPフレームワーク。
  - `numpy`: ROS 2メッセージタイプに必要。

## インストール

1. **リポジトリのクローン**:
   ```bash
   git clone https://github.com/kakimochi/ros2-mcp-server.git
   cd ros2-mcp-server
   ```

2. **Pythonバージョンの設定**:
   このプロジェクトはROS 2 Humbleが必要とするPython 3.10を使用します。`.python-version`ファイルは既に設定されています：
   ```bash
   # .python-versionの内容
   3.10
   ```

3. **プロジェクトの依存関係**:
   `pyproject.toml`ファイルには必要な依存関係が設定されています：
   ```toml
   # pyproject.tomlの内容
   [project]
   name = "ros2-mcp-server"
   version = "0.1.0"
   description = "ROS 2 MCP Server"
   readme = "README.md"
   requires-python = ">=3.10"
   dependencies = [
       "fastmcp",
       "numpy",
   ]
   ```

4. **uv環境の作成**:
   ```bash
   uv venv --python /usr/bin/python3.10
   ```

5. **仮想環境のアクティベーション**:
   ```bash
   source .venv/bin/activate
   ```
   コマンドプロンプトの先頭に`(.venv)`が表示され、仮想環境がアクティブであることを示します。

6. **依存関係のインストール**:
   ```bash
   uv pip install -e .
   ```

## MCPサーバーの設定

このサーバーをClaudeや他のMCPクライアントで使用するには、MCPサーバーとして設定する必要があります。設定方法は以下の通りです：

### Claude Desktop向け

1. Claude Desktopの設定を開き、MCPサーバーセクションに移動します。
2. 以下の設定で新しいMCPサーバーを追加します：
   ```json
   "ros2-mcp-server": {
     "autoApprove": [],
     "disabled": false,
     "timeout": 60,
     "command": "uv",
     "args": [
       "--directory",
       "/path/to/ros2-mcp-server",
       "run",
       "bash",
       "-c",
       "export ROS_LOG_DIR=/tmp && source /opt/ros/humble/setup.bash && python3 /path/to/ros2-mcp-server/ros2-mcp-server.py"
     ],
     "transportType": "stdio"
   }
   ```
   
   **重要**: `/path/to/ros2-mcp-server`をリポジトリの実際のパスに置き換えてください。例えば、リポジトリを`/home/user/projects/ros2-mcp-server`にクローンした場合は、そのパスを使用します。

3. 設定を保存し、Claudeを再起動します。

### Cline（VSCode拡張機能）向け

1. VSCodeで、サイドバーのClineアイコンをクリックしてCline拡張機能の設定を開きます。
2. MCPサーバー設定セクションに移動します。
3. 以下の設定で新しいMCPサーバーを追加します：
   ```json
   "ros2-mcp-server": {
     "autoApprove": [],
     "disabled": false,
     "timeout": 60,
     "command": "uv",
     "args": [
       "--directory",
       "/path/to/ros2-mcp-server",
       "run",
       "bash",
       "-c",
       "export ROS_LOG_DIR=/tmp && source /opt/ros/humble/setup.bash && python3 /path/to/ros2-mcp-server/ros2-mcp-server.py"
     ],
     "transportType": "stdio"
   }
   ```
   
   **重要**: `/path/to/ros2-mcp-server`をリポジトリの実際のパスに置き換えてください（Claude Desktopの例と同様）。

4. VSCodeやエクステンションを再起動することなく、Cline MCP設定インターフェースから直接サーバーのオン/オフを切り替えたり、接続を確認したりすることができます。

## 使用方法

MCPサーバーが設定されたら、Claudeを使用してロボットにコマンドを送信できます：

1. **コマンド例**:
   Claudeに0.2 m/sで5秒間前進するよう指示します：
   ```
   ロボットを0.2 m/sで5秒間前進させてください。
   ```

2. **ツールの直接使用**:
   `move_robot`ツールを直接使用することもできます：
   ```json
   {
     "linear": [0.2, 0.0, 0.0],
     "angular": [0.0, 0.0, 0.0],
     "duration": 5.0
   }
   ```

3. **ROS 2トピックの監視**:
   `/cmd_vel`トピックの出力を確認します：
   ```bash
   ros2 topic echo /cmd_vel
   ```

## テスト

1. **シミュレータでのテスト**:
   - ROS 2互換のシミュレータ（例：TurtleBot3を使用したGazebo）を起動します：
     ```bash
     export TURTLEBOT3_MODEL=burger
     ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
     ```
   - Claudeを使用して移動コマンドを送信します。
   - Gazeboでロボットが動くのを観察します。

2. **実機ロボットでのテスト**:
   - ロボットが`/cmd_vel`トピックを購読するように適切に設定されていることを確認します。
   - Claudeを使用して移動コマンドを送信します。
   - ロボットはコマンドに従って動くはずです。

3. **期待される出力**:
   - サーバーは移動コマンドと停止コマンドをログに記録します。
   - Claudeは「Successfully moved for 5.0 seconds and stopped」のようなレスポンスを受け取ります。

## トラブルシューティング

- **ROS 2ロギングエラー**: ロギングディレクトリのエラーが発生した場合は、`ROS_LOG_DIR`環境変数が書き込み可能なディレクトリ（例：`/tmp`）に設定されていることを確認してください。
- **Pythonバージョンの不一致**: ROS 2 HumbleはPython 3.10用に構築されているため、Python 3.10を使用していることを確認してください。
- **接続エラー**: Claudeが「Connection closed」エラーを報告する場合は、MCPサーバーの設定が正しいこと、およびすべての依存関係がインストールされていることを確認してください。

## ディレクトリ構造
```
ros2-mcp-server/
├── ros2-mcp-server.py  # FastMCPとROS 2を統合するメインサーバースクリプト
├── pyproject.toml      # プロジェクトの依存関係とメタデータ
├── .python-version     # Pythonバージョンの指定
├── .gitignore          # Gitの無視ファイル
└── README.md           # このファイル
```

## 制限事項
- **単一トピック**: 現在は`Twist`メッセージを使用した`/cmd_vel`のみをサポートしています。他のトピックやサービスについては`ros2-mcp-server.py`を拡張してください。
- **基本的なコマンド**: 現在は単純な移動コマンドをサポートしています。より複雑な動作には追加の実装が必要です。

## ライセンス

```
MIT License

Copyright (c) 2025 kakimochi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

このプロジェクトは[FastMCP](https://github.com/jlowin/fastmcp)を使用しており、Apache License 2.0の下でライセンスされています。そのライセンスの条件もFastMCPコンポーネントの使用に適用されます。

## 謝辞
- [FastMCP](https://github.com/jlowin/fastmcp)と[ROS 2](https://docs.ros.org)を使用して構築されています。
