from __future__ import annotations

from collections.abc import Callable

from nexusops_agent.contracts.state import WorkflowState


class BoundedReworkController:
    def apply_once(self, state: WorkflowState, action: Callable[[], None]) -> bool:
        if state.rework_count >= 1:
            return False
        state.rework_count += 1
        action()
        return True
