# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import approval as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

AID = "55555555-5555-4555-8555-555555555555"
EID = "44444444-4444-4444-8444-444444444444"
PID = "11111111-1111-4111-8111-111111111111"
ITEM = "/api/v1/approvals/" + AID
LIST = "/api/v1/approvals"


def _appr(**kw):
    obj = {"id": AID, "name": "release-gate", "execution_id": EID, "status": "pending"}
    obj.update(kw)
    return obj


def _list(*items):
    return {"resources": list(items)}


def _methods(fake_api):
    return [c["method"] for c in fake_api.calls]


def test_decide_pending_patches(fake_api):
    fake_api.add("GET", ITEM, 200, _appr())
    fake_api.add("PATCH", ITEM, 200, _appr(status="approved"))
    result = run_module(module_under_test.main, {"id": AID, "decision": "approved", "notes": "ship it"}, fake_api)
    assert result["changed"] is True
    assert result["status"] == "approved"
    assert result["id"] == AID
    assert result["approval"]["status"] == "approved"
    assert fake_api.calls[-1]["body"] == {"status": "approved", "notes": "ship it"}


def test_decide_without_notes_omits_notes(fake_api):
    fake_api.add("GET", ITEM, 200, _appr())
    fake_api.add("PATCH", ITEM, 200, _appr(status="rejected"))
    run_module(module_under_test.main, {"id": AID, "decision": "rejected"}, fake_api)
    assert fake_api.calls[-1]["body"] == {"status": "rejected"}


def test_already_same_decision_noop(fake_api):
    fake_api.add("GET", ITEM, 200, _appr(status="approved"))
    result = run_module(module_under_test.main, {"id": AID, "decision": "approved"}, fake_api)
    assert result["changed"] is False
    assert result["status"] == "approved"
    assert _methods(fake_api) == ["GET"]


def test_conflicting_decision_fails(fake_api):
    fake_api.add("GET", ITEM, 200, _appr(status="approved"))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"id": AID, "decision": "rejected"}, fake_api)
    assert exc.value.kwargs["msg"] == "Approval 'release-gate' already approved"
    assert _methods(fake_api) == ["GET"]


def test_expired_fails(fake_api):
    fake_api.add("GET", ITEM, 200, _appr(status="expired"))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"id": AID, "decision": "approved"}, fake_api)
    assert exc.value.kwargs["msg"] == "Approval 'release-gate' already expired"


def test_lookup_by_execution_and_name(fake_api):
    other = _appr(id="66666666-6666-4666-8666-666666666666", name="other-gate")
    fake_api.add("GET", LIST, 200, _list(other, _appr()))
    fake_api.add("PATCH", ITEM, 200, _appr(status="approved"))
    result = run_module(module_under_test.main, {"execution": EID, "name": "release-gate", "decision": "approved"}, fake_api)
    assert result["changed"] is True
    assert result["id"] == AID
    assert fake_api.calls[0]["query"]["execution_id"] == EID
    assert fake_api.calls[1]["path"] == ITEM


def test_lookup_by_name_not_found_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list(_appr(name="other-gate")))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"execution": EID, "name": "release-gate", "decision": "approved"}, fake_api)
    assert exc.value.kwargs["msg"] == "approval 'release-gate' not found for execution {0}".format(EID)


def test_lookup_by_name_multiple_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list(_appr(), _appr(id="66666666-6666-4666-8666-666666666666")))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"execution": EID, "name": "release-gate", "decision": "approved"}, fake_api)
    assert "2" in exc.value.kwargs["msg"]


def test_lookup_by_id_404_fails(fake_api):
    fake_api.add("GET", ITEM, 404, {"detail": "not found"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"id": AID, "decision": "approved"}, fake_api)
    assert exc.value.kwargs["msg"] == "approval '{0}' not found".format(AID)


def test_check_mode_no_patch_but_changed(fake_api):
    fake_api.add("GET", ITEM, 200, _appr())
    result = run_module(module_under_test.main, {"id": AID, "decision": "approved", "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert result["status"] == "approved"
    assert _methods(fake_api) == ["GET"]


def test_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", ITEM, 200, _appr())
    fake_api.add("PATCH", ITEM, 409, {"detail": "conflict"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"id": AID, "decision": "approved"}, fake_api)
    assert exc.value.kwargs["msg"].startswith("Failed to decide approval 'release-gate'")
    assert exc.value.kwargs["status"] == 409


def test_diff_mode_status_change(fake_api):
    fake_api.add("GET", ITEM, 200, _appr())
    fake_api.add("PATCH", ITEM, 200, _appr(status="approved"))
    result = run_module(module_under_test.main, {"id": AID, "decision": "approved", "_ansible_diff": True}, fake_api)
    assert result["diff"] == {"before": {"status": "pending"}, "after": {"status": "approved"}}
