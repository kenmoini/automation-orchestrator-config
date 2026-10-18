# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared unit-test helpers for the collection (importable from any test directory)."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import contextlib
import json
from unittest import mock
from urllib.parse import parse_qsl, urlparse

from ansible.module_utils import basic

try:
    from ansible.module_utils.testing import patch_module_args as _patch_module_args
except ImportError:  # ansible-core < 2.19
    _patch_module_args = None

DEFAULT_HOST = "https://orch.example.com"
DEFAULT_TOKEN = "t0k"
FETCH_URL_TARGET = "ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api.fetch_url"


class AnsibleExitJson(Exception):
    """Raised in place of ``exit_json`` so tests can inspect the result."""

    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.kwargs = kwargs


class AnsibleFailJson(Exception):
    """Raised in place of ``fail_json`` so tests can inspect the failure."""

    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.kwargs = kwargs


def _exit_json(self, **kwargs):
    kwargs.setdefault("changed", False)
    raise AnsibleExitJson(kwargs)


def _fail_json(self, **kwargs):
    kwargs["failed"] = True
    raise AnsibleFailJson(kwargs)


@contextlib.contextmanager
def module_args(args):
    """Expose ``args`` as the module arguments of AnsibleModule instances created in this context."""
    if _patch_module_args is not None:
        with _patch_module_args(args):
            yield
        return
    payload = json.dumps({"ANSIBLE_MODULE_ARGS": args}).encode("utf-8")
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(basic, "_ANSIBLE_ARGS", payload))
        if hasattr(basic, "_ANSIBLE_PROFILE"):  # only present on 2.19+, where patch_module_args normally exists
            stack.enter_context(mock.patch.object(basic, "_ANSIBLE_PROFILE", "legacy"))
        yield


@contextlib.contextmanager
def patched_exits():
    """Patch AnsibleModule.exit_json/fail_json to raise AnsibleExitJson/AnsibleFailJson."""
    with mock.patch.object(basic.AnsibleModule, "exit_json", _exit_json), mock.patch.object(basic.AnsibleModule, "fail_json", _fail_json):
        yield


class FakeResponse:
    def __init__(self, raw):
        self._raw = raw

    def read(self):
        return self._raw


class FakeAPI:
    """Stand-in for ``fetch_url`` that serves canned responses and records every call."""

    def __init__(self):
        self.routes = []
        self.calls = []

    def add(self, method, path, status, body=None, query=None, headers=None, times=None):
        self.routes.append(
            {
                "method": method.upper(),
                "path": path,
                "status": status,
                "body": body,
                "query": dict(query or {}),
                "headers": dict(headers or {}),
                "times": times,
            }
        )
        return self

    def _match(self, method, path, query):
        for route in self.routes:
            if route["times"] is not None and route["times"] <= 0:
                continue
            if route["method"] != method or route["path"] != path:
                continue
            if any(query.get(k) != str(v) for k, v in route["query"].items()):
                continue
            return route
        return None

    def __call__(self, module, url, data=None, headers=None, method=None, timeout=None, **kw):
        parsed = urlparse(url)
        method = (method or "GET").upper()
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        raw = data.decode("utf-8") if isinstance(data, bytes) else data
        try:
            body = json.loads(raw) if raw else None
        except ValueError:
            body = raw
        self.calls.append({"method": method, "path": parsed.path, "query": query, "body": body, "raw": raw, "headers": dict(headers or {}), "timeout": timeout})

        route = self._match(method, parsed.path, query)
        if route is None:
            raise AssertionError(f"FakeAPI: unexpected request {method} {url}")
        if route["times"] is not None:
            route["times"] -= 1

        status = route["status"]
        payload = b"" if route["body"] is None else json.dumps(route["body"]).encode("utf-8")
        info = {"status": status, "url": url, "body": payload, "msg": f"HTTP Error {status}"}
        for key, value in route["headers"].items():
            info[key.lower()] = str(value)
        if 200 <= status < 300:
            info["msg"] = "OK"
            return FakeResponse(payload), info
        return None, info


def make_module(fake_api=None, argument_spec=None, supports_check_mode=False, **params):
    """Build an OrchestratorModule with default host/token unless overridden; exits raise test exceptions."""
    from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule

    args = {"orchestrator_host": DEFAULT_HOST}
    if not any(params.get(k) is not None for k in ("orchestrator_username", "orchestrator_client_id")):
        args["orchestrator_token"] = DEFAULT_TOKEN
    args.update(params)
    args = {k: v for k, v in args.items() if v is not None}
    with module_args(args), patched_exits():
        module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=supports_check_mode)
    module.exit_json = lambda **kw: _exit_json(module, **kw)
    module.fail_json = lambda **kw: _fail_json(module, **kw)
    return module
