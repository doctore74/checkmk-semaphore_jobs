# Development

How to build, test and release checkmk-semaphore_jobs. For installing and using it, see the
[README](../README.md).

## Building the MKP

Clone the repository and execute:

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd <REPOSITORY-DIRECTORY>
python3 build_mkp.py
```

The build script creates:

```text
semaphore_jobs-1.2.1.mkp
```

It reproducibly packages the files below `local/lib/python3/cmk_addons/plugins/semaphore_jobs/` and writes both Checkmk metadata formats (`info` and `info.json`).

Validate the generated package on a Checkmk 2.5 test site before publishing a release:

```bash
mkp add ./semaphore_jobs-1.2.1.mkp
mkp enable semaphore_jobs 1.2.1
cmk-validate-plugins
```

Contributions and issue reports are welcome. Useful issue reports should include:

- Checkmk edition and exact version
- Semaphore UI version
- Plug-in version
- Output of `cmk-validate-plugins`
- Relevant `cmk --debug` error text with credentials removed
- A sanitized `<<<semaphore_jobs:sep(0)>>>` section when the issue concerns parsing or counters
