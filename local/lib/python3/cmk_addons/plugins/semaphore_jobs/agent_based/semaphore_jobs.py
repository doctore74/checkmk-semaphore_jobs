#!/usr/bin/env python3
"""Check plug-in for Semaphore UI task/job states."""


from __future__ import annotations

__author__ = "Christian Wirtz"
__contact__ = "doc[at]snowheaven.de"
__version__ = "1.2.0"

import itertools
import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State,
    render,
)

DEFAULT_PARAMETERS = {
    "waiting_count": ("fixed", (3, 10)),
    "waiting_age": ("fixed", (300.0, 1800.0)),
    "running_age": ("fixed", (3600.0, 7200.0)),
    "starting_age": ("fixed", (120.0, 600.0)),
    "stopping_age": ("fixed", (120.0, 600.0)),
    "confirmed_age": ("fixed", (120.0, 600.0)),
    "confirmation_age": ("fixed", (86400.0, 604800.0)),
    "recent_errors": ("fixed", (1, 5)),
    "unknown_statuses": ("fixed", (1, 5)),
    "invalid_timestamps": ("fixed", (1, 5)),
    "truncated_projects": ("fixed", (1, 2)),
}


def parse_semaphore_jobs(string_table):
    raw = "".join(itertools.chain.from_iterable(string_table))
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        return {"error": f"Invalid special-agent output: {exc}"}
    if not isinstance(parsed, dict):
        return {"error": "Special-agent output is not a JSON object"}
    return parsed


def discover_semaphore_jobs(section):
    yield Service()


def _fixed_levels(levels: Any) -> tuple[float, float] | None:
    if (
        isinstance(levels, tuple)
        and len(levels) == 2
        and levels[0] == "fixed"
        and isinstance(levels[1], tuple)
        and len(levels[1]) == 2
    ):
        return float(levels[1][0]), float(levels[1][1])
    return None


def _upper_state(value: float, levels: Any) -> State:
    fixed = _fixed_levels(levels)
    if fixed is None:
        return State.OK
    warn, crit = fixed
    if value >= crit:
        return State.CRIT
    if value >= warn:
        return State.WARN
    return State.OK


def _metric_levels(levels: Any) -> tuple[float, float] | None:
    return _fixed_levels(levels)


def _evaluate(
    *,
    value: int | float,
    levels: Any,
    metric_name: str,
    label: str,
    renderer,
):
    state = _upper_state(float(value), levels)
    fixed = _metric_levels(levels)
    yield Metric(
        name=metric_name,
        value=float(value),
        levels=fixed,
        boundaries=(0.0, None),
    )
    text = f"{label}: {renderer(value)}"
    if state is State.OK:
        yield Result(state=State.OK, notice=text)
    else:
        yield Result(state=state, summary=text)


def _count(value: int | float) -> str:
    return str(int(value))


def _duration(value: int | float) -> str:
    return "-" if value <= 0 else render.timespan(float(value))


def _dict(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def check_semaphore_jobs(params, section):
    if error := section.get("error"):
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    totals = _dict(section.get("totals"))
    counts = _dict(totals.get("counts"))
    ages = _dict(totals.get("oldest_ages"))
    recent = _dict(totals.get("recent"))

    project_count = int(section.get("project_count", 0) or 0)
    active = int(totals.get("active", 0) or 0)
    running = int(counts.get("running", 0) or 0)
    waiting = int(counts.get("waiting", 0) or 0)
    starting = int(counts.get("starting", 0) or 0)
    confirmation = int(counts.get("waiting_confirmation", 0) or 0)
    stopping = int(counts.get("stopping", 0) or 0)
    lookback = int(section.get("lookback_hours", 24) or 24)

    yield Result(
        state=State.OK,
        summary=(
            f"Projects: {project_count}, active: {active}, running: {running}, "
            f"waiting: {waiting}, starting: {starting}, confirmation: {confirmation}, "
            f"stopping: {stopping}"
        ),
    )

    for status in (
        "running",
        "starting",
        "waiting_confirmation",
        "confirmed",
        "rejected",
        "stopping",
    ):
        yield Metric(
            name=f"semaphore_{status}_jobs",
            value=float(counts.get(status, 0) or 0),
            boundaries=(0.0, None),
        )
    yield Metric(
        name="semaphore_success_recent_jobs",
        value=float(recent.get("success", 0) or 0),
        boundaries=(0.0, None),
    )
    yield Metric(
        name="semaphore_stopped_recent_jobs",
        value=float(recent.get("stopped", 0) or 0),
        boundaries=(0.0, None),
    )
    yield Metric(name="semaphore_active_jobs", value=float(active), boundaries=(0.0, None))

    yield from _evaluate(
        value=waiting,
        levels=params["waiting_count"],
        metric_name="semaphore_waiting_jobs",
        label="Waiting jobs",
        renderer=_count,
    )

    age_checks = (
        ("waiting", "waiting_age", "Oldest waiting job"),
        ("running", "running_age", "Oldest running job"),
        ("starting", "starting_age", "Oldest starting job"),
        ("stopping", "stopping_age", "Oldest stopping job"),
        ("confirmed", "confirmed_age", "Oldest confirmed job"),
        (
            "waiting_confirmation",
            "confirmation_age",
            "Oldest job waiting for confirmation",
        ),
    )
    for status, parameter, label in age_checks:
        yield from _evaluate(
            value=int(ages.get(status, 0) or 0),
            levels=params[parameter],
            metric_name=f"semaphore_oldest_{status}_seconds",
            label=label,
            renderer=_duration,
        )

    yield from _evaluate(
        value=int(recent.get("error", 0) or 0),
        levels=params["recent_errors"],
        metric_name="semaphore_error_recent_jobs",
        label=f"Failed jobs in last {lookback} hours",
        renderer=_count,
    )
    yield from _evaluate(
        value=int(totals.get("unknown_count", 0) or 0),
        levels=params["unknown_statuses"],
        metric_name="semaphore_unknown_status_jobs",
        label="Jobs with unknown status",
        renderer=_count,
    )
    yield from _evaluate(
        value=int(totals.get("invalid_timestamps", 0) or 0),
        levels=params["invalid_timestamps"],
        metric_name="semaphore_invalid_timestamp_jobs",
        label="Jobs with invalid timestamps",
        renderer=_count,
    )
    truncated_count = int(totals.get("truncated_projects", 0) or 0)
    truncated_state = _upper_state(
        float(truncated_count), params["truncated_projects"]
    )
    yield Metric(
        name="semaphore_truncated_projects",
        value=float(truncated_count),
        levels=_metric_levels(params["truncated_projects"]),
        boundaries=(0.0, None),
    )

    projects = section.get("projects")
    project_list = projects if isinstance(projects, list) else []
    truncated_projects = [
        project
        for project in project_list
        if isinstance(project, dict) and bool(project.get("truncated"))
    ]
    if truncated_count > 0:
        task_list_limit = int(section.get("task_list_limit", 1000) or 1000)
        affected_lines = []
        for project in truncated_projects:
            project_id = project.get("id", "?")
            project_name = project.get("name", f"Project {project_id}")
            returned = int(project.get("task_count", 0) or 0)
            limit = int(project.get("task_limit", task_list_limit) or task_list_limit)
            context = [
                f"{project_name} (ID {project_id}): {returned:,} tasks returned",
                f"API limit {limit:,}",
            ]

            identifier_range = _dict(project.get("returned_id_range"))
            minimum_id = identifier_range.get("minimum")
            maximum_id = identifier_range.get("maximum")
            if minimum_id is not None and maximum_id is not None:
                context.append(f"returned task IDs {minimum_id}-{maximum_id}")

            time_range = _dict(project.get("returned_time_range"))
            oldest = time_range.get("oldest")
            newest = time_range.get("newest")
            if oldest and newest:
                context.append(f"returned time range {oldest} to {newest}")

            affected_lines.append("; ".join(context))

        details = (
            "Semaphore limits GET /api/project/{project_id}/tasks to "
            f"{task_list_limit} records. Older task history is not available to "
            "this check, so all counters for the affected projects are calculated "
            "only from the records returned by the API."
        )
        if affected_lines:
            details += "\nAffected projects:\n- " + "\n- ".join(affected_lines)

        project_word = "project" if truncated_count == 1 else "projects"
        yield Result(
            state=truncated_state,
            notice=(
                f"Task history possibly incomplete: "
                f"{truncated_count} {project_word}"
            ),
            details=details,
        )

    unknown = _dict(totals.get("unknown_statuses"))
    if unknown:
        yield Result(
            state=State.OK,
            notice="Unknown status details: "
            + ", ".join(f"{name}={count}" for name, count in sorted(unknown.items())),
        )

    for project in project_list:
        if not isinstance(project, dict):
            continue
        project_counts = _dict(project.get("counts"))
        project_name = project.get("name", project.get("id", "?"))
        project_text = (
            f"{project_name}: "
            f"running={project_counts.get('running', 0)}, "
            f"waiting={project_counts.get('waiting', 0)}, "
            f"error({lookback}h)={_dict(project.get('recent')).get('error', 0)}"
        )
        if bool(project.get("truncated")):
            limit = int(
                project.get(
                    "task_limit", section.get("task_list_limit", 1000)
                )
                or 1000
            )
            project_text += f", history limited to {limit:,} tasks"
        yield Result(state=State.OK, notice=project_text)


agent_section_semaphore_jobs = AgentSection(
    name="semaphore_jobs",
    parse_function=parse_semaphore_jobs,
)

check_plugin_semaphore_jobs = CheckPlugin(
    name="semaphore_jobs",
    service_name="Semaphore Jobs",
    discovery_function=discover_semaphore_jobs,
    check_function=check_semaphore_jobs,
    check_default_parameters=DEFAULT_PARAMETERS,
    check_ruleset_name="semaphore_jobs",
)
