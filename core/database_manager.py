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

from typing import Optional, List, Dict, Any
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
        self.cursor.execute('SELECT * FROM irc_networks')
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

    def add_network(
        self,
        name: str,
        address: str,
        port: int,
        use_ssl: bool,
        nicknames: str,
        ident: str,
        realname: str,
        services_username: str = "",
        services_password: str = "",
        oper_username: str = "",
        oper_password: str = "",
        command_trigger: str = "!"
    ) -> int:
        try:
            ssl_str = "yes" if use_ssl else "no"

            self.cursor.execute(
                '''INSERT INTO irc_networks
                   (name, address, port, ssl,
                    nicknames, ident, realname,
                    services_username, services_password,
                    oper_username, oper_password, command_trigger)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (name, address, port, ssl_str, nicknames, ident, realname,
                 services_username, services_password, oper_username,
                 oper_password, command_trigger)
            )
            self.connection.commit()

            network_id = self.cursor.lastrowid
            Logger.info(f"Added network '{name}' with ID {network_id}")
            return network_id

        except sqlite3.Error as e:
            Logger.error(f"Failed to add network: {e}")
            raise

    def remove_network(self, network_id: int) -> bool:
        try:
            # First, remove associated channels
            self.cursor.execute(
                'DELETE FROM irc_channels WHERE network_id=?',
                (network_id,)
            )

            # Remove associated plugins
            self.cursor.execute(
                'DELETE FROM plugins WHERE network_id=?',
                (network_id,)
            )

            # Remove the network
            self.cursor.execute(
                'DELETE FROM irc_networks WHERE ID=?',
                (network_id,)
            )

            rows_affected = self.cursor.rowcount
            self.connection.commit()

            if rows_affected > 0:
                Logger.info(f"Removed network ID {network_id}")
                return True
            else:
                Logger.warning(f"Network ID {network_id} not found")
                return False

        except sqlite3.Error as e:
            Logger.error(f"Failed to remove network: {e}")
            return False

    def update_network(self, network_id: int, updates: Dict[str, Any]) -> bool:
        try:
            # Map friendly names to database columns
            column_map = {
                'name': 'name',
                'address': 'address',
                'port': 'port',
                'use_ssl': 'ssl',
                'nicknames': 'nicknames',
                'ident': 'ident',
                'realname': 'realname',
                'services_username': 'services_username',
                'services_password': 'services_password',
                'oper_username': 'oper_username',
                'oper_password': 'oper_password',
                'command_trigger': 'command_trigger'
            }

            # Build UPDATE query
            set_clauses = []
            values = []

            for key, value in updates.items():
                db_column = column_map.get(key, key)

                # Convert boolean to yes/no for SSL
                if key == 'use_ssl':
                    value = "yes" if value else "no"

                set_clauses.append(f"{db_column}=?")
                values.append(value)

            if not set_clauses:
                return False

            values.append(network_id)
            query = f"UPDATE irc_networks SET {', '.join(set_clauses)} WHERE ID=?"

            self.cursor.execute(query, values)
            rows_affected = self.cursor.rowcount
            self.connection.commit()

            if rows_affected > 0:
                Logger.info(f"Updated network ID {network_id}")
                return True
            else:
                Logger.warning(f"Network ID {network_id} not found")
                return False

        except sqlite3.Error as e:
            Logger.error(f"Failed to update network: {e}")
            return False

    def get_channels(self, network_id: int) -> List[str]:
        self.cursor.execute(
            'SELECT name FROM irc_channels WHERE network_id=?',
            (network_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_enabled_plugins(self, network_id: int) -> List[str]:
        self.cursor.execute(
            'SELECT name FROM plugins WHERE network_id=? AND enabled=1',
            (network_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def add_channel(self, network_id: int, channel_name: str):
        try:
            self.cursor.execute(
                'INSERT INTO irc_channels (network_id, name) VALUES (?, ?)',
                (network_id, channel_name)
            )
            self.connection.commit()
            Logger.info(f"Added channel {channel_name} to database")
        except sqlite3.IntegrityError:
            Logger.info(f"Channel {channel_name} already in database")

    def remove_channel(self, network_id: int, channel_name: str):
        self.cursor.execute(
            'DELETE FROM irc_channels WHERE name=? AND network_id=?',
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
            'UPDATE plugins SET enabled=? WHERE network_id=? AND name=?',
            (1 if enabled else 0, network_id, plugin_name)
        )
        self.connection.commit()
