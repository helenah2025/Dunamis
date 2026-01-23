"""
ServiceX IRC Bot - Time Formatter

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

from typing import Optional
from datetime import datetime
from pytz import timezone as pytz_timezone


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
