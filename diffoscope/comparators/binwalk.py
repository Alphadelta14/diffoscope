# -*- coding: utf-8 -*-
#
# diffoscope: in-depth comparison of files, archives, and directories
#
# Copyright © 2017 Chris Lamb <lamby@debian.org>
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

import os
import re
import glob
import logging

from diffoscope.tempfiles import get_temporary_directory

from .utils.file import File
from .utils.archive import Archive


try:
    import binwalk
except ImportError:
    binwalk = None

logger = logging.getLogger(__name__)


class BinwalkFileContainer(Archive):
    def open_archive(self):
        return self

    def close_archive(self):
        self.source._unpacked.cleanup()

    def get_member_names(self):
        return sorted(self.source._members.keys())

    def extract(self, member_name, dest_dir):
        return self.source._members[member_name]


class BinwalkFile(File):
    FILE_TYPE_RE = re.compile(r'\bcpio archive\b')
    CONTAINER_CLASS = BinwalkFileContainer

    @classmethod
    def recognizes(cls, file):
        if binwalk is None:
            return False

        if not super().recognizes(file):
            return False

        # Don't recurse; binwalk has already found everything
        if isinstance(file.container, cls.CONTAINER_CLASS):
            return False

        unpacked = get_temporary_directory(prefix='binwalk')
        logger.debug("Extracting %s to %s", file.path, unpacked.name)

        binwalk.scan(
            file.path,
            dd='cpio:cpio',
            carve=True,
            quiet=True,
            signature=True,
            directory=unpacked.name,
        )

        members = {
            os.path.basename(x): x
            for x in glob.glob(os.path.join(unpacked.name, '*/*'))
        }

        logger.debug("Found %d embedded member(s)", len(members))

        if not members:
            unpacked.cleanup()
            return False

        file._members = members
        file._unpacked = unpacked

        return True