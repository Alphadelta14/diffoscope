# -*- coding: utf-8 -*-
#
# diffoscope: in-depth comparison of files, archives, and directories
#
# Copyright © 2016 Emanuel Bronshtein <e3amn2l@gmx.com>
# Copyright © 2017 Vagrant Cascadian <vagrant@debian.org>
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

import pytest
import subprocess

from diffoscope.config import Config
from diffoscope.comparators.dtb import DeviceTreeFile
from diffoscope.comparators.missing_file import MissingFile

from utils.data import load_fixture, get_data
from utils.tools import skip_unless_tools_exist, skip_unless_tool_is_at_least

# Generated by: dtc --in-format=dts --out-format=dtb --out=devicetree1.dtb devicetree1.dts
dtb1 = load_fixture('devicetree1.dtb')
# Generated by: dtc --in-format=dts --out-format=dtb --out=devicetree2.dtb devicetree2.dts
dtb2 = load_fixture('devicetree2.dtb')

def fdtdump_version():
    out = subprocess.check_output(('fdtdump', '--version'), stderr=subprocess.STDOUT)
    return out.decode().split()[2]

def test_identification(dtb1):
    assert isinstance(dtb1, DeviceTreeFile)

def test_no_differences(dtb1):
    difference = dtb1.compare(dtb1)
    assert difference is None

@pytest.fixture
def differences(dtb1, dtb2):
    return dtb1.compare(dtb2).details

@skip_unless_tool_is_at_least('fdtdump', fdtdump_version, '1.4.2')
def test_diff(differences):
    expected_diff = get_data('devicetree_expected_diff')
    assert differences[0].unified_diff == expected_diff

@skip_unless_tools_exist('fdtdump')
def test_compare_non_existing(monkeypatch, dtb1):
    monkeypatch.setattr(Config(), 'new_file', True)
    difference = dtb1.compare(MissingFile('/nonexisting', dtb1))
    assert difference.source2 == '/nonexisting'
    assert len(difference.details) > 0
