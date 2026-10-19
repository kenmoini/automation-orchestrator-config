# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fixtures shared by every unit-test directory below tests/unit/plugins."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import FETCH_URL_TARGET, FakeAPI


@pytest.fixture(autouse=True)
def clean_orchestrator_env(monkeypatch):
    """Drop every ORCHESTRATOR_* variable so a developer's shell cannot change auth behavior in tests."""
    for name in [k for k in os.environ if k.startswith("ORCHESTRATOR_")]:
        monkeypatch.delenv(name)


@pytest.fixture
def fake_api(mocker):
    """Patch ``fetch_url`` with a FakeAPI so every test directory shares the same fake server."""
    api = FakeAPI()
    mocker.patch(FETCH_URL_TARGET, new=api)
    return api
