# check-workflow

[![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fsco1%2Fcheck-workflow%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&logo=python&logoColor=FFD43B)](https://github.com/sco1/check-workflow/blob/main/pyproject.toml)
[![GitHub Release](https://img.shields.io/github/v/release/sco1/check-workflow)](https://github.com/sco1/check-workflow/releases)
[![GitHub License](https://img.shields.io/github/license/sco1/check-workflow?color=magenta)](https://github.com/sco1/check-workflow/blob/main/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/check-workflow/main.svg)](https://results.pre-commit.ci/latest/github/sco1/check-workflow/main)

Check GHA For Dependency Updates

```text
$ CheckWorkflow remote sco1 check-workflow
lint_test.yml
+-------------+-------------------------+---------------------------+-----------+--------+
|     Job     |        Step Name        |           Action          | Specified | Latest |
+-------------+-------------------------+---------------------------+-----------+--------+
|     lint    |           None          |      actions/checkout     |   ~=4.0   | 5.0.0  |
|     test    |           None          |      actions/checkout     |   ~=4.0   | 5.0.0  |
| combine-cov |           None          |      actions/checkout     |   ~=4.0   | 5.0.0  |
| combine-cov | Pull workflow artifacts | actions/download-artifact |   ~=4.0   | 5.0.0  |
+-------------+-------------------------+---------------------------+-----------+--------+

release.yml
+-------+-----------+------------------+-----------+--------+
|  Job  | Step Name |      Action      | Specified | Latest |
+-------+-----------+------------------+-----------+--------+
| build |    None   | actions/checkout |   ~=4.0   | 5.0.0  |
+-------+-----------+------------------+-----------+--------+
```

## Installation

Since this is mainly intended as a personal helper, I do not intend to deploy this project to PyPI. Wheels are built in CI for each [released version](https://github.com/sco1/check-workflow/releases/latest).

Alternatively, you can use a tool like `uv` or `pipx` to run or install this project as a standalone tool, e.g.:

```text
$ uvx --from git+https://github.com/sco1/check-workflow@v1.1.0 CheckWorkflow --help
usage: CheckWorkflow [-h] {local,remote} ...

positional arguments:
  {local,remote}
    local         Query local project
    remote        Query remote repository

options:
  -h, --help      show this help message and exit
```

## Usage

Manual reports can be generated using the `CheckWorkflow` CLI for either a local or remote project.

### Local

<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["CheckWorkflow", "local", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"\n```text\n$ CheckWorkflow local --help\n{out.stdout.rstrip()}\n```\n\n"
)
]]] -->

```text
$ CheckWorkflow local --help
usage: CheckWorkflow local [-h] [-r ROOT] [-m]

options:
  -h, --help       show this help message and exit
  -r, --root ROOT  Workflow root (default: ./.github/workflows/)
  -m, --markdown   Format report as markdown (default: False)
```

<!-- [[[end]]] -->

### Remote

<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["CheckWorkflow", "remote", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"\n```text\n$ CheckWorkflow remote --help\n{out.stdout.rstrip()}\n```\n\n"
)
]]] -->

```text
$ CheckWorkflow remote --help
usage: CheckWorkflow remote [-h] [-b BRANCH] [-r ROOT] [-m] org repo

positional arguments:
  org                  Query repository parent
  repo                 Query repository

options:
  -h, --help           show this help message and exit
  -b, --branch BRANCH  Query branch (default: main)
  -r, --root ROOT      Workflow root (default: .github/workflows/)
  -m, --markdown       Format report as markdown (default: False)
```

<!-- [[[end]]] -->

## Why Don't You Just Use Dependabot?

Because I don't want to! 😊

The idea initially came because Dependabot for a very long time did not support grouping PRs, which led to a ton of noise that I didn't particularly care for. Though it was eventually added, workflow updates aren't something I need to constantly be pinged on to take care of; it's sufficient for my needs to bump them while I'm bumping or adjusting other things.

Also it's fun to solve problems on my own.
