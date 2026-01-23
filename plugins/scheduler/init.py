"""
Scheduler Plugin for ServiceX
Provides commands for testing and managing the task scheduler

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

from typing import List, Optional, Dict, Any
from getopt import getopt, GetoptError
from datetime import datetime


PLUGIN_INFO = {
    "name": "Scheduler",
    "author": "Helenah, Helena Bolan",
    "version": "1.0",
    "description": "Task scheduler management and testing commands"
}

PLUGIN_NAME = "scheduler"


def format_task_info(task_info: Dict[str, Any]) -> str:
    lines = [
        f"Task: {task_info['name']} (ID: {task_info['id']})",
        f"  State: {task_info['state']}",
        f"  Type: {'Periodic' if task_info['periodic'] else 'One-time'}",
    ]

    if task_info['periodic']:
        lines.append(f"  Interval: {task_info['interval']}s")

    if task_info['delay']:
        lines.append(f"  Initial Delay: {task_info['delay']}s")

    lines.append(f"Run Count: {task_info['run_count']}")

    if task_info['max_runs']:
        lines.append(f"  Max Runs: {task_info['max_runs']}")

    if task_info['last_run']:
        lines.append(f"  Last Run: {task_info['last_run']}")

    if task_info['plugin']:
        lines.append(f"  Plugin: {task_info['plugin']}")

    if task_info['description']:
        lines.append(f"  Description: {task_info['description']}")

    return "\n".join(lines)


def format_task_list(tasks: List[Any]) -> str:
    if not tasks:
        return "No tasks found"

    lines = []

    for task in tasks:
        task_type = "Periodic" if task.periodic else "Once"
        lines.append(
            f"ID: {task.id:<10}, Name: {task.name:<20}, State: {task.state.name:<12}, Type: {task_type:<10}, Runs: {task.run_count:<6}")

    return "\n".join(lines)


def periodic_message_callback(bot, target: str, message: str):
    """Callback for periodic message task"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    bot.send_message(target, f"[{timestamp}] {message}")


def countdown_callback(bot, target: str, task_id: str, count: List[int]):
    """Callback for countdown task"""
    if count[0] > 0:
        bot.send_message(target, f"Countdown: {count[0]}")
        count[0] -= 1
    else:
        bot.send_message(target, "Countdown complete!")
        bot.scheduler.stop_task(task_id)


def reminder_callback(bot, target: str, nickname: str, message: str):
    """Callback for one-time reminder"""
    bot.send_message(target, f"{nickname}: Reminder - {message}")


def heartbeat_callback(bot, target: str):
    """Simple heartbeat callback for testing"""
    bot.send_message(
        target,
        f"♥ Heartbeat at {datetime.now().strftime('%H:%M:%S')}")


def command_task(bot, target: str, nickname: str, args: List[str]):
    """
    Manage scheduled tasks

    Usage: task SUBCOMMAND [OPTIONS]

    Subcommands:
        list [-p PLUGIN] [-s STATE]    List all tasks
        info TASK_ID                   Show task details
        start TASK_ID                  Start a task
        stop TASK_ID                   Stop a task
        pause TASK_ID                  Pause a periodic task
        resume TASK_ID                 Resume a paused task
        remove TASK_ID                 Remove a task
        stopall                        Stop all tasks

    Examples:
        task list
        task list -s RUNNING
        task info abc123
        task start abc123
        task stop abc123
    """
    if not args:
        bot.send_message(target, "Usage: task SUBCOMMAND [OPTIONS]", nickname)
        return

    subcommand = args[0].lower()
    subargs = args[1:]

    scheduler = bot.scheduler

    if subcommand == "list":
        # Parse filter options
        plugin_filter = None
        state_filter = None

        try:
            opts, _ = getopt(subargs, "p:s:", ["plugin=", "state="])
            for opt, arg in opts:
                if opt in ("-p", "--plugin"):
                    plugin_filter = arg
                elif opt in ("-s", "--state"):
                    from servicex import TaskState
                    try:
                        state_filter = TaskState[arg.upper()]
                    except KeyError:
                        bot.send_message(
                            target, f"Invalid state: {arg}", nickname)
                        return
        except GetoptError as e:
            bot.send_message(target, f"Invalid option: {e}", nickname)
            return

        tasks = scheduler.list_tasks(
            plugin_name=plugin_filter,
            state=state_filter)
        output = format_task_list(tasks)
        bot.send_message(target, output, nickname)

    elif subcommand == "info":
        if not subargs:
            bot.send_message(target, "Usage: task info TASK_ID", nickname)
            return

        task_id = subargs[0]
        task_info = scheduler.get_task_info(task_id)

        if task_info:
            output = format_task_info(task_info)
            bot.send_message(target, output, nickname)
        else:
            bot.send_message(target, f"Task not found: {task_id}", nickname)

    elif subcommand == "start":
        if not subargs:
            bot.send_message(target, "Usage: task start TASK_ID", nickname)
            return

        task_id = subargs[0]
        if scheduler.start_task(task_id):
            task = scheduler.get_task(task_id)
            bot.send_message(
                target,
                f"Task started: ID: {task_id}, Name: {task.name}",
                nickname)
        else:
            bot.send_message(
                target,
                f"Failed to start task: {task_id}",
                nickname)

    elif subcommand == "stop":
        if not subargs:
            bot.send_message(target, "Usage: task stop TASK_ID", nickname)
            return

        task_id = subargs[0]
        if scheduler.stop_task(task_id):
            bot.send_message(target, f"Task stopped: {task_id}", nickname)
        else:
            bot.send_message(
                target,
                f"Failed to stop task: {task_id}",
                nickname)

    elif subcommand == "pause":
        if not subargs:
            bot.send_message(target, "Usage: task pause TASK_ID", nickname)
            return

        task_id = subargs[0]
        if scheduler.pause_task(task_id):
            bot.send_message(target, f"Task paused: {task_id}", nickname)
        else:
            bot.send_message(
                target,
                f"Failed to pause task: {task_id}",
                nickname)

    elif subcommand == "resume":
        if not subargs:
            bot.send_message(target, "Usage: task resume TASK_ID", nickname)
            return

        task_id = subargs[0]
        if scheduler.resume_task(task_id):
            bot.send_message(target, f"Task resumed: {task_id}", nickname)
        else:
            bot.send_message(
                target,
                f"Failed to resume task: {task_id}",
                nickname)

    elif subcommand == "remove":
        if not subargs:
            bot.send_message(target, "Usage: task remove TASK_ID", nickname)
            return

        task_id = subargs[0]
        if scheduler.remove_task(task_id):
            bot.send_message(target, f"Task removed: {task_id}", nickname)
        else:
            bot.send_message(
                target,
                f"Failed to remove task {task_id}",
                nickname)

    elif subcommand == "stopall":
        scheduler.stop_all_tasks()
        bot.send_message(target, "Stopped all tasks", nickname)

    else:
        bot.send_message(target, f"Unknown subcommand: {subcommand}", nickname)


def command_schedule(bot, target: str, nickname: str, args: List[str]):
    """
    Schedule a new task

    Usage: schedule TYPE [OPTIONS] TASK_ARGS

    Types:
        message    Send a message periodically
        reminder   Send a one-time reminder
        heartbeat  Simple periodic heartbeat for testing
        countdown  Count down from N with message each second

    Options:
        -i, --interval SECONDS   Interval for periodic tasks (default: 60)
        -d, --delay SECONDS      Initial delay before first run
        -m, --max-runs N         Maximum number of runs
        -n, --name NAME          Custom task name
        --no-start               Don't start the task immediately

    Examples:
        schedule message -i 30 "Hello every 30 seconds!"
        schedule reminder -d 300 "Meeting in 5 minutes"
        schedule heartbeat -i 10
        schedule countdown 10
        schedule message -i 60 -m 5 "This will run 5 times"
    """
    if not args:
        bot.send_message(
            target,
            "Usage: schedule TYPE [OPTIONS] TASK_ARGS",
            nickname
        )
        return

    task_type = args[0].lower()
    remaining_args = args[1:]

    # Parse options
    interval = 60.0
    delay = 0.0
    max_runs = None
    custom_name = None
    auto_start = True

    try:
        opts, task_args = getopt(
            remaining_args,
            "i:d:m:n:",
            ["interval=", "delay=", "max-runs=", "name=", "no-start"]
        )

        for opt, arg in opts:
            if opt in ("-i", "--interval"):
                interval = float(arg)
            elif opt in ("-d", "--delay"):
                delay = float(arg)
            elif opt in ("-m", "--max-runs"):
                max_runs = int(arg)
            elif opt in ("-n", "--name"):
                custom_name = arg
            elif opt == "--no-start":
                auto_start = False
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return
    except ValueError as e:
        bot.send_message(target, f"Invalid value: {e}", nickname)
        return

    scheduler = bot.scheduler
    task_id = None

    if task_type == "message":
        if not task_args:
            bot.send_message(target, "Provide a message to send", nickname)
            return

        message = " ".join(task_args)
        name = custom_name or f"periodic-msg-{target}"

        task_id = scheduler.add_task(
            name=name,
            callback=periodic_message_callback,
            interval=interval,
            args=(bot, target, message),
            periodic=True,
            delay=delay,
            max_runs=max_runs,
            plugin_name=PLUGIN_NAME,
            description=f"Periodic message: {message[:30]}...",
            auto_start=auto_start
        )

    elif task_type == "reminder":
        if not task_args:
            bot.send_message(target, "Provide a reminder message", nickname)
            return

        message = " ".join(task_args)
        name = custom_name or f"reminder-{nickname}"

        # For reminders, use delay as the trigger time
        if delay == 0.0:
            delay = interval  # Default to interval if no delay specified

        task_id = scheduler.add_task(
            name=name,
            callback=reminder_callback,
            interval=delay,
            args=(bot, target, nickname, message),
            periodic=False,
            delay=delay,
            plugin_name=PLUGIN_NAME,
            description=f"Reminder: {message[:30]}...",
            auto_start=auto_start
        )

    elif task_type == "heartbeat":
        name = custom_name or f"heartbeat-{target}"

        task_id = scheduler.add_task(
            name=name,
            callback=heartbeat_callback,
            interval=interval,
            args=(bot, target),
            periodic=True,
            delay=delay,
            max_runs=max_runs,
            plugin_name=PLUGIN_NAME,
            description="Periodic heartbeat for testing",
            auto_start=auto_start
        )

    elif task_type == "countdown":
        if not task_args:
            bot.send_message(target, "Provide a countdown number", nickname)
            return

        try:
            count_from = int(task_args[0])
        except ValueError:
            bot.send_message(target, "Invalid countdown number", nickname)
            return

        name = custom_name or f"countdown-{count_from}"
        count_holder = [count_from]  # Mutable to track countdown

        # First create the task to get its ID
        task_id = scheduler.add_task(
            name=name,
            callback=lambda: None,  # Placeholder
            interval=1.0,
            periodic=True,
            delay=delay,
            max_runs=count_from + 1,
            plugin_name=PLUGIN_NAME,
            description=f"Countdown from {count_from}",
            auto_start=False
        )

        if task_id:
            # Update the callback with the actual task ID
            task = scheduler.get_task(task_id)
            task.callback = lambda: countdown_callback(
                bot, target, task_id, count_holder)
            task.args = ()

            if auto_start:
                scheduler.start_task(task_id)

    else:
        bot.send_message(target, f"Unknown task type: {task_type}", nickname)
        return

    if task_id:
        status = "started" if auto_start else "created (not started)"
        bot.send_message(target, f"Task {status}: {task_id}", nickname)
    else:
        bot.send_message(target, "Failed to create task", nickname)


def command_modify(bot, target: str, nickname: str, args: List[str]):
    """
    Modify an existing task

    Usage: modify TASK_ID [OPTIONS]

    Options:
        -i, --interval SECONDS   New interval
        -m, --max-runs N         New maximum runs (0 for unlimited)
        -D, --description TEXT   New description

    Examples:
        modify abc123 -i 30
        modify abc123 -m 10
        modify abc123 -D "New description"
    """
    if not args:
        bot.send_message(target, "Usage: modify TASK_ID [OPTIONS]", nickname)
        return

    task_id = args[0]
    remaining = args[1:]

    # Parse options
    new_interval = None
    new_max_runs = None
    new_description = None

    try:
        opts, _ = getopt(
            remaining,
            "i:m:D:",
            ["interval=", "max-runs=", "description="]
        )

        for opt, arg in opts:
            if opt in ("-i", "--interval"):
                new_interval = float(arg)
            elif opt in ("-m", "--max-runs"):
                new_max_runs = int(arg) if int(arg) > 0 else None
            elif opt in ("-D", "--description"):
                new_description = arg
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return
    except ValueError as e:
        bot.send_message(target, f"Invalid value: {e}", nickname)
        return

    if new_interval is None and new_max_runs is None and new_description is None:
        bot.send_message(target, "No modifications specified", nickname)
        return

    if bot.scheduler.modify_task(
        task_id,
        interval=new_interval,
        max_runs=new_max_runs,
        description=new_description
    ):
        bot.send_message(target, f"Modified task {task_id}", nickname)
    else:
        bot.send_message(target, f"Failed to modify task {task_id}", nickname)


def command_cron(bot, target: str, nickname: str, args: List[str]):
    """
    Quick scheduling shortcuts

    Usage: cron PRESET [OPTIONS] MESSAGE

    Presets:
        minutely   Run every minute
        hourly     Run every hour
        daily      Run every 24 hours

    Options:
        -n, --name NAME   Custom task name

    Examples:
        cron minutely "System check"
        cron hourly -n "status" "Hourly status update"
    """
    presets = {
        "minutely": 60,
        "hourly": 3600,
        "daily": 86400
    }

    if not args:
        bot.send_message(
            target,
            "Usage: cron PRESET [OPTIONS] MESSAGE",
            nickname)
        return

    preset = args[0].lower()
    remaining = args[1:]

    if preset not in presets:
        available = ", ".join(presets.keys())
        bot.send_message(
            target,
            f"Unknown preset. Available: {available}",
            nickname)
        return

    interval = presets[preset]
    custom_name = None

    try:
        opts, message_parts = getopt(remaining, "n:", ["name="])
        for opt, arg in opts:
            if opt in ("-n", "--name"):
                custom_name = arg
    except GetoptError as e:
        bot.send_message(target, f"Invalid option: {e}", nickname)
        return

    if not message_parts:
        bot.send_message(target, "Provide a message", nickname)
        return

    message = " ".join(message_parts)
    name = custom_name or f"{preset}-{target}"

    task_id = bot.scheduler.add_task(
        name=name,
        callback=periodic_message_callback,
        interval=interval,
        args=(bot, target, message),
        periodic=True,
        plugin_name=PLUGIN_NAME,
        description=f"{preset.capitalize()} message: {message[:20]}...",
        auto_start=True
    )

    if task_id:
        bot.send_message(
            target,
            f"Created {preset} task: {task_id} (every {interval}s)",
            nickname
        )
    else:
        bot.send_message(target, "Failed to create task", nickname)


__all__ = [
    'PLUGIN_INFO',
    'command_task',
    'command_schedule',
    'command_modify',
    'command_cron',
]
