"""
ServiceX IRC Bot - Factory

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

from twisted.internet import reactor, protocol

from .logger import Logger
from .network_config import NetworkConfig
from .database_manager import DatabaseManager
from .protocol import Protocol


class Factory(protocol.ClientFactory):
    protocol = Protocol

    def __init__(self, config: NetworkConfig, db: DatabaseManager):
        self.config = config
        self.db = db

    def buildProtocol(self, addr):
        proto = self.protocol()
        proto.factory = self
        proto.nickname = self.config.primary_nickname
        proto.username = self.config.ident
        proto.realname = self.config.realname
        proto.db = self.db
        return proto

    def clientConnectionLost(self, connector, reason):
        Logger.warning(
            f"Connection lost, reconnecting: {reason.getErrorMessage()}")
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        Logger.error(f"Connection failed: {reason.getErrorMessage()}")
        reactor.stop()
