"""
ServiceX IRC Bot - Network Configuration

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
from typing import List
from dataclasses import dataclass


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
