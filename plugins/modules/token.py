# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: token
short_description: Obtain an access token from the Automation Orchestrator
description:
  - Logs in with a username and password or with OAuth2 client credentials and returns the bearer access token.
  - Register the result and pass it as O(orchestrator_token) to later tasks, so a large run logs in only once.
  - The module does not change any state on the Orchestrator, so it also runs in check mode, but it always reports C(changed=true) like a login.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: The module only logs in and does not modify any state.
  diff_mode:
    support: none
    description: The module does not produce a diff.
seealso:
  - module: kenmoini.automation_orchestrator_config.api
"""

EXAMPLES = r"""
- name: Log in once and reuse the token
  kenmoini.automation_orchestrator_config.token:
    orchestrator_host: orchestrator.example.com
    orchestrator_username: admin
    orchestrator_password: "{{ admin_password }}"
  register: orchestrator_login
  no_log: true

- name: Use the token in a later task
  kenmoini.automation_orchestrator_config.api:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_login.access_token }}"
    endpoint: /version

- name: Log in with a service account
  kenmoini.automation_orchestrator_config.token:
    orchestrator_host: orchestrator.example.com
    orchestrator_client_id: "{{ client_id }}"
    orchestrator_client_secret: "{{ client_secret }}"
  register: orchestrator_login
  no_log: true
...
"""

RETURN = r"""
access_token:
  description: The bearer access token. Treat it as a secret and use C(no_log) on the task.
  returned: always
  type: str
  sample: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.example
token_type:
  description: The token type, always C(Bearer).
  returned: always
  type: str
  sample: Bearer
expires_in:
  description: Lifetime of the token in seconds, or V(null) when the server did not report one.
  returned: always
  type: int
  sample: 3600
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict()
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)

    params = module.params
    if not (params.get("orchestrator_username") or params.get("orchestrator_client_id")):
        module.fail_json(msg="token module needs orchestrator_username/orchestrator_password or orchestrator_client_id/orchestrator_client_secret")

    access_token = module.authenticate()
    module.exit_json(changed=True, access_token=access_token, token_type="Bearer", expires_in=module._token_expires_in)


if __name__ == "__main__":
    main()
