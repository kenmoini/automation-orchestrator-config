# API compatibility

Tested against Automation Orchestrator API 1.3.1 (OpenAPI title "Syntara API"); spec snapshot in `docs/api/openapi-1.3.1.json`.

Automation Orchestrator is a tech preview. The table lists behaviors the collection assumes that have not yet been verified against a live instance. Each is to be confirmed on the first live run (`make live`) and this page updated with the result.

## Unverified assumptions

| # | Behavior assumed | Where it matters | Status |
| --- | --- | --- | --- |
| 1 | Workflow definition round trip: the server may rewrite a stored definition (`is_import`, model and service-account fields stripped). The `workflow` module warns when the stored definition differs from the requested one. | `workflow`, `orchestrator_workflows` | unverified — to confirm on first live run |
| 2 | LLM model and MCP tool rows are created by `POST /integrations/discover` on create or by `/refresh`. `refresh` may be MCP-only. | `integration`, `orchestrator_integrations` | unverified — to confirm on first live run |
| 3 | Soft-deleted names (users, groups, service accounts, identity providers): whether a deleted name can be re-created. | `user`, `group`, `service_account`, `identity_provider` | unverified — to confirm on first live run |
| 4 | Which `credential_type` names exist on an instance. Test configs use "Generic". | `credential`, `credential_type_info` | unverified — to confirm on first live run |
| 5 | Policy action strings, for example `workflow:read`. | `policy`, `role` | unverified — to confirm on first live run |
| 6 | `enforce_defaults` sends `labels: {}` and `description: ''`; the server may store nulls instead, which would show as drift. | all resource roles | unverified — to confirm on first live run |
| 7 | Accepted `scope` filter values for roles and policies. | `role`, `policy`, `role_info`, `policy_info` | unverified — to confirm on first live run |
| 8 | List endpoints that accept `limit`, in particular `/credential_types` and `/identity_providers`. | `credential_type_info`, `identity_provider` | unverified — to confirm on first live run |

## Known API facts

From the OpenAPI spec (126 endpoints, 259 schemas).

- Authentication: Bearer JWT. `POST /auth/login` (username and password) returns `{access_token, expires_in}`; `POST /auth/token` with `grant_type=client_credentials` serves service accounts. Every endpoint, including `/version`, needs authentication.
- Pagination: cursor based. `limit` is at most 100, the response is `{next, prev, total?, resources}`.
- Identifiers are UUIDs. Updates use PATCH, deletes return 204.
- Name filters: a server-side `name=` filter exists for projects, roles, policies and service accounts, and `username=` for users. Workflows (listed per project at `/projects/{id}/workflows`), credentials (listed per project), groups, integrations and identity providers have no filter, so the collection matches names client-side after paginating. `/groups/directory` and `/users/directory` are used as cheaper lookups.
- Errors: RFC 9457 problem-details documents.
- Secrets are write-only: credential `inputs`, OIDC `client_secret`; a service account `client_secret` is returned once.
- Immutables and limits: `is_builtin` objects cannot be deleted; `expected_version` gives optimistic locking on settings and workflows; `GroupCreate` and `UserCreate` have no `labels`; `ServiceAccountRead.labels` is read-only; `WorkflowRead.is_enabled` is not settable; `UserUpdate` has no `group_names` (use `PUT /users/{id}/groups`).
- A workflow `PATCH` with `workflow_definition` is change-detected server side and bumps `current_version`. Publishing is `POST /workflows/{id}/versions/{v}/publish`, which also accepts an inline definition.
- `GET /workflows/{id}/versions/{v}/export` has no response schema, so the collection reads definitions from `GET /workflows/{id}` and `GET /workflows/{id}/versions/{v}` instead.
