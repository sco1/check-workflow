# check-workflow

[![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fsco1%2Fcheck-workflow%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&logo=python&logoColor=FFD43B)](https://github.com/sco1/check-workflow/blob/main/pyproject.toml)
[![GitHub Release](https://img.shields.io/github/v/release/sco1/check-workflow)](https://github.com/sco1/check-workflow/releases)
[![GitHub License](https://img.shields.io/github/license/sco1/check-workflow?color=magenta)](https://github.com/sco1/check-workflow/blob/main/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/check-workflow/main.svg)](https://results.pre-commit.ci/latest/github/sco1/check-workflow/main)

Check GHA For Dependency Updates

## Usage

### CLI

Manual reports can be generated using the `CheckWorkflow` CLI.

<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["CheckWorkflow", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"\n```text\n$ CheckWorkflow --help\n{out.stdout.rstrip()}\n```\n\n"
)
]]] -->

```text
$ CheckWorkflow --help
usage: CheckWorkflow [-h] [-r ROOT] [-b BRANCH] [-m] org repo

positional arguments:
  org                  Query repository parent
  repo                 Query repository

options:
  -h, --help           show this help message and exit
  -r, --root ROOT      Workflow root (default: .github/workflows/)
  -b, --branch BRANCH  Query branch (default: main)
  -m, --markdown       Format report as markdown (default: False)
```

<!-- [[[end]]] -->

For example:

```text
$ CheckWorkflow sco1 wheely-bucket
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

### CRON

A CRON job is scheduled [via GHA](https://github.com/sco1/check-workflow/blob/main/.github/workflows/check_cron.yml) to check the workflows used by [sco1/py-template](https://github.com/sco1/py-template) on the first of every month @ 0900 UTC. If outdated dependencies are found, an issue is opened under this repository summarizing the report.

## Why Don't You Just Use Dependabot?

Because I don't want to! 😊

The idea initially came because Dependabot for a very long time did not support grouping PRs, which led to a ton of noise that I didn't particularly care for. Though it was eventually added, workflow updates aren't something I need to constantly be pinged on to take care of; it's sufficient for my needs to bump them while I'm bumping or adjusting other things.

Also it's fun to solve problems on my own.
