# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: setting
short_description: Manage runtime settings of the Automation Orchestrator
description:
  - Sets one runtime setting by key with O(name) and O(value), or several at once with O(settings).
  - Settings always exist, so the module never creates or deletes them. It only changes their value.
  - Only settings whose value differs are written. Several changed settings are written with one bulk request.
  - A setting whose value is V(null) uses its default. Setting the value to what the default already is changes nothing.
  - The value type of every setting is reported by the API as C(value_type), one of V(string), V(integer), V(float), V(boolean) or V(json).
    Use M(kenmoini.automation_orchestrator_config.setting_info) to inspect it.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
  diff_mode:
    support: full
options:
  name:
    description:
      - Key of the setting to change, for example V(general.session_timeout).
      - Mutually exclusive with O(settings). One of O(name) or O(settings) is required.
    type: str
  value:
    description:
      - New value of the setting named by O(name). It can be of any type that matches the C(value_type) of the setting.
      - When O(name) is given without O(value), the setting is reset to its default by sending V(null).
      - Ignored when O(settings) is used.
      - A string is converted to a number when the C(value_type) of the setting is V(integer) or V(float), and to a boolean (V(true) or V(false), any case)
        when it is V(boolean). A boolean is never considered equal to a number.
      - Sensitive values appear in the C(diff) and C(settings) output. Use C(no_log) on the task to hide them.
    type: raw
  settings:
    description:
      - Dictionary of setting keys and their new values.
      - A value of V(null) resets that setting to its default.
      - Mutually exclusive with O(name).
    type: dict
  expected_version:
    description:
      - Version of the setting the change is based on. The API answers with a conflict when the setting was changed in the meantime.
      - Only valid together with O(name).
    type: int
seealso:
  - module: kenmoini.automation_orchestrator_config.setting_info
"""

EXAMPLES = r"""
- name: Change one setting
  kenmoini.automation_orchestrator_config.setting:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: general.session_timeout
    value: 3600

- name: Change several settings at once
  kenmoini.automation_orchestrator_config.setting:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    settings:
      general.session_timeout: 3600
      notifications.enabled: true

- name: Reset a setting to its default
  kenmoini.automation_orchestrator_config.setting:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: general.session_timeout
...
"""

RETURN = r"""
settings:
  description: The effective value of every requested setting after the module ran. In check mode it is what the value would be.
  returned: always
  type: dict
  sample:
    general.session_timeout: 3600
changed_keys:
  description: Sorted keys of the settings that were changed, or would be changed in check mode.
  returned: always
  type: list
  elements: str
  sample:
    - general.session_timeout
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import (
    OrchestratorAPIError,
    OrchestratorModule,
    _differs,
)


def _coerce(row, wanted):
    """Convert a string ``wanted`` to the ``value_type`` of the setting row when it is a number or a boolean; otherwise return it as is."""
    if not isinstance(wanted, str):
        return wanted
    value_type = row.get("value_type")
    text = wanted.strip()
    try:
        if value_type == "integer":
            return int(text)
        if value_type == "float":
            return float(text)
    except ValueError:
        return wanted
    if value_type == "boolean" and text.lower() in ("true", "false"):
        return text.lower() == "true"
    return wanted


def _differ(current, wanted):
    """Compare like ``_differs`` but never treat a boolean as equal to a number."""
    if isinstance(current, bool) != isinstance(wanted, bool):
        return True
    return _differs(current, wanted)


def _is_unchanged(current, wanted):
    """Return True when the setting row ``current`` already has the desired ``wanted`` value (None means: use the default)."""
    explicit = current.get("value")
    if wanted is None:
        return explicit is None
    if explicit is None:
        return not _differ(current.get("default_value"), wanted)
    return not _differ(explicit, wanted)


def main():
    argument_spec = dict(
        name=dict(type="str"),
        value=dict(type="raw"),
        settings=dict(type="dict"),
        expected_version=dict(type="int"),
    )
    module = OrchestratorModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[["name", "settings"]],
        required_one_of=[["name", "settings"]],
    )
    params = module.params
    if params["settings"] is not None and params["expected_version"] is not None:
        module.fail_json(msg="expected_version can only be used together with name")

    if params["name"] is not None and not params["name"]:
        module.fail_json(msg="name must not be empty")
    if params["name"] is not None:
        wanted = [(params["name"], params["value"])]
    else:
        wanted = list(params["settings"].items())
    keys = [key for key, _ in wanted]

    try:
        if len(wanted) == 1:
            key = keys[0]
            try:
                rows = {key: module.request("GET", "/settings/{0}".format(key))}
            except OrchestratorAPIError as err:
                if err.status != 404:
                    raise
                rows = {}
        else:
            rows = dict((row["key"], row) for row in module.get_all("/settings"))
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to look up settings")
    for key in keys:
        if key not in rows or rows[key] is None:
            module.fail_json(msg="setting '{0}' not found".format(key))

    result = {}
    changes = []
    for key, value in wanted:
        current = rows[key]
        value = _coerce(current, value)
        if _is_unchanged(current, value):
            result[key] = current.get("effective_value")
        else:
            changes.append((key, value))
            result[key] = current.get("default_value") if value is None else value
    changed_keys = sorted(key for key, _ in changes)

    module._diff = {"before": {}, "after": {}}
    if changes:
        module._diff = {
            "before": dict((key, rows[key].get("effective_value")) for key, _ in changes),
            "after": dict((key, result[key]) for key, _ in changes),
        }
    if changes and not module.check_mode:
        try:
            if params["name"] is not None:
                body = {"value": changes[0][1]}
                if params["expected_version"] is not None:
                    body["expected_version"] = params["expected_version"]
                updated = module.request("PATCH", "/settings/{0}".format(changes[0][0]), data=body)
                updated_rows = [updated] if isinstance(updated, dict) else []
            else:
                updated = module.request("PATCH", "/settings", data={"updates": [{"key": key, "value": value} for key, value in changes]})
                updated_rows = updated.get("resources") or [] if isinstance(updated, dict) else []
        except OrchestratorAPIError as err:
            module.fail_api(err, "Failed to update setting(s) {0}".format(", ".join(key for key, _ in changes)))
        for row in updated_rows:
            if row.get("key") in result and "effective_value" in row:
                result[row["key"]] = row["effective_value"]

    out = dict(changed=bool(changes), settings=result, changed_keys=changed_keys)
    if module._diff_mode and module._diff is not None:
        out["diff"] = module._diff
    module.exit_json(**out)


if __name__ == "__main__":
    main()
