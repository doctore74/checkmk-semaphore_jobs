#!/usr/bin/env python3
"""Threshold rule for the Semaphore UI jobs service."""

__author__ = "Christian Wirtz"
__contact__ = "doc[at]snowheaven.de"
__version__ = "1.2.0"

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _count_levels(title: str, warn: int, crit: int, help_text: str = ""):
    arguments = {
        "title": Title(title),
        "form_spec_template": Integer(),
        "level_direction": LevelDirection.UPPER,
        "prefill_fixed_levels": DefaultValue(value=(warn, crit)),
    }
    if help_text:
        arguments["help_text"] = Help(help_text)
    return DictElement(
        required=True,
        parameter_form=SimpleLevels(**arguments),
    )


def _age_levels(title: str, warn: int, crit: int, help_text: str = ""):
    arguments = {
        "title": Title(title),
        "form_spec_template": TimeSpan(
            displayed_magnitudes=[
                TimeMagnitude.MINUTE,
                TimeMagnitude.HOUR,
                TimeMagnitude.DAY,
            ]
        ),
        "level_direction": LevelDirection.UPPER,
        "prefill_fixed_levels": DefaultValue(value=(float(warn), float(crit))),
    }
    if help_text:
        arguments["help_text"] = Help(help_text)
    return DictElement(
        required=True,
        parameter_form=SimpleLevels(**arguments),
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Semaphore UI job thresholds"),
        elements={
            "waiting_count": _count_levels(
                "Number of waiting jobs",
                3,
                10,
                "A small queue is normal; alert only when the queue accumulates.",
            ),
            "waiting_age": _age_levels("Age of oldest waiting job", 300, 1800),
            "running_age": _age_levels(
                "Age of oldest running job",
                3600,
                7200,
                "Adjust this to the expected maximum runtime of your automation.",
            ),
            "starting_age": _age_levels("Age of oldest starting job", 120, 600),
            "stopping_age": _age_levels("Age of oldest stopping job", 120, 600),
            "confirmed_age": _age_levels("Age of oldest confirmed job", 120, 600),
            "confirmation_age": _age_levels(
                "Age of oldest job waiting for confirmation", 86400, 604800
            ),
            "recent_errors": _count_levels(
                "Failed jobs within the configured lookback",
                1,
                5,
                "The lookback is configured in the Semaphore UI special-agent rule.",
            ),
            "unknown_statuses": _count_levels(
                "Jobs with an unknown status", 1, 5
            ),
            "invalid_timestamps": _count_levels(
                "Jobs with invalid or missing timestamps", 1, 5
            ),
            "truncated_projects": _count_levels(
                "Projects at the Semaphore task-list API limit", 1, 2,
                "Semaphore currently limits this endpoint to 1,000 tasks. The service details name every affected project and show the returned data range.",
            ),
        },
    )


rule_spec_semaphore_jobs_parameters = CheckParameters(
    name="semaphore_jobs",
    title=Title("Semaphore UI jobs"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
    condition=HostCondition(),
)
