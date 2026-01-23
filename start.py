"""
ServiceX IRC Bot
A modular IRC bot built on Twisted with plugin support

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

from pathlib import Path
from twisted.internet import reactor, ssl

from core import (
    Logger,
    DatabaseManager,
    Factory
)


def main():
    # Initialize logging first
    Logger.setup()
    Logger.info("ServiceX starting...")

    # Check database exists
    db_path = Path("servicex.db")
    if not db_path.exists():
        Logger.error("Database not found. Run 'servicex-setup' first.")
        return

    # Connect to database
    db = DatabaseManager(db_path)
    if not db.connect():
        Logger.error("Failed to connect to database")
        return

    # Load network configurations
    networks = db.get_networks()
    Logger.info(f"IRC network configurations loaded: {len(networks)}")

    # Create connections for each network
    for network_config in networks:
        factory = Factory(network_config, db)

        if network_config.use_ssl:
            reactor.connectSSL(
                network_config.address,
                network_config.port,
                factory,
                ssl.ClientContextFactory()
            )
        else:
            reactor.connectTCP(
                network_config.address,
                network_config.port,
                factory
            )

        Logger.info(f"Connecting to IRC network: {network_config.name}")

    # Start reactor
    reactor.run()


if __name__ == '__main__':
    main()
