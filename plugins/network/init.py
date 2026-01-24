"""
Network Plugin for Dunamis
Provides IRC network management commands

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

from typing import List
from getopt import getopt, GetoptError


PLUGIN_INFO = {
    "name": "Network",
    "author": "Helenah, Helena Bolan",
    "version": "1.0",
    "description": "IRC network management commands"
}


def get_network_manager(bot):
    if hasattr(bot, 'factory') and hasattr(bot.factory, 'network_manager'):
        return bot.factory.network_manager
    return None


def format_network_info(status: dict) -> str:
    lines = [
        f"Network: {status['name']} (ID: {status['id']})",
        f"  Address: {status['address']}:{status['port']}",
        f"  SSL: {'Yes' if status['ssl'] else 'No'}",
        f"  Status: {'Connected' if status['connected'] else 'Disconnected'}",
    ]

    if status.get('nickname'):
        lines.append(f"  Nickname: {status['nickname']}")

    if status.get('channels'):
        channel_list = ', '.join(status['channels'])
        lines.append(f"  Channels: {channel_list}")

    return '\n'.join(lines)


def format_network_list(networks: List[dict]) -> str:
    if not networks:
        return "No networks configured"

    lines = []
    for net in networks:
        lines.append(
            f"ID: {net['id']}, Name: {net['name']}, Address: {net['address']}, Port: {net['port']}"
        )

    return '\n'.join(lines)


def command_network(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if network_manager is None:
        bot.send_message(target, "Error: network manager not available", nickname)
        return

    handlers = {
        "list": handle_list,
        "info": handle_info,
        "connect": handle_connect,
        "disconnect": handle_disconnect,
        "reconnect": handle_reconnect,
        "current": handle_current,
        "add": handle_add,
        "remove": handle_remove,
        "modify": handle_modify,
    }

    subcommand_list = ", ".join(handlers.keys())

    if not args:
        bot.send_message(
            target,
            f"Usage: requires a subcommand: {subcommand_list}",
            nickname
        )
        return

    subcommand = args[0].lower()
    subargs = args[1:]

    handler = handlers.get(subcommand)

    if handler:
        handler(bot, target, nickname, subargs)
    else:
        bot.send_message(
            target,
            f"Error: unknown subcommand: {subcommand} - available: {subcommand_list}",
            nickname
        )


def handle_list(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)
    networks = network_manager.list_networks()
    output = format_network_list(networks)
    bot.send_message(target, output, nickname)


def handle_info(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network info NETWORK_ID", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    status = network_manager.get_network_status(network_id)

    if status is None:
        bot.send_message(target, f"Error: network not found: {network_id}", nickname)
        return

    output = format_network_info(status)
    bot.send_message(target, output, nickname)


def handle_connect(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network connect NETWORK_ID", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    if network_manager.connect_network(network_id):
        network_name = network_manager.networks[network_id].name
        bot.send_message(
            target,
            f"Success: connecting to network: {network_name}",
            nickname
        )
    else:
        bot.send_message(
            target,
            f"Error: failed to connect to network: {network_id}",
            nickname
        )


def handle_disconnect(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network disconnect NETWORK_ID", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    if network_manager.disconnect_network(network_id):
        network_name = network_manager.networks[network_id].name
        bot.send_message(
            target,
            f"Success: disconnected from network: {network_name}",
            nickname
        )
    else:
        bot.send_message(
            target,
            f"Error: failed to disconnect from network: {network_id}",
            nickname
        )


def handle_reconnect(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network reconnect NETWORK_ID", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    if network_manager.reconnect_network(network_id):
        network_name = network_manager.networks[network_id].name
        bot.send_message(
            target,
            f"Success: reconnecting to network: {network_name}",
            nickname
        )
    else:
        bot.send_message(
            target,
            f"Error: failed to reconnect to network: {network_id}",
            nickname
        )


def handle_current(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)
    network_id = bot.factory.config.id
    status = network_manager.get_network_status(network_id)

    if status is None:
        bot.send_message(target, "Error: current network not found", nickname)
        return

    output = format_network_info(status)
    bot.send_message(target, output, nickname)


def handle_add(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    # Parse options
    name = None
    address = None
    port = None
    enable_ssl = False
    nicknames = "Dunamis"
    ident = "dunamis"
    realname = "Dunamis IRC Bot"
    services_user = ""
    services_pass = ""
    oper_user = ""
    oper_pass = ""
    trigger = "!"

    try:
        opts, _ = getopt(
            args,
            "n:a:p:s",
            [
                "name=", "address=", "port=", "ssl",
                "nick=", "ident=", "realname=",
                "services-user=", "services-pass=",
                "oper-user=", "oper-pass=",
                "trigger="
            ]
        )

        for opt, arg in opts:
            if opt in ("-n", "--name"):
                name = arg
            elif opt in ("-a", "--address"):
                address = arg
            elif opt in ("-p", "--port"):
                port = int(arg)
            elif opt in ("-s", "--ssl"):
                enable_ssl = True
            elif opt == "--nick":
                nicknames = arg
            elif opt == "--ident":
                ident = arg
            elif opt == "--realname":
                realname = arg
            elif opt == "--services-user":
                services_user = arg
            elif opt == "--services-pass":
                services_pass = arg
            elif opt == "--oper-user":
                oper_user = arg
            elif opt == "--oper-pass":
                oper_pass = arg
            elif opt == "--trigger":
                trigger = arg

    except GetoptError as e:
        bot.send_message(target, f"Error: invalid option: {e}", nickname)
        return
    except ValueError:
        bot.send_message(target, "Error: port must be a number", nickname)
        return

    # Validate required fields
    if not name:
        bot.send_message(target, "Error: network name required (-n NAME)", nickname)
        return

    if not address:
        bot.send_message(target, "Error: server address required (-a ADDRESS)", nickname)
        return

    # Set default port based on SSL
    if port is None:
        port = 6697 if enable_ssl else 6667

    # Add network to database
    try:
        network_id = bot.db.add_network(
            name=name,
            address=address,
            port=port,
            enable_ssl=enable_ssl,
            nicknames=nicknames,
            ident=ident,
            realname=realname,
            services_username=services_user,
            services_password=services_pass,
            oper_username=oper_user,
            oper_password=oper_pass,
            command_trigger=trigger
        )

        # Reload networks in network manager
        network_manager.load_networks()

        bot.send_message(
            target,
            f"Success: added network '{name}' (ID: {network_id}). Use 'network connect {network_id}' to connect.",
            nickname
        )

    except Exception as e:
        bot.send_message(target, f"Error: failed to add network: {e}", nickname)


def handle_remove(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network remove NETWORK_ID", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    # Don't allow removing currently connected networks
    if network_id in network_manager.connectors:
        bot.send_message(
            target,
            f"Error: cannot remove connected network. Disconnect first with 'network disconnect {network_id}'",
            nickname
        )
        return

    # Remove from database
    try:
        network_name = network_manager.networks.get(network_id, {}).get('name', str(network_id))

        if bot.db.remove_network(network_id):
            # Reload networks
            network_manager.load_networks()
            bot.send_message(
                target,
                f"Success: removed network '{network_name}' (ID: {network_id})",
                nickname
            )
        else:
            bot.send_message(target, f"Error: network {network_id} not found", nickname)

    except Exception as e:
        bot.send_message(target, f"Error: failed to remove network: {e}", nickname)


def handle_modify(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network modify NETWORK_ID [OPTIONS]", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    remaining_args = args[1:]

    if not remaining_args:
        bot.send_message(target, "Error: no modifications specified", nickname)
        return

    # Parse modification options
    updates = {}

    try:
        opts, _ = getopt(
            remaining_args,
            "n:a:p:s:",
            [
                "name=", "address=", "port=", "ssl=",
                "nick=", "ident=", "realname=",
                "services-user=", "services-pass=",
                "oper-user=", "oper-pass=",
                "trigger="
            ]
        )

        for opt, arg in opts:
            if opt in ("-n", "--name"):
                updates['name'] = arg
            elif opt in ("-a", "--address"):
                updates['address'] = arg
            elif opt in ("-p", "--port"):
                updates['port'] = int(arg)
            elif opt in ("-s", "--ssl"):
                updates['enable_ssl'] = arg.lower() in ('true', 'yes', '1')
            elif opt == "--nick":
                updates['nicknames'] = arg
            elif opt == "--ident":
                updates['ident'] = arg
            elif opt == "--realname":
                updates['realname'] = arg
            elif opt == "--services-user":
                updates['services_username'] = arg
            elif opt == "--services-pass":
                updates['services_password'] = arg
            elif opt == "--oper-user":
                updates['oper_username'] = arg
            elif opt == "--oper-pass":
                updates['oper_password'] = arg
            elif opt == "--trigger":
                updates['command_trigger'] = arg

    except GetoptError as e:
        bot.send_message(target, f"Error: invalid option: {e}", nickname)
        return
    except ValueError:
        bot.send_message(target, "Error: port must be a number", nickname)
        return

    # Warn if network is connected
    if network_id in network_manager.connectors:
        bot.send_message(
            target,
            f"Warning: network {network_id} is currently connected. Changes will take effect after reconnect.",
            nickname
        )

    # Update database
    try:
        if bot.db.update_network(network_id, updates):
            # Reload networks
            network_manager.load_networks()
            bot.send_message(
                target,
                f"Success: modified network: {network_id}",
                nickname
            )
        else:
            bot.send_message(target, f"Error: network not found: {network_id}", nickname)

    except Exception as e:
        bot.send_message(target, f"Error: failed to modify network: {e}", nickname)


__all__ = [
    'PLUGIN_INFO',
    'command_network',
]
