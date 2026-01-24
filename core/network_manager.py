"""
Dunamis IRC Bot - Network Manager

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

from typing import Dict, Optional, List
from twisted.internet import reactor, ssl

from .logger import Logger
from .network_config import NetworkConfig
from .database_manager import DatabaseManager
from .factory import Factory
from .plugin_manager import PluginManager


class NetworkManager:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.networks: Dict[int, NetworkConfig] = {}
        self.factories: Dict[int, Factory] = {}
        self.connectors: Dict[int, any] = {}
        self.plugin_manager = PluginManager()

    def load_networks(self) -> List[NetworkConfig]:
        networks = self.db.get_networks()
        for network in networks:
            self.networks[network.id] = network
        Logger.info(f"Loaded {len(networks)} network configurations")
        return networks

    def connect_network(self, network_id: int) -> bool:
        if network_id not in self.networks:
            Logger.error(f"Network {network_id} not found")
            return False

        if network_id in self.connectors:
            Logger.warning(f"Already connected to network {network_id}")
            return False

        network_config = self.networks[network_id]
        factory = Factory(network_config, self.db, self.plugin_manager, self)
        self.factories[network_id] = factory

        try:
            if network_config.enable_ssl:
                connector = reactor.connectSSL(
                    network_config.address,
                    network_config.port,
                    factory,
                    ssl.ClientContextFactory()
                )
            else:
                connector = reactor.connectTCP(
                    network_config.address,
                    network_config.port,
                    factory
                )

            self.connectors[network_id] = connector
            Logger.info(f"Connecting to network: {network_config.name}")
            return True

        except Exception as e:
            Logger.error(f"Failed to connect to network {network_id}: {e}")
            return False

    def disconnect_network(self, network_id: int, reconnect: bool = False) -> bool:
        if network_id not in self.connectors:
            Logger.warning(f"Not connected to network {network_id}")
            return False

        try:
            connector = self.connectors[network_id]

            # Mark factory to not reconnect if requested
            if not reconnect and network_id in self.factories:
                self.factories[network_id].should_reconnect = False

            connector.disconnect()

            if not reconnect:
                del self.connectors[network_id]
                if network_id in self.factories:
                    del self.factories[network_id]

            network_name = self.networks[network_id].name
            Logger.info(f"Disconnected from network: {network_name}")
            return True

        except Exception as e:
            Logger.error(f"Failed to disconnect from network {network_id}: {e}")
            return False

    def reconnect_network(self, network_id: int) -> bool:
        if network_id in self.connectors:
            # Disconnect first, allowing reconnect
            if not self.disconnect_network(network_id, reconnect=True):
                return False

        return self.connect_network(network_id)

    def get_network_status(self, network_id: int) -> Optional[Dict]:
        if network_id not in self.networks:
            return None

        network = self.networks[network_id]
        is_connected = network_id in self.connectors

        status = {
            "id": network.id,
            "name": network.name,
            "address": network.address,
            "port": network.port,
            "ssl": network.enable_ssl,
            "connected": is_connected,
        }

        if is_connected and network_id in self.factories:
            factory = self.factories[network_id]
            if hasattr(factory, 'protocol') and factory.protocol:
                proto = factory.protocol
                status["nickname"] = getattr(proto, 'nickname', None)
                status["channels"] = getattr(proto, 'joined_channels', [])

        return status

    def list_networks(self) -> List[Dict]:
        return [self.get_network_status(net_id) for net_id in self.networks.keys()]

    def connect_all(self):
        for network_id in self.networks.keys():
            self.connect_network(network_id)

    def disconnect_all(self):
        for network_id in list(self.connectors.keys()):
            self.disconnect_network(network_id)

    def get_factory(self, network_id: int) -> Optional[Factory]:
        return self.factories.get(network_id)

    def get_protocol(self, network_id: int):
        factory = self.get_factory(network_id)
        if factory and hasattr(factory, 'protocol'):
            return factory.protocol
        return None
