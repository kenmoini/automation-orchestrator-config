# API compatibility

Built against the Automation Orchestrator API 1.3.1 OpenAPI snapshot (`docs/api/openapi-1.3.1.json`, OpenAPI title "Syntara API") and verified on 2026-10-18 against a live instance reporting `info_version` 1.3.1 (`GET /version`). The live checks are in `tests/live/spot_checks.yml` (`make live-spot`); their output is written to `tests/output/spot_findings.json`.

Automation Orchestrator is a tech preview. The table lists behaviors the collection depends on, what the live instance did, and what that means for users.

## Verified behaviors

| # | Behavior | Where it matters | Live result (API 1.3.1) |
| --- | --- | --- | --- |
| 1 | Workflow definition round trip. | `workflow`, `workflow_info`, `orchestrator_workflows`, `export_workflows.yml` | Verified. A valid definition is stored byte-for-byte as sent (key order aside); `GET /workflows/{id}` returns it under `version.workflow_definition`; `GET /workflows/{id}/versions/{v}/export` returns the bare definition (`schema_version`, `name`, `triggers`, `nodes`, `edges`), identical to the stored one. Re-applying the same definition reports `changed: false`. Publishing version 1 sets `published_version_number: 1`. |
| 2 | LLM model and MCP tool rows. | `integration`, `orchestrator_integrations` | Verified. `POST /integrations/{id}/refresh` works for both `llm_provider` and `mcp_server` and returns `{synced_count, updated_count, missing_count, refreshed_at}`. An integration created without `discovered_models`/`discovered_tools` has no rows; a refresh against an endpoint that is not a real provider leaves them empty. `POST /integrations/{id}/validate` returns `{success, checked_at, error, error_type}` and does not fail the request when the endpoint is unreachable. |
| 3 | Soft-deleted names can be re-created. | `user`, `group` | Verified for users and groups: delete then re-create with the same name succeeds. Service accounts and identity providers were not exercised. |
| 4 | `credential_type` names. | `credential`, `credential_type_info` | Verified. The instance ships six managed types: `HTTP Bearer Token` (input `token`), `HTTP Basic Auth` (`username`, `password`), `Ansible Automation Platform` (`username`/`password` or `oauth_token`), `LLM Provider` (`api_key`), `SSH Key` (`username`, `ssh_private_key`), `Secret URL` (`url`). There is no "Generic" type; the test configs use `HTTP Bearer Token`. Credential types are read-only on this release. |
| 5 | Policy action strings and scopes. | `policy`, `role` | Verified. Built-in policies use `<resource>:<verb>` actions such as `user:read`, `credential:use`, `tool:update`, `llm_model:read`, `integration:read`, with statement scopes `self` and `any`. Built-in roles: `admin`, `auditor`, `user`, `authenticated` (scope `system`) and `project-admin`, `project-user`, `project-auditor` (scope `project`). |
| 6 | `enforce_defaults` sends `labels: {}` and `description: ''`. | all resource roles | Not exercised by the live run (the test configs leave `enforce_defaults` off). The server returns `description: null` and `labels: {}` for objects created without them, so enforcing an empty description would show as drift. Leave `enforce_defaults` off unless every item sets `description`. |
| 7 | `scope` filter values for roles and policies. | `role`, `policy`, `role_info`, `policy_info` | Verified values: roles use `system` and `project`; policy statements use `self`, `any` and (for project-scoped custom policies) `project`. |
| 8 | List endpoints accept `limit`. | `credential_type_info`, `identity_provider`, pagination in `module_utils` | Verified. `/identity_providers?limit=100`, `/policies?limit=100`, `/roles?limit=100`, `/projects?limit=100` and `/settings` all return 200. `total` is `null` on every list response seen, so the collection never relies on it. |
| 9 | Service-account role assignments use `principal_id`. | `role_assignment`, `orchestrator_role_assignments` | Implemented per the spec (`RoleAssignmentCreate` has only `principal_id` and `group_id`; the read model's `principal_type` includes `service_account`). Exercised by `tests/configs/role_assignments.yml` in `make live`. |

## Live findings that shape how you write configuration

- **Workflow definitions must follow the server's node schema or the request fails.** Edges use `from` and `to` (not `source`/`target`); sending `source`/`target` produces an HTTP 500 rather than a validation error. Node and trigger ids must match `^[a-zA-Z_][a-zA-Z0-9_]*$` (no hyphens). Trigger types are `manual_trigger`, `scheduled_trigger`, `webhook_trigger` and `eda_trigger`, and every trigger needs a `parameters` object (`{}` for a manual trigger). Definitions that violate the schema may still be stored with `has_validation_issues: true` and a `validation_result.findings` list; the `workflow` module reports the server object, so inspect `validation_result` after a create. The minimal valid definition is in `tests/configs/files/aoc-test-wait.json`.
- **Integration `base_url` must resolve to a public address.** Hostnames that do not resolve (for example `*.invalid`) or that resolve to private, reserved or cloud-metadata ranges are rejected with HTTP 422 `VALIDATION_ERROR`.
- **`llm_provider` integrations need a management credential and a `provider_hint`.** Creating one without `management_credential` fails with HTTP 422 `INTEGRATION_CREDENTIAL_REQUIRED`; `configuration.provider_hint` is required (`openai` was accepted). `mcp_server` integrations need only `base_url`.
- **Settings are typed rows.** `GET /settings` returns a list of rows with `key`, `value` (null when unset), `default_value`, `effective_value`, `value_type`, `version` and `requires_restart`. The `setting` module diffs against `value`, so a setting left at its default shows `value: null`.
- **Every user is a member of the implicit built-in `authenticated` group.** `PUT /users/{id}/groups` without it does not remove it, so the `user` module keeps that membership out of the comparison and never reports it as drift. Other built-in groups (`users`, `admins`, `auditors`) are ordinary memberships that `groups` manages.
- **The server normalises OIDC URLs.** `issuer_url` is stored with a trailing slash (`https://idp.example.com` becomes `https://idp.example.com/`). The `identity_provider` module treats URL fields that differ only by a trailing slash as equal.
- **`include_vars dir:` is recursive.** The configure playbooks load only the top level of the configs directory (`depth: 1`) so that a `files/` subdirectory holding workflow definitions is not parsed as variables.
- **Server-side name filters are exact.** `name=` on `/projects`, `/roles`, `/policies`, `/service_accounts` and `username=` on `/users` return exact matches only.

## Known API facts

From the OpenAPI spec (126 endpoints, 259 schemas), confirmed live where noted.

- Authentication: Bearer JWT. `POST /auth/login` (username and password) returns `{access_token, expires_in}`; `POST /auth/token` with `grant_type=client_credentials` serves service accounts. Every endpoint, including `/version`, needs authentication (confirmed).
- Pagination: cursor based. `limit` is at most 100, the response is `{next, prev, total, resources}` with `total` null in practice (confirmed).
- Identifiers are UUIDs. Updates use PATCH, deletes return 204 (confirmed).
- Name filters: a server-side `name=` filter exists for projects, roles, policies and service accounts, and `username=` for users. Workflows (listed per project at `/projects/{id}/workflows`), credentials (listed per project), groups, integrations and identity providers have no filter, so the collection matches names client-side after paginating. `/groups/directory` and `/users/directory` are used as cheaper lookups.
- Errors: RFC 9457 problem-details documents with `type`, `title`, `detail`, `code`, `retryable` and `instance` (confirmed).
- Secrets are write-only: credential `inputs`, OIDC `client_secret`; a service account `client_secret` is returned once.
- Immutables and limits: `is_builtin` objects cannot be deleted; `expected_version` gives optimistic locking on settings and workflows; `GroupCreate` and `UserCreate` have no `labels`; `ServiceAccountRead.labels` is read-only; `WorkflowRead.is_enabled` is not settable; `UserUpdate` has no `group_names` (use `PUT /users/{id}/groups`).
- A workflow `PATCH` with `workflow_definition` is change-detected server side and bumps `current_version`. Publishing is `POST /workflows/{id}/versions/{v}/publish`, which also accepts an inline definition.
- `GET /workflows/{id}/versions/{v}/export` has no response schema; live it returns the bare definition. The collection reads definitions from `GET /workflows/{id}` and `GET /workflows/{id}/versions/{v}`, which carry the same content plus metadata.
