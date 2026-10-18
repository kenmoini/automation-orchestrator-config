# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: integration
short_description: Manage integrations in the Automation Orchestrator
description:
  - Creates, updates, renames and deletes integrations with MCP servers, LLM providers and Ansible Automation Platform.
  - Also assigns integrations to projects, enables or disables their models and tools, and can refresh and validate them.
  - Integrations are looked up by O(name). Only the options you set are compared and changed.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description:
      - Project, model and tool changes are read and reported but not made.
      - O(refresh), O(validate) and the discovery done when creating are skipped.
  diff_mode:
    support: partial
    description: Project, model and tool changes are not shown in the diff.
options:
  name:
    description: Name of the integration, used to look it up.
    type: str
    required: true
  new_name:
    description:
      - Rename the integration called O(name) to this name. Only used when O(state=present).
      - The module is idempotent. When no integration is called O(name) but one is called O(new_name),
        that integration is used as is, so a rerun makes no change.
      - When neither integration exists, the integration is created with O(new_name).
    type: str
  description:
    description: Description of the integration.
    type: str
  integration_type:
    description:
      - Type of the integration.
      - Required to create an integration. It cannot be changed on an existing integration.
    type: str
    choices: [mcp_server, llm_provider, ansible_automation_platform]
  configuration:
    description:
      - Connection settings of the integration, such as C(base_url), C(allow_http), C(insecure_skip_tls_verify) and C(ca_certificate).
      - LLM providers also need C(provider_hint), one of C(red_hat_ai), C(openai), C(anthropic), C(gemini) or C(custom).
      - The module adds the integration type to it as C(integration_type).
      - The keys you set are compared with the existing configuration. When any differs, the whole configuration is sent, with the keys you did not set kept.
    type: dict
  management_credential:
    description:
      - Name or ID of the credential used to connect to the integration.
      - A name is looked up in O(management_credential_project).
    type: str
  management_credential_project:
    description:
      - Name or ID of the project that owns O(management_credential).
      - Required when O(management_credential) is a name.
    type: str
  enabled:
    description: Whether the integration is enabled.
    type: bool
  scope:
    description: Whether the integration is available to all projects (V(global)) or only to the projects it is assigned to (V(project)).
    type: str
    choices: [global, project]
  labels:
    description: Labels of the integration as key/value pairs.
    type: dict
  projects:
    description:
      - Names or IDs of the projects the integration is assigned to.
      - When set, the assignments are made to match this list, and an empty list removes all of them.
      - When not set, assignments are left untouched.
    type: list
    elements: str
  models:
    description:
      - Models of an LLM provider integration to enable, disable or make the default.
      - Models that are not listed are left untouched.
      - The task fails when a listed model is not known to the integration. Use O(refresh=true) to fetch new models from the provider.
    type: list
    elements: dict
    suboptions:
      model_id:
        description: ID of the model at the provider. Matched before O(models[].name).
        type: str
      name:
        description: Name of the model. Matched against the model ID first, then the model name.
        type: str
      enabled:
        description: Whether the model is enabled.
        type: bool
      is_default:
        description: Whether the model is the default model of the integration.
        type: bool
  tools:
    description:
      - Tools of an MCP server integration to enable or disable.
      - Tools that are not listed are left untouched.
      - The task fails when a listed tool is not known to the integration. Use O(refresh=true) to fetch new tools from the server.
    type: list
    elements: dict
    suboptions:
      name:
        description: Name of the tool. Matched against the tool name first, then the namespaced name.
        type: str
        required: true
      enabled:
        description: Whether the tool is enabled.
        type: bool
  discover:
    description:
      - When creating an integration with O(models) or O(tools), discover them on the provider first and create the integration with them.
      - The listed models and tools are created with the requested flags. The others are created with the server defaults.
      - When V(false), the integration is created first and the listed models and tools are updated afterwards.
    type: bool
    default: true
  refresh:
    description:
      - Fetch the current models or tools from the provider after the integration is created or updated.
      - Reported as a change only when existing models or tools were updated.
    type: bool
    default: false
  validate:
    description:
      - Test the connection to the integration at the end of the task. The result is returned in RV(validation).
      - A failed validation does not fail the task and is never reported as a change.
    type: bool
    default: false
  state:
    description:
      - V(present) creates the integration or updates it to match the options.
      - V(exists) creates the integration when it is missing and never modifies an existing one.
      - V(absent) deletes the integration. Deletion is permanent.
    type: str
    choices: [present, absent, exists]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.integration_info
  - module: kenmoini.automation_orchestrator_config.credential
"""

EXAMPLES = r"""
- name: Create an LLM provider with two enabled models
  kenmoini.automation_orchestrator_config.integration:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: openai
    integration_type: llm_provider
    configuration:
      provider_hint: openai
      base_url: https://api.openai.com/v1
    management_credential: openai-key
    management_credential_project: platform
    models:
      - model_id: gpt-4o
        enabled: true
        is_default: true
      - name: gpt-4o-mini
        enabled: true
    validate: true
  register: openai

- name: Assign an MCP server to two projects and disable one tool
  kenmoini.automation_orchestrator_config.integration:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: docs-mcp
    integration_type: mcp_server
    configuration:
      base_url: https://mcp.example.com/mcp
    scope: project
    projects:
      - platform
      - networking
    tools:
      - name: delete_page
        enabled: false
    refresh: true

- name: Delete an integration
  kenmoini.automation_orchestrator_config.integration:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: docs-mcp
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the integration, or V(null) when it was deleted or does not exist.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
integration:
  description: The integration as returned by the API, or V(null) when it was deleted or does not exist.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the integration.
      type: str
    name:
      description: Name of the integration.
      type: str
    description:
      description: Description of the integration.
      type: str
    integration_type:
      description: Type of the integration.
      type: str
    enabled:
      description: Whether the integration is enabled.
      type: bool
    scope:
      description: V(global) or V(project).
      type: str
    configuration:
      description: Connection settings of the integration.
      type: dict
    management_credential_id:
      description: ID of the management credential.
      type: str
    validation_status:
      description: Result of the last validation.
      type: str
    last_validated_at:
      description: Timestamp of the last validation.
      type: str
    validation_error:
      description: Error of the last validation.
      type: str
    refresh_status:
      description: Result of the last refresh.
      type: str
    last_refreshed_at:
      description: Timestamp of the last refresh.
      type: str
    refresh_error:
      description: Error of the last refresh.
      type: str
    project_ids:
      description: IDs of the projects the integration is assigned to.
      type: list
      elements: str
    total_tool_count:
      description: Number of tools.
      type: int
    enabled_tool_count:
      description: Number of enabled tools.
      type: int
    total_model_count:
      description: Number of models.
      type: int
    enabled_model_count:
      description: Number of enabled models.
      type: int
    labels:
      description: Labels of the integration.
      type: dict
  sample:
    id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    name: openai
    integration_type: llm_provider
    enabled: true
    scope: global
    configuration:
      integration_type: llm_provider
      provider_hint: openai
      base_url: https://api.openai.com/v1
projects:
  description: Names of the projects the integration is assigned to after the module ran.
  returned: when O(projects) is set and the integration exists
  type: list
  elements: str
  sample: [platform, networking]
models:
  description: The models of the integration after the module ran.
  returned: when O(models) is set and the integration exists
  type: list
  elements: dict
  sample:
    - id: 5b0a7c1e-2f3d-4e6a-8b9c-0d1e2f3a4b5c
      model_id: gpt-4o
      name: GPT-4o
      enabled: true
      is_default: true
tools:
  description: The tools of the integration after the module ran.
  returned: when O(tools) is set and the integration exists
  type: list
  elements: dict
  sample:
    - id: 7c1e2f3d-4e6a-4b9c-8d1e-2f3a4b5c6d7e
      name: delete_page
      namespaced_name: docs_mcp__delete_page
      enabled: false
refresh_result:
  description: Result of the refresh.
  returned: when O(refresh=true) and not in check mode
  type: dict
  contains:
    synced_count:
      description: Number of new models or tools.
      type: int
    updated_count:
      description: Number of updated models or tools.
      type: int
    missing_count:
      description: Number of models or tools the provider no longer offers.
      type: int
    refreshed_at:
      description: Timestamp of the refresh.
      type: str
  sample:
    synced_count: 2
    updated_count: 0
    missing_count: 0
    refreshed_at: "2026-10-18T12:00:00Z"
validation:
  description: Result of the connection test.
  returned: when O(validate=true) and not in check mode
  type: dict
  contains:
    success:
      description: Whether the connection test succeeded.
      type: bool
    checked_at:
      description: Timestamp of the test.
      type: str
    error:
      description: Error message when the test failed.
      type: str
    error_type:
      description: Category of the error when the test failed.
      type: str
  sample:
    success: true
    checked_at: "2026-10-18T12:00:00Z"
    error: null
    error_type: null
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule, is_uuid

INTEGRATIONS = "/integrations"
MODEL_FLAGS = ("enabled", "is_default")
TOOL_FLAGS = ("enabled",)


def _fail_missing(module, kind, key, name):
    module.fail_json(msg="{0} '{1}' not found on integration '{2}'; run with refresh: true".format(kind, key, name))


def _model_key(entry):
    return entry.get("model_id") or entry.get("name")


def _find(items, key, fields):
    """Return the first item whose ``fields`` (tried in order) equals ``key``, or ``None``."""
    for field in fields:
        for item in items:
            if item.get(field) == key:
                return item
    return None


def _flags(entry, flags):
    return dict((flag, entry[flag]) for flag in flags if entry.get(flag) is not None)


def _resolve_management_credential(module, params):
    """Return the ID of O(management_credential), failing early when a name has no project."""
    value = params["management_credential"]
    if not value:
        return None
    if is_uuid(value):
        return value
    if not params["management_credential_project"]:
        module.fail_json(msg="management_credential_project is required when management_credential is a name")
    project_id = module.resolve_id("project", params["management_credential_project"])
    return module.resolve_id("credential", value, project_id=project_id)


def _discover(module, name, desired, params):
    """Discover models/tools on the provider and add the ``discovered_*`` selections to the create body ``desired``."""
    body = module.build_desired(
        {
            "integration_type": desired["integration_type"],
            "configuration": desired.get("configuration"),
            "credential_id": desired.get("management_credential_id"),
        }
    )
    context = "Failed to discover models and tools for integration '{0}'".format(name)
    try:
        result = module.request("POST", INTEGRATIONS + "/discover", data=body) or {}
    except OrchestratorAPIError as err:
        module.fail_api(err, context)
    if result.get("success") is False:
        module.fail_json(msg="{0}: {1}".format(context, result.get("error") or "unknown error"), discover_result=result)
    if params["models"] is not None:
        desired["discovered_models"] = _discovered_models(module, name, result.get("discovered_models") or [], params["models"])
    if params["tools"] is not None:
        desired["discovered_tools"] = _discovered_tools(module, name, result.get("discovered_tools") or [], params["tools"])


def _discovered_models(module, name, discovered, entries):
    selections = [
        module.build_desired({"model_id": m.get("id"), "name": m.get("name") or m.get("id"), "description": m.get("description")}) for m in discovered
    ]
    for entry in entries:
        match = _find(discovered, _model_key(entry), ("id", "name"))
        if match is None:
            _fail_missing(module, "Model", _model_key(entry), name)
        selections[discovered.index(match)].update(_flags(entry, MODEL_FLAGS))
    return selections


def _discovered_tools(module, name, discovered, entries):
    selections = [module.build_desired({"name": t.get("name"), "description": t.get("description"), "parameters": t.get("parameters")}) for t in discovered]
    for entry in entries:
        match = _find(discovered, entry["name"], ("name",))
        if match is None:
            _fail_missing(module, "Tool", entry["name"], name)
        selections[discovered.index(match)].update(_flags(entry, TOOL_FLAGS))
    return selections


def _refresh(module, integration, name):
    """Refresh models/tools from the provider; return (changed, result)."""
    try:
        result = module.request("POST", "{0}/{1}/refresh".format(INTEGRATIONS, integration["id"])) or {}
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to refresh integration '{0}'".format(name))
    return (result.get("updated_count") or 0) > 0, result


def _validate(module, integration, name):
    try:
        return module.request("POST", "{0}/{1}/validate".format(INTEGRATIONS, integration["id"])) or {}
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to validate integration '{0}'".format(name))


def _reconcile_projects(module, integration, name, values):
    """Make the project assignments of ``integration`` match ``values``; return (changed, project names)."""
    path = "{0}/{1}/projects".format(INTEGRATIONS, integration["id"])
    context = "Failed to update projects for integration '{0}'".format(name)
    current = module.get_all(path, context=context)
    current_names = dict((p.get("project_id"), p.get("project_name")) for p in current)
    target = {}
    order = []
    for value in values:
        project_id = module.resolve_id("project", value)
        if project_id in target:
            continue
        project_name = current_names.get(project_id)
        if project_name is None:
            project_name = value
            if is_uuid(value):
                obj = module.resolve_obj("project", value)
                if obj is None:
                    module.fail_json(msg="project '{0}' not found".format(value))
                project_name = obj.get("name")
        target[project_id] = project_name
        order.append(project_id)
    to_add = [pid for pid in order if pid not in current_names]
    to_remove = [p.get("project_id") for p in current if p.get("project_id") not in target]
    if not module.check_mode:
        try:
            for project_id in to_add:
                module.request("POST", "{0}/{1}".format(path, project_id))
            for project_id in to_remove:
                module.request("DELETE", "{0}/{1}".format(path, project_id), expect=(200, 204))
        except OrchestratorAPIError as err:
            module.fail_api(err, context)
    return bool(to_add or to_remove), sorted(n or "" for n in target.values())


def _reconcile_rows(module, integration, name, kind, entries):
    """PATCH only the differing flags of the listed models or tools; return (changed, rows)."""
    if kind == "models":
        label, flags, key_of, fields = "Model", MODEL_FLAGS, _model_key, ("model_id", "name")
    else:
        label, flags, key_of, fields = "Tool", TOOL_FLAGS, (lambda entry: entry["name"]), ("name", "namespaced_name")
    path = "{0}/{1}/{2}".format(INTEGRATIONS, integration["id"], kind)
    context = "Failed to update {0} for integration '{1}'".format(kind, name)
    rows = module.get_all(path, context=context)
    patches = []
    for entry in entries:
        row = _find(rows, key_of(entry), fields)
        if row is None:
            _fail_missing(module, label, key_of(entry), name)
        body = dict((flag, value) for flag, value in _flags(entry, flags).items() if row.get(flag) != value)
        if body:
            patches.append((row, body))
    for row, body in patches:
        if module.check_mode:
            row.update(body)
            continue
        try:
            updated = module.request("PATCH", "{0}/{1}".format(path, row["id"]), data=body)
        except OrchestratorAPIError as err:
            module.fail_api(err, context)
        row.update(updated if isinstance(updated, dict) else body)
    return bool(patches), rows


def _sub_resources(module, integration, name, params):
    """Run refresh, project/model/tool reconciliation and validation; return (changed, extra result keys)."""
    changed = False
    extra = {}
    if params["refresh"] and not module.check_mode:
        changed, extra["refresh_result"] = _refresh(module, integration, name)
    if params["projects"] is not None:
        projects_changed, extra["projects"] = _reconcile_projects(module, integration, name, params["projects"])
        changed = changed or projects_changed
    for kind in ("models", "tools"):
        if params[kind] is not None:
            rows_changed, extra[kind] = _reconcile_rows(module, integration, name, kind, params[kind])
            changed = changed or rows_changed
    if params["validate"] and not module.check_mode:
        extra["validation"] = _validate(module, integration, name)
    return changed, extra


def main():
    argument_spec = dict(
        name=dict(type="str", required=True),
        new_name=dict(type="str"),
        description=dict(type="str"),
        integration_type=dict(type="str", choices=["mcp_server", "llm_provider", "ansible_automation_platform"]),
        configuration=dict(type="dict"),
        management_credential=dict(type="str"),
        management_credential_project=dict(type="str"),
        enabled=dict(type="bool"),
        scope=dict(type="str", choices=["global", "project"]),
        labels=dict(type="dict"),
        projects=dict(type="list", elements="str"),
        models=dict(
            type="list",
            elements="dict",
            options=dict(
                model_id=dict(type="str"),
                name=dict(type="str"),
                enabled=dict(type="bool"),
                is_default=dict(type="bool"),
            ),
            required_one_of=[["name", "model_id"]],
        ),
        tools=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                enabled=dict(type="bool"),
            ),
        ),
        discover=dict(type="bool", default=True),
        refresh=dict(type="bool", default=False),
        validate=dict(type="bool", default=False),
        state=dict(type="str", default="present", choices=["present", "absent", "exists"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "integration"
    params = module.params
    state = params["state"]

    credential_id = _resolve_management_credential(module, params) if state != "absent" else None

    if state == "present":
        existing = module.find_existing(INTEGRATIONS, params["name"], params["new_name"], kind="integration")
    else:
        existing = module.resolve_obj("integration", params["name"])

    if state == "absent":
        changed = module.delete_if_needed(existing, INTEGRATIONS, item_label="integration")
        module.exit_result(changed, None)

    if state == "exists" and existing is not None:
        module.exit_result(False, existing)

    name = params["new_name"] if state == "present" and params["new_name"] else params["name"]
    if existing is None and not params["integration_type"]:
        module.fail_json(msg="integration_type is required to create integration '{0}'".format(name))

    configuration = None
    if params["configuration"] is not None:
        configuration = dict(params["configuration"])
        configuration["integration_type"] = params["integration_type"] or existing.get("integration_type")
    desired = module.build_desired(
        {
            "name": name,
            "description": params["description"],
            "integration_type": params["integration_type"],
            "configuration": configuration,
            "management_credential_id": credential_id,
            "enabled": params["enabled"],
            "scope": params["scope"],
            "labels": params["labels"],
        }
    )
    if existing is None and params["discover"] and not module.check_mode and (params["models"] is not None or params["tools"] is not None):
        _discover(module, name, desired, params)

    changed, obj = module.create_or_update(
        existing,
        desired,
        INTEGRATIONS,
        full_fields=("configuration",),
        immutable=("integration_type",),
        item_label="integration",
    )

    extra = {}
    if obj and obj.get("id"):
        sub_changed, extra = _sub_resources(module, obj, name, params)
        changed = changed or sub_changed
    module.exit_result(changed, obj, **extra)


if __name__ == "__main__":
    main()
