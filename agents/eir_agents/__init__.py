"""EIR agent fleet.

Agents must not import FastAPI or frontend code. Testable logic lives in
handler.py / descriptor.py; agent.py is the ADK `root_agent` wrapper.
"""

from eir_shared.env import load_root_env

load_root_env()
