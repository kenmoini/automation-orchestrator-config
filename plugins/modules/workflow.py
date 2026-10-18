# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: workflow
short_description: Manage workflows in the Automation Orchestrator
description:
  - Creates, updates, renames, publishes, unpublishes and deletes workflows of a project.
  - Workflows are versioned graph documents. Sending a workflow definition that differs from the current version
    makes the server create a new version. An unchanged definition is not sent, so reruns create no versions.
  - Workflows are looked up by O(name) within O(project). Only the options you set are compared and changed.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: Changes, including publishing and unpublishing, are computed and reported but not made.
  diff_mode:
    support: partial
    description: Publishing and unpublishing are not shown in the diff.
options:
  name:
    description:
      - Name of the workflow, used to look it up within O(project).
      - An ID is also accepted. The workflow then keeps its current name unless O(new_name) is set.
      - The workflow name is also written to the V(name) key of the workflow definition.
    type: str
    required: true
  new_name:
    description:
      - Rename the workflow called O(name) to this name. Only used when O(state=present).
      - The module is idempotent. When no workflow is called O(name) but one is called O(new_name), that workflow is used as is, so a rerun makes no change.
      - When neither workflow exists, the workflow is created with O(new_name).
    type: str
  description:
    description: Description of the workflow.
    type: str
  labels:
    description: Labels of the workflow as key/value pairs.
    type: dict
  project:
    description:
      - Name or ID of the project that owns the workflow.
      - It cannot be changed on an existing workflow.
    type: str
    required: true
  workflow_definition:
    description:
      - The workflow definition, with V(triggers), V(nodes) and V(edges).
      - Its V(name) is always set to the workflow name, and V(schema_version) defaults to V(2.0.0).
      - Required to create a workflow. On an existing workflow it is compared with the definition of the current version,
        with key order ignored but list order kept, and sent only when it differs.
      - Mutually exclusive with O(definition_file).
    type: dict
  definition_file:
    description:
      - Path to a JSON or YAML file holding the workflow definition, used like O(workflow_definition).
      - The file is read on the host that runs the module.
      - Mutually exclusive with O(workflow_definition).
    type: path
  is_import:
    description: Mark the workflow as imported when it is created. Ignored for existing workflows.
    type: bool
    default: false
  change_description:
    description: Description of the change, recorded on the new version and on publishing.
    type: str
  publish:
    description:
      - Publish the current version after any update.
      - Nothing is done when the current version is already the published one.
      - Mutually exclusive with O(unpublish).
    type: bool
    default: false
  unpublish:
    description:
      - Unpublish the workflow when it has a published version.
      - Mutually exclusive with O(publish).
    type: bool
    default: false
  state:
    description:
      - V(present) creates the workflow or updates it to match the options.
      - V(exists) creates the workflow when it is missing and never modifies an existing one.
      - V(absent) deletes the workflow. Deletion is permanent and also removes all its versions and executions.
    type: str
    choices: [present, absent, exists]
    default: present
notes:
  - O(definition_file) is parsed as JSON first and as YAML when that fails. YAML needs PyYAML on the host that runs the module.
seealso:
  - module: kenmoini.automation_orchestrator_config.workflow_info
"""

EXAMPLES = r"""
- name: Create or update a workflow from a file and publish it
  kenmoini.automation_orchestrator_config.workflow:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: deploy-app
    project: platform
    description: Deploys the application
    definition_file: files/workflows/deploy-app.yml
    change_description: Add approval step
    publish: true

- name: Manage a workflow with an inline definition
  kenmoini.automation_orchestrator_config.workflow:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: hello
    project: platform
    workflow_definition:
      triggers:
        - id: manual
          type: manual
      nodes: []
      edges: []

- name: Unpublish a workflow
  kenmoini.automation_orchestrator_config.workflow:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: deploy-app
    project: platform
    unpublish: true

- name: Delete a workflow with all its versions and executions
  kenmoini.automation_orchestrator_config.workflow:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: deploy-app
    project: platform
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the workflow, or V(null) when it was deleted, does not exist or would be created in check mode.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
workflow:
  description: The workflow metadata as returned by the API, without the version details, or V(null) when it was deleted or does not exist.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the workflow.
      type: str
    name:
      description: Name of the workflow.
      type: str
    description:
      description: Description of the workflow.
      type: str
    labels:
      description: Labels of the workflow.
      type: dict
    project_id:
      description: ID of the project.
      type: str
    current_version:
      description: Number of the current version.
      type: int
    published_version_number:
      description: Number of the published version, or V(null) when the workflow is not published.
      type: int
    is_enabled:
      description: Whether the workflow is enabled.
      type: bool
    has_validation_issues:
      description: Whether the current version has validation issues.
      type: bool
  sample:
    id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    name: deploy-app
    project_id: 9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d
    current_version: 3
    published_version_number: 3
    is_enabled: true
version:
  description: Number of the current version of the workflow, or V(null) when it is unknown, deleted or does not exist.
  returned: always
  type: int
  sample: 3
published_version:
  description: Number of the published version, or V(null) when the workflow is not published.
  returned: always
  type: int
  sample: 3
definition_changed:
  description: Whether the workflow definition was created or changed, which creates a new version.
  returned: always
  type: bool
  sample: true
"""

import copy
import io
import json

try:
    import yaml

    HAS_YAML = True
except ImportError:  # pragma: no cover - PyYAML ships with ansible-core
    HAS_YAML = False

from ansible.module_utils.common.text.converters import to_native
from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import (
    OrchestratorAPIError,
    OrchestratorModule,
    is_uuid,
)

WORKFLOWS = "/workflows"
SCHEMA_VERSION = "2.0.0"


def _load_definition_file(module, path):
    """Return the mapping in the JSON or YAML file ``path``, failing with a clear message otherwise."""
    prefix = "definition_file '{0}' could not be read/parsed: ".format(path)
    try:
        with io.open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except (IOError, OSError) as exc:
        module.fail_json(msg=prefix + to_native(exc))
    try:
        data = json.loads(text)
    except ValueError as json_err:
        if not HAS_YAML:
            module.fail_json(msg=prefix + "not valid JSON ({0}) and PyYAML is not installed to parse YAML".format(to_native(json_err)))
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            module.fail_json(msg=prefix + to_native(exc))
    if not isinstance(data, dict):
        module.fail_json(msg=prefix + "the document is not a mapping")
    return data


def _prepare_definition(definition, name):
    """Return a copy of ``definition`` named ``name`` with a default ``schema_version``."""
    result = copy.deepcopy(definition)
    result["name"] = name
    result.setdefault("schema_version", SCHEMA_VERSION)
    return result


def _canonical(definition):
    """Return ``definition`` as canonical JSON: keys sorted, list order kept."""
    return json.dumps(definition, sort_keys=True)


def _definition_changed(new, current):
    return current is None or _canonical(new) != _canonical(current)


def _metadata(obj):
    """Return the workflow fields of an API response, without the nested version details."""
    if obj is None:
        return None
    return dict((k, v) for k, v in obj.items() if k not in ("version", "warning"))


def _get_full(module, workflow_id, name):
    """Return ``GET /workflows/{id}`` (the workflow with its current version)."""
    try:
        return module.request("GET", "{0}/{1}".format(WORKFLOWS, workflow_id))
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to read workflow '{0}'".format(name))


def _lookup(module, value, project_id):
    """Return ``(workflow, full)`` for a name or ID; ``full`` is the workflow with its version when fetched by ID."""
    if not is_uuid(value):
        return module.resolve_obj("workflow", value, project_id=project_id), None
    try:
        full = module.request("GET", "{0}/{1}".format(WORKFLOWS, value))
    except OrchestratorAPIError as err:
        if err.status == 404:
            return None, None
        module.fail_api(err, "Failed to read workflow '{0}'".format(value))
    return full, full


def _create(module, name, params, project_id, definition):
    body = module.build_desired(
        {
            "name": name,
            "description": params["description"],
            "labels": params["labels"],
            "workflow_definition": definition,
            "project_id": project_id,
            "is_import": params["is_import"],
        }
    )
    module._diff = {"before": {}, "after": copy.deepcopy(body)}
    if module.check_mode:
        return dict((k, v) for k, v in body.items() if k not in ("workflow_definition", "is_import"))
    try:
        obj = module.request("POST", WORKFLOWS, data=body)
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to create workflow '{0}'".format(name))
    return obj if obj is not None else body


def _update(module, existing, name, params, definition, full):
    """PATCH metadata and definition together; return ``(changed, obj, definition_changed)``."""
    wanted = module.build_desired({"name": name, "description": params["description"], "labels": params["labels"]})
    metadata = module.compute_patch(existing, wanted)
    definition_changed = False
    current_definition = None
    if definition is not None:
        if full is None:
            full = _get_full(module, existing["id"], name)
        current_definition = ((full or {}).get("version") or {}).get("workflow_definition")
        definition_changed = _definition_changed(definition, current_definition)

    patch = copy.deepcopy(metadata)
    before = dict((k, existing.get(k)) for k in metadata)
    after = copy.deepcopy(metadata)
    if definition_changed:
        patch["workflow_definition"] = definition
        if params["change_description"] is not None:
            patch["change_description"] = params["change_description"]
        patch["expected_version"] = existing.get("current_version")
        before["workflow_definition"] = copy.deepcopy(current_definition)
        after["workflow_definition"] = copy.deepcopy(definition)
    module._diff = {"before": before, "after": after}

    if not patch:
        return False, existing, False
    merged = copy.deepcopy(existing)
    merged.update(metadata)
    if module.check_mode:
        return True, merged, definition_changed
    try:
        obj = module.request("PATCH", "{0}/{1}".format(WORKFLOWS, existing["id"]), data=patch)
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to update workflow '{0}'".format(name))
    if not isinstance(obj, dict) or obj.get("current_version") is None:
        obj = _get_full(module, existing["id"], name)
    return True, obj, definition_changed


def _publish(module, obj, name, definition_changed, change_description):
    current = obj.get("current_version")
    if not definition_changed and obj.get("published_version_number") == current:
        return False, obj
    if module.check_mode or not obj.get("id"):
        preview = dict(obj)
        preview["published_version_number"] = current
        return True, preview
    path = "{0}/{1}/versions/{2}/publish".format(WORKFLOWS, obj["id"], current)
    try:
        result = module.request("POST", path, data=module.build_desired({"change_description": change_description}))
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to publish workflow '{0}'".format(name))
    return True, result if isinstance(result, dict) else obj


def _unpublish(module, obj, name):
    if obj.get("published_version_number") is None:
        return False, obj
    if module.check_mode:
        preview = dict(obj)
        preview["published_version_number"] = None
        return True, preview
    try:
        result = module.request("POST", "{0}/{1}/unpublish".format(WORKFLOWS, obj["id"]))
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to unpublish workflow '{0}'".format(name))
    return True, result if isinstance(result, dict) else obj


def _exit(module, changed, obj, definition_changed):
    obj = obj or {}
    module.exit_result(
        changed,
        _metadata(obj) if obj else None,
        version=obj.get("current_version"),
        published_version=obj.get("published_version_number"),
        definition_changed=definition_changed,
    )


def main():
    argument_spec = dict(
        name=dict(type="str", required=True),
        new_name=dict(type="str"),
        description=dict(type="str"),
        labels=dict(type="dict"),
        project=dict(type="str", required=True),
        workflow_definition=dict(type="dict"),
        definition_file=dict(type="path"),
        is_import=dict(type="bool", default=False),
        change_description=dict(type="str"),
        publish=dict(type="bool", default=False),
        unpublish=dict(type="bool", default=False),
        state=dict(type="str", default="present", choices=["present", "absent", "exists"]),
    )
    module = OrchestratorModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[["workflow_definition", "definition_file"], ["publish", "unpublish"]],
    )
    module.result_key = "workflow"
    params = module.params
    state = params["state"]

    definition = params["workflow_definition"]
    if state != "absent" and params["definition_file"]:
        definition = _load_definition_file(module, params["definition_file"])

    project_id = module.resolve_id("project", params["project"])
    existing, full = _lookup(module, params["name"], project_id)
    if existing is None and state == "present" and params["new_name"]:
        existing, full = _lookup(module, params["new_name"], project_id)
    if existing is not None and existing.get("project_id") != project_id:
        module.fail_json(msg="project_id cannot be changed on an existing workflow")

    if state == "absent":
        changed = module.delete_if_needed(existing, WORKFLOWS, item_label="workflow")
        _exit(module, changed, None, False)

    if state == "exists" and existing is not None:
        _exit(module, False, existing, False)

    if state == "present" and params["new_name"]:
        name = params["new_name"]
    elif existing is not None and is_uuid(params["name"]):
        name = existing.get("name")  # addressed by ID: keep the current name
    else:
        name = params["name"]
    if definition is not None:
        definition = _prepare_definition(definition, name)

    if existing is None:
        if definition is None:
            module.fail_json(msg="workflow_definition or definition_file is required to create workflow '{0}'".format(name))
        obj = _create(module, name, params, project_id, definition)
        changed, definition_changed = True, True
    else:
        changed, obj, definition_changed = _update(module, existing, name, params, definition, full)

    if params["publish"]:
        published, obj = _publish(module, obj, name, definition_changed, params["change_description"])
        changed = changed or published
    elif params["unpublish"]:
        unpublished, obj = _unpublish(module, obj, name)
        changed = changed or unpublished
    _exit(module, changed, obj, definition_changed)


if __name__ == "__main__":
    main()
