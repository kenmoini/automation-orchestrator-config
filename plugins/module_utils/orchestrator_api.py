# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared base class for kenmoini.automation_orchestrator_config modules.

Provides authentication (static token, OAuth2 client credentials, username/password login),
a JSON HTTP client on top of ``fetch_url``, RFC 9457 problem-details error handling,
cursor pagination and name -> UUID resolution.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import time
import uuid

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
PAGE_LIMIT = 100

# List path -> server-side query parameter that filters by name. Matches are still exact-checked client-side.
SERVER_NAME_FILTERS = {
    "/projects": "name",
    "/roles": "name",
    "/policies": "name",
    "/service_accounts": "name",
    "/users": "username",
    "/users/directory": "username",
    "/groups/directory": "name",
}

# Scope rules for LOOKUPS.
SCOPE_NONE = None  # global resource
SCOPE_QUERY = "query"  # optional project_id sent as a list query parameter; None means system scope (project_id null)
SCOPE_CLIENT = "client"  # optional project_id matched client-side against the object's project_id
SCOPE_PATH = "path"  # project_id required in the path template

# kind -> (list path template, name field, scope rule)
LOOKUPS = {
    "project": ("/projects", "name", SCOPE_NONE),
    "user": ("/users", "username", SCOPE_NONE),
    "group": ("/groups", "name", SCOPE_NONE),
    "role": ("/roles", "name", SCOPE_QUERY),
    "policy": ("/policies", "name", SCOPE_QUERY),
    "credential_type": ("/credential_types", "name", SCOPE_NONE),
    "credential": ("/projects/{project_id}/credentials", "name", SCOPE_PATH),
    "integration": ("/integrations", "name", SCOPE_NONE),
    "identity_provider": ("/identity_providers", "name", SCOPE_NONE),
    "service_account": ("/service_accounts", "name", SCOPE_CLIENT),
    "workflow": ("/projects/{project_id}/workflows", "name", SCOPE_PATH),
}

GROUP_DIRECTORY_PATH = "/groups/directory"

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


def is_uuid(value):
    """Return True when ``value`` parses as a UUID."""
    if value is None or isinstance(value, bool):
        return False
    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def _in_project(project_id):
    """Return a predicate matching objects whose ``project_id`` equals ``project_id``."""

    def predicate(obj):
        return obj.get("project_id") == project_id

    return predicate


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
        # On HTTP errors fetch_url returns the already-read-and-closed HTTPError as ``response``
        # and puts the body in info["body"]; on connection failures ``response`` is None.
        if response is None or status >= 400:
            raw = info.get("body")
        else:
            raw = response.read()
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

    # ------------------------------------------------------------ pagination

    def get_all(self, path, query=None):
        """Return every resource of a cursor-paginated list endpoint (``limit=100``, following ``next``)."""
        base_query = dict(query or {})
        base_query["limit"] = PAGE_LIMIT
        base_query.pop("cursor", None)
        resources = []
        seen = set()
        cursor = None
        while True:
            page_query = dict(base_query)
            if cursor is not None:
                page_query["cursor"] = cursor
            body = self.request("GET", path, query=page_query)
            if not isinstance(body, dict):
                self.fail_json(msg="Unexpected list response from {0}{1}: expected an object with 'resources'".format(API_PREFIX, path))
            resources.extend(body.get("resources") or [])
            cursor = body.get("next")
            if cursor is None or cursor == "":
                return resources
            if cursor in seen:
                self.fail_json(msg="Pagination loop on {0}{1}: the API returned cursor '{2}' more than once".format(API_PREFIX, path, cursor))
            seen.add(cursor)

    def get_one_by_name(self, path, name, name_field="name", query=None, label=None):
        """Return the single object of ``path`` whose ``name_field`` equals ``name`` exactly, or ``None``.

        Uses the server-side name filter when ``path`` has one (``SERVER_NAME_FILTERS``) and fails
        the module when more than one object matches.
        """
        return self._find_by_name(path, name, name_field=name_field, query=query, label=label)

    def _find_by_name(self, path, name, name_field="name", query=None, label=None, predicate=None):
        query = dict(query or {})
        filter_param = SERVER_NAME_FILTERS.get(path)
        if filter_param:
            query[filter_param] = name
        matches = [obj for obj in self.get_all(path, query=query) if isinstance(obj, dict) and obj.get(name_field) == name]
        if predicate is not None:
            matches = [obj for obj in matches if predicate(obj)]
        if not matches:
            return None
        if len(matches) > 1:
            if label is None:
                label = path.rstrip("/").split("/")[-1]
            self.fail_json(msg="Found {0} {1} named '{2}'; expected 1".format(len(matches), label, name))
        return matches[0]

    # ------------------------------------------------------------ resolution

    def _lookup_spec(self, kind):
        if kind not in LOOKUPS:
            self.fail_json(msg="Unknown lookup kind '{0}'; expected one of: {1}".format(kind, ", ".join(sorted(LOOKUPS))))
        return LOOKUPS[kind]

    def _lookup_path(self, kind, value, project_id):
        """Return ``(list path, scope rule, name field)`` for ``kind``, failing when a required project_id is missing."""
        template, name_field, scope = self._lookup_spec(kind)
        if scope == SCOPE_PATH:
            if project_id is None:
                self.fail_json(msg="Cannot resolve {0} '{1}' without project_id: {0}s are scoped to a project".format(kind, value))
            return template.format(project_id=project_id), scope, name_field
        return template, scope, name_field

    def _not_found_msg(self, kind, value, project_id):
        msg = "{0} '{1}' not found".format(kind, value)
        if project_id is not None and LOOKUPS[kind][2] is not SCOPE_NONE:
            msg += " in project {0}".format(project_id)
        return msg

    def _lookup_by_name(self, kind, value, project_id):
        path, scope, name_field = self._lookup_path(kind, value, project_id)
        label = path.rstrip("/").split("/")[-1]
        query = None
        predicate = None
        if scope == SCOPE_QUERY:
            # project_id None means system scope: only objects without a project_id match.
            predicate = _in_project(project_id)
            if project_id is not None:
                query = {"project_id": project_id}
        elif scope == SCOPE_CLIENT and project_id is not None:
            predicate = _in_project(project_id)
        try:
            if kind == "group":
                try:
                    return self._find_by_name(GROUP_DIRECTORY_PATH, value, name_field=name_field, label=label)
                except OrchestratorAPIError as err:
                    if err.status != 403:
                        raise
            return self._find_by_name(path, value, name_field=name_field, query=query, label=label, predicate=predicate)
        except OrchestratorAPIError as err:
            self.fail_api(err, "Failed to look up {0} '{1}'".format(kind, value))

    def resolve_id(self, kind, value, project_id=None, required=True):
        """Return the UUID for ``value`` (a UUID is returned as-is without any HTTP call).

        Fails with ``"<kind> '<value>' not found"`` when ``required``; returns ``None`` otherwise.
        """
        self._lookup_spec(kind)
        if value is None or value == "":
            return None
        if is_uuid(value):
            return value
        obj = self._lookup_by_name(kind, value, project_id)
        if obj is None:
            if required:
                self.fail_json(msg=self._not_found_msg(kind, value, project_id))
            return None
        return obj["id"]

    def resolve_obj(self, kind, value, project_id=None):
        """Return the object for ``value`` (name or UUID), or ``None`` when it does not exist.

        A UUID is fetched with ``GET <path>/<id>`` (404 -> ``None``). Groups found by name are
        re-fetched by id because the group directory only returns ``id`` and ``name``.
        """
        self._lookup_spec(kind)
        if value is None or value == "":
            return None
        if not is_uuid(value):
            obj = self._lookup_by_name(kind, value, project_id)
            if obj is None or kind != "group":
                return obj
            value = obj["id"]
        path = self._lookup_path(kind, value, project_id)[0]
        try:
            return self.request("GET", "{0}/{1}".format(path, value))
        except OrchestratorAPIError as err:
            if err.status == 404:
                return None
            self.fail_api(err, "Failed to fetch {0} '{1}'".format(kind, value))
