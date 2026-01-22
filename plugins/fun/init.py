"""
Fun Plugin for ServiceX
Provides entertainment and novelty commands for IRC bot

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

from typing import List, Dict, Tuple
from random import randint
from getopt import getopt, GetoptError
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    from requests import get
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ============================================================================
# Plugin Metadata
# ============================================================================

PLUGIN_INFO = {
    "name": "Fun",
    "author": "Helena Bolan",
    "version": "2.0",
    "description": "Entertainment and novelty commands"
}


# ============================================================================
# ASCII Art Definitions
# ============================================================================

DIGIT_ART: Dict[str, Tuple[str, ...]] = {
    '0': ('██████', '██  ██', '██  ██', '██  ██', '██████'),
    '1': ('    ██', '    ██', '    ██', '    ██', '    ██'),
    '2': ('██████', '    ██', '██████', '██    ', '██████'),
    '3': ('██████', '    ██', '██████', '    ██', '██████'),
    '4': ('██  ██', '██  ██', '██████', '    ██', '    ██'),
    '5': ('██████', '██    ', '██████', '    ██', '██████'),
    '6': ('██████', '██    ', '██████', '██  ██', '██████'),
    '7': ('██████', '    ██', '    ██', '    ██', '    ██'),
    '8': ('██████', '██  ██', '██████', '██  ██', '██████'),
    '9': ('██████', '██  ██', '██████', '    ██', '██████'),
    ':': ('      ', '  ██  ', '      ', '  ██  ', '      '),
}


# ============================================================================
# Helper Functions
# ============================================================================

def render_ascii_text(text: str, char_map: Dict[str, Tuple[str, ...]]) -> List[str]:
    """
    Render text as ASCII art using a character map
    
    Args:
        text: Text to render
        char_map: Dictionary mapping characters to ASCII art tuples
    
    Returns:
        List of strings representing each line of the ASCII art
    """
    # Filter text to only include supported characters
    filtered_text = ''.join(c for c in text if c in char_map)
    
    if not filtered_text:
        return []
    
    # Get ASCII representation for each character
    char_art = [char_map[char] for char in filtered_text]
    
    # Combine horizontally (assuming all have same height)
    height = len(char_art[0])
    lines = []
    
    for row in range(height):
        line_parts = [art[row] for art in char_art]
        lines.append(' '.join(line_parts))
    
    return lines


def fetch_developer_excuse() -> str:
    """
    Fetch a random developer excuse from developerexcuses.com
    
    Returns:
        Excuse text or error message
    """
    if not REQUESTS_AVAILABLE:
        return "Required libraries (requests, beautifulsoup4) not available"
    
    try:
        response = get('http://developerexcuses.com/', timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, features="html.parser")
        elem = soup.find('a')
        
        if elem and elem.text:
            # Handle encoding issues gracefully
            return elem.text.encode('ascii', 'ignore').decode()
        else:
            return "Could not parse excuse from website"
    
    except Exception as e:
        return f"Failed to fetch excuse: {str(e)}"


def roll_dice(count: int, sides: int) -> Tuple[bool, str, List[int]]:
    """
    Roll dice and return results
    
    Args:
        count: Number of dice to roll
        sides: Number of sides per die
    
    Returns:
        Tuple of (success, message, results)
    """
    # Validation
    if count <= 0:
        return False, "You appear to be rolling thin air.", []
    
    if count > 100:
        return False, "That's too many dice! Maximum is 100.", []
    
    if sides < 2:
        return False, "A one sided die is not possible, however a two sided die is.", []
    
    if sides > 1000:
        return False, "That's too many sides! Maximum is 1000.", []
    
    # Roll dice
    results = [randint(1, sides) for _ in range(count)]
    
    return True, "", results


def format_dice_results(count: int, sides: int, results: List[int]) -> str:
    """
    Format dice roll results into a readable message
    
    Args:
        count: Number of dice rolled
        sides: Number of sides per die
        results: List of roll results
    
    Returns:
        Formatted message string
    """
    if count == 1:
        return f"You rolled a single die with {sides} sides and got a {results[0]}."
    
    # For multiple dice
    total = sum(results)
    results_str = results[:-1]
    last_result = results[-1]
    
    if count == 2:
        return (
            f"You rolled {count} dice with {sides} sides and got "
            f"a {results_str[0]} and a {last_result}. Total: {total}"
        )
    else:
        result_list = ", ".join(str(r) for r in results_str)
        return (
            f"You rolled {count} dice with {sides} sides and got "
            f"{result_list}, and a {last_result}. Total: {total}"
        )


# ============================================================================
# Command Functions
# ============================================================================

def command_why(bot, target: str, nickname: str, args: List[str]):
    """
    Fetch a random developer excuse
    
    Usage: why
    
    Retrieves a random programming-related excuse from developerexcuses.com
    
    Examples:
        why
    """
    excuse = fetch_developer_excuse()
    bot.send_message(target, excuse, nickname)


def command_digits(bot, target: str, nickname: str, args: List[str]):
    """
    Display numbers as ASCII art
    
    Usage: digits NUMBER [NUMBER...]
    
    Converts numeric input into block ASCII art display.
    Only digits 0-9 are supported.
    
    Examples:
        digits 42
        digits 123 456
        digits 8675309
    """
    if not args:
        bot.send_message(target, "Usage: digits NUMBER [NUMBER...]", nickname)
        return
    
    # Join all arguments and filter to digits only
    text = ''.join(args)
    digits_only = ''.join(c for c in text if c.isdigit())
    
    if not digits_only:
        bot.send_message(target, "No valid digits provided", nickname)
        return
    
    if len(digits_only) > 20:
        bot.send_message(target, "Too many digits! Maximum is 20.", nickname)
        return
    
    # Render and send ASCII art
    lines = render_ascii_text(digits_only, DIGIT_ART)
    for line in lines:
        bot.send_message(target, line, nickname)


def command_digiclock(bot, target: str, nickname: str, args: List[str]):
    """
    Display current time as ASCII art clock
    
    Usage: digiclock [-t TIMEZONE]
    
    Options:
        -t, --timezone  Timezone (e.g., 'US/Eastern', 'Europe/London')
    
    Shows the current time in large ASCII block numbers.
    
    Examples:
        digiclock
        digiclock -t US/Pacific
        digiclock --timezone Europe/Paris
    """
    timezone_arg = None
    
    try:
        opts, _ = getopt(args, "t:", ["timezone="])
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return
    
    for opt, arg in opts:
        if opt in ("-t", "--timezone"):
            timezone_arg = arg
    
    # Get current time
    try:
        if timezone_arg:
            from pytz import timezone as pytz_timezone
            now = datetime.now(pytz_timezone(timezone_arg))
        else:
            now = datetime.now()
        
        time_str = now.strftime('%H:%M:%S')
    except Exception as e:
        bot.send_message(target, f"Error getting time: {e}", nickname)
        return
    
    # Render and send ASCII art
    lines = render_ascii_text(time_str, DIGIT_ART)
    for line in lines:
        bot.send_message(target, line, nickname)


def command_dice(bot, target: str, nickname: str, args: List[str]):
    """
    Roll dice with customizable count and sides
    
    Usage: dice [-c COUNT] [-s SIDES]
    
    Options:
        -c, --count  Number of dice to roll (default: 1, max: 100)
        -s, --sides  Number of sides per die (default: 6, max: 1000)
    
    Roll virtual dice and get random results. Perfect for games
    and random number generation.
    
    Examples:
        dice
        dice -c 3
        dice -s 20
        dice -c 2 -s 6
        dice --count 5 --sides 12
    """
    dice_count = 1
    dice_sides = 6
    
    try:
        opts, _ = getopt(args, "c:s:", ["count=", "sides="])
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return
    
    for opt, arg in opts:
        if opt in ("-c", "--count"):
            try:
                dice_count = int(arg)
            except ValueError:
                bot.send_message(target, f"Invalid count: {arg}", nickname)
                return
        
        elif opt in ("-s", "--sides"):
            try:
                dice_sides = int(arg)
            except ValueError:
                bot.send_message(target, f"Invalid sides: {arg}", nickname)
                return
    
    # Roll the dice
    success, message, results = roll_dice(dice_count, dice_sides)
    
    if not success:
        bot.send_message(target, message, nickname)
        return
    
    # Format and send results
    result_message = format_dice_results(dice_count, dice_sides, results)
    bot.send_message(target, result_message, nickname)


def command_coin(bot, target: str, nickname: str, args: List[str]):
    """
    Flip a coin (or multiple coins)
    
    Usage: coin [-c COUNT]
    
    Options:
        -c, --count  Number of coins to flip (default: 1, max: 100)
    
    Flip virtual coins and get heads or tails results.
    
    Examples:
        coin
        coin -c 3
        coin --count 10
    """
    coin_count = 1
    
    try:
        opts, _ = getopt(args, "c:", ["count="])
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return
    
    for opt, arg in opts:
        if opt in ("-c", "--count"):
            try:
                coin_count = int(arg)
            except ValueError:
                bot.send_message(target, f"Invalid count: {arg}", nickname)
                return
    
    if coin_count <= 0:
        bot.send_message(target, "You need to flip at least one coin!", nickname)
        return
    
    if coin_count > 100:
        bot.send_message(target, "That's too many coins! Maximum is 100.", nickname)
        return
    
    # Flip coins
    results = ['Heads' if randint(0, 1) == 0 else 'Tails' for _ in range(coin_count)]
    heads_count = results.count('Heads')
    tails_count = results.count('Tails')
    
    if coin_count == 1:
        bot.send_message(target, f"You flipped: {results[0]}", nickname)
    else:
        result_str = ', '.join(results[:-1]) + f', and {results[-1]}'
        summary = f"Heads: {heads_count}, Tails: {tails_count}"
        bot.send_message(
            target,
            f"You flipped {coin_count} coins: {result_str}. ({summary})",
            nickname
        )


def command_8ball(bot, target: str, nickname: str, args: List[str]):
    """
    Ask the Magic 8-Ball a question
    
    Usage: 8ball QUESTION
    
    Ask a yes/no question and receive mystical guidance.
    
    Examples:
        8ball Will it rain tomorrow?
        8ball Should I learn Python?
    """
    if not args:
        bot.send_message(target, "Ask me a question!", nickname)
        return
    
    responses = [
        # Positive
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes, definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        # Non-committal
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        # Negative
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful.",
    ]
    
    answer = responses[randint(0, len(responses) - 1)]
    bot.send_message(target, f"{answer}", nickname)


# ============================================================================
# Plugin Exports
# ============================================================================

__all__ = [
    'PLUGIN_INFO',
    'command_why',
    'command_digits',
    'command_digiclock',
    'command_dice',
    'command_coin',
    'command_8ball',
]
