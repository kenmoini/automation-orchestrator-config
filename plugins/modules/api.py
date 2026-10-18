# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: api
short_description: Call any Automation Orchestrator API endpoint
description:
  - Sends an authenticated request to the Automation Orchestrator REST API and returns the HTTP status and the parsed JSON body.
  - Use it for endpoints that have no dedicated module.
  - Any method other than C(GET) is reported as changed. In check mode such requests are skipped.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: partial
    details: GET requests are sent, other methods are skipped and reported as changed.
  diff_mode:
    support: none
options:
  endpoint:
    description:
      - API path to call, for example C(/projects) or C(/api/v1/projects).
      - The C(/api/v1) prefix is added when missing.
    type: str
    required: true
  method:
    description: HTTP method to use.
    type: str
    choices: [GET, POST, PATCH, PUT, DELETE]
    default: GET
  data:
    description: JSON request body, sent as is.
    type: raw
  query_params:
    description: Query string parameters. Parameters set to V(null) are dropped.
    type: dict
  expect:
    description:
      - HTTP status codes to accept as success.
      - Defaults to C(200), C(201), C(202) and C(204). Any other status fails the task.
    type: list
    elements: int
  return_all_pages:
    description:
      - Follow the cursor pagination of a list endpoint and return all pages merged into one C(resources) list.
      - Only meaningful for C(GET) requests on list endpoints.
    type: bool
    default: false
seealso:
  - module: kenmoini.automation_orchestrator_config.token
"""

EXAMPLES = r"""
- name: Read the server version
  kenmoini.automation_orchestrator_config.api:
    endpoint: /version
  register: version

- name: Filter a list with query parameters
  kenmoini.automation_orchestrator_config.api:
    endpoint: /projects
    query_params:
      name: demo

- name: Fetch every user across all pages
  kenmoini.automation_orchestrator_config.api:
    endpoint: /users
    return_all_pages: true
  register: users

- name: Create a project
  kenmoini.automation_orchestrator_config.api:
    endpoint: /projects
    method: POST
    data:
      name: demo
...
"""

RETURN = r"""
status:
  description:
    - HTTP status code of the response.
    - V(null) when the request was skipped in check mode, and for C(return_all_pages) it is the status of the last page.
  returned: always
  type: int
  sample: 200
json:
  description:
    - Parsed response body, or V(null) when the response had no body or the request was skipped in check mode.
    - With O(return_all_pages) it is a mapping with a single C(resources) list holding every item.
  returned: always
  type: raw
  sample: {"id": "7b0b5a1e-3c1f-4d3e-9d54-2f6a9c1d0e11", "name": "demo"}
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import (
    OrchestratorAPIError,
    OrchestratorModule,
)


def main():
    argument_spec = dict(
        endpoint=dict(type="str", required=True),
        method=dict(type="str", default="GET", choices=["GET", "POST", "PATCH", "PUT", "DELETE"]),
        data=dict(type="raw"),
        query_params=dict(type="dict"),
        expect=dict(type="list", elements="int"),
        return_all_pages=dict(type="bool", default=False),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "json"

    params = module.params
    method = params["method"]
    changed = method != "GET"

    if module.check_mode and changed:
        module.exit_json(changed=True, status=None, json=None)

    expect = tuple(params["expect"]) if params["expect"] else None
    try:
        if params["return_all_pages"] and method == "GET":
            body = {"resources": module.get_all(params["endpoint"], query=params["query_params"])}
        else:
            body = module.request(method, params["endpoint"], query=params["query_params"], data=params["data"], expect=expect)
    except OrchestratorAPIError as err:
        module.fail_api(err, "API request failed")

    module.exit_json(changed=changed, status=module.last_status, json=body)


if __name__ == "__main__":
    main()
