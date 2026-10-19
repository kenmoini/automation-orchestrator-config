# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: workflow_info
short_description: Gather information about workflows in the Automation Orchestrator
description:
  - Lists the workflows of a project or returns one workflow by ID.
  - Optionally adds the workflow definition of the current or a given version, and the list of versions.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: The module only reads data.
  diff_mode:
    support: none
    description: The module does not produce a diff.
options:
  project:
    description:
      - Name or ID of the project whose workflows are listed.
      - Required unless O(id) is given. With O(id), only a workflow of this project is returned.
    type: str
  name:
    description:
      - Return only the workflow with exactly this name.
      - The API has no name filter, so the match is done after listing.
    type: str
  id:
    description: Return only the workflow with this ID. Returns an empty list when it does not exist.
    type: str
  include_definition:
    description: Add the definition of the current version of each workflow as V(workflow_definition).
    type: bool
    default: false
  version:
    description:
      - Add the definition of this version number of each workflow as V(workflow_definition), instead of the current one.
      - Fails when a returned workflow has no such version.
    type: int
  include_versions:
    description: Add the versions of each workflow as V(versions).
    type: bool
    default: false
seealso:
  - module: kenmoini.automation_orchestrator_config.workflow
"""

EXAMPLES = r"""
- name: List the workflows of a project
  kenmoini.automation_orchestrator_config.workflow_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    project: platform
  register: workflows

- name: Export the current definition of one workflow
  kenmoini.automation_orchestrator_config.workflow_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    project: platform
    name: deploy-app
    include_definition: true
  register: deploy_app

- name: Get version 2 of a workflow by ID with its version history
  kenmoini.automation_orchestrator_config.workflow_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    version: 2
    include_versions: true
...
"""

RETURN = r"""
resources:
  description:
    - The matching workflows. At most one item when O(name) or O(id) is given.
    - V(workflow_definition) is present when O(include_definition) or O(version) is set, V(versions) when O(include_versions=true).
  returned: always
  type: list
  elements: dict
  sample:
    - id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      name: deploy-app
      project_id: 9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d
      current_version: 3
      published_version_number: 2
      workflow_definition:
        schema_version: "2.0.0"
        name: deploy-app
        triggers: []
        nodes: []
        edges: []
      versions:
        - version: 3
          status: draft
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import (
    OrchestratorAPIError,
    OrchestratorModule,
)

WORKFLOWS = "/workflows"


def _request(module, path, context):
    try:
        return module.request("GET", path)
    except OrchestratorAPIError as err:
        module.fail_api(err, context)


def _by_id(module, workflow_id):
    """Return ``(workflow, full)`` for ``workflow_id``, or ``(None, None)`` when it does not exist."""
    try:
        full = module.request("GET", "{0}/{1}".format(WORKFLOWS, workflow_id))
    except OrchestratorAPIError as err:
        if err.status == 404:
            return None, None
        module.fail_api(err, "Failed to read workflow '{0}'".format(workflow_id))
    workflow = dict((k, v) for k, v in full.items() if k not in ("version", "warning"))
    return workflow, full


def _enrich(module, workflow, full, params):
    """Attach the requested definition and versions to ``workflow``."""
    path = "{0}/{1}".format(WORKFLOWS, workflow["id"])
    name = workflow.get("name") or workflow["id"]
    if params["version"] is not None:
        version = _request(
            module, "{0}/versions/{1}".format(path, params["version"]), "Failed to read version {0} of workflow '{1}'".format(params["version"], name)
        )
        workflow["workflow_definition"] = (version or {}).get("workflow_definition")
    elif params["include_definition"]:
        if full is None:
            full = _request(module, path, "Failed to read workflow '{0}'".format(name))
        workflow["workflow_definition"] = ((full or {}).get("version") or {}).get("workflow_definition")
    if params["include_versions"]:
        workflow["versions"] = module.get_all(path + "/versions", context="Failed to list versions of workflow '{0}'".format(name))
    return workflow


def main():
    argument_spec = dict(
        project=dict(type="str"),
        name=dict(type="str"),
        id=dict(type="str"),
        include_definition=dict(type="bool", default=False),
        version=dict(type="int"),
        include_versions=dict(type="bool", default=False),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True, required_one_of=[["project", "id"]])
    params = module.params

    project_id = module.resolve_id("project", params["project"]) if params["project"] else None
    full_by_id = {}
    if params["id"]:
        workflow, full = _by_id(module, params["id"])
        resources = [workflow] if workflow is not None else []
        if full is not None:
            full_by_id[workflow["id"]] = full
        if project_id is not None:
            resources = [r for r in resources if r.get("project_id") == project_id]
    else:
        resources = module.get_all("/projects/{0}/workflows".format(project_id), context="Failed to list workflows")
    if params["name"] is not None:
        resources = [r for r in resources if r.get("name") == params["name"]]

    module.exit_info([_enrich(module, r, full_by_id.get(r.get("id")), params) for r in resources])


if __name__ == "__main__":
    main()
