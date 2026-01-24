"""
Dunamis IRC Bot - Plugin Manager

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

from typing import Optional, Callable, Any
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

from .logger import Logger
from .task_scheduler import TaskScheduler


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
                Logger.info(f"Unregistered value: {var_name}")

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
