#!/usr/bin/env python3
"""Setup rule for the Semaphore UI jobs special agent."""

__author__ = "Christian Wirtz"
__contact__ = "doc[at]snowheaven.de"
__version__ = "1.2.0"

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    Password,
    String,
    migrate_to_password,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Semaphore UI jobs"),
        help_text=Help(
            "Query the Semaphore UI API and monitor current job states, job ages, "
            "and recently completed jobs."
        ),
        elements={
            "url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Semaphore base URL"),
                    help_text=Help("For example: https://semaphore.example.com"),
                ),
            ),
            "api_token": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("API token"),
                    help_text=Help(
                        "A Semaphore API token with read access to the monitored projects."
                    ),
                    migrate=migrate_to_password,
                ),
            ),
            "project_ids": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Project IDs"),
                    help_text=Help(
                        "Enter 'all' or a comma-separated list such as 1,3,7."
                    ),
                    prefill=DefaultValue("all"),
                ),
            ),
            "verify_tls": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("TLS certificate verification"),
                    label=Label("Verify the Semaphore server certificate"),
                    prefill=DefaultValue(True),
                ),
            ),
            "timeout": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("HTTP timeout"),
                    help_text=Help("Maximum duration of each API request in seconds."),
                    prefill=DefaultValue(30),
                ),
            ),
            "lookback_hours": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Completed-job lookback"),
                    help_text=Help(
                        "Count successful, failed, and stopped jobs completed within this many hours."
                    ),
                    prefill=DefaultValue(24),
                ),
            ),
        },
    )


rule_spec_semaphore_jobs = SpecialAgent(
    topic=Topic.CONFIGURATION_DEPLOYMENT,
    name="semaphore_jobs",
    title=Title("Semaphore UI jobs"),
    parameter_form=_parameter_form,
)
