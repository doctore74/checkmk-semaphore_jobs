# Checkmk Special Agent for Semaphore UI Jobs

Monitor [Semaphore UI](https://semaphoreui.com/) task states, queue conditions, job ages, recent failures, and API data quality with Checkmk.

The extension runs entirely on the Checkmk server as a **special agent**. Nothing has to be installed on the Semaphore host or on a monitored Linux/Windows agent.

## Features

- Queries Semaphore UI through its REST API using a bearer token
- Monitors all accessible projects or an explicit list of project IDs
- Counts these task states:
  - `waiting`
  - `starting`
  - `waiting_confirmation`
  - `confirmed`
  - `rejected`
  - `running`
  - `stopping`
  - `stopped`
  - `success`
  - `error`
- Tracks the age of the oldest active task per relevant state
- Counts successful, failed, and stopped tasks within a configurable lookback period
- Shows one project summary per line in the service details
- Identifies projects whose task history may be incomplete because Semaphore returned the API limit of 1,000 tasks
- Detects unknown task states and invalid timestamps
- Provides configurable WARN/CRIT thresholds through Checkmk Setup
- Uses only the Python standard library at runtime

## Example service output

```text
Projects: 2, active: 1, running: 1, waiting: 0, starting: 0, confirmation: 0, stopping: 0
Waiting jobs: 0
Oldest waiting job: -
Oldest running job: 8 minutes 14 seconds
Failed jobs in last 24 hours: 0
Task history possibly incomplete: 1 project WARN
Demoprojekt: running=0, waiting=0, error(24h)=0
IaC Home: running=1, waiting=0, error(24h)=0, history limited to 1,000 tasks
```

When a project reaches the API limit, the long service output explains which project is affected:

```text
Affected projects:
- IaC Home (ID 2): 1,000 tasks returned; API limit 1,000;
  returned task IDs 1234-5678;
  returned time range 2026-04-01T12:00:00+00:00 to 2026-07-17T19:32:00+00:00
```

## Compatibility

| Component | Supported version |
|---|---|
| Checkmk | 2.5.0p1 through the 2.5 release line |
| Check API | v2 |
| Rulesets API | v1 |
| Server-side calls API | v1 |
| Semaphore | A version exposing the REST API endpoints used below |
| Python | The Python runtime supplied by Checkmk |

The special agent uses these Semaphore endpoints:

```text
GET /api/projects
GET /api/project/{project_id}/tasks
```

## Package contents

```text
local/lib/python3/cmk_addons/plugins/semaphore_jobs/
├── agent_based/semaphore_jobs.py
├── checkman/semaphore_jobs
├── libexec/agent_semaphore_jobs
├── rulesets/check_parameters.py
├── rulesets/special_agent.py
└── server_side_calls/special_agent.py
```

## Installation

### Checkmk commercial editions

1. Open **Setup → Maintenance → Extension packages**.
2. Upload `semaphore_jobs-1.2.1.mkp`.
3. Enable the package.
4. Activate the pending changes.

### Command line

Copy the MKP to the Checkmk server and run the following commands as the site user:

```bash
su - <SITE>
mkp add /tmp/semaphore_jobs-1.2.1.mkp
mkp enable semaphore_jobs 1.2.1
cmk-validate-plugins
cmk -R
```

Confirm the installed package:

```bash
mkp list
mkp show semaphore_jobs
```

## Semaphore API token

Semaphore UI supports API tokens in the web interface under the user settings/API token section. The token must have access to every project that should be monitored.

The special agent sends it as:

```text
Authorization: Bearer <TOKEN>
```

Use the Checkmk password store when entering the token in the rule.

## Checkmk configuration

### 1. Create a host

Create a Checkmk host representing the Semaphore UI installation. The host name does not have to resolve to the Semaphore server because the URL is configured separately in the special-agent rule.

Ensure the host is configured to execute configured API integrations/special agents. Depending on the Checkmk edition and host configuration, this is selected in the host property for **Checkmk agent / API integrations**.

### 2. Configure the data source

Create a rule under:

```text
Setup → Agents → Other integrations → Semaphore UI jobs
```

Configure:

| Setting | Description | Example |
|---|---|---|
| Semaphore base URL | URL without a trailing `/api` | `https://semaphore.example.com` |
| API token | Bearer token, preferably from the password store | password-store entry |
| Project IDs | `all` or comma-separated IDs | `all` or `1,2,7` |
| TLS verification | Verify the server certificate | enabled |
| HTTP timeout | Timeout per API request | `30` seconds |
| Completed-job lookback | Window for recent success/error/stopped counters | `24` hours |

Disable TLS certificate verification only for a controlled test environment or when using a self-signed certificate that cannot be added to the Checkmk server's trust store.

### 3. Discover the service

```bash
cmk -vI --detect-plugins=semaphore_jobs <HOSTNAME>
cmk -R
```

The package discovers one service:

```text
Semaphore Jobs
```

### 4. Configure thresholds

Create a rule under:

```text
Setup → Services → Service monitoring rules → Semaphore UI jobs
```

Default thresholds:

| Condition | WARN | CRIT | Rationale |
|---|---:|---:|---|
| Waiting jobs | 3 | 10 | Detect an accumulating queue |
| Oldest waiting job | 5 min | 30 min | Detect jobs that are not being scheduled |
| Oldest running job | 1 h | 2 h | Detect unusually long runs |
| Oldest starting job | 2 min | 10 min | Detect a stuck startup transition |
| Oldest stopping job | 2 min | 10 min | Detect a job that cannot terminate |
| Oldest confirmed job | 2 min | 10 min | Detect a confirmed job that does not start |
| Waiting for confirmation | 1 day | 7 days | Detect forgotten manual approvals |
| Failed jobs in lookback | 1 | 5 | Surface recent automation failures |
| Unknown task states | 1 | 5 | Detect API/schema changes |
| Invalid timestamps | 1 | 5 | Detect incomplete or malformed task data |
| Projects at API limit | 1 | 2 | Warn when counters may exclude older tasks |

The number of running jobs is intentionally informational. Normal concurrency differs significantly between Semaphore installations, so job age is generally a more meaningful health indicator.

## Understanding the 1,000-task warning

Semaphore's project task-list endpoint can return at most 1,000 task records. When a project returns exactly 1,000 records, the plug-in cannot prove that the history is complete and reports:

```text
Task history possibly incomplete: 1 project
```

The service details name each affected project and show:

- Project name and ID
- Number of returned tasks
- API limit
- Minimum and maximum returned task IDs, when available
- Oldest and newest timestamp in the returned dataset, when available

Current task-state counters normally remain useful because active jobs are generally part of the newest records. Historical totals and lookback counters can be incomplete when the selected lookback extends beyond the oldest returned task.

To reduce the impact:

- Monitor only the projects that matter by entering explicit project IDs.
- Use a shorter completed-job lookback.
- Adjust the **Projects at the Semaphore task-list API limit** threshold when the warning is accepted operationally.

## Testing and troubleshooting

### Validate the extension

```bash
cmk-validate-plugins
```

### Show the special-agent output

```bash
cmk -d <HOSTNAME> --debug \
  | sed -n '/<<<semaphore_jobs/,/^<<<.*>>>/p'
```

Expected section header:

```text
<<<semaphore_jobs:sep(0)>>>
```

### Run only this check plug-in

```bash
cmk --detect-plugins=semaphore_jobs -v <HOSTNAME>
```

For full debug output:

```bash
cmk --detect-plugins=semaphore_jobs -vv --debug <HOSTNAME>
```

### Test the collector directly

Run this as the Checkmk site user. Avoid placing a real token in shared shell history.

```bash
~/local/lib/python3/cmk_addons/plugins/semaphore_jobs/libexec/agent_semaphore_jobs \
  --url 'https://semaphore.example.com' \
  --token 'YOUR_TOKEN' \
  --projects 'all' \
  --timeout 30 \
  --lookback-hours 24
```

### Common problems

#### `401 Unauthorized` or `403 Forbidden`

- Verify the token.
- Verify that the user/token can access the selected projects.
- Confirm that the URL points to the Semaphore base URL and does not already end in `/api`.

#### TLS certificate error

- Install the issuing CA certificate in the Checkmk server trust store, which is the preferred solution.
- For testing, disable TLS verification in the special-agent rule.

#### No service discovered

- Confirm that the host executes configured API integrations.
- Check the special-agent output with `cmk -d`.
- Run `cmk-validate-plugins`.
- Rediscover with `cmk -vI --detect-plugins=semaphore_jobs <HOSTNAME>`.

#### Project names appear as `Project 2`

When explicit project IDs are configured, the collector does not fetch the complete project list and uses a generated name. Configure `all` when the token should monitor all accessible projects and human-readable names are preferred.

#### Recent error count appears lower than expected

Check whether the project has reached the 1,000-task API limit. The lookback counter can only evaluate records returned by Semaphore.

## Metrics

The service exposes metrics for graphing, including:

- Active jobs
- Waiting jobs
- Running jobs
- Starting jobs
- Jobs waiting for confirmation
- Confirmed jobs
- Rejected jobs
- Stopping jobs
- Recently successful jobs
- Recently failed jobs
- Recently stopped jobs
- Age of the oldest job in each monitored active state
- Unknown task-state count
- Invalid timestamp count
- Number of projects at the API task-list limit

Metric names use the `semaphore_` prefix.

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

## Repository workflow

A typical first publication on GitHub is:

```bash
git init
git add .
git commit -m "Initial release of Semaphore Jobs special agent"
git branch -M main
git remote add origin <YOUR-GITHUB-REPOSITORY-URL>
git push -u origin main
```

Create a GitHub release for version `1.2.1` and attach `semaphore_jobs-1.2.1.mkp` as the binary release asset.

## Security considerations

- Store the API token in the Checkmk password store.
- Grant the token only the access needed for monitoring.
- Keep TLS verification enabled wherever possible.
- The Checkmk server-side call resolves password-store values when constructing the special-agent command. The collector makes a best-effort attempt to replace its process title when the optional `setproctitle` module is available, but command-line exposure may still be possible briefly on the Checkmk server.
- Do not include API tokens in debug output, issue reports, screenshots, or repository commits.

## Development

Contributions and issue reports are welcome. Useful issue reports should include:

- Checkmk edition and exact version
- Semaphore UI version
- Plug-in version
- Output of `cmk-validate-plugins`
- Relevant `cmk --debug` error text with credentials removed
- A sanitized `<<<semaphore_jobs:sep(0)>>>` section when the issue concerns parsing or counters

## Author

**Christian Wirtz**  
Email: **doc[at]snowheaven.de**

## License

This project is licensed under the [MIT License](LICENSE).

## References

- [Checkmk extension packages](https://docs.checkmk.com/latest/en/mkps.html)
- [Checkmk special-agent development](https://docs.checkmk.com/latest/en/devel_special_agents.html)
- [Semaphore UI API documentation](https://semaphoreui.com/docs/admin-guide/api)
