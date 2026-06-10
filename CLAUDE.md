# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of rapid, self-contained Python **POCs**. Each lives in its own
`projects/<name>/` directory as an independent mini-project with its **own isolated
environment** (`.venv`), `pyproject.toml`, and `uv.lock` — managed by
[uv](https://docs.astral.sh/uv/). POCs do not import each other and never share an
environment. The goal of the repo is to prototype an idea fast, keep it organized, and
store it for future reuse.

Every project follows the same shape as `template/`:

```
projects/<name>/
├── pyproject.toml   # name, description, deps, requires-python (>=3.11)
├── uv.lock          # committed for reproducibility
├── README.md
├── main.py          # def main() + if __name__ == "__main__"
└── tests/test_main.py
```

## Commands

Always work **inside a project directory** — `uv` resolves the right `.venv` from the
`pyproject.toml` in the current dir.

```bash
cd projects/<name>
uv run main.py        # run the POC (creates/syncs .venv automatically)
uv run pytest         # run that project's tests
uv add <pkg>          # add a runtime dependency (updates pyproject.toml + uv.lock)
uv add --dev <pkg>    # add a dev dependency
uv sync               # recreate .venv from the lockfile
```

Create a new POC from the template (run from repo root):

```bash
./new-poc.sh <name> ["short description"]
```

This copies `template/`, fills in the `{{NAME}}`/`{{DESC}}` placeholders, and runs
`uv sync` to build the `.venv`. To add a project by hand, copy `template/` into
`projects/` and edit `pyproject.toml`.

## Conventions

- **Tests are pytest** (in each project's `dev` dependency group), discovered under
  `projects/<name>/tests/`. There is no repo-wide test runner — tests are per project.
- Each `main.py` wraps its logic in `main()` guarded by `if __name__ == "__main__"`.
- Formatting is **black** (set as the Python formatter in `.vscode/settings.json`).
- `uv.lock` is committed; `.venv/` is gitignored. Generated artifacts
  (`beliche.stl`/`beliche.dae`) are gitignored.

## VS Code

Open the **multi-root workspace**, not individual folders:
`code python-stuffs.code-workspace`. It lists the repo root plus each project as a
separate folder, so every project keeps its own `.venv` (auto-detected per folder).
pytest/black settings live in the `.code-workspace` file; `new-poc.sh` appends each
new project to its `folders` list automatically (via a small inline Python snippet —
keep the workspace file pure JSON, no comments, so it stays parseable). The root
`.vscode/settings.json` mirrors the same settings for when the root folder is opened
directly.

## Notes

- `projects/3d-mesh-beliche/` is written in **Portuguese** (comments and names like
  `cama`, `degrau`, `beliche`); match that language when editing it. It writes
  `beliche.stl`/`beliche.dae` to the current working directory.
- `projects/network-scanner/` scans the real LAN (`192.168.0.0/24`, port 554); its test
  only checks `isReachable` against a closed local port, it does not run a full scan.
- `django-simple-api/` is untracked and contains only stale `.pyc` files with no source
  — treat it as empty/abandoned, not a working Django project.
- The `.devcontainer` uses Python 3.11 but does not ship `uv`; install it in the
  container before using these commands.
