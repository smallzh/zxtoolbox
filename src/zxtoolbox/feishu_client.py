"""Feishu (Lark) Bot Client - 飞书客户端集成模块。

通过长连接（WebSocket）接收飞书消息事件，支持执行 CLI 命令。

主要功能:
    - WebSocket 长连接接收飞书消息
    - 支持 git pull 命令
    - 支持 mkdocs batch 命令
    - 交互式命令执行和结果返回

使用示例:
    >>> from zxtoolbox.feishu_client import FeishuClient
    >>> client = FeishuClient(app_id="cli_xxx", app_secret="xxx")
    >>> client.start()

配置文件 (zxtool.toml):
    [feishu]
    app_id = "cli_xxxxxxxxxxxxx"
    app_secret = "xxxxxxxxxxxxxxxxxxxx"
"""

from __future__ import annotations

import io
import json
import logging
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

from zxtoolbox import logging_manager as lm

logger = logging.getLogger(__name__)


@dataclass
class FeishuConfig:
    """飞书客户端配置。"""

    app_id: str
    app_secret: str


class FeishuClient:
    """飞书客户端，支持 WebSocket 长连接接收事件。

    Attributes:
        app_id: 飞书应用 ID
        app_secret: 飞书应用密钥
        client: lark API 客户端
    """

    def __init__(self, app_id: str, app_secret: str):
        """初始化飞书客户端。

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
        """
        self.app_id = app_id
        self.app_secret = app_secret

        # 创建 API 客户端用于发送消息
        self.client = (
            lark.Client.builder()
            .app_settings(
                lark.AppSettings.builder()
                .app_id(self.app_id)
                .app_secret(self.app_secret)
                .build()
            )
            .build()
        )

        logger.info("Feishu client initialized")

    def _parse_command(self, text: str) -> tuple[str | None, list[str]]:
        """解析命令文本。

        Args:
            text: 消息文本内容

        Returns:
            (命令名称, 参数列表)，如果不是有效命令返回 (None, [])

        Examples:
            "git pull" -> ("git_pull", [])
            "git pull origin main" -> ("git_pull", ["origin", "main"])
            "mkdocs batch" -> ("mkdocs_batch", [])
            "help" -> ("help", [])
        """
        text = text.strip()
        if not text:
            return None, []

        parts = text.lower().split()
        if len(parts) == 0:
            return None, []

        # 支持的命令映射
        command_map = {
            "git pull": "git_pull",
            "mkdocs batch": "mkdocs_batch",
            "help": "help",
            "?": "help",
        }

        # 检查完整命令（包括子命令）
        full_command = " ".join(parts[:2])
        if full_command in command_map:
            return command_map[full_command], parts[2:]

        # 检查单命令
        single_command = parts[0]
        if single_command in command_map:
            return command_map[single_command], parts[1:]

        # 不支持的命令
        return "unknown", parts

    def _send_text_message(self, chat_id: str, text: str) -> bool:
        """发送文本消息到飞书。

        Args:
            chat_id: 聊天 ID
            text: 消息内容

        Returns:
            是否发送成功
        """
        try:
            # 构建消息内容
            content = json.dumps({"text": text})

            request = (
                CreateMessageRequest.builder()
                .receive_id_type("chat_id")
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("text")
                    .content(content)
                    .build()
                )
                .build()
            )

            response = self.client.im.v1.message.create(request)

            if response.success():
                logger.info(f"Message sent to chat {chat_id}")
                return True
            else:
                logger.error(f"Failed to send message: {response.msg}")
                return False

        except Exception as e:
            logger.error(f"Exception sending message: {e}")
            return False

    def _execute_git_pull(self, args: list[str]) -> str:
        """执行 git pull 命令。

        Args:
            args: 额外参数，如 ["origin", "main"]

        Returns:
            命令执行结果文本
        """
        from zxtoolbox.config_manager import load_projects_with_domain
        from zxtoolbox.git_config import git_pull_by_name

        try:
            # 如果没有参数，使用默认配置
            if not args:
                # 尝试从配置文件获取项目名称
                try:
                    projects = load_projects_with_domain()
                    if projects:
                        results = []
                        for proj in projects:
                            name = proj.get("name")
                            if name:
                                result = git_pull_by_name(name)
                                status = "✅ 成功" if result else "❌ 失败"
                                results.append(f"{name}: {status}")
                        return "Git Pull 结果:\n" + "\n".join(results)
                    else:
                        return "❌ 未找到配置的项目，请指定项目名称"
                except Exception as e:
                    return f"❌ 执行失败: {e}"
            else:
                # 第一个参数作为项目名称
                project_name = args[0]
                remote = args[1] if len(args) > 1 else None
                branch = args[2] if len(args) > 2 else None

                result = git_pull_by_name(
                    name=project_name,
                    remote=remote,
                    branch=branch,
                )
                return "✅ Git pull 成功" if result else "❌ Git pull 失败"

        except Exception as e:
            return f"❌ 执行出错: {e}"

    def _execute_mkdocs_batch(self, args: list[str]) -> str:
        """执行 mkdocs batch 构建。

        Args:
            args: 额外参数

        Returns:
            构建结果文本
        """
        from zxtoolbox.mkdocs_manager import batch_build

        try:
            # 捕获输出
            output_buffer = io.StringIO()

            with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                result = batch_build(dry_run=False)

            output = output_buffer.getvalue()

            # 统计结果
            if result:
                success_count = sum(1 for v in result.values() if v)
                total = len(result)
                summary = f"\n📊 构建结果: {success_count}/{total} 成功"

                if output:
                    return output[:2000] + summary  # 限制长度
                else:
                    return summary
            else:
                return "❌ 未找到可构建的项目，请检查配置文件"

        except Exception as e:
            return f"❌ 构建失败: {e}"

    def _get_help_text(self) -> str:
        """获取帮助文本。

        Returns:
            帮助信息文本
        """
        return """🤖 **ZXToolbox 飞书助手**

支持的命令：

📦 **Git 操作**
• `git pull` - 拉取所有配置项目的更新
• `git pull <项目名>` - 拉取指定项目
• `git pull <项目名> <remote> <branch>` - 指定远程和分支

📚 **MkDocs 操作**
• `mkdocs batch` - 批量构建所有 MkDocs 项目

❓ **帮助**
• `help` 或 `?` - 显示此帮助信息

💡 **使用示例：**
```
git pull myproject
git pull myproject origin main
mkdocs batch
```
"""

    def _handle_message(self, data: lark.im.v1.P2ImMessageReceiveV1) -> None:
        """处理接收到的消息事件。

        Args:
            data: 消息事件数据
        """
        try:
            message = data.event.message
            chat_id = message.chat_id
            content_str = message.content
            message_type = message.message_type

            logger.info(f"Received message in chat {chat_id}, type: {message_type}")

            # 只处理文本消息
            if message_type != "text":
                logger.info(f"Ignoring non-text message: {message_type}")
                return

            # 解析消息内容
            try:
                content = json.loads(content_str)
                text = content.get("text", "").strip()
            except json.JSONDecodeError:
                text = content_str.strip()

            if not text:
                return

            logger.info(f"Message text: {text}")

            # 解析命令
            command, args = self._parse_command(text)

            if command is None:
                return

            # 执行命令
            if command == "help":
                response = self._get_help_text()
            elif command == "git_pull":
                response = self._execute_git_pull(args)
            elif command == "mkdocs_batch":
                response = self._execute_mkdocs_batch(args)
            elif command == "unknown":
                response = (
                    f"❓ 不支持的命令: `{text}`\n\n"
                    f"输入 `help` 或 `?` 查看支持的命令列表。"
                )
            else:
                response = f"❌ 命令执行出错: {command}"

            # 发送回复
            if response:
                self._send_text_message(chat_id, response)

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            # 尝试发送错误信息
            try:
                if "chat_id" in dir() and chat_id:
                    self._send_text_message(chat_id, f"❌ 处理消息时出错: {e}")
            except:
                pass

    def _create_event_handler(self) -> lark.EventDispatcherHandler:
        """创建事件处理器。

        Returns:
            配置好的事件处理器
        """
        return (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self._handle_message)
            .build()
        )

    def start(self) -> None:
        """启动 WebSocket 长连接。

        此方法会阻塞主线程，直到连接中断。
        """
        event_handler = self._create_event_handler()

        cli = lark.ws.Client(
            self.app_id,
            self.app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO,
        )

        logger.info("Starting Feishu WebSocket connection...")
        print("🚀 飞书客户端已启动，等待消息...")
        print("按 Ctrl+C 停止")

        try:
            cli.start()
        except KeyboardInterrupt:
            print("\n👋 飞书客户端已停止")
            logger.info("Feishu client stopped by user")


def create_client_from_config(config_path: str | Path | None = None) -> FeishuClient:
    """从配置文件创建飞书客户端。

    Args:
        config_path: 配置文件路径，默认 ~/.config/zxtool.toml

    Returns:
        配置好的 FeishuClient 实例

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置不完整
    """
    from zxtoolbox.config_manager import load_config

    if config_path is None:
        from zxtoolbox.config_manager import DEFAULT_CONFIG_PATH

        config_path = DEFAULT_CONFIG_PATH

    data = load_config(config_path)
    feishu_config = data.get("feishu", {})

    app_id = feishu_config.get("app_id")
    app_secret = feishu_config.get("app_secret")

    if not app_id or not app_secret:
        raise ValueError(
            "飞书配置不完整，请在 zxtool.toml 中添加:\n"
            "[feishu]\n"
            'app_id = "cli_xxxxxxxxxxxxx"\n'
            'app_secret = "xxxxxxxxxxxxxxxxxxxx"'
        )

    return FeishuClient(app_id=app_id, app_secret=app_secret)


def run_client(config_path: str | Path | None = None) -> None:
    """运行飞书客户端（便捷函数）。

    Args:
        config_path: 配置文件路径
    """
    client = create_client_from_config(config_path)
    client.start()
