#!/usr/bin/env python3
"""Command-line mapping for the Semaphore UI jobs special agent."""

__author__ = "Christian Wirtz"
__contact__ = "doc[at]snowheaven.de"
__version__ = "1.2.0"

from cmk.server_side_calls.v1 import SpecialAgentCommand, SpecialAgentConfig, noop_parser


def _agent_arguments(params, host_config):
    arguments = [
        "--url",
        str(params["url"]),
        "--token",
        params["api_token"].unsafe(),
        "--projects",
        str(params.get("project_ids", "all")),
        "--timeout",
        str(params.get("timeout", 30)),
        "--lookback-hours",
        str(params.get("lookback_hours", 24)),
    ]
    if not params.get("verify_tls", True):
        arguments.append("--no-verify-tls")
    yield SpecialAgentCommand(command_arguments=arguments)


special_agent_semaphore_jobs = SpecialAgentConfig(
    name="semaphore_jobs",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
