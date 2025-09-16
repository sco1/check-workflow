# check-workflow

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
