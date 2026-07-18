from __future__ import annotations

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.state import WorkflowState
from nexusops_agent.orchestration.router import route_case

from .runner import AgentWorkflowRunner


def langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401
    except ImportError:
        return False
    return True


def build_langgraph_for_case(runner: AgentWorkflowRunner, case: CaseContext):
    """Compile the case-specific sparse route into a LangGraph StateGraph."""
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("Install the optional 'ai' dependencies to enable LangGraph") from exc

    graph = StateGraph(dict)
    route = route_case(case).nodes

    for node_id in route:
        def execute(envelope: dict, current_node: str = node_id) -> dict:
            state_value = envelope.get("workflow_state")
            state = state_value if isinstance(state_value, WorkflowState) else WorkflowState.model_validate(state_value)
            runner.execute_node(state, current_node)
            return {"workflow_state": state}

        graph.add_node(node_id, execute)

    graph.add_edge(START, route[0])
    for previous, current in zip(route, route[1:]):
        graph.add_edge(previous, current)
    graph.add_edge(route[-1], END)
    return graph.compile()
