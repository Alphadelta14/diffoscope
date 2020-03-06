# -*- coding: utf-8 -*-
#
# diffoscope: in-depth comparison of files, archives, and directories
#
# Copyright © 2017 Ximin Luo <infinity0@debian.org>
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

from diffoscope.tools import tool_required
from diffoscope.tempfiles import get_temporary_directory
from diffoscope.difference import Difference

from .utils.file import File
from .utils.command import Command

import shutil
import os.path
import logging
import binascii


RDS_HEADERS = {
    binascii.a2b_hex("580a000000020003"),
    binascii.a2b_hex("580a000000030003"),
}

DUMP_RDB = rb"""
hideOutput = lazyLoad(commandArgs(TRUE));

safeDeparse <- function(obj) {
    tryCatch({
        deparse(obj)
    }, error = function (e) {
        (deparse(e))
    });
}

for (x in ls(all.names = TRUE, sorted = TRUE)) {
    obj = get(x)

    cat(sprintf("%s (%s) = ", x, typeof(obj)), sep = "");

    if (typeof(obj) == "environment") {
        cat("\n{\n", sep = "");
        for (y in ls(obj, all.names = TRUE, sorted = TRUE)) {
            obj2 = get(y, envir = obj);
            cat(sprintf("    \"%s\" = \"%s\"\n", y, safeDeparse(obj2)), sep = "");
        }
        cat("}\n");
    } else {
        for (line in safeDeparse(obj))
            cat(line, "\n", sep = "");
    }
    cat("\n");
}
"""

logger = logging.getLogger(__name__)


def check_rds_extension(f):
    return f.name.endswith(".rds") or f.name.endswith(".rdx")


def get_module_path_for_rdb(rdb):
    """
    R's lazyLoad method does not take a filename directly to an .rdb file (eg.
    `/path/to/foo.rdb`) but rather the path without any extension (eg.
    `/path/to/foo`). It also requires that the .rdx file exists at
    `/path/to/foo.rdx`.

    We thus locate the corresponding .rdx file in the surrounding container and
    copy that to `foo.rdx`. We use a temporary directory to ensure we do not
    add files to the user's filesystem in the case of directly comparing two
    .rdb files or, worse, overwriting a file in its place.
    """

    # If we are not in a container, we will never be able to locate the
    # corresponding .rdx
    if rdb.container is None:
        return

    # Calculate location of parallel .rdx file
    rdx_name = "{}.rdx".format(os.path.splitext(rdb.name)[0])

    # Query the container for the full path (eg. `./path/to/foo.rdx`)...
    rdx = rdb.container.get_member(rdx_name)

    if not os.path.exists(rdx.path):
        # ... falling back to looking in the same directory for when
        # comparing two .rdb files directly
        rdx = rdb.container.get_member(os.path.basename(rdx_name))

    if not os.path.exists(rdx.path):
        # Corresponding .rdx does not exist
        return

    temp_dir = get_temporary_directory().name
    prefix = os.path.join(temp_dir, "temp")

    logger.debug("Copying %s and %s to %s", rdx.path, rdb.path, temp_dir)
    shutil.copy(rdb.path, '{}.rdb'.format(prefix))
    shutil.copy(rdx.path, '{}.rdx'.format(prefix))

    # Return the "module" path, ie. without an extension
    return os.path.join(temp_dir, "temp")


class RdsReader(Command):
    @tool_required('Rscript')
    def cmdline(self):
        return [
            'Rscript',
            '--vanilla',
            '-e',
            'args <- commandArgs(TRUE); readRDS(args[1])',
            self.path,
        ]


class RdsFile(File):
    DESCRIPTION = "GNU R Rscript files (.rds)"
    MEMOIZE_OUTPUT = True

    @classmethod
    def recognizes(cls, file):
        if (
            check_rds_extension(file)
            or file.container
            and check_rds_extension(file.container.source)
        ):
            return file.file_header[:8] in RDS_HEADERS
        return False

    def compare_details(self, other, source=None):
        return [Difference.from_command(RdsReader, self.path, other.path)]


class RdbReader(Command):
    MASK_STDERR = True
    MEMOIZE_OUTPUT = True

    @tool_required('Rscript')
    def cmdline(self):
        return ['Rscript', '--vanilla', '-', self.path]

    def input(self):
        return DUMP_RDB


class RdbFile(File):
    DESCRIPTION = "GNU R database files (.rdb)"
    FILE_EXTENSION_SUFFIX = '.rdb'

    def compare_details(self, other, source=None):
        a = get_module_path_for_rdb(self)
        b = get_module_path_for_rdb(other)

        if a is None or b is None:
            return []

        return [Difference.from_command(RdbReader, a, b)]
