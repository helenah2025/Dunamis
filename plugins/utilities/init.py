"""
Utilities Plugin for ServiceX
Provides basic utility commands for IRC bot functionality

Copyright (C) 2026 Helenah, Helena Bolan <helenah2025@proton.me>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from typing import List, Tuple, Optional
from platform import system, node, release, version, machine
from getopt import getopt, GetoptError
from dataclasses import dataclass


PLUGIN_INFO = {
    "name": "Utilities",
    "author": "Helenah, Helena Bolan",
    "version": "2.0",
    "description": "Core utility commands for ServiceX bot"
}


@dataclass
class CommandContext:
    target: str
    nickname: str
    arguments: List[str]


class MessageFormatter:
    @staticmethod
    def grid(rows: List[List[str]], columns: int = 6) -> str:
        if not rows:
            return ""

        # Split into chunks
        chunks = [rows[i::columns] for i in range(columns)]

        # Find max width for each column
        col_widths = [max(len(str(item)) for item in col) for col in chunks]

        # Build grid
        lines = []
        max_rows = max(len(col) for col in chunks)

        for row_idx in range(max_rows):
            row_parts = []
            for col_idx, col in enumerate(chunks):
                if row_idx < len(col):
                    item = str(col[row_idx]).ljust(col_widths[col_idx])
                    row_parts.append(item)
            lines.append("  ".join(row_parts))

        return "\n".join(lines)

    @staticmethod
    def escape_sequences(text: str) -> str:
        # Replace tab with spaces
        text = text.replace("\\t", "    ")
        return text


def value_self_nick(bot) -> str:
    return bot.nickname


def value_self_ident(bot) -> str:
    return bot.username


def value_self_name(bot) -> str:
    return bot.realname


def value_date(bot) -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def value_time(bot) -> str:
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


def value_network(bot) -> str:
    print(dir(bot))
    return


def command_help(bot, target: str, nickname: str, args: List[str]):
    help_text = (
        f"Hello there, I am a ServiceX bot called {bot.nickname}. "
        f"For a list of commands, send '{bot.factory.config.command_trigger}commands' "
        f"into a channel or 'commands' to me as a PM.\n"
        f"For more information: https://github.com/helenah2025/ServiceX/wiki/User-Guide\n"
        f"NOTICE: This project has been totally refactored, the wiki page above does not yet exist.")
    bot.send_message(target, help_text, nickname)


def command_commands(bot, target: str, nickname: str, args: List[str]):
    # Get all registered commands
    commands = sorted(bot.plugin_manager.commands.keys())

    if not commands:
        bot.send_message(target, "No commands available", nickname)
        return

    # Count unique plugins
    plugins = set()
    for cmd_name in commands:
        cmd_func = bot.plugin_manager.commands[cmd_name]
        plugins.add(cmd_func.__module__)

    command_count = len(commands)
    plugin_count = len(plugins)

    # Build description
    if command_count == 1:
        desc = "is 1 command"
    else:
        desc = f"are {command_count} commands"

    if plugin_count == 1:
        desc += " from a single plugin"
    else:
        desc += f" from {plugin_count} plugins"

    # Format command list
    command_grid = MessageFormatter.grid(commands, columns=6)

    message = f"There {desc} available, these commands are:\n{command_grid}"
    bot.send_message(target, message, nickname)


def command_date(bot, target: str, nickname: str, args: List[str]):
    from datetime import datetime
    from pytz import timezone as pytz_timezone

    timezone_arg = None
    format_arg = None
    preset_arg = None

    try:
        opts, _ = getopt(args, "f:p:t:", ["format=", "preset=", "timezone="])
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return

    for opt, arg in opts:
        if opt in ("-t", "--timezone"):
            timezone_arg = arg
        elif opt in ("-f", "--format"):
            format_arg = arg
        elif opt in ("-p", "--preset"):
            preset_arg = arg

    # Get current time
    try:
        if timezone_arg:
            now = datetime.now(pytz_timezone(timezone_arg))
        else:
            now = datetime.now()
    except Exception as e:
        bot.send_message(target, f"Invalid timezone: {timezone_arg}", nickname)
        return

    # Format output
    if format_arg:
        result = now.strftime(format_arg)
    elif preset_arg == "date":
        result = now.strftime("%Y-%m-%d")
    elif preset_arg == "time":
        result = now.strftime("%H:%M:%S")
    elif preset_arg == "datetime":
        result = now.strftime("%Y-%m-%d %H:%M:%S")
    else:
        result = now.strftime("%Y-%m-%d %H:%M:%S")

    bot.send_message(target, result, nickname)


def command_uname(bot, target: str, nickname: str, args: List[str]):
    # Imitation of the uname system command
    os_name = "GNU/Linux"

    try:
        opts, _ = getopt(
            args,
            "snrvmoa",
            ["kernel-name", "nodename", "kernel-release",
             "kernel-version", "machine", "operating-system", "all"]
        )
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return

    # If no options, print everything
    if not opts:
        result = f"{system()} {node()} {release()} {version()} {machine()} {os_name}"
        bot.send_message(target, result, nickname)
        return

    # Build output based on options
    parts = []
    flags = {
        "system": False,
        "node": False,
        "release": False,
        "version": False,
        "machine": False,
        "os": False
    }

    for opt, _ in opts:
        if opt in ("-s", "--kernel-name", "-a", "--all"):
            flags["system"] = True
        if opt in ("-n", "--nodename", "-a", "--all"):
            flags["node"] = True
        if opt in ("-r", "--kernel-release", "-a", "--all"):
            flags["release"] = True
        if opt in ("-v", "--kernel-version", "-a", "--all"):
            flags["version"] = True
        if opt in ("-m", "--machine", "-a", "--all"):
            flags["machine"] = True
        if opt in ("-o", "--operating-system", "-a", "--all"):
            flags["os"] = True

    if flags["system"]:
        parts.append(system())
    if flags["node"]:
        parts.append(node())
    if flags["release"]:
        parts.append(release())
    if flags["version"]:
        parts.append(version())
    if flags["machine"]:
        parts.append(machine())
    if flags["os"]:
        parts.append(os_name)

    bot.send_message(target, " ".join(parts), nickname)


def command_echo(bot, target: str, nickname: str, args: List[str]):
    enable_escapes = False
    suppress_newline = False

    try:
        opts, remaining_args = getopt(args, "en")
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return

    for opt, _ in opts:
        if opt == "-e":
            enable_escapes = True
        elif opt == "-n":
            suppress_newline = True

    # Join remaining arguments
    if not remaining_args:
        message = ""
    else:
        message = " ".join(remaining_args)

    # Parse values
    message = bot.plugin_manager.parse_values(message, bot)

    # Process escape sequences if enabled
    if enable_escapes:
        message = MessageFormatter.escape_sequences(message)
        # Split on actual newlines for multi-line output
        for line in message.split("\\n"):
            bot.send_message(target, line, nickname)
    else:
        bot.send_message(target, message, nickname)


def command_nick(bot, target: str, nickname: str, args: List[str]):
    if not args:
        bot.send_message(target, "Usage: nick NEWNICK", nickname)
        return

    new_nick = args[0]
    bot.setNick(new_nick)
    bot.send_message(target, f"Changing nickname to: {new_nick}", nickname)


def command_plugin(bot, target: str, nickname: str, args: List[str]):
    handlers = {
        "help": handle_plugin_help,
        "list": handle_plugin_list,
        "load": handle_plugin_load,
        "unload": handle_plugin_unload,
        "enable": handle_plugin_enable,
        "disable": handle_plugin_disable,
    }

    subcommand_list = ", ".join(handlers.keys())

    if not args:
        bot.send_message(target, f"Usage: requires a subcommand: {subcommand_list}", nickname)
        return

    subcommand = args[0].lower()
    subargs = args[1:]

    handler = handlers.get(subcommand)

    if handler:
        handler(bot, target, nickname, subargs)
    else:
        bot.send_message(target, f"Error: unknown subcommand: {subcommand} - available subcommands: {subcommand_list}", nickname)

def handle_plugin_help(bot, target: str, nickname: str, args: List[str]):
    help_text = (
        "ServiceX Plugin Manager\n"
        "Commands: list, load, unload, enable, disable, help"
    )
    bot.send_message(target, help_text, nickname)


def handle_plugin_list(bot, target: str, nickname: str, args: List[str]):
    plugins = sorted(bot.plugin_manager.loaded_plugins.keys())
    if plugins:
        plugin_list = ", ".join(plugins)
        bot.send_message(
            target,
            f"Info: loaded plugins: {plugin_list}",
            nickname)
    else:
        bot.send_message(target, "Info: no plugins loaded", nickname)

def handle_plugin_load(bot, target: str, nickname: str, args: List[str]):
    if not args:
        bot.send_message(target, "Specify plugin(s) to load", nickname)
        return

    for plugin_name in args:
        if bot.plugin_manager.load_plugin(plugin_name):
            bot.send_message(
                target, f"Success: loaded plugin: {plugin_name}", nickname)
        else:
            bot.send_message(
                target, f"Error: failed to load: {plugin_name}", nickname)

def handle_plugin_unload(bot, target: str, nickname: str, args: List[str]):
    if not args:
        bot.send_message(target, "Specify plugin(s) to unload", nickname)
        return

    for plugin_name in args:
        if bot.plugin_manager.unload_plugin(plugin_name):
            bot.send_message(
                target, f"Success: unloaded plugin: {plugin_name}", nickname)
        else:
            bot.send_message(
                target, f"Error: failed to unload: {plugin_name}", nickname)

def handle_plugin_enable(bot, target: str, nickname: str, args: List[str]):
    if not args:
        bot.send_message(target, "Specify plugin(s) to enable", nickname)
        return

    for plugin_name in args:
        bot.db.update_plugin_status(
            bot.factory.config.id, plugin_name, enabled=True)
        bot.send_message(
            target,
            f"Success: enabled plugin: {plugin_name}",
            nickname)

def handle_plugin_disable(bot, target: str, nickname: str, args: List[str]):
    if not args:
        bot.send_message(target, "Specify plugin(s) to disable", nickname)
        return

    for plugin_name in args:
        bot.db.update_plugin_status(
            bot.factory.config.id, plugin_name, enabled=False)
        bot.send_message(
            target,
            f"Success: disabled plugin: {plugin_name}",
            nickname)


__all__ = [
    'PLUGIN_INFO',
    'value_nick',
    'value_date',
    'value_time',
    'command_help',
    'command_commands',
    'command_date',
    'command_uname',
    'command_echo',
    'command_nick',
    'command_join',
    'command_part',
    'command_plugin',
    'handle_plugin_help',
    'handle_plugin_list',
    'handle_plugin_load',
    'handle_plugin_unload',
    'handle_plugin_enable',
    'handle_plugin_disable',
]
