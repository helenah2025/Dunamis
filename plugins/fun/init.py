"""
Fun Plugin for ServiceX
Provides entertainment and novelty commands for IRC bot

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


PLUGIN_INFO = {
    "name": "Fun",
    "author": "Helenah, Helena Bolan",
    "version": "2.0",
    "description": "Entertainment and novelty commands"
}


# Block style
DIGIT_ART_BLOCK: Dict[str, Tuple[str, ...]] = {
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


# Braille style
DIGIT_ART_BRAILLE: Dict[str, Tuple[str, ...]] = {
    '0': ('⣾⠛⢻⡆', '⣿⠀⢸⡇', '⢿⣤⣼⠇'),
    '1': ('⢸⡇', '⢸⡇', '⢸⡇'),
    '2': ('⠙⠛⢻⡆', '⣴⠶⠾⠃', '⢿⣤⣤⡀'),
    '3': ('⠙⠛⢻⡆', '⠰⠶⢾⡇', '⣠⣤⣼⠇'),
    '4': ('⣿⠀⢸⡇', '⠻⠶⢾⡇', '⠀⠀⢸⡇'),
    '5': ('⣾⠛⠛⠁', '⠻⠶⢶⡄', '⢠⣤⣼⠇'),
    '6': ('⣾⠛⠛⠁', '⣿⠶⢶⡄', '⢿⣤⣼⠇'),
    '7': ('⠙⠛⢻⡇', '⠀⠀⢸⡇', '⠀⠀⢸⡇'),
    '8': ('⣾⠛⢻⡆', '⣿⠶⢾⡇', '⢿⣤⣼⠇'),
    '9': ('⣾⠛⢻⡆', '⠻⠶⢾⡇', '⢠⣤⣼⠇'),
    ':': ('⢀⡀', '⢈⡁', '⠈⠁'),
}


# Style registry
DIGIT_STYLES = {
    'block': DIGIT_ART_BLOCK,
    'braille': DIGIT_ART_BRAILLE,
}


DEFAULT_STYLE = 'block'


def render_ascii_text(
        text: str, char_map: Dict[str, Tuple[str, ...]]) -> List[str]:
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
    max_dice = 150
    max_sides = 150

    # Validation
    if count <= 0:
        return False, "You appear to be rolling thin air.", []

    if count > max_dice:
        return False, f"That's too many dice! Maximum is {max_dice}.", []

    if sides == 0:
        return False, "A zero sided die is not possible, however a two sided die is.", []

    if sides == 1:
        return False, "A one sided die is not possible, however a two sided die is.", []

    if sides > max_sides:
        return False, f"That's too many sides! Maximum is {max_sides}.", []

    # Roll dice
    results = [randint(1, sides) for _ in range(count)]

    return True, "", results


def format_dice_results(count: int, sides: int, results: List[int]) -> str:
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


def command_why(bot, target: str, nickname: str, args: List[str]):
    excuse = fetch_developer_excuse()
    bot.send_message(target, excuse, nickname)


def command_digits(bot, target: str, nickname: str, args: List[str]):
    style = DEFAULT_STYLE
    use_braille_blank = False

    try:
        opts, remaining_args = getopt(args, "s:b", ["style=", "braille-blank"])
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return

    for opt, arg in opts:
        if opt in ("-s", "--style"):
            if arg in DIGIT_STYLES:
                style = arg
            else:
                available = ', '.join(DIGIT_STYLES.keys())
                bot.send_message(
                    target,
                    f"Unknown style '{arg}'. Available: {available}",
                    nickname
                )
                return

        elif opt in ("-b", "--braille-blank"):
            use_braille_blank = True

    if not remaining_args:
        bot.send_message(target, "Usage: digits [-s STYLE] [-b] NUMBER [NUMBER...]", nickname)
        return

    # Join all arguments and filter to digits only
    text = ''.join(remaining_args)
    digits_only = ''.join(c for c in text if c.isdigit())

    if not digits_only:
        bot.send_message(target, "No valid digits provided", nickname)
        return

    if len(digits_only) > 20:
        bot.send_message(target, "Too many digits! Maximum is 20.", nickname)
        return

    # Render and send ASCII art
    char_map = DIGIT_STYLES[style]
    lines = render_ascii_text(digits_only, char_map)

    # Replace spaces with braille blank if requested
    if use_braille_blank:
        lines = [line.replace(' ', '\u2800') for line in lines]

    for line in lines:
        bot.send_message(target, line, nickname)


def command_digiclock(bot, target: str, nickname: str, args: List[str]):
    timezone_arg = None
    style = DEFAULT_STYLE
    use_braille_blank = False

    try:
        opts, _ = getopt(args, "t:s:b", ["timezone=", "style=", "braille-blank"])
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return

    for opt, arg in opts:
        if opt in ("-t", "--timezone"):
            timezone_arg = arg
        elif opt in ("-s", "--style"):
            if arg in DIGIT_STYLES:
                style = arg
            else:
                available = ', '.join(DIGIT_STYLES.keys())
                bot.send_message(
                    target,
                    f"Unknown style '{arg}'. Available: {available}",
                    nickname
                )
                return

        elif opt in ("-b", "--braille-blank"):
            use_braille_blank = True

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
    char_map = DIGIT_STYLES[style]
    lines = render_ascii_text(time_str, char_map)

    # Replace spaces with braille blank if requested
    if use_braille_blank:
        lines = [line.replace(' ', '\u2800') for line in lines]

    for line in lines:
        bot.send_message(target, line, nickname)


def command_dice(bot, target: str, nickname: str, args: List[str]):
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
        bot.send_message(
            target,
            "You need to flip at least one coin!",
            nickname)
        return

    if coin_count > 100:
        bot.send_message(
            target,
            "That's too many coins! Maximum is 100.",
            nickname)
        return

    # Flip coins
    results = [
        'Heads' if randint(
            0,
            1) == 0 else 'Tails' for _ in range(coin_count)]
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


__all__ = [
    'PLUGIN_INFO',
    'command_why',
    'command_digits',
    'command_digiclock',
    'command_dice',
    'command_coin',
    'command_8ball',
]
