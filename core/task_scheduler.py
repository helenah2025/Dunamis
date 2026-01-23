"""
ServiceX IRC Bot - Task Scheduler

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

from __future__ import annotations
from typing import Optional, List, Tuple, Callable, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import uuid

from twisted.internet import reactor, task

from .logger import Logger


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
