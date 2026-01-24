"""
Dunamis IRC Bot - Factory

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

from typing import Optional
from twisted.internet import reactor, protocol

from .logger import Logger
from .network_config import NetworkConfig
from .database_manager import DatabaseManager
from .protocol import Protocol
from .plugin_manager import PluginManager


class Factory(protocol.ClientFactory):
    protocol_class = Protocol

    def __init__(self, config: NetworkConfig, db: DatabaseManager,
                 plugin_manager: Optional[PluginManager] = None,
                 network_manager = None):
        self.config = config
        self.db = db
        self.plugin_manager = plugin_manager or PluginManager()
        self.network_manager = network_manager
        self.protocol = None
        self.should_reconnect = True

    def buildProtocol(self, addr):
        proto = self.protocol_class()
        proto.factory = self
        proto.nickname = self.config.primary_nickname
        proto.username = self.config.ident
        proto.realname = self.config.realname
        proto.db = self.db
        proto.plugin_manager = self.plugin_manager  # Use shared plugin manager

        # Store reference to protocol
        self.protocol = proto
        return proto

    def clientConnectionLost(self, connector, reason):
        Logger.warning(
            f"Connection lost to {self.config.name}: {reason.getErrorMessage()}")

        if self.should_reconnect:
            Logger.info(f"Reconnecting to {self.config.name}...")
            connector.connect()
        else:
            Logger.info(f"Not reconnecting to {self.config.name} (disabled)")

    def clientConnectionFailed(self, connector, reason):
        Logger.error(
            f"Connection failed to {self.config.name}: {reason.getErrorMessage()}")

        if self.should_reconnect:
            Logger.info(f"Retrying connection to {self.config.name}...")
            connector.connect()
        else:
            Logger.info(f"Not retrying connection to {self.config.name} (disabled)")
