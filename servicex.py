"""
ServiceX IRC Bot
A modular IRC bot built on Twisted with plugin support

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

from __future__ import annotations
from typing import Optional, List, Tuple, Callable, Any, Dict, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
from importlib.util import spec_from_file_location, module_from_spec
from enum import Enum, auto
import shlex
import sqlite3
import logging
import uuid

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, ssl, task
from twisted.python import log as twisted_log
from tabulate import tabulate
from pytz import timezone as pytz_timezone


@dataclass
class NetworkConfig:
    id: int
    name: str
    address: str
    port: int
    use_ssl: bool
    nicknames: List[str]
    ident: str
    realname: str
    nickserv_username: str
    nickserv_password: str
    oper_username: str
    oper_password: str
    command_trigger: str

    @property
    def primary_nickname(self) -> str:
        return self.nicknames[0]


class TaskState(Enum):
    PENDING = auto()      # Task created but not started
    RUNNING = auto()      # Task is actively running
    PAUSED = auto()       # Task is paused
    STOPPED = auto()      # Task has been stopped
    COMPLETED = auto()    # One-time task has completed
    FAILED = auto()       # Task encountered an error


@dataclass
class ScheduledTask:
    id: str
    name: str
    callback: Callable
    interval: Optional[float]  # None for one-time tasks
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict = field(default_factory=dict)
    state: TaskState = TaskState.PENDING
    periodic: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None  # None for unlimited
    delay: float = 0.0  # Initial delay before first run
    plugin_name: Optional[str] = None
    description: str = ""
    _looping_call: Optional[task.LoopingCall] = field(default=None, repr=False)
    _delayed_call: Optional[Any] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.name,
            "periodic": self.periodic,
            "interval": self.interval,
            "delay": self.delay,
            "run_count": self.run_count,
            "max_runs": self.max_runs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "plugin": self.plugin_name,
            "description": self.description}


class Logger:
    _initialized = False
    _log_dir = Path("logs")

    @classmethod
    def setup(cls, log_dir: Path = Path("logs")):
        if cls._initialized:
            return

        cls._log_dir = log_dir
        cls._log_dir.mkdir(exist_ok=True)

        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Set level
        root_logger.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler
        log_file = cls._log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        cls._initialized = True

    @staticmethod
    def info(message: str):
        logging.info(message)

    @staticmethod
    def warning(message: str):
        logging.warning(message)

    @staticmethod
    def error(message: str):
        logging.error(message)

    @staticmethod
    def debug(message: str):
        logging.debug(message)


class TimeFormatter:
    @staticmethod
    def format(tz: Optional[str] = None, preset: Optional[str] = None,
               fmt: Optional[str] = None) -> str:
        now = datetime.now(pytz_timezone(tz)) if tz else datetime.now()

        if preset == "datetime":
            return now.strftime("%Y-%m-%d_%H:%M:%S")
        elif preset == "date":
            return now.strftime("%Y-%m-%d")
        elif preset == "time":
            return now.strftime("%H:%M:%S")
        elif fmt:
            return now.strftime(fmt)

        return now.isoformat()


class TaskScheduler:
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self._id_counter = 0

    def _generate_id(self) -> str:
        return str(uuid.uuid4())[:8]

    def add_task(
        self,
        name: str,
        callback: Callable,
        interval: Optional[float] = None,
        args: Tuple = (),
        kwargs: Optional[Dict] = None,
        periodic: bool = True,
        delay: float = 0.0,
        max_runs: Optional[int] = None,
        plugin_name: Optional[str] = None,
        description: str = "",
        auto_start: bool = False
    ) -> Optional[str]:
        if kwargs is None:
            kwargs = {}

        # Validate periodic tasks have an interval
        if periodic and interval is None:
            Logger.error(f"Periodic task '{name}' requires an interval")
            return None

        # For one-time tasks, interval represents the delay if not specified
        if not periodic and interval is None:
            interval = delay

        task_id = self._generate_id()

        scheduled_task = ScheduledTask(
            id=task_id,
            name=name,
            callback=callback,
            interval=interval,
            args=args,
            kwargs=kwargs,
            periodic=periodic,
            delay=delay,
            max_runs=max_runs,
            plugin_name=plugin_name,
            description=description
        )

        self.tasks[task_id] = scheduled_task
        Logger.info(
            f"Task added: ID: {task_id}, Name: {name}, Periodic: {periodic}")

        if auto_start:
            self.start_task(task_id)

        return task_id

    def remove_task(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            Logger.warning(f"Task {task_id} not found")
            return False

        # Stop the task first if running
        self.stop_task(task_id)

        task = self.tasks.pop(task_id)
        Logger.info(f"Task removed: ID: {task_id}, Name: {task.name}")
        return True

    def start_task(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            Logger.warning(f"Task {task_id} not found")
            return False

        scheduled_task = self.tasks[task_id]

        if scheduled_task.state == TaskState.RUNNING:
            Logger.warning(f"Task {task_id} is already running")
            return False

        if scheduled_task.state == TaskState.COMPLETED:
            Logger.warning(f"Task {task_id} has already completed")
            return False

        try:
            if scheduled_task.periodic:
                self._start_periodic_task(scheduled_task)
            else:
                self._start_onetime_task(scheduled_task)

            scheduled_task.state = TaskState.RUNNING
            scheduled_task.started_at = datetime.now()
            Logger.info(
                f"Task started: ID: {task_id}, Name: {scheduled_task.name}")
            return True
        except Exception as e:
            Logger.error(f"Failed to start task: {task_id}: {e}")
            scheduled_task.state = TaskState.FAILED
            return False

    def _start_periodic_task(self, scheduled_task: ScheduledTask):
        def wrapped_callback():
            self._execute_task(scheduled_task)

        looping_call = task.LoopingCall(wrapped_callback)
        scheduled_task._looping_call = looping_call

        # Start with delay if specified, otherwise start immediately
        if scheduled_task.delay > 0:
            looping_call.start(scheduled_task.interval, now=False)
            # The delay is handled by starting with now=False
            scheduled_task._delayed_call = reactor.callLater(
                scheduled_task.delay,
                lambda: None  # Dummy, actual start handled by LoopingCall
            )
        else:
            looping_call.start(scheduled_task.interval, now=True)

    def _start_onetime_task(self, scheduled_task: ScheduledTask):
        def wrapped_callback():
            self._execute_task(scheduled_task)
            scheduled_task.state = TaskState.COMPLETED

        delay = scheduled_task.delay if scheduled_task.delay > 0 else scheduled_task.interval
        if delay is None:
            delay = 0

        scheduled_task._delayed_call = reactor.callLater(
            delay, wrapped_callback)

    def _execute_task(self, scheduled_task: ScheduledTask):
        try:
            scheduled_task.callback(
                *scheduled_task.args,
                **scheduled_task.kwargs)
            scheduled_task.last_run = datetime.now()
            scheduled_task.run_count += 1

            # Check max runs for periodic tasks
            if scheduled_task.periodic and scheduled_task.max_runs is not None:
                if scheduled_task.run_count >= scheduled_task.max_runs:
                    Logger.info(
                        f"Task '{scheduled_task.name}' reached max runs ({scheduled_task.max_runs})")
                    self.stop_task(scheduled_task.id)
                    scheduled_task.state = TaskState.COMPLETED
        except Exception as e:
            Logger.error(f"Task '{scheduled_task.name}' execution failed: {e}")
            scheduled_task.state = TaskState.FAILED

    def stop_task(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            Logger.warning(f"Task {task_id} not found")
            return False

        scheduled_task = self.tasks[task_id]

        if scheduled_task.state not in (TaskState.RUNNING, TaskState.PAUSED):
            Logger.warning(f"Task {task_id} is not running")
            return False

        try:
            if scheduled_task._looping_call and scheduled_task._looping_call.running:
                scheduled_task._looping_call.stop()

            if scheduled_task._delayed_call and scheduled_task._delayed_call.active():
                scheduled_task._delayed_call.cancel()

            scheduled_task.state = TaskState.STOPPED
            Logger.info(
                f"Task stopped: ID: {task_id}, Name: {scheduled_task.name}")
            return True
        except Exception as e:
            Logger.error(f"Failed to stop task: {task_id}: {e}")
            return False

    def pause_task(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            Logger.warning(f"Task {task_id} not found")
            return False

        scheduled_task = self.tasks[task_id]

        if not scheduled_task.periodic:
            Logger.warning(f"Cannot pause one-time task {task_id}")
            return False

        if scheduled_task.state != TaskState.RUNNING:
            Logger.warning(f"Task {task_id} is not running")
            return False

        try:
            if scheduled_task._looping_call and scheduled_task._looping_call.running:
                scheduled_task._looping_call.stop()

            scheduled_task.state = TaskState.PAUSED
            Logger.info(
                f"Task paused: ID: {task_id}, Name: {scheduled_task.name}")
            return True
        except Exception as e:
            Logger.error(f"Failed to pause task: {task_id}: {e}")
            return False

    def resume_task(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            Logger.warning(f"Task {task_id} not found")
            return False

        scheduled_task = self.tasks[task_id]

        if scheduled_task.state != TaskState.PAUSED:
            Logger.warning(f"Task {task_id} is not paused")
            return False

        try:
            if scheduled_task._looping_call:
                scheduled_task._looping_call.start(
                    scheduled_task.interval, now=False)

            scheduled_task.state = TaskState.RUNNING
            Logger.info(
                f"Task resumed: ID: {task_id}, Name: {scheduled_task.name}")
            return True
        except Exception as e:
            Logger.error(f"Failed to resume task {task_id}: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self.tasks.get(task_id)

    def get_task_by_name(self, name: str) -> Optional[ScheduledTask]:
        for scheduled_task in self.tasks.values():
            if scheduled_task.name == name:
                return scheduled_task
        return None

    def list_tasks(
        self,
        plugin_name: Optional[str] = None,
        state: Optional[TaskState] = None
    ) -> List[ScheduledTask]:
        result = []
        for scheduled_task in self.tasks.values():
            if plugin_name and scheduled_task.plugin_name != plugin_name:
                continue
            if state and scheduled_task.state != state:
                continue
            result.append(scheduled_task)
        return result

    def modify_task(
        self,
        task_id: str,
        interval: Optional[float] = None,
        max_runs: Optional[int] = None,
        description: Optional[str] = None
    ) -> bool:
        if task_id not in self.tasks:
            Logger.warning(f"Task {task_id} not found")
            return False

        scheduled_task = self.tasks[task_id]
        was_running = scheduled_task.state == TaskState.RUNNING

        # Stop task if running to apply changes
        if was_running and interval is not None:
            self.pause_task(task_id)

        if interval is not None:
            scheduled_task.interval = interval

        if max_runs is not None:
            scheduled_task.max_runs = max_runs

        if description is not None:
            scheduled_task.description = description

        # Restart if was running and interval changed
        if was_running and interval is not None:
            scheduled_task.state = TaskState.PAUSED
            self.resume_task(task_id)

        Logger.info(
            f"Task modified: ID: {task_id}, Name: {scheduled_task.name}")
        return True

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        scheduled_task = self.get_task(task_id)
        if scheduled_task:
            return scheduled_task.to_dict()
        return None

    def stop_all_tasks(self):
        for task_id in list(self.tasks.keys()):
            if self.tasks[task_id].state in (
                    TaskState.RUNNING, TaskState.PAUSED):
                self.stop_task(task_id)
        Logger.info("Stopped all tasks")

    def remove_plugin_tasks(self, plugin_name: str) -> int:
        to_remove = [
            task_id for task_id, scheduled_task in self.tasks.items()
            if scheduled_task.plugin_name == plugin_name
        ]

        for task_id in to_remove:
            self.remove_task(task_id)

        Logger.info(
            f"Removed {len(to_remove)} tasks for plugin '{plugin_name}'")
        return len(to_remove)


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
                nickserv_username=row[8],
                nickserv_password=row[9],
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


class PluginManager:
    def __init__(self, plugins_dir: Path = Path("plugins")):
        self.plugins_dir = plugins_dir
        self.loaded_plugins: dict[str, Any] = {}
        self.commands: dict[str, Callable] = {}
        self.values: dict[str, Callable] = {}

    def load_plugin(self, plugin_name: str) -> bool:
        if plugin_name in self.loaded_plugins:
            Logger.warning(f"Plugin {plugin_name} already loaded")
            return False

        init_path = self.plugins_dir / plugin_name / "init.py"

        if not init_path.exists():
            Logger.error(f"Plugin {plugin_name} not found at {init_path}")
            return False

        try:
            spec = spec_from_file_location(plugin_name, init_path)
            plugin = module_from_spec(spec)
            spec.loader.exec_module(plugin)

            self.loaded_plugins[plugin_name] = plugin
            self._register_plugin_features(plugin_name, plugin)

            Logger.info(f"Loaded plugin: {plugin_name}")
            return True
        except Exception as e:
            Logger.error(f"Plugin {plugin_name} not loaded: {e}")
            return False

    def unload_plugin(
            self,
            plugin_name: str,
            scheduler: Optional[TaskScheduler] = None) -> bool:
        if plugin_name not in self.loaded_plugins:
            Logger.warning(f"Plugin {plugin_name} not loaded")
            return False

        plugin = self.loaded_plugins[plugin_name]
        self._unregister_plugin_features(plugin)

        # Remove plugin's scheduled tasks
        if scheduler:
            scheduler.remove_plugin_tasks(plugin_name)

        del self.loaded_plugins[plugin_name]

        Logger.info(f"Unloaded plugin: {plugin_name}")
        return True

    def _register_plugin_features(self, plugin_name: str, plugin: Any):
        for attr_name in dir(plugin):
            if attr_name.startswith("command_"):
                cmd_name = attr_name.replace("command_", "")
                self.commands[cmd_name] = getattr(plugin, attr_name)
                Logger.info(f"Registered command: {cmd_name}")

            elif attr_name.startswith("value_"):
                val_name = attr_name.replace("value_", "")
                self.values[val_name] = getattr(plugin, attr_name)
                Logger.info(f"Registered value: {val_name}")

    def _unregister_plugin_features(self, plugin: Any):
        for attr_name in dir(plugin):
            if attr_name.startswith("command_"):
                cmd_name = attr_name.replace("command_", "")
                self.commands.pop(cmd_name, None)
                Logger.info(f"Unregistered command: {cmd_name}")

            elif attr_name.startswith("value_"):
                var_name = attr_name.replace("value_", "")
                self.values.pop(var_name, None)
                Logger.info(f"Unregistered command: {cmd_name}")

    def execute_command(self, command: str, *args) -> bool:
        if command in self.commands:
            self.commands[command](*args)
            return True
        return False

    def parse_values(self, message: str, context: Any) -> str:
        for val_name, val_func in self.values.items():
            placeholder = f"${val_name}"
            if placeholder in message:
                value = val_func(context)
                message = message.replace(placeholder, value)
        return message


class ServiceXProtocol(irc.IRCClient):
    versionName = "ServiceX"
    versionNum = "2.0"
    versionEnv = "Python/Twisted"

    def __init__(self):
        super().__init__()
        self.plugin_manager = PluginManager()
        self.scheduler = TaskScheduler()
        self.db: Optional[DatabaseManager] = None
        self.joined_channels: List[str] = []

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        Logger.info(
            f"Connected to IRC network: {self.factory.config.name}"
            f"({self.factory.config.address}:{self.factory.config.port})"
        )

        # Load enabled plugins
        enabled_plugins = self.db.get_enabled_plugins(self.factory.config.id)
        for plugin_name in enabled_plugins:
            self.plugin_manager.load_plugin(plugin_name)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        Logger.warning(
            f"Connection lost to {self.factory.config.name}: {reason.getErrorMessage()}"
        )
        # Stop all scheduled tasks on disconnect
        self.scheduler.stop_all_tasks()

    def signedOn(self):
        config = self.factory.config

        # Identify with NickServ
        Logger.info(f"Identifying with NickServ as {config.nickserv_username}")
        self.msg(
            'NickServ',
            f'IDENTIFY {config.nickserv_username} {config.nickserv_password}'
        )

        # Join channels
        channels = self.db.get_channels(config.id)
        for channel in channels:
            self.join_channel(channel, save_to_db=False)

    def alterCollidedNick(self, nickname: str) -> str:
        nicknames = self.factory.config.nicknames

        try:
            current_index = nicknames.index(nickname)
            next_index = (current_index + 1) % len(nicknames)
            new_nickname = nicknames[next_index]
        except ValueError:
            new_nickname = nicknames[0]

        Logger.info(f"Nickname {nickname} taken, trying {new_nickname}")
        return new_nickname

    def joined(self, channel: str):
        Logger.info(f"Joined channel: {channel}")
        if channel not in self.joined_channels:
            self.joined_channels.append(channel)

    def left(self, channel: str):
        Logger.info(f"Left channel: {channel}")
        if channel in self.joined_channels:
            self.joined_channels.remove(channel)

    def join_channel(self, channel: str, save_to_db: bool = True):
        if not channel:
            return

        channel = channel.split()[0]

        if channel in self.joined_channels:
            Logger.info(f"Already in channel: {channel}")
            return

        Logger.info(f"Joining channel: {channel}")
        self.join(channel)

        if save_to_db:
            self.db.add_channel(self.factory.config.id, channel)

    def part_channel(self, channel: str, save_to_db: bool = True):
        if not channel:
            return

        channel = channel.split()[0]

        if channel not in self.joined_channels:
            Logger.info(f"Not in channel: {channel}")
            return

        Logger.info(f"Leaving channel: {channel}")
        self.leave(channel)

        if save_to_db:
            self.db.remove_channel(self.factory.config.id, channel)

    def send_message(self, target: str, message: str,
                     prefix_nick: Optional[str] = None):
        if prefix_nick:
            message = f"{prefix_nick}: {message}"

        # Handle multi-line messages
        for line in message.split('\n'):
            self.msg(target, line)

    def privmsg(self, user: str, channel: str, message: str):
        try:
            nickname, user_info = user.split('!')
            ident, hostname = user_info.split('@')
        except ValueError:
            return

        message = message.strip()

        if not message:
            return

        # Determine if this is a PM or channel message
        is_pm = (channel == self.nickname)
        target = nickname if is_pm else channel

        # Check for command trigger
        trigger = self.factory.config.command_trigger
        if is_pm or message.startswith(trigger):
            self._handle_command(target, nickname, message, is_pm)

    def _handle_command(
            self,
            target: str,
            nickname: str,
            message: str,
            is_pm: bool):

        # Strip trigger if present
        if not is_pm:
            message = message[len(self.factory.config.command_trigger):]

        # Parse command and arguments
        try:
            parts = shlex.split(message)
        except ValueError as e:
            if "closing quotation" in str(e).lower():
                self.send_message(
                    target, "Missing closing quotation mark", nickname)
            return

        if not parts:
            return

        command = parts[0]
        args = parts[1:]

        # Execute command
        success = self.plugin_manager.execute_command(
            command, self, target, nickname, args
        )

        if not success:
            Logger.info(f"Unknown command '{command}' from {nickname}")
            self.send_message(target, "Command not found", nickname)
        else:
            Logger.info(f"Executed command '{command}' from {nickname}")

    def noticed(self, user: str, channel: str, message: str):
        if user == "NickServ!services@services.":
            if "Password accepted" in message:
                Logger.info("Successfully identified with NickServ")
            elif "isn't registered" in message:
                Logger.error("Failed to identify with NickServ")


class ServiceXFactory(protocol.ClientFactory):
    protocol = ServiceXProtocol

    def __init__(self, config: NetworkConfig, db: DatabaseManager):
        self.config = config
        self.db = db

    def buildProtocol(self, addr):
        proto = self.protocol()
        proto.factory = self
        proto.nickname = self.config.primary_nickname
        proto.username = self.config.ident
        proto.realname = self.config.realname
        proto.db = self.db
        return proto

    def clientConnectionLost(self, connector, reason):
        Logger.warning(
            f"Connection lost, reconnecting: {reason.getErrorMessage()}")
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        Logger.error(f"Connection failed: {reason.getErrorMessage()}")
        reactor.stop()


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
        factory = ServiceXFactory(network_config, db)

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
