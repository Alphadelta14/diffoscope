# -*- coding: utf-8 -*-
#
# diffoscope: in-depth comparison of files, archives, and directories
#
# Copyright © 2016 Chris Lamb <lamby@debian.org>
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

import abc
import logging
import shlex
import subprocess

from ...utils import format_cmdline

logger = logging.getLogger(__name__)


class Command(metaclass=abc.ABCMeta):
    MASK_STDERR = False
    MEMOIZE_OUTPUT = False
    MAX_STDERR_LINES = 50
    VALID_RETURNCODES = {0}

    def __init__(self, path):
        self._path = path

    def start(self):
        logger.debug("Executing %s", self.shell_cmdline())

        self._stdin = self.stdin()
        # "stdin" used to be a feeder but we didn't need the functionality so
        # it was simplified into the current form. it can be recovered from git
        # the extra functionality is needed in the future. alternatively,
        # consider using a shell pipeline ("sh -ec $script") to implement what
        # you need, because that involves much less code - like it or not (I
        # don't) shell is still the most readable option for composing processes
        self._process = subprocess.run(
            self.cmdline(),
            shell=False,
            close_fds=True,
            env=self.env(),
            input=self.input(),
            stdin=self._stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.stderr = self._read_stderr()

    @property
    def path(self):
        return self._path

    def stdin(self):
        return None

    @abc.abstractmethod
    def cmdline(self):
        raise NotImplementedError()

    def shell_cmdline(self, *args, **kwargs):
        kwargs.setdefault('replace', (self.path,))
        return format_cmdline(self.cmdline(), *args, **kwargs)

    def env(self):
        return None  # inherit parent environment by default

    def filter(self, line):
        # Assume command output is utf-8 by default
        return line

    def poll(self):
        pass

    def terminate(self):
        pass

    def input(self):
        pass

    def _read_stderr(self):
        if self.MASK_STDERR:
            return ""

        buf = ""
        lines = self._process.stderr.splitlines(True)

        for index, line in enumerate(lines):
            if index >= Command.MAX_STDERR_LINES:
                break
            buf += line.decode('utf-8', errors='replace')

        if len(lines) > Command.MAX_STDERR_LINES:
            buf += '[ {} lines ignored ]\n'.format(
                len(lines) - Command.MAX_STDERR_LINES
            )

        return buf

    @property
    def returncode(self):
        val = self._process.returncode

        if val in self.VALID_RETURNCODES:
            return 0

        return val

    @property
    def stdout(self):
        return self._process.stdout.splitlines(True)
