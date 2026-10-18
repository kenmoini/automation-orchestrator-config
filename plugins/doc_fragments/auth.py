# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options:
  orchestrator_host:
    description:
      - Hostname or URL of the Automation Orchestrator, for example C(orchestrator.example.com) or C(https://orchestrator.example.com).
      - When no scheme is given, C(https://) is assumed.
      - If not set, the value of the E(ORCHESTRATOR_HOST) environment variable is used.
    type: str
    required: true
  orchestrator_username:
    description:
      - Username used to log in with C(/auth/login).
      - Requires O(orchestrator_password). Used only when neither O(orchestrator_token) nor O(orchestrator_client_id) is set.
      - If not set, the value of the E(ORCHESTRATOR_USERNAME) environment variable is used.
    type: str
  orchestrator_password:
    description:
      - Password for O(orchestrator_username).
      - If not set, the value of the E(ORCHESTRATOR_PASSWORD) environment variable is used.
    type: str
  orchestrator_token:
    description:
      - A bearer access token, used as is without any login request.
      - Takes precedence over O(orchestrator_client_id) and O(orchestrator_username) when several are set.
      - If not set, the value of the E(ORCHESTRATOR_TOKEN) environment variable is used.
    type: str
  orchestrator_client_id:
    description:
      - OAuth2 client ID of a service account, used with the C(client_credentials) grant.
      - Requires O(orchestrator_client_secret). Takes precedence over O(orchestrator_username); O(orchestrator_token) takes precedence over it.
      - If not set, the value of the E(ORCHESTRATOR_CLIENT_ID) environment variable is used.
    type: str
  orchestrator_client_secret:
    description:
      - OAuth2 client secret of the service account named by O(orchestrator_client_id).
      - If not set, the value of the E(ORCHESTRATOR_CLIENT_SECRET) environment variable is used.
    type: str
  validate_certs:
    description:
      - Whether to validate the TLS certificate of the Automation Orchestrator.
      - If not set, the value of the E(ORCHESTRATOR_VERIFY_SSL) environment variable is used.
    type: bool
    default: true
    aliases: [orchestrator_validate_certs]
  request_timeout:
    description:
      - Timeout in seconds for each HTTP request.
      - If not set, the value of the E(ORCHESTRATOR_REQUEST_TIMEOUT) environment variable is used.
    type: float
    default: 10
notes:
  - Authentication methods are not mutually exclusive. When several are set (as options or E(ORCHESTRATOR_*) environment variables),
    the module uses O(orchestrator_token) first, then O(orchestrator_client_id) with O(orchestrator_client_secret),
    then O(orchestrator_username) with O(orchestrator_password).
  - Set the connection options once for a whole play with
    C(module_defaults) and C(group/kenmoini.automation_orchestrator_config.orchestrator).
  - Prefer O(orchestrator_token), obtained once with the M(kenmoini.automation_orchestrator_config.token) module,
    for large runs so that each task does not log in again.
"""
