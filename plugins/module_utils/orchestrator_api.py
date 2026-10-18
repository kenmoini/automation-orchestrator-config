# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared base class for kenmoini.automation_orchestrator_config modules.

Provides authentication (static token, OAuth2 client credentials, username/password login),
a JSON HTTP client on top of ``fetch_url`` and RFC 9457 problem-details error handling.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import time

from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.urls import fetch_url

try:
    from urllib.parse import urlencode
except ImportError:  # pragma: no cover - Python 2
    from urllib import urlencode

API_PREFIX = "/api/v1"
DEFAULT_EXPECT = (200, 201, 202, 204)
MAX_RATE_LIMIT_RETRIES = 3
DEFAULT_RETRY_AFTER = 1.0
MAX_RETRY_AFTER = 30.0

AUTH_ARGUMENT_SPEC = dict(
    orchestrator_host=dict(type="str", required=True, fallback=(env_fallback, ["ORCHESTRATOR_HOST"])),
    orchestrator_username=dict(type="str", fallback=(env_fallback, ["ORCHESTRATOR_USERNAME"])),
    orchestrator_password=dict(type="str", no_log=True, fallback=(env_fallback, ["ORCHESTRATOR_PASSWORD"])),
    orchestrator_token=dict(type="str", no_log=True, fallback=(env_fallback, ["ORCHESTRATOR_TOKEN"])),
    orchestrator_client_id=dict(type="str", fallback=(env_fallback, ["ORCHESTRATOR_CLIENT_ID"])),
    orchestrator_client_secret=dict(type="str", no_log=True, fallback=(env_fallback, ["ORCHESTRATOR_CLIENT_SECRET"])),
    validate_certs=dict(type="bool", default=True, aliases=["orchestrator_validate_certs"], fallback=(env_fallback, ["ORCHESTRATOR_VERIFY_SSL"])),
    request_timeout=dict(type="float", default=10, fallback=(env_fallback, ["ORCHESTRATOR_REQUEST_TIMEOUT"])),
)

AUTH_MUTUALLY_EXCLUSIVE = [
    ["orchestrator_token", "orchestrator_username"],
    ["orchestrator_token", "orchestrator_client_id"],
    ["orchestrator_username", "orchestrator_client_id"],
]

AUTH_REQUIRED_TOGETHER = [
    ["orchestrator_username", "orchestrator_password"],
    ["orchestrator_client_id", "orchestrator_client_secret"],
]


class OrchestratorAPIError(Exception):
    """A non-successful Automation Orchestrator API response (RFC 9457 problem details when available)."""

    def __init__(self, status, detail, code=None, title=None, body=None):
        super(OrchestratorAPIError, self).__init__(detail)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.body = body

    @classmethod
    def from_response(cls, status, body, info):
        """Build an error from a parsed response body, falling back to the transport message."""
        fallback = to_text(info.get("msg") or "HTTP Error {0}".format(status))
        if isinstance(body, dict):
            detail = body.get("detail") or body.get("title") or fallback
            return cls(status, to_text(detail), code=body.get("code"), title=body.get("title"), body=body)
        return cls(status, fallback, body=body)


def normalize_host(host):
    """Return ``host`` as a base URL: ``https://`` added when no scheme is given, no trailing slash."""
    host = (host or "").strip()
    if not host:
        raise ValueError("orchestrator_host must not be empty")
    if "://" not in host:
        host = "https://" + host
    host = host.rstrip("/")
    if host.endswith("://"):
        raise ValueError("orchestrator_host must include a hostname")
    return host


def _parse_body(raw):
    """Decode a response body: parsed JSON when possible, else text, ``None`` when empty."""
    if raw is None:
        return None
    text = to_text(raw, errors="surrogate_or_strict")
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except ValueError:
        return text


def _query_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


class OrchestratorModule(AnsibleModule):
    """AnsibleModule with Automation Orchestrator auth options and an authenticated JSON client."""

    def __init__(self, argument_spec=None, **kwargs):
        spec = dict(argument_spec or {})
        spec.update(AUTH_ARGUMENT_SPEC)
        kwargs["mutually_exclusive"] = list(kwargs.get("mutually_exclusive") or []) + AUTH_MUTUALLY_EXCLUSIVE
        kwargs["required_together"] = list(kwargs.get("required_together") or []) + AUTH_REQUIRED_TOGETHER
        super(OrchestratorModule, self).__init__(argument_spec=spec, **kwargs)

        try:
            self.base_url = normalize_host(self.params["orchestrator_host"])
        except ValueError as exc:
            self.fail_json(msg=to_text(exc))
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self._token = None
        self._authenticated = False

    # ------------------------------------------------------------------ auth

    def authenticate(self):
        """Obtain a bearer token (static token > client credentials > username/password) and store it."""
        self.headers.pop("Authorization", None)
        params = self.params
        if params.get("orchestrator_token"):
            token = params["orchestrator_token"]
        elif params.get("orchestrator_client_id"):
            form = {
                "grant_type": "client_credentials",
                "client_id": params["orchestrator_client_id"],
                "client_secret": params["orchestrator_client_secret"],
            }
            token = self._fetch_token("/auth/token", form=form)
        elif params.get("orchestrator_username"):
            data = {"username": params["orchestrator_username"], "password": params["orchestrator_password"]}
            token = self._fetch_token("/auth/login", data=data)
        else:
            self.fail_json(
                msg="No credentials supplied: set orchestrator_token, orchestrator_client_id/orchestrator_client_secret, "
                "or orchestrator_username/orchestrator_password (or the matching ORCHESTRATOR_* environment variables)."
            )
        self._token = token
        self.headers["Authorization"] = "Bearer {0}".format(token)
        self._authenticated = True
        return token

    def _fetch_token(self, path, data=None, form=None):
        try:
            body = self._call("POST", self._build_url(path), data=data, form=form, expect=(200, 201))
        except OrchestratorAPIError as err:
            self.fail_api(err, "Authentication against {0}{1} failed".format(API_PREFIX, path))
        if not isinstance(body, dict) or not body.get("access_token"):
            self.fail_json(msg="Authentication response from {0}{1} did not contain an access_token".format(API_PREFIX, path))
        return body["access_token"]

    def _can_reauthenticate(self):
        return bool(self.params.get("orchestrator_client_id") or self.params.get("orchestrator_username"))

    # ------------------------------------------------------------------ http

    def _build_url(self, path, query=None):
        if not path.startswith("/"):
            path = "/" + path
        if not (path == API_PREFIX or path.startswith(API_PREFIX + "/")):
            path = API_PREFIX + path
        url = self.base_url + path
        if query:
            pairs = [(k, _query_value(v)) for k, v in query.items() if v is not None]
            if pairs:
                url += "?" + urlencode(pairs, doseq=True)
        return url

    def _send(self, method, url, data=None, form=None):
        """Perform one HTTP request; return ``(status, parsed_body, info)``."""
        headers = dict(self.headers)
        payload = None
        if form is not None:
            payload = urlencode(form)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif data is not None:
            payload = json.dumps(data)
        response, info = fetch_url(self, url, data=payload, headers=headers, method=method, timeout=self.params["request_timeout"])
        status = info.get("status", -1)
        if response is not None:
            raw = response.read()
        else:
            raw = info.get("body")
        return status, _parse_body(raw), info

    def _retry_after(self, info):
        value = info.get("retry-after")
        try:
            delay = float(value)
        except (TypeError, ValueError):
            delay = DEFAULT_RETRY_AFTER
        return max(0.0, min(delay, MAX_RETRY_AFTER))

    def _call(self, method, url, data=None, form=None, expect=None):
        """Send a request, retrying 429 responses; return the parsed body or raise OrchestratorAPIError."""
        expect = DEFAULT_EXPECT if expect is None else expect
        attempts = 0
        while True:
            status, body, info = self._send(method, url, data=data, form=form)
            if status in expect:
                return None if status == 204 else body
            if status == 429 and attempts < MAX_RATE_LIMIT_RETRIES:
                attempts += 1
                time.sleep(self._retry_after(info))
                continue
            raise OrchestratorAPIError.from_response(status, body, info)

    def request(self, method, path, query=None, data=None, form=None, expect=None):
        """Call ``API_PREFIX + path`` with bearer auth; return parsed JSON (``None`` for 204).

        Re-authenticates once on 401 when credentials allow it, retries 429 per ``Retry-After``
        and raises OrchestratorAPIError for any other unexpected status.
        """
        if not self._authenticated:
            self.authenticate()
        method = method.upper()
        url = self._build_url(path, query)
        try:
            return self._call(method, url, data=data, form=form, expect=expect)
        except OrchestratorAPIError as err:
            if err.status != 401 or not self._can_reauthenticate():
                raise
        self.authenticate()
        return self._call(method, url, data=data, form=form, expect=expect)

    # ---------------------------------------------------------------- errors

    def fail_api(self, err, context=""):
        """Fail the module from an OrchestratorAPIError, keeping status, code and body for the user."""
        msg = "{0}: {1}".format(context, err.detail) if context else err.detail
        self.fail_json(msg=msg, status=err.status, code=err.code, body=err.body)
