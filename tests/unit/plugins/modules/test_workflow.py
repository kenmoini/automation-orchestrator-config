# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import workflow as module_under_test
from ansible.module_utils import basic
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

PID = "11111111-1111-4111-8111-111111111111"
PID2 = "22222222-2222-4222-8222-222222222222"
WID = "33333333-3333-4333-8333-333333333333"
LIST = "/api/v1/projects/" + PID + "/workflows"
WFS = "/api/v1/workflows"
ITEM = WFS + "/" + WID


def _definition(**kw):
    obj = {
        "schema_version": "2.0.0",
        "name": "deploy",
        "triggers": [{"id": "t1", "type": "manual_trigger"}],
        "nodes": [{"id": "n1", "type": "start"}, {"id": "n2", "type": "end"}],
        "edges": [{"from": "n1", "to": "n2"}],
    }
    obj.update(kw)
    return obj


def _wf(**kw):
    obj = {
        "id": WID,
        "name": "deploy",
        "description": "old",
        "labels": {"a": "1"},
        "current_version": 2,
        "is_builtin": False,
        "is_enabled": True,
        "published_version_id": None,
        "published_version_number": None,
        "project_id": PID,
    }
    obj.update(kw)
    return obj


def _with_version(definition=None, **kw):
    obj = _wf(**kw)
    obj["version"] = {
        "id": "v-id",
        "workflow_id": WID,
        "version": obj["current_version"],
        "workflow_definition": definition or _definition(),
        "status": "draft",
    }
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def _calls(api, method):
    return [c for c in api.calls if c["method"] == method]


BASE = {"name": "deploy", "project": PID}


# ------------------------------------------------------------------ create


def test_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", WFS, 201, _wf())
    definition = {"triggers": [{"id": "t1"}], "nodes": [], "edges": []}
    stored = {"schema_version": "2.0.0", "name": "deploy", "triggers": [{"id": "t1"}], "nodes": [], "edges": []}
    fake_api.add("GET", ITEM, 200, _with_version(stored))
    params = dict(BASE, description="d", labels={"a": "1"}, workflow_definition=definition)
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    assert result["id"] == WID
    assert result["version"] == 2
    assert result["published_version"] is None
    assert result["definition_changed"] is True
    assert _calls(fake_api, "POST")[0]["body"] == {
        "name": "deploy",
        "description": "d",
        "labels": {"a": "1"},
        "workflow_definition": {"schema_version": "2.0.0", "name": "deploy", "triggers": [{"id": "t1"}], "nodes": [], "edges": []},
        "project_id": PID,
        "is_import": False,
    }


def test_create_resolves_project_name(fake_api):
    fake_api.add("GET", "/api/v1/projects", 200, _list({"id": PID, "name": "platform"}))
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", WFS, 201, _with_version(_definition()))
    run_module(module_under_test.main, {"name": "deploy", "project": "platform", "workflow_definition": _definition(), "is_import": True}, fake_api)
    body = _calls(fake_api, "POST")[0]["body"]
    assert body["project_id"] == PID
    assert body["is_import"] is True


def test_create_requires_definition(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, description="d"), fake_api)
    assert exc.value.kwargs["msg"] == "workflow_definition or definition_file is required to create workflow 'deploy'"
    assert _calls(fake_api, "POST") == []


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(module_under_test.main, dict(BASE, workflow_definition=_definition(), _ansible_check_mode=True), fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "POST") == []
    assert result["workflow"]["name"] == "deploy"


def test_definition_file_json_and_yaml_loaded(fake_api, tmp_path):
    json_file = tmp_path / "wf.json"
    json_file.write_text(json.dumps({"triggers": [{"id": "j"}], "nodes": [], "edges": []}))
    yaml_file = tmp_path / "wf.yml"
    yaml_file.write_text("triggers:\n  - id: y\nnodes: []\nedges: []\n")
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", WFS, 201, _wf())
    fake_api.add("GET", ITEM, 200, _with_version({"schema_version": "2.0.0", "name": "deploy", "triggers": [{"id": "j"}], "nodes": [], "edges": []}), times=1)
    fake_api.add("GET", ITEM, 200, _with_version({"schema_version": "2.0.0", "name": "deploy", "triggers": [{"id": "y"}], "nodes": [], "edges": []}), times=1)
    run_module(module_under_test.main, dict(BASE, definition_file=str(json_file)), fake_api)
    run_module(module_under_test.main, dict(BASE, definition_file=str(yaml_file)), fake_api)
    posts = _calls(fake_api, "POST")
    assert posts[0]["body"]["workflow_definition"] == {"schema_version": "2.0.0", "name": "deploy", "triggers": [{"id": "j"}], "nodes": [], "edges": []}
    assert posts[1]["body"]["workflow_definition"] == {"schema_version": "2.0.0", "name": "deploy", "triggers": [{"id": "y"}], "nodes": [], "edges": []}


def test_definition_file_unreadable_fails(fake_api, tmp_path):
    missing = str(tmp_path / "nope.json")
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, definition_file=missing), fake_api)
    assert exc.value.kwargs["msg"].startswith("definition_file '{0}' could not be read/parsed: ".format(missing))


def test_definition_file_not_a_mapping_fails(fake_api, tmp_path):
    path = tmp_path / "list.yml"
    path.write_text("- a\n- b\n")
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, definition_file=str(path)), fake_api)
    assert "could not be read/parsed" in exc.value.kwargs["msg"]


def test_definition_name_overridden_to_item_name(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", WFS, 201, _with_version(_definition()))
    definition = _definition(name="something-else", schema_version="2.0.0")
    run_module(module_under_test.main, dict(BASE, workflow_definition=definition), fake_api)
    assert _calls(fake_api, "POST")[0]["body"]["workflow_definition"]["name"] == "deploy"


# ------------------------------------------------------------------ update


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("PATCH", ITEM, 200, _with_version(description="new"))
    result = run_module(module_under_test.main, dict(BASE, description="new"), fake_api)
    assert result["changed"] is True
    assert result["definition_changed"] is False
    assert _calls(fake_api, "PATCH")[0]["body"] == {"description": "new"}
    assert "version" not in result["workflow"]


def test_update_diff_mode(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("PATCH", ITEM, 200, _with_version(description="new"))
    result = run_module(module_under_test.main, dict(BASE, description="new", _ansible_diff=True), fake_api)
    assert result["diff"] == {"before": {"description": "old"}, "after": {"description": "new"}}


def test_labels_changed_patch(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("PATCH", ITEM, 200, _with_version(labels={"b": "2"}))
    run_module(module_under_test.main, dict(BASE, labels={"b": "2"}), fake_api)
    assert _calls(fake_api, "PATCH")[0]["body"] == {"labels": {"b": "2"}}


def test_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    result = run_module(module_under_test.main, dict(BASE, description="old", labels={"a": "1"}), fake_api)
    assert result["changed"] is False
    assert result["version"] == 2
    assert _calls(fake_api, "PATCH") == []


@pytest.mark.parametrize("check_mode", [False, True])
def test_unchanged_definition_no_patch_in_run_and_check_mode(fake_api, check_mode):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM, 200, _with_version(_definition()))
    # Same content, different key order and no schema_version/name: still unchanged after normalization.
    given = {
        "edges": [{"to": "n2", "from": "n1"}],
        "nodes": [{"type": "start", "id": "n1"}, {"id": "n2", "type": "end"}],
        "triggers": [{"type": "manual_trigger", "id": "t1"}],
    }
    result = run_module(module_under_test.main, dict(BASE, workflow_definition=given, description="old", _ansible_check_mode=check_mode), fake_api)
    assert result["changed"] is False
    assert result["definition_changed"] is False
    assert _calls(fake_api, "PATCH") == []


def test_reordered_nodes_count_as_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM, 200, _with_version(_definition()))
    given = _definition(nodes=[{"id": "n2", "type": "end"}, {"id": "n1", "type": "start"}])
    result = run_module(module_under_test.main, dict(BASE, workflow_definition=given, _ansible_check_mode=True), fake_api)
    assert result["definition_changed"] is True
    assert result["changed"] is True


def test_changed_definition_patch_includes_expected_version(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM, 200, _with_version(_definition()))
    new_definition = _definition(edges=[])
    fake_api.add("PATCH", ITEM, 200, _with_version(new_definition, current_version=3))
    params = dict(BASE, workflow_definition=new_definition, change_description="drop edge", description="new", _ansible_diff=True)
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    assert result["definition_changed"] is True
    assert result["version"] == 3
    assert _calls(fake_api, "PATCH")[0]["body"] == {
        "description": "new",
        "workflow_definition": new_definition,
        "change_description": "drop edge",
        "expected_version": 2,
    }
    assert result["diff"]["before"]["workflow_definition"]["edges"] == [{"from": "n1", "to": "n2"}]
    assert result["diff"]["after"]["workflow_definition"]["edges"] == []
    assert result["diff"]["before"]["description"] == "old"


def test_changed_definition_check_mode_no_patch(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM, 200, _with_version(_definition()))
    result = run_module(module_under_test.main, dict(BASE, workflow_definition=_definition(edges=[]), _ansible_check_mode=True), fake_api)
    assert result["changed"] is True
    assert result["definition_changed"] is True
    assert _calls(fake_api, "PATCH") == []


def test_warns_when_server_rewrites_definition(fake_api, mocker):
    warn = mocker.patch.object(basic.AnsibleModule, "warn")
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM, 200, _with_version(_definition()))
    sent = _definition(edges=[])
    stored = _definition(edges=[], nodes=[{"id": "n1", "type": "start", "model": None}])
    fake_api.add("PATCH", ITEM, 200, _with_version(stored, current_version=3))
    result = run_module(module_under_test.main, dict(BASE, workflow_definition=sent), fake_api)
    assert result["changed"] is True
    messages = [c.args[0] for c in warn.call_args_list]
    assert len(messages) == 1
    assert messages[0].startswith("The server stored a modified definition for workflow 'deploy'")


def test_create_warns_when_import_rewrites_definition(fake_api, mocker):
    warn = mocker.patch.object(basic.AnsibleModule, "warn")
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", WFS, 201, _wf(current_version=1))
    fake_api.add("GET", ITEM, 200, _with_version(_definition(nodes=[]), current_version=1))
    run_module(module_under_test.main, dict(BASE, workflow_definition=_definition(), is_import=True), fake_api)
    assert warn.call_args_list[0].args[0].startswith("The server stored a modified definition for workflow 'deploy'")


def test_no_warning_when_stored_definition_matches(fake_api, mocker):
    warn = mocker.patch.object(basic.AnsibleModule, "warn")
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM, 200, _with_version(_definition()))
    fake_api.add("PATCH", ITEM, 200, _with_version(_definition(edges=[]), current_version=3))
    run_module(module_under_test.main, dict(BASE, workflow_definition=_definition(edges=[])), fake_api)
    assert warn.call_args_list == []


# ------------------------------------------------------------------ publish / unpublish


def test_create_with_publish_publishes_version_1(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", WFS, 201, _with_version(_definition(), current_version=1))
    fake_api.add("POST", ITEM + "/versions/1/publish", 200, _with_version(_definition(), current_version=1, published_version_number=1))
    result = run_module(module_under_test.main, dict(BASE, workflow_definition=_definition(), publish=True, change_description="first"), fake_api)
    assert result["changed"] is True
    assert result["version"] == 1
    assert result["published_version"] == 1
    posts = _calls(fake_api, "POST")
    assert [p["path"] for p in posts] == [WFS, ITEM + "/versions/1/publish"]
    assert posts[1]["body"] == {"change_description": "first"}


def test_expected_version_comes_from_fetched_definition(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf(current_version=2)))
    fake_api.add("GET", ITEM, 200, _with_version(_definition(), current_version=4))
    fake_api.add("PATCH", ITEM, 200, _with_version(_definition(edges=[]), current_version=5))
    run_module(module_under_test.main, dict(BASE, workflow_definition=_definition(edges=[])), fake_api)
    assert _calls(fake_api, "PATCH")[0]["body"]["expected_version"] == 4


def test_publish_after_change_targets_new_version(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf(published_version_number=2)))
    fake_api.add("GET", ITEM, 200, _with_version(_definition(), published_version_number=2))
    new_definition = _definition(edges=[])
    fake_api.add("PATCH", ITEM, 200, _with_version(new_definition, current_version=3, published_version_number=2))
    publish_response = _with_version(new_definition, current_version=3, published_version_number=3)
    publish_response["warning"] = ""
    fake_api.add("POST", ITEM + "/versions/3/publish", 200, publish_response)
    result = run_module(module_under_test.main, dict(BASE, workflow_definition=new_definition, change_description="v3", publish=True), fake_api)
    assert result["changed"] is True
    posts = _calls(fake_api, "POST")
    assert [p["path"] for p in posts] == [ITEM + "/versions/3/publish"]
    assert posts[0]["body"] == {"change_description": "v3"}
    assert result["version"] == 3
    assert result["published_version"] == 3
    assert "version" not in result["workflow"]
    assert "warning" not in result["workflow"]


def test_publish_current_when_unpublished(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("POST", ITEM + "/versions/2/publish", 200, _with_version(published_version_number=2))
    result = run_module(module_under_test.main, dict(BASE, publish=True), fake_api)
    assert result["changed"] is True
    assert result["published_version"] == 2
    assert _calls(fake_api, "POST")[0]["body"] == {}


def test_publish_noop_when_already_published(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf(published_version_number=2)))
    fake_api.add("GET", ITEM, 200, _with_version(_definition(), published_version_number=2))
    result = run_module(module_under_test.main, dict(BASE, workflow_definition=_definition(), publish=True), fake_api)
    assert result["changed"] is False
    assert result["published_version"] == 2
    assert _calls(fake_api, "POST") == []
    assert _calls(fake_api, "PATCH") == []


def test_publish_check_mode_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    result = run_module(module_under_test.main, dict(BASE, publish=True, _ansible_check_mode=True), fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "POST") == []


def test_unpublish_when_published(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf(published_version_number=2)))
    fake_api.add("POST", ITEM + "/unpublish", 200, _wf(published_version_number=None))
    result = run_module(module_under_test.main, dict(BASE, unpublish=True), fake_api)
    assert result["changed"] is True
    assert result["published_version"] is None
    assert [c["path"] for c in _calls(fake_api, "POST")] == [ITEM + "/unpublish"]


def test_unpublish_noop_when_not_published(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    result = run_module(module_under_test.main, dict(BASE, unpublish=True), fake_api)
    assert result["changed"] is False
    assert _calls(fake_api, "POST") == []


def test_publish_and_unpublish_mutually_exclusive(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, publish=True, unpublish=True), fake_api)
    assert "mutually exclusive" in exc.value.kwargs["msg"]


# ------------------------------------------------------------------ project / rename / errors


def test_project_immutable(fake_api):
    fake_api.add("GET", ITEM, 200, _with_version(project_id=PID2))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"name": WID, "project": PID, "description": "x"}, fake_api)
    assert exc.value.kwargs["msg"] == "project_id cannot be changed on an existing workflow"
    assert _calls(fake_api, "PATCH") == []


def test_uuid_lookup_reuses_definition(fake_api):
    fake_api.add("GET", ITEM, 200, _with_version(_definition()))
    result = run_module(module_under_test.main, {"name": WID, "project": PID, "workflow_definition": _definition()}, fake_api)
    assert result["changed"] is False
    assert len([c for c in fake_api.calls if c["path"] == ITEM]) == 1


def test_rename(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("PATCH", ITEM, 200, _with_version(name="deploy-v2"))
    result = run_module(module_under_test.main, dict(BASE, new_name="deploy-v2"), fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {"name": "deploy-v2"}


def test_rename_rerun_is_idempotent(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf(name="deploy-v2")))
    fake_api.add("GET", ITEM, 200, _with_version(_definition(name="deploy-v2"), name="deploy-v2"))
    result = run_module(module_under_test.main, dict(BASE, new_name="deploy-v2", workflow_definition=_definition()), fake_api)
    assert result["changed"] is False
    assert _calls(fake_api, "PATCH") == []


def test_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM, 200, _with_version(_definition()))
    fake_api.add("PATCH", ITEM, 409, {"detail": "version conflict"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, workflow_definition=_definition(edges=[])), fake_api)
    assert exc.value.kwargs["msg"] == "Failed to update workflow 'deploy': version conflict"
    assert exc.value.kwargs["status"] == 409


def test_publish_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("POST", ITEM + "/versions/2/publish", 422, {"detail": "invalid"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, publish=True), fake_api)
    assert exc.value.kwargs["msg"] == "Failed to publish workflow 'deploy': invalid"


# ------------------------------------------------------------------ exists / absent


def test_exists_does_not_modify(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    result = run_module(module_under_test.main, dict(BASE, state="exists", description="zzz", workflow_definition=_definition(edges=[])), fake_api)
    assert result["changed"] is False
    assert _calls(fake_api, "PATCH") == []


def test_exists_creates_when_missing(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", WFS, 201, _with_version(_definition()))
    result = run_module(module_under_test.main, dict(BASE, state="exists", workflow_definition=_definition()), fake_api)
    assert result["changed"] is True
    assert len(_calls(fake_api, "POST")) == 1


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("DELETE", ITEM, 204)
    result = run_module(module_under_test.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is True
    assert result["workflow"] is None
    assert len(_calls(fake_api, "DELETE")) == 1


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(module_under_test.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is False
    assert _calls(fake_api, "DELETE") == []
