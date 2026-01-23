"""
ServiceX IRC Bot - Database Manager

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
from pathlib import Path
import sqlite3

from .logger import Logger
from .network_config import NetworkConfig


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def connect(self) -> bool:
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.cursor = self.connection.cursor()
            Logger.info(f"Connected to database: {self.db_path}")
            return True
        except sqlite3.Error as e:
            Logger.error(f"Database connection failed: {e}")
            return False

    def get_networks(self) -> List[NetworkConfig]:
        self.cursor.execute('SELECT * FROM ircNetworks')
        networks = []

        for row in self.cursor.fetchall():
            config = NetworkConfig(
                id=row[0],
                name=row[1],
                address=row[2],
                port=row[3],
                use_ssl=(row[4] == "yes"),
                nicknames=row[5].split(', '),
                ident=row[6],
                realname=row[7],
                services_username=row[8],
                services_password=row[9],
                oper_username=row[10],
                oper_password=row[11],
                command_trigger=row[12]
            )
            networks.append(config)

        return networks

    def get_channels(self, network_id: int) -> List[str]:
        self.cursor.execute(
            'SELECT channelName FROM ircChannels WHERE networkID=?',
            (network_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_enabled_plugins(self, network_id: int) -> List[str]:
        self.cursor.execute(
            'SELECT pluginName FROM plugins WHERE networkID=? AND pluginEnabled=1',
            (network_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def add_channel(self, network_id: int, channel_name: str):
        try:
            self.cursor.execute(
                'INSERT INTO ircChannels (networkID, channelName) VALUES (?, ?)',
                (network_id, channel_name)
            )
            self.connection.commit()
            Logger.info(f"Added channel {channel_name} to database")
        except sqlite3.IntegrityError:
            Logger.info(f"Channel {channel_name} already in database")

    def remove_channel(self, network_id: int, channel_name: str):
        self.cursor.execute(
            'DELETE FROM ircChannels WHERE channelName=? AND networkID=?',
            (channel_name, network_id)
        )
        self.connection.commit()
        Logger.info(f"Removed channel {channel_name} from database")

    def update_plugin_status(
            self,
            network_id: int,
            plugin_name: str,
            enabled: bool):
        # Enable or disable plugin
        self.cursor.execute(
            'UPDATE plugins SET pluginEnabled=? WHERE networkID=? AND pluginName=?',
            (1 if enabled else 0, network_id, plugin_name)
        )
        self.connection.commit()
