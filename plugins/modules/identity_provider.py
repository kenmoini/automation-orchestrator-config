# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: identity_provider
short_description: Manage OIDC identity providers in the Automation Orchestrator
description:
  - Creates, updates, renames and deletes OpenID Connect identity providers used to sign in to the Automation Orchestrator.
  - Identity providers are looked up by O(name). Only the options you set are compared and changed.
  - Can test the provider configuration with the Orchestrator before it is created or updated.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: Changes are reported but not made. O(test) is skipped.
  diff_mode:
    support: full
    description: The client secret is never shown in the diff.
options:
  name:
    description: Name of the identity provider, used to look it up.
    type: str
    required: true
  new_name:
    description:
      - Rename the identity provider called O(name) to this name. Only used when O(state=present).
      - The module is idempotent. When no identity provider is called O(name) but one is called O(new_name),
        that identity provider is used as is, so a rerun makes no change.
      - When neither identity provider exists, it is created with O(new_name).
    type: str
  description:
    description: Description of the identity provider.
    type: str
  enabled:
    description: Whether the identity provider is enabled.
    type: bool
  configuration:
    description:
      - OIDC configuration of the identity provider, as documented by the API (V(issuer_url), V(client_id), V(client_secret), V(redirect_uri),
        V(scopes), V(claim_mapping), V(group_mapping_entries) and so on).
      - Required to create an identity provider. V(provider_type) defaults to V(oidc).
      - Only the keys you set are compared. When any of them differs, the whole configuration is sent, completed with the existing values.
      - Each entry of V(group_mapping_entries) may give V(mapped_group), the name or ID of an Orchestrator group, instead of V(mapped_group_id).
        It is resolved to V(mapped_group_id) before the comparison.
      - When both are given, V(mapped_group) takes precedence over V(mapped_group_id).
      - Write list entries exactly as the API returns them, because entries are compared as a whole (in any order).
      - V(client_secret) is sensitive. It is sent only when set and O(update_secrets=true), is never returned and is hidden from the diff.
        Because it is a key of a dict, Ansible cannot hide it from the task arguments, so pass it from a vaulted variable.
    type: dict
  update_secrets:
    description:
      - When V(false), V(client_secret) in O(configuration) is never written to the identity provider.
      - With O(update_secrets=false) a supplied C(client_secret) is still sent to the test endpoint when O(test=true); it is never written to the provider.
      - When V(true), a supplied V(client_secret) is always sent and reported as a change, because the server never returns it.
    type: bool
    default: true
  test:
    description:
      - Test the OIDC configuration with the Orchestrator before the identity provider is created or updated, and also when nothing else changes.
      - The result is returned in RV(test_result) and is never reported as a change.
      - The task fails and the identity provider is not created or updated when the test is not successful.
      - A supplied C(client_secret) is sent to the test endpoint even with O(update_secrets=false); it is never written to the provider.
      - Skipped in check mode.
    type: bool
    default: false
  state:
    description:
      - V(present) creates the identity provider or updates it to match the options.
      - V(exists) creates the identity provider when it is missing and never modifies an existing one.
      - V(absent) deletes the identity provider. Deletion is permanent.
    type: str
    choices: [present, absent, exists]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.identity_provider_info
  - module: kenmoini.automation_orchestrator_config.group
"""

EXAMPLES = r"""
- name: Create an OIDC identity provider that maps a provider group to an Orchestrator group
  kenmoini.automation_orchestrator_config.identity_provider:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: corporate-sso
    description: Corporate single sign-on
    enabled: true
    configuration:
      issuer_url: https://sso.example.com/realms/corp
      client_id: automation-orchestrator
      client_secret: "{{ oidc_client_secret }}"
      redirect_uri: https://orchestrator.example.com/auth/callback
      scopes: [openid, email, profile]
      group_jmespath_expression: groups
      group_mapping_entries:
        - idp_group_value: platform-ops
          mapped_group: operators
    test: true
  register: sso

- name: Rotate nothing, only change the scopes
  kenmoini.automation_orchestrator_config.identity_provider:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: corporate-sso
    configuration:
      scopes: [openid, email]
    update_secrets: false

- name: Delete an identity provider
  kenmoini.automation_orchestrator_config.identity_provider:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: corporate-sso
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the identity provider, or V(null) when it was deleted or does not exist.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
identity_provider:
  description: The identity provider as returned by the API, or V(null) when it was deleted or does not exist. The client secret is never returned.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the identity provider.
      type: str
    name:
      description: Name of the identity provider.
      type: str
    description:
      description: Description of the identity provider.
      type: str
    enabled:
      description: Whether the identity provider is enabled.
      type: bool
    configuration:
      description: OIDC configuration of the identity provider, without the client secret.
      type: dict
    labels:
      description: Labels of the identity provider.
      type: dict
    created_at:
      description: Creation timestamp.
      type: str
    updated_at:
      description: Timestamp of the last update.
      type: str
  sample:
    id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    name: corporate-sso
    enabled: true
    configuration:
      provider_type: oidc
      issuer_url: https://sso.example.com/realms/corp
      client_id: automation-orchestrator
      redirect_uri: https://orchestrator.example.com/auth/callback
test_result:
  description: Result of the configuration test.
  returned: when O(test=true) and not in check mode
  type: dict
  contains:
    success:
      description: Whether the test succeeded.
      type: bool
    message:
      description: Message of the test.
      type: str
    metadata:
      description: Metadata discovered from the identity provider.
      type: dict
    claims_supported:
      description: Claims the identity provider supports.
      type: list
      elements: str
    claim_aliases:
      description: Suggested claim aliases.
      type: dict
    end_session_endpoint_supported:
      description: Whether the identity provider supports ending the session.
      type: bool
  sample:
    success: true
    message: Discovery succeeded
"""

import copy

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import (
    OrchestratorAPIError,
    OrchestratorModule,
    strip_secrets,
)

IDENTITY_PROVIDERS = "/identity_providers"


def _group_id(module, group):
    if group == "":
        module.fail_json(msg="group '' not found")
    return module.resolve_id("group", group)


def _resolve_configuration(module, configuration):
    """Return a deep copy of ``configuration`` with ``provider_type`` set and ``mapped_group`` resolved to ``mapped_group_id``."""
    resolved = copy.deepcopy(configuration)
    resolved.setdefault("provider_type", "oidc")
    entries = resolved.get("group_mapping_entries")
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and "mapped_group" in entry:
                group = entry.pop("mapped_group")
                if group is not None:
                    entry["mapped_group_id"] = _group_id(module, group)
    return resolved


def _run_test(module, name, desired, existing):
    """Test the OIDC configuration; fail when it is not successful; return the test result."""
    configuration = copy.deepcopy((existing or {}).get("configuration") or {})
    configuration.update(copy.deepcopy(desired.get("configuration") or {}))
    description = desired.get("description", (existing or {}).get("description"))
    body = module.build_desired({"name": name, "description": description, "configuration": configuration})
    try:
        result = module.request("POST", IDENTITY_PROVIDERS + "/test", data=body) or {}
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to test identity provider '{0}'".format(name))
    if not result.get("success"):
        module.fail_json(msg="Identity provider test failed: {0}".format(result.get("message") or "unknown error"), test_result=strip_secrets(result))
    return result


def main():
    argument_spec = dict(
        name=dict(type="str", required=True),
        new_name=dict(type="str"),
        description=dict(type="str"),
        enabled=dict(type="bool"),
        configuration=dict(type="dict"),
        update_secrets=dict(type="bool", default=True),
        test=dict(type="bool", default=False),
        state=dict(type="str", default="present", choices=["present", "absent", "exists"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "identity_provider"
    params = module.params
    state = params["state"]

    if state == "present":
        existing = module.find_existing(IDENTITY_PROVIDERS, params["name"], params["new_name"], kind="identity_provider")
    else:
        existing = module.resolve_obj("identity_provider", params["name"])

    if state == "absent":
        changed = module.delete_if_needed(existing, IDENTITY_PROVIDERS, item_label="identity provider")
        module.exit_result(changed, None)

    if state == "exists" and existing is not None:
        module.exit_result(False, existing)

    name = params["new_name"] if state == "present" and params["new_name"] else params["name"]
    if existing is None and params["configuration"] is None:
        module.fail_json(msg="configuration is required to create identity provider '{0}'".format(name))

    configuration = _resolve_configuration(module, params["configuration"]) if params["configuration"] is not None else None
    desired = module.build_desired(
        {
            "name": name,
            "description": params["description"],
            "enabled": params["enabled"],
            "configuration": configuration,
        }
    )
    create_body = dict((k, v) for k, v in desired.items() if k != "enabled") if existing is None else desired

    extra = {}
    if params["test"] and not module.check_mode:
        extra["test_result"] = _run_test(module, name, desired, existing)

    changed, obj = module.create_or_update(
        existing,
        create_body,
        IDENTITY_PROVIDERS,
        full_fields=("configuration",),
        secret_fields=("client_secret",),
        update_secrets=params["update_secrets"],
        item_label="identity provider",
    )
    if existing is None and params["enabled"] is not None and obj is not None and obj.get("enabled") != params["enabled"]:
        if module.check_mode:
            obj = dict(obj, enabled=params["enabled"])
        else:
            try:
                obj = module.request("PATCH", "{0}/{1}".format(IDENTITY_PROVIDERS, obj["id"]), data={"enabled": params["enabled"]}) or dict(
                    obj, enabled=params["enabled"]
                )
            except OrchestratorAPIError as err:
                module.fail_api(err, "Failed to update identity provider '{0}'".format(name))
    module.exit_result(changed, obj, **extra)


if __name__ == "__main__":
    main()
