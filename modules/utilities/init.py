"""
Utilities Module for ServiceX
Provides basic utility commands for IRC bot functionality

Copyright (C) 2026 Helena Bolan <helenah2025@proton.me>

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


# ============================================================================
# Module Metadata
# ============================================================================

MODULE_INFO = {
    "name": "Utilities",
    "author": "Helena Bolan",
    "version": "2.0",
    "description": "Core utility commands for ServiceX bot"
}


# ============================================================================
# Helper Classes
# ============================================================================

@dataclass
class CommandContext:
    """Context for command execution"""
    target: str
    nickname: str
    arguments: List[str]


class MessageFormatter:
    """Helper for formatting bot messages"""
    
    @staticmethod
    def grid(rows: List[List[str]], columns: int = 2) -> str:
        """
        Format a list into a grid layout
        
        Args:
            rows: List of items to format
            columns: Number of columns in grid
        
        Returns:
            Formatted grid string with newlines
        """
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
        """
        Process escape sequences in text
        
        Args:
            text: Text with escape sequences
        
        Returns:
            Text with escape sequences processed
        """
        # Replace tab with spaces
        text = text.replace("\\t", "    ")
        return text


# ============================================================================
# Variable Functions
# ============================================================================

def variable_nick(bot) -> str:
    """Return the bot's current nickname"""
    return bot.nickname


def variable_date(bot) -> str:
    """Return the current date"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def variable_time(bot) -> str:
    """Return the current time"""
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


# ============================================================================
# Command Functions
# ============================================================================

def command_help(bot, target: str, nickname: str, args: List[str]):
    """
    Display help information about the bot
    
    Usage: help
    """
    help_text = (
        f"Hello there, I am a ServiceX bot called {bot.nickname}. "
        f"For a list of commands, send '{bot.factory.config.command_trigger}commands' "
        f"into a channel or 'commands' to me as a PM.\n"
        f"For more information: https://github.com/DGS-Dead-Gnome-Society/ServiceX/wiki/User-Guide\n"
        f"NOTICE: This project has been totally refactored, the repository above is no longer maintained."
    )
    bot.send_message(target, help_text, nickname)


def command_commands(bot, target: str, nickname: str, args: List[str]):
    """
    List all available commands
    
    Usage: commands
    """
    # Get all registered commands
    commands = sorted(bot.module_manager.commands.keys())
    
    if not commands:
        bot.send_message(target, "No commands available", nickname)
        return
    
    # Count unique modules
    modules = set()
    for cmd_name in commands:
        cmd_func = bot.module_manager.commands[cmd_name]
        modules.add(cmd_func.__module__)
    
    command_count = len(commands)
    module_count = len(modules)
    
    # Build description
    if command_count == 1:
        desc = "is 1 command"
    else:
        desc = f"are {command_count} commands"
    
    if module_count == 1:
        desc += " from a single module"
    else:
        desc += f" from {module_count} modules"
    
    # Format command list
    command_grid = MessageFormatter.grid(commands, columns=2)
    
    message = f"There {desc} available, these commands are:\n{command_grid}"
    bot.send_message(target, message, nickname)


def command_date(bot, target: str, nickname: str, args: List[str]):
    """
    Display current date/time with optional formatting
    
    Usage: date [-t TIMEZONE] [-f FORMAT] [-p PRESET]
    
    Options:
        -t, --timezone  Timezone (e.g., 'US/Eastern')
        -f, --format    Custom strftime format
        -p, --preset    Preset format (date, time, datetime)
    
    Examples:
        date
        date -p datetime
        date -t US/Eastern
        date -f "%Y-%m-%d %H:%M"
    """
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
    """
    Display system information
    
    Usage: uname [OPTIONS]
    
    Options:
        -s, --kernel-name      Print kernel name
        -n, --nodename         Print network node hostname
        -r, --kernel-release   Print kernel release
        -v, --kernel-version   Print kernel version
        -m, --machine          Print machine hardware name
        -o, --operating-system Print operating system
        -a, --all              Print all information
    
    Examples:
        uname
        uname -a
        uname -s -r
    """
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
    """
    Echo text back to the channel/user
    
    Usage: echo [OPTIONS] TEXT
    
    Options:
        -e  Enable interpretation of backslash escapes
        -n  Do not output trailing newline
    
    Variables:
        $nick  Bot's nickname
        $date  Current date
        $time  Current time
    
    Examples:
        echo Hello, world!
        echo -e First line\\nSecond line
        echo My name is $nick
    """
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
    
    # Parse variables
    message = bot.module_manager.parse_variables(message, bot)
    
    # Process escape sequences if enabled
    if enable_escapes:
        message = MessageFormatter.escape_sequences(message)
        # Split on actual newlines for multi-line output
        for line in message.split("\\n"):
            bot.send_message(target, line, nickname)
    else:
        bot.send_message(target, message, nickname)


def command_nick(bot, target: str, nickname: str, args: List[str]):
    """
    Change the bot's nickname
    
    Usage: nick NEWNICK
    
    Examples:
        nick ServiceBot
    """
    if not args:
        bot.send_message(target, "Usage: nick NEWNICK", nickname)
        return
    
    new_nick = args[0]
    bot.setNick(new_nick)
    bot.send_message(target, f"Changing nickname to: {new_nick}", nickname)


def command_module(bot, target: str, nickname: str, args: List[str]):
    """
    Manage bot modules
    
    Usage: module SUBCOMMAND [ARGS...]
    
    Subcommands:
        list              List loaded modules
        load MODULE       Load a module
        unload MODULE     Unload a module
        enable MODULE     Enable module in database
        disable MODULE    Disable module in database
        help              Show this help
    
    Examples:
        module list
        module load admin
        module unload utilities
    """
    if not args:
        bot.send_message(target, "Usage: module SUBCOMMAND [ARGS...]", nickname)
        return
    
    subcommand = args[0].lower()
    subcommand_args = args[1:]
    
    if subcommand == "help":
        help_text = (
            "ServiceX Module Manager\n"
            "Commands: list, load, unload, enable, disable, help"
        )
        bot.send_message(target, help_text, nickname)
    
    elif subcommand == "list":
        modules = sorted(bot.module_manager.loaded_modules.keys())
        if modules:
            module_list = ", ".join(modules)
            bot.send_message(target, f"Loaded modules: {module_list}", nickname)
        else:
            bot.send_message(target, "No modules loaded", nickname)
    
    elif subcommand == "load":
        if not subcommand_args:
            bot.send_message(target, "Specify module(s) to load", nickname)
            return
        
        for module_name in subcommand_args:
            if bot.module_manager.load_module(module_name):
                bot.send_message(target, f"Loaded module: {module_name}", nickname)
            else:
                bot.send_message(target, f"Failed to load: {module_name}", nickname)
    
    elif subcommand == "unload":
        if not subcommand_args:
            bot.send_message(target, "Specify module(s) to unload", nickname)
            return
        
        for module_name in subcommand_args:
            if bot.module_manager.unload_module(module_name):
                bot.send_message(target, f"Unloaded module: {module_name}", nickname)
            else:
                bot.send_message(target, f"Failed to unload: {module_name}", nickname)
    
    elif subcommand == "enable":
        if not subcommand_args:
            bot.send_message(target, "Specify module(s) to enable", nickname)
            return
        
        for module_name in subcommand_args:
            bot.db.update_module_status(bot.factory.config.id, module_name, enabled=True)
            bot.send_message(target, f"Enabled module: {module_name}", nickname)
    
    elif subcommand == "disable":
        if not subcommand_args:
            bot.send_message(target, "Specify module(s) to disable", nickname)
            return
        
        for module_name in subcommand_args:
            bot.db.update_module_status(bot.factory.config.id, module_name, enabled=False)
            bot.send_message(target, f"Disabled module: {module_name}", nickname)
    
    else:
        bot.send_message(target, f"Unknown subcommand: {subcommand}", nickname)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'MODULE_INFO',
    'variable_nick',
    'variable_date',
    'variable_time',
    'command_help',
    'command_commands',
    'command_date',
    'command_uname',
    'command_echo',
    'command_nick',
    'command_join',
    'command_part',
    'command_module',
]
