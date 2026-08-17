"""Agent invocation adapter.

HTTP routes never contain agent prompts. This package is the local composition
root that binds the event bus to capability-based handlers.

TODO: AgentRuntimeAdapter invoking registered agents on Agent Runtime / Gateway.
"""

from app.integrations.agents.runtime import WorkflowRuntime

__all__ = ["WorkflowRuntime"]
