# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: user
short_description: Manage local users in the Automation Orchestrator
description:
  - Creates, updates, renames and deletes users and manages their group memberships.
  - Users are looked up by O(username). Only the options you set are compared and changed.
  - Federated users are created by their identity provider. Their password is never sent.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: Changes are computed and reported but not made.
  diff_mode:
    support: partial
    description: Group membership changes are not shown in the diff.
options:
  username:
    description:
      - Username of the user, used to look it up.
    type: str
    required: true
  new_username:
    description:
      - Rename the user called O(username) to this username. Only used when O(state=present).
      - The module is idempotent. When no user is called O(username) but one is called O(new_username), that user is used as is, so a rerun makes no change.
      - When neither user exists, the user is created with O(new_username).
    type: str
  password:
    description:
      - Password of the user. It must be at least 14 characters long.
      - Required to create a local user. For an existing user it is only sent when O(update_password=always).
      - Never returned in clear text.
    type: str
  update_password:
    description:
      - V(on_create) sends O(password) only when the user is created.
      - V(always) also sets O(password) on an existing local user, which is always reported as a change.
    type: str
    choices: [on_create, always]
    default: on_create
  email:
    description: Email address of the user.
    type: str
  first_name:
    description: First name of the user.
    type: str
  last_name:
    description: Last name of the user.
    type: str
  is_enabled:
    description: Whether the user can log in.
    type: bool
  groups:
    description:
      - Names or IDs of the groups the user belongs to.
      - When set, the memberships of the user are made to match this list. Memberships granted by an identity provider are always kept,
        as is the implicit built-in C(authenticated) group that the server adds to every user.
      - An empty list removes all manual memberships. When the user is created, an empty list also skips the default C(users) group.
      - When not set, memberships are left untouched, and a new user joins the default C(users) group.
    type: list
    elements: str
  state:
    description:
      - V(present) creates the user or updates it to match the options.
      - V(exists) creates the user when it is missing and never modifies an existing one.
      - V(absent) deletes the user. Deletion is permanent. Built-in users cannot be deleted.
    type: str
    choices: [present, absent, exists]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.user_info
  - module: kenmoini.automation_orchestrator_config.group
"""

EXAMPLES = r"""
- name: Create a user in two groups
  kenmoini.automation_orchestrator_config.user:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    username: alice
    password: "{{ alice_password }}"
    email: alice@example.com
    first_name: Alice
    groups:
      - users
      - operators

- name: Reset a password
  kenmoini.automation_orchestrator_config.user:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    username: alice
    password: "{{ new_password }}"
    update_password: always

- name: Disable a user
  kenmoini.automation_orchestrator_config.user:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    username: alice
    is_enabled: false

- name: Delete a user
  kenmoini.automation_orchestrator_config.user:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    username: alice
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the user, or V(null) when it was deleted or does not exist.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
user:
  description: The user as returned by the API, or V(null) when it was deleted or does not exist. The password is never returned.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the user.
      type: str
    username:
      description: Username of the user.
      type: str
    email:
      description: Email address of the user.
      type: str
    first_name:
      description: First name of the user.
      type: str
    last_name:
      description: Last name of the user.
      type: str
    is_enabled:
      description: Whether the user can log in.
      type: bool
    is_builtin:
      description: Whether this is a built-in user.
      type: bool
    auth_type:
      description: Authentication type, V(local) or V(federated).
      type: str
    auth_sources:
      description: Authentication sources of the user.
      type: list
      elements: raw
    last_login:
      description: Last login timestamp.
      type: str
    created_at:
      description: Creation timestamp.
      type: str
    updated_at:
      description: Last update timestamp.
      type: str
  sample:
    id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    username: alice
    email: alice@example.com
    is_enabled: true
    auth_type: local
groups:
  description: Names of the groups the user belongs to after the module ran.
  returned: when O(groups) is set and the user was created or O(state) is V(present)
  type: list
  elements: str
  sample: [users, operators]
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule, is_uuid


def _group_names_for_create(module, values):
    """Return group names for group_names; UUIDs are turned into names."""
    names = []
    for value in values:
        if is_uuid(value):
            obj = module.resolve_obj("group", value)
            if obj is None:
                module.fail_json(msg="group '{0}' not found".format(value))
            value = obj["name"]
        names.append(value)
    return names


# Built-in groups whose membership the server manages itself; it ignores attempts to remove them.
IMPLICIT_GROUPS = frozenset(["authenticated"])


def _is_implicit(group):
    """True for memberships the server owns: identity-provider sourced, or the implicit built-in groups."""
    if group.get("is_builtin") and group.get("name") in IMPLICIT_GROUPS:
        return True
    return any(src.get("type") != "manual" for src in group.get("membership_sources") or [])


def _reconcile_groups(module, user, values):
    """Make the manual group memberships of ``user`` match ``values``; return (changed, group names)."""
    context = "Failed to update groups of user '{0}'".format(user.get("username"))
    current = module.get_all("/users/{0}/groups".format(user["id"]), context=context)
    current_names = dict((g["id"], g.get("name")) for g in current)
    target = {}
    for value in values:
        group_id = module.resolve_id("group", value)
        name = current_names.get(group_id)
        if name is None:
            name = value
            if is_uuid(value):
                obj = module.resolve_obj("group", value)
                if obj is None:
                    module.fail_json(msg="group '{0}' not found".format(value))
                name = obj["name"]
        target[group_id] = name
    for group in current:
        if _is_implicit(group):
            target[group["id"]] = group.get("name")
    if set(target) == set(current_names):
        return False, sorted(g.get("name") or "" for g in current)
    if not module.check_mode:
        try:
            module.request("PUT", "/users/{0}/groups".format(user["id"]), data={"group_ids": sorted(target)})
        except OrchestratorAPIError as err:
            module.fail_api(err, context)
    return True, sorted((name or "" for name in target.values()))


def main():
    argument_spec = dict(
        username=dict(type="str", required=True),
        new_username=dict(type="str"),
        password=dict(type="str", no_log=True),
        update_password=dict(type="str", default="on_create", choices=["on_create", "always"], no_log=False),
        email=dict(type="str"),
        first_name=dict(type="str"),
        last_name=dict(type="str"),
        is_enabled=dict(type="bool"),
        groups=dict(type="list", elements="str"),
        state=dict(type="str", default="present", choices=["present", "absent", "exists"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "user"
    params = module.params
    state = params["state"]

    if state == "present":
        existing = module.find_existing("/users", params["username"], params["new_username"], name_field="username")
    else:
        existing = module.get_one_by_name("/users", params["username"], name_field="username")

    if state == "absent":
        changed = module.delete_if_needed(existing, "/users")
        module.exit_result(changed, None)

    if state == "exists" and existing is not None:
        module.exit_result(False, existing)

    username = params["new_username"] if state == "present" and params["new_username"] else params["username"]
    desired = module.build_desired(
        {
            "username": username,
            "email": params["email"],
            "first_name": params["first_name"],
            "last_name": params["last_name"],
            "is_enabled": params["is_enabled"],
        }
    )
    extra = {}
    if existing is None:
        if not params["password"]:
            module.fail_json(msg="password is required to create a local user '{0}'".format(username))
        desired["password"] = params["password"]
        if params["groups"] is not None:
            desired["group_names"] = _group_names_for_create(module, params["groups"])
            extra["groups"] = list(desired["group_names"])
    elif params["password"] and params["update_password"] == "always" and existing.get("auth_type") != "federated":
        desired["password"] = params["password"]

    changed, obj = module.create_or_update(existing, desired, "/users", secret_fields=("password",))

    if existing is not None and state == "present" and params["groups"] is not None:
        groups_changed, names = _reconcile_groups(module, existing, params["groups"])
        changed = changed or groups_changed
        extra["groups"] = names
    module.exit_result(changed, obj, **extra)


if __name__ == "__main__":
    main()
