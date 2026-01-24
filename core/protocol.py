"""
Dunamis IRC Bot - Protocol

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

from typing import Optional, List
import shlex

from twisted.words.protocols import irc

from .logger import Logger
from .plugin_manager import PluginManager
from .task_scheduler import TaskScheduler
from .database_manager import DatabaseManager


class Protocol(irc.IRCClient):
    versionName = "Dunamis"
    versionNum = "2.0"
    versionEnv = "Python/Twisted"

    def __init__(self):
        super().__init__()
        # Don't create plugin_manager here - it will be set by factory
        self.plugin_manager: Optional[PluginManager] = None
        self.scheduler = TaskScheduler()
        self.db: Optional[DatabaseManager] = None
        self.joined_channels: List[str] = []

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        Logger.info(
            f"Connected to IRC network: {self.factory.config.name} "
            f"({self.factory.config.address}:{self.factory.config.port})"
        )

        # Load enabled plugins for this network if not already loaded
        enabled_plugins = self.db.get_enabled_plugins(self.factory.config.id)
        for plugin_name in enabled_plugins:
            if plugin_name not in self.plugin_manager.loaded_plugins:
                self.plugin_manager.load_plugin(plugin_name)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        Logger.warning(
            f"Connection lost to {self.factory.config.name}: {reason.getErrorMessage()}"
        )
        # Stop all scheduled tasks on disconnect
        self.scheduler.stop_all_tasks()

    def signedOn(self):
        config = self.factory.config

        # Identify with services
        Logger.info(f"Identifying with services as {config.services_username}")
        self.msg(
            'NickServ',
            f'IDENTIFY {config.services_username} {config.services_password}'
        )

        # Join channels
        channels = self.db.get_channels(config.id)
        for channel in channels:
            self.join_channel(channel, save_to_db=False)

    def alterCollidedNick(self, nickname: str) -> str:
        nicknames = self.factory.config.nicknames

        try:
            current_index = nicknames.index(nickname)
            next_index = (current_index + 1) % len(nicknames)
            new_nickname = nicknames[next_index]
        except ValueError:
            new_nickname = nicknames[0]

        Logger.info(f"Nickname {nickname} taken, trying {new_nickname}")
        return new_nickname

    def joined(self, channel: str):
        Logger.info(f"[{self.factory.config.name}] Joined channel: {channel}")
        if channel not in self.joined_channels:
            self.joined_channels.append(channel)

    def left(self, channel: str):
        Logger.info(f"[{self.factory.config.name}] Left channel: {channel}")
        if channel in self.joined_channels:
            self.joined_channels.remove(channel)

    def join_channel(self, channel: str, save_to_db: bool = True):
        if not channel:
            return

        channel = channel.split()[0]

        if channel in self.joined_channels:
            Logger.info(f"Already in channel: {channel}")
            return

        Logger.info(f"[{self.factory.config.name}] Joining channel: {channel}")
        self.join(channel)

        if save_to_db:
            self.db.add_channel(self.factory.config.id, channel)

    def part_channel(self, channel: str, save_to_db: bool = True):
        if not channel:
            return

        channel = channel.split()[0]

        if channel not in self.joined_channels:
            Logger.info(f"Not in channel: {channel}")
            return

        Logger.info(f"[{self.factory.config.name}] Leaving channel: {channel}")
        self.leave(channel)

        if save_to_db:
            self.db.remove_channel(self.factory.config.id, channel)

    def send_message(self, target: str, message: str,
                     prefix_nick: Optional[str] = None):
        if prefix_nick:
            message = f"{prefix_nick}: {message}"

        # Handle multi-line messages
        for line in message.split('\n'):
            self.msg(target, line)

    def privmsg(self, user: str, channel: str, message: str):
        try:
            nickname, user_info = user.split('!')
            ident, hostname = user_info.split('@')
        except ValueError:
            return

        message = message.strip()

        if not message:
            return

        # Determine if this is a PM or channel message
        is_pm = (channel == self.nickname)
        target = nickname if is_pm else channel

        # Check for command trigger
        trigger = self.factory.config.command_trigger
        if is_pm or message.startswith(trigger):
            self._handle_command(target, nickname, message, is_pm)

    def _handle_command(
            self,
            target: str,
            nickname: str,
            message: str,
            is_pm: bool):

        # Strip trigger if present
        if not is_pm:
            message = message[len(self.factory.config.command_trigger):]

        # Parse command and arguments
        try:
            parts = shlex.split(message)
        except ValueError as e:
            if "closing quotation" in str(e).lower():
                self.send_message(
                    target, "Missing closing quotation mark", nickname)
            return

        if not parts:
            return

        command = parts[0]
        args = parts[1:]

        # Execute command
        success = self.plugin_manager.execute_command(
            command, self, target, nickname, args
        )

        if not success:
            Logger.info(f"Unknown command '{command}' from {nickname}")
            self.send_message(target, "Command not found", nickname)
        else:
            Logger.info(
                f"[{self.factory.config.name}] Executed command '{command}' from {nickname}")

    def noticed(self, user: str, channel: str, message: str):
        if user == "NickServ!services@services.":
            if "Password accepted" in message:
                Logger.info("Successfully identified with services")
            elif "isn't registered" in message:
                Logger.error("Failed to identify with services")
