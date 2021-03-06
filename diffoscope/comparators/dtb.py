#
# diffoscope: in-depth comparison of files, archives, and directories
#
# Copyright © 2016 Emanuel Bronshtein <e3amn2l@gmx.com>
# Copyright © 2016 Vagrant Cascadian <vagrant@debian.org>
# Copyright © 2018-2020 Chris Lamb <lamby@debian.org>
#
# diffoscope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# diffoscope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with diffoscope.  If not, see <https://www.gnu.org/licenses/>.

import re

from diffoscope.tools import tool_required
from diffoscope.difference import Difference

from .utils.file import File
from .utils.command import Command


class DeviceTreeContents(Command):
    @tool_required("fdtdump")
    def cmdline(self):
        return ["fdtdump", self.path]


class DeviceTreeFile(File):
    DESCRIPTION = "Device Tree Compiler blob files"
    FILE_TYPE_RE = re.compile(r"^Device Tree Blob")

    def compare_details(self, other, source=None):
        return [
            Difference.from_operation(
                DeviceTreeContents, self.path, other.path
            )
        ]
