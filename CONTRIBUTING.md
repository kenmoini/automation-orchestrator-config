# How to Contribute

Contributions are welcome. If you see something you would like changed, open an issue describing it.

## Working Locally

1. Create the dev environment: `make venv`.
2. Install pre-commit hooks: `pre-commit install --install-hooks -c .pre-commit-config.yaml`. Hooks run on `git commit` and block it on failure.
3. Run all checks at any time: `pre-commit run --all -c .pre-commit-config.yaml`.
4. Useful targets: `make lint`, `make sanity`, `make unit`, `make build`.

See [pre-commit](https://pre-commit.com/) for details. Coding rules are in `docs/STANDARDS.md`.

## Submit a Pull Request

1. Fork the repo and clone it locally.
2. Create an appropriately named branch.
3. Make your change, with unit tests for modules and a role test entry for new roles.
4. Add a changelog fragment in `changelogs/fragments/` as described in the [Ansible changelog docs](https://docs.ansible.com/ansible/latest/community/development_process.html#changelogs).
5. Make sure pre-commit, ansible-lint, and sanity checks pass.
6. Push to your fork and open a Pull Request.

## Code of Conduct

As with all Ansible projects, we have a [Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html).
