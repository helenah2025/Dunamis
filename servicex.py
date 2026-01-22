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
from typing import Optional, List, Tuple, Callable, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from importlib.util import spec_from_file_location, module_from_spec
import shlex
import sqlite3
import logging

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, ssl
from twisted.python import log as twisted_log
from tabulate import tabulate
from pytz import timezone as pytz_timezone


# ============================================================================
# Configuration and Data Models
# ============================================================================

@dataclass
class NetworkConfig:
    """Configuration for an IRC network connection"""
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


# ============================================================================
# Utilities
# ============================================================================

class Logger:
    """Centralized logging handler"""
    
    _initialized = False
    _log_dir = Path("logs")
    
    @classmethod
    def setup(cls, log_dir: Path = Path("logs")):
        """Initialize logging system"""
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


class TimeFormatter:
    """Handle timestamp formatting with timezone support"""
    
    @staticmethod
    def format(tz: Optional[str] = None, preset: Optional[str] = None, 
               fmt: Optional[str] = None) -> str:
        """
        Format current time with optional timezone and format
        
        Args:
            tz: Timezone string (e.g., 'US/Eastern')
            preset: Preset format ('datetime', 'date', 'time')
            fmt: Custom strftime format string
        """
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


# ============================================================================
# Database Management
# ============================================================================

class DatabaseManager:
    """Handle all database operations"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
    
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.cursor = self.connection.cursor()
            Logger.info(f"Connected to database: {self.db_path}")
            return True
        except sqlite3.Error as e:
            Logger.error(f"Database connection failed: {e}")
            return False
    
    def get_networks(self) -> List[NetworkConfig]:
        """Retrieve all network configurations"""
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
        """Get channels for a specific network"""
        self.cursor.execute(
            'SELECT channelName FROM ircChannels WHERE networkID=?',
            (network_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_enabled_modules(self, network_id: int) -> List[str]:
        """Get enabled modules for a network"""
        self.cursor.execute(
            'SELECT moduleName FROM modules WHERE networkID=? AND moduleEnabled=1',
            (network_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]
    
    def add_channel(self, network_id: int, channel_name: str):
        """Add channel to database"""
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
        """Remove channel from database"""
        self.cursor.execute(
            'DELETE FROM ircChannels WHERE channelName=? AND networkID=?',
            (channel_name, network_id)
        )
        self.connection.commit()
        Logger.info(f"Removed channel {channel_name} from database")
    
    def update_module_status(self, network_id: int, module_name: str, enabled: bool):
        """Enable or disable a module"""
        self.cursor.execute(
            'UPDATE modules SET moduleEnabled=? WHERE networkID=? AND moduleName=?',
            (1 if enabled else 0, network_id, module_name)
        )
        self.connection.commit()


# ============================================================================
# Module System
# ============================================================================

class ModuleManager:
    """Manage bot modules and their commands/variables"""
    
    def __init__(self, modules_dir: Path = Path("modules")):
        self.modules_dir = modules_dir
        self.loaded_modules: dict[str, Any] = {}
        self.commands: dict[str, Callable] = {}
        self.variables: dict[str, Callable] = {}
    
    def load_module(self, module_name: str) -> bool:
        """Load a module and register its commands/variables"""
        if module_name in self.loaded_modules:
            Logger.warning(f"Module {module_name} already loaded")
            return False
        
        init_path = self.modules_dir / module_name / "init.py"
        
        if not init_path.exists():
            Logger.error(f"Module {module_name} not found at {init_path}")
            return False
        
        try:
            spec = spec_from_file_location(module_name, init_path)
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            
            self.loaded_modules[module_name] = module
            self._register_module_features(module_name, module)
            
            Logger.info(f"Module {module_name} loaded successfully")
            return True
        except Exception as e:
            Logger.error(f"Failed to load module {module_name}: {e}")
            return False
    
    def unload_module(self, module_name: str) -> bool:
        """Unload a module and unregister its features"""
        if module_name not in self.loaded_modules:
            Logger.warning(f"Module {module_name} not loaded")
            return False
        
        module = self.loaded_modules[module_name]
        self._unregister_module_features(module)
        del self.loaded_modules[module_name]
        
        Logger.info(f"Module {module_name} unloaded")
        return True
    
    def _register_module_features(self, module_name: str, module: Any):
        """Register commands and variables from a module"""
        for attr_name in dir(module):
            if attr_name.startswith("command_"):
                cmd_name = attr_name.replace("command_", "")
                self.commands[cmd_name] = getattr(module, attr_name)
                Logger.info(f"Registered command: {cmd_name}")
            
            elif attr_name.startswith("variable_"):
                var_name = attr_name.replace("variable_", "")
                self.variables[var_name] = getattr(module, attr_name)
                Logger.info(f"Registered variable: {var_name}")
    
    def _unregister_module_features(self, module: Any):
        """Unregister commands and variables from a module"""
        for attr_name in dir(module):
            if attr_name.startswith("command_"):
                cmd_name = attr_name.replace("command_", "")
                self.commands.pop(cmd_name, None)
            
            elif attr_name.startswith("variable_"):
                var_name = attr_name.replace("variable_", "")
                self.variables.pop(var_name, None)
    
    def execute_command(self, command: str, *args) -> bool:
        """Execute a registered command"""
        if command in self.commands:
            self.commands[command](*args)
            return True
        return False
    
    def parse_variables(self, message: str, context: Any) -> str:
        """Replace variables in message with their values"""
        for var_name, var_func in self.variables.items():
            placeholder = f"${var_name}"
            if placeholder in message:
                value = var_func(context)
                message = message.replace(placeholder, value)
        return message


# ============================================================================
# IRC Protocol
# ============================================================================

class ServiceXProtocol(irc.IRCClient):
    """IRC protocol implementation for ServiceX bot"""
    
    versionName = "ServiceX"
    versionNum = "2.0"
    versionEnv = "Python/Twisted"
    
    def __init__(self):
        super().__init__()
        self.module_manager = ModuleManager()
        self.db: Optional[DatabaseManager] = None
        self.joined_channels: List[str] = []
    
    def connectionMade(self):
        """Handle successful connection to IRC server"""
        irc.IRCClient.connectionMade(self)
        Logger.info(
            f"Connected to {self.factory.config.name} "
            f"({self.factory.config.address}:{self.factory.config.port})"
        )
        
        # Load enabled modules
        enabled_modules = self.db.get_enabled_modules(self.factory.config.id)
        for module_name in enabled_modules:
            self.module_manager.load_module(module_name)
    
    def connectionLost(self, reason):
        """Handle lost connection"""
        irc.IRCClient.connectionLost(self, reason)
        Logger.warning(
            f"Connection lost to {self.factory.config.name}: {reason.getErrorMessage()}"
        )
    
    def signedOn(self):
        """Handle successful sign-on to IRC server"""
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
        """Handle nickname collision by cycling through alternatives"""
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
        """Handle successful channel join"""
        Logger.info(f"Joined channel: {channel}")
        if channel not in self.joined_channels:
            self.joined_channels.append(channel)
    
    def left(self, channel: str):
        """Handle channel part"""
        Logger.info(f"Left channel: {channel}")
        if channel in self.joined_channels:
            self.joined_channels.remove(channel)
    
    def join_channel(self, channel: str, save_to_db: bool = True):
        """Join a channel and optionally save to database"""
        if not channel:
            return
        
        channel = channel.split()[0]
        
        if channel in self.joined_channels:
            Logger.info(f"Already in channel {channel}")
            return
        
        Logger.info(f"Joining channel {channel}")
        self.join(channel)
        
        if save_to_db:
            self.db.add_channel(self.factory.config.id, channel)
    
    def part_channel(self, channel: str, save_to_db: bool = True):
        """Leave a channel and optionally remove from database"""
        if not channel:
            return
        
        channel = channel.split()[0]
        
        if channel not in self.joined_channels:
            Logger.info(f"Not in channel {channel}")
            return
        
        Logger.info(f"Leaving channel {channel}")
        self.leave(channel)
        
        if save_to_db:
            self.db.remove_channel(self.factory.config.id, channel)
    
    def send_message(self, target: str, message: str, prefix_nick: Optional[str] = None):
        """Send a message to a target (channel or user)"""
        if prefix_nick:
            message = f"{prefix_nick}: {message}"
        
        # Handle multi-line messages
        for line in message.split('\n'):
            self.msg(target, line)
    
    def privmsg(self, user: str, channel: str, message: str):
        """Handle incoming PRIVMSG"""
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
    
    def _handle_command(self, target: str, nickname: str, message: str, is_pm: bool):
        """Process a command message"""
        # Strip trigger if present
        if not is_pm:
            message = message[len(self.factory.config.command_trigger):]
        
        # Parse command and arguments
        try:
            parts = shlex.split(message)
        except ValueError as e:
            if "closing quotation" in str(e).lower():
                self.send_message(target, "Missing closing quotation mark", nickname)
            return
        
        if not parts:
            return
        
        command = parts[0]
        args = parts[1:]
        
        # Execute command
        success = self.module_manager.execute_command(
            command, self, target, nickname, args
        )
        
        if not success:
            Logger.info(f"Unknown command '{command}' from {nickname}")
            self.send_message(target, "Command not found", nickname)
        else:
            Logger.info(f"Executed command '{command}' from {nickname}")
    
    def noticed(self, user: str, channel: str, message: str):
        """Handle NOTICE messages"""
        if user == "NickServ!services@services.":
            if "Password accepted" in message:
                Logger.info("Successfully identified with NickServ")
            elif "isn't registered" in message:
                Logger.error("Failed to identify with NickServ")


# ============================================================================
# Factory
# ============================================================================

class ServiceXFactory(protocol.ClientFactory):
    """Factory for creating ServiceX protocol instances"""
    
    protocol = ServiceXProtocol
    
    def __init__(self, config: NetworkConfig, db: DatabaseManager):
        self.config = config
        self.db = db
    
    def buildProtocol(self, addr):
        """Build protocol instance with proper configuration"""
        proto = self.protocol()
        proto.factory = self
        proto.nickname = self.config.primary_nickname
        proto.username = self.config.ident
        proto.realname = self.config.realname
        proto.db = self.db
        return proto
    
    def clientConnectionLost(self, connector, reason):
        """Handle connection loss - attempt reconnection"""
        Logger.warning(f"Connection lost, reconnecting: {reason.getErrorMessage()}")
        connector.connect()
    
    def clientConnectionFailed(self, connector, reason):
        """Handle connection failure"""
        Logger.error(f"Connection failed: {reason.getErrorMessage()}")
        reactor.stop()


# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main application entry point"""
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
    Logger.info(f"Loaded {len(networks)} network configurations")
    
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
        
        Logger.info(f"Configured connection to {network_config.name}")
    
    # Start reactor
    reactor.run()


if __name__ == '__main__':
    main()
