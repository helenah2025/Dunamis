"""
Channel Plugin for ServiceX
Provides IRC channel management commands

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
    "name": "Channel",
    "author": "Helenah, Helena Bolan",
    "version": "2.0",
    "description": "IRC channel management and information commands"
}


def format_channel_list(channels: List[str]) -> str:
    if not channels:
        return "I am not in any channels on this IRC network."

    if len(channels) == 1:
        return f"I am just in {channels[0]} on this IRC network."

    # Multiple channels
    all_but_last = ", ".join(channels[:-1])
    last_channel = channels[-1]
    total = len(channels)

    return (
        f"I am in {all_but_last} and {last_channel} on this IRC network, "
        f"a total of {total} channel{'s' if total != 1 else ''}."
    )


def command_channel(bot, target: str, nickname: str, args: List[str]):
    try:
        opts, _ = getopt(
            args, "j:p:c:l:i:a:", [
                "format=", "preset=", "timezone="])
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return

    for opt, arg in opts:
        if opt in ("-j", "--join"):
            join_arg = arg
        elif opt in ("-p", "--part"):
            part_arg = arg
        elif opt in ("-c", "--cycle"):
            cycle_arg = arg
        elif opt in ("-l", "--list"):
            list_arg = arg
        elif opt in ("-i", "--info"):
            info_arg = arg
        elif opt in ("-a", "--autojoin"):
            autojoin_arg = arg


def command_chanjoin(bot, target: str, nickname: str, args: List[str]):
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chanjoin [channel]", nickname)
            return

    if not channel_name.startswith('#'):
        bot.send_message(
            target,
            f"Invalid channel name: {channel_name}",
            nickname)
        return

    # Send confirmation and then join channel
    bot.send_message(target, f"Joining channel: {channel_name}", nickname)
    bot.join_channel(channel_name, save_to_db=True)


def command_chanpart(bot, target: str, nickname: str, args: List[str]):
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chanpart [channel]", nickname)
            return

    if not channel_name.startswith('#'):
        bot.send_message(
            target,
            f"Invalid channel name: {channel_name}",
            nickname)
        return

    # Send confirmation and then part channel
    bot.send_message(target, f"Parting channel: {channel_name}", nickname)
    bot.part_channel(channel_name, save_to_db=True)


def command_chancycle(bot, target: str, nickname: str, args: List[str]):
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chancycle [channel]", nickname)
            return

    if not channel_name.startswith('#'):
        bot.send_message(
            target,
            f"Invalid channel name: {channel_name}",
            nickname)
        return

    # Send confirmation and then cycle channel
    bot.send_message(target, f"Cycling channel: {channel_name}", nickname)
    bot.leave(channel_name)
    bot.join(channel_name)


def command_chanlist(bot, target: str, nickname: str, args: List[str]):
    mode = args[0].lower() if args else "simple"
    channels = sorted(bot.joined_channels)

    if mode == "count":
        # Just show the count
        count = len(channels)
        bot.send_message(target, count, nickname)

    elif mode == "fancy":
        # Natural language description
        message = format_channel_list(channels)
        bot.send_message(target, message, nickname)

    elif mode == "simple":
        # Simple comma-separated list
        if channels:
            bot.send_message(target, ", ".join(channels), nickname)
        else:
            bot.send_message(target, "Not in any channels", nickname)

    else:
        # Unknown mode
        bot.send_message(
            target,
            f"Unknown mode: {mode}. Use: simple, count, or fancy",
            nickname
        )


def command_chaninfo(bot, target: str, nickname: str, args: List[str]):
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chaninfo [channel]", nickname)
            return

    if not channel_name.startswith('#'):
        bot.send_message(
            target,
            f"Invalid channel name: {channel_name}",
            nickname)
        return

    # Check if bot is in the channel
    if channel_name in bot.joined_channels:
        status = "Joined"
    else:
        status = "Not joined"

    # Check if channel is in database
    channels_in_db = bot.db.get_channels(bot.factory.config.id)
    in_database = "Yes" if channel_name in channels_in_db else "No"

    info = (
        f"Channel: {channel_name}\n"
        f"Status: {status}\n"
        f"Auto-join: {in_database}"
    )

    bot.send_message(target, info, nickname)


def command_chansave(bot, target: str, nickname: str, args: List[str]):
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chansave [channel]", nickname)
            return

    if not channel_name.startswith('#'):
        bot.send_message(
            target,
            f"Invalid channel name: {channel_name}",
            nickname)
        return

    # Check if already in database
    channels_in_db = bot.db.get_channels(bot.factory.config.id)

    if channel_name in channels_in_db:
        bot.send_message(
            target,
            f"Channel {channel_name} already saved",
            nickname)
    else:
        bot.db.add_channel(bot.factory.config.id, channel_name)
        bot.send_message(
            target,
            f"Saved channel {channel_name} for auto-join",
            nickname)


def command_chanunsave(bot, target: str, nickname: str, args: List[str]):
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chanunsave [channel]", nickname)
            return

    if not channel_name.startswith('#'):
        bot.send_message(
            target,
            f"Invalid channel name: {channel_name}",
            nickname)
        return

    # Check if in database
    channels_in_db = bot.db.get_channels(bot.factory.config.id)

    if channel_name not in channels_in_db:
        bot.send_message(
            target,
            f"Channel {channel_name} not in auto-join list",
            nickname)
    else:
        bot.db.remove_channel(bot.factory.config.id, channel_name)
        bot.send_message(
            target,
            f"Removed {channel_name} from auto-join list",
            nickname)


__all__ = [
    'PLUGIN_INFO',
    'command_chanjoin',
    'command_chanpart',
    'command_chancycle',
    'command_chanlist',
    'command_chaninfo',
    'command_chansave',
    'command_chanunsave',
]
