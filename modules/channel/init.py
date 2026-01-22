"""
Channel Module for ServiceX
Provides IRC channel management commands

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

from typing import List


# ============================================================================
# Module Metadata
# ============================================================================

MODULE_INFO = {
    "name": "Channel",
    "author": "Helena Bolan",
    "version": "2.0",
    "description": "IRC channel management and information commands"
}


# ============================================================================
# Helper Functions
# ============================================================================

def format_channel_list(channels: List[str]) -> str:
    """
    Format a list of channels into a natural language string
    
    Args:
        channels: List of channel names
    
    Returns:
        Formatted string describing channels
    """
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


# ============================================================================
# Command Functions
# ============================================================================

def command_chanjoin(bot, target: str, nickname: str, args: List[str]):
    """
    Join an IRC channel
    
    Usage: chanjoin [CHANNEL]
    
    If no channel is specified and the command is used in a channel,
    rejoins the current channel. Otherwise, joins the specified channel.
    The channel will be saved to the database for auto-join on reconnect.
    
    Examples:
        chanjoin #general
        chanjoin (when used in a channel, rejoins that channel)
    """
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chanjoin CHANNEL", nickname)
            return
    
    if not channel_name.startswith('#'):
        bot.send_message(target, f"Invalid channel name: {channel_name}", nickname)
        return
    
    bot.join_channel(channel_name, save_to_db=True)
    bot.send_message(target, f"Joining channel: {channel_name}", nickname)


def command_chanpart(bot, target: str, nickname: str, args: List[str]):
    """
    Leave an IRC channel
    
    Usage: chanpart [CHANNEL]
    
    If no channel is specified and the command is used in a channel,
    leaves the current channel. Otherwise, leaves the specified channel.
    The channel will be removed from the database.
    
    Examples:
        chanpart #general
        chanpart (when used in a channel, leaves that channel)
    """
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chanpart CHANNEL", nickname)
            return
    
    if not channel_name.startswith('#'):
        bot.send_message(target, f"Invalid channel name: {channel_name}", nickname)
        return
    
    bot.part_channel(channel_name, save_to_db=True)
    
    # Send confirmation to a different target if we're leaving the current channel
    response_target = target if target != channel_name else nickname
    bot.send_message(response_target, f"Left channel: {channel_name}", nickname)


def command_chancycle(bot, target: str, nickname: str, args: List[str]):
    """
    Cycle (part and rejoin) an IRC channel
    
    Usage: chancycle [CHANNEL]
    
    If no channel is specified and the command is used in a channel,
    cycles the current channel. Otherwise, cycles the specified channel.
    This does not modify the database - the channel status remains unchanged.
    
    Useful for refreshing channel state, regaining ops, or troubleshooting.
    
    Examples:
        chancycle #general
        chancycle (when used in a channel, cycles that channel)
    """
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chancycle CHANNEL", nickname)
            return
    
    if not channel_name.startswith('#'):
        bot.send_message(target, f"Invalid channel name: {channel_name}", nickname)
        return
    
    # Part and rejoin without database updates
    bot.part_channel(channel_name, save_to_db=False)
    bot.join_channel(channel_name, save_to_db=False)
    
    # Send confirmation to a different target if we're cycling the current channel
    response_target = target if target != channel_name else nickname
    bot.send_message(response_target, f"Cycling channel: {channel_name}", nickname)


def command_chanlist(bot, target: str, nickname: str, args: List[str]):
    """
    List channels the bot is currently in
    
    Usage: chanlist [MODE]
    
    Modes:
        (none)  Simple comma-separated list
        count   Show only the number of channels
        fancy   Natural language description with count
    
    Examples:
        chanlist
        chanlist count
        chanlist fancy
    """
    mode = args[0].lower() if args else "simple"
    
    channels = sorted(bot.joined_channels)
    
    if mode == "count":
        # Just show the count
        count = len(channels)
        bot.send_message(
            target,
            f"{count} channel{'s' if count != 1 else ''}",
            nickname
        )
    
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
    """
    Get information about a channel
    
    Usage: chaninfo [CHANNEL]
    
    If no channel is specified and the command is used in a channel,
    shows info about the current channel. Otherwise, shows info about
    the specified channel.
    
    Examples:
        chaninfo #general
        chaninfo (when used in a channel, shows info about that channel)
    """
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chaninfo CHANNEL", nickname)
            return
    
    if not channel_name.startswith('#'):
        bot.send_message(target, f"Invalid channel name: {channel_name}", nickname)
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
    """
    Save current channel to database for auto-join
    
    Usage: chansave [CHANNEL]
    
    Adds a channel to the auto-join list without actually joining it.
    Useful for pre-configuring channels to join on next connection.
    
    Examples:
        chansave #general
        chansave (when used in a channel, saves that channel)
    """
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chansave CHANNEL", nickname)
            return
    
    if not channel_name.startswith('#'):
        bot.send_message(target, f"Invalid channel name: {channel_name}", nickname)
        return
    
    # Check if already in database
    channels_in_db = bot.db.get_channels(bot.factory.config.id)
    
    if channel_name in channels_in_db:
        bot.send_message(target, f"Channel {channel_name} already saved", nickname)
    else:
        bot.db.add_channel(bot.factory.config.id, channel_name)
        bot.send_message(target, f"Saved channel {channel_name} for auto-join", nickname)


def command_chanunsave(bot, target: str, nickname: str, args: List[str]):
    """
    Remove channel from database auto-join list
    
    Usage: chanunsave [CHANNEL]
    
    Removes a channel from the auto-join list without actually leaving it.
    The bot will stay in the channel but won't rejoin on reconnect.
    
    Examples:
        chanunsave #general
        chanunsave (when used in a channel, unsaves that channel)
    """
    if args:
        channel_name = args[0]
    else:
        # Default to current target if in a channel
        if target.startswith('#'):
            channel_name = target
        else:
            bot.send_message(target, "Usage: chanunsave CHANNEL", nickname)
            return
    
    if not channel_name.startswith('#'):
        bot.send_message(target, f"Invalid channel name: {channel_name}", nickname)
        return
    
    # Check if in database
    channels_in_db = bot.db.get_channels(bot.factory.config.id)
    
    if channel_name not in channels_in_db:
        bot.send_message(target, f"Channel {channel_name} not in auto-join list", nickname)
    else:
        bot.db.remove_channel(bot.factory.config.id, channel_name)
        bot.send_message(target, f"Removed {channel_name} from auto-join list", nickname)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'MODULE_INFO',
    'command_chanjoin',
    'command_chanpart',
    'command_chancycle',
    'command_chanlist',
    'command_chaninfo',
    'command_chansave',
    'command_chanunsave',
]
