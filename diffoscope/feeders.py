# -*- coding: utf-8 -*-
#
# diffoscope: in-depth comparison of files, archives, and directories
#
# Copyright © 2014-2015 Jérémy Bobbio <lunar@debian.org>
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
import signal
import hashlib
import logging
import subprocess

from .config import Config
from .profiling import profile

logger = logging.getLogger(__name__)

DIFF_CHUNK = 4096


def from_raw_reader(in_file, filter=None):
    def feeder(out_file):
        max_lines = Config().max_diff_input_lines
        end_nl = False
        line_count = 0

        # If we have a maximum size, hash the content as we go along so we can
        # display a nicer message.
        h = None
        if max_lines < float('inf'):
            h = hashlib.sha1()

        for buf in in_file:
            line_count += 1
            out = buf if filter is None else filter(buf)

            if h is not None:
                h.update(out)

            if line_count < max_lines:
                out_file.write(out)
                # very long lines can sometimes interact negatively with
                # python buffering; force a flush here to avoid this,
                # see https://bugs.debian.org/870049
                out_file.flush()
            if buf:
                end_nl = buf[-1] == '\n'

        if h is not None and line_count >= max_lines:
            out_file.write(
                "[ Too much input for diff (SHA1: {}) ]\n".format(
                    h.hexdigest()
                ).encode('utf-8')
            )
            end_nl = True

        return end_nl

    return feeder


def from_text_reader(in_file, filter=None):
    if filter is None:

        def encoding_filter(text_buf):
            return text_buf.encode('utf-8')

    else:

        def encoding_filter(text_buf):
            return filter(text_buf).encode('utf-8')

    return from_raw_reader(in_file, encoding_filter)


def get_cache_key(command):
    print(command)
    if not command.MEMOIZE_OUTPUT:
        return

    if not os.path.isfile(command.path):
        return

    sha1 = hashlib.sha1()

    # Key on the contents of the file
    with open(command.path, 'rb') as f:
        while True:
            data = f.read(2 ** 16)
            if not data:
                break
            sha1.update(data)

    # Vary via the stripped commandline too
    sha1.update(command.shell_cmdline().encode('utf-8'))

    return sha1.hexdigest()


def from_command(command):
    def feeder(out_file):
        key = get_cache_key(command)

        try:
            # Cache hit
            stdout = from_command.cache[key]
            returncode = 0
            logger.debug(
                "Not running %s; we have already saved output",
                command.cmdline(),
            )
        except KeyError:
            with profile('command', command.cmdline()[0]):
                stdout = command.stdout
                returncode = command.returncode

        feeder = from_raw_reader(stdout, command.filter)
        end_nl = feeder(out_file)

        if returncode in (0, -signal.SIGTERM):
            # On success, potentially save the output for later
            if key is not None:
                from_command.cache[key] = stdout
        else:
            # On error, default to displaying all lines of standard output.
            output = command.stderr
            if not output and command.stdout:
                # ... but if we don't have, return the first line of the
                # standard output.
                output = '{}{}'.format(
                    command.stdout[0].decode('utf-8', 'ignore').strip(),
                    '\n[…]' if len(command.stdout) > 1 else '',
                )
            raise subprocess.CalledProcessError(
                returncode, command.cmdline(), output=output.encode('utf-8')
            )
        return end_nl

    return feeder


from_command.cache = {}


def from_text(content):
    def feeder(f):
        for offset in range(0, len(content), DIFF_CHUNK):
            f.write(content[offset : offset + DIFF_CHUNK].encode('utf-8'))
        return content and content[-1] == '\n'

    return feeder


def empty():
    def feeder(f):
        return False

    return feeder
