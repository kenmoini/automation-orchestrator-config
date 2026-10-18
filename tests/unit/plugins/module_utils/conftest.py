# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import FETCH_URL_TARGET, FakeAPI


@pytest.fixture
def fake_api(mocker):
    api = FakeAPI()
    mocker.patch(FETCH_URL_TARGET, new=api)
    return api
