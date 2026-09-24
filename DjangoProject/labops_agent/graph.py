from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class AgentGraphState(TypedDict, total=False):
    actor: Any
    question: str
    history: list
    conversation: Any
    input_items: list
    instructions: str
    response: dict
    calls: list
    round_index: int
    traces: list
    actions: list
    domains: set
    answer: str
    domain: str
    request_id: str
    evidence: list
    retrieval: dict


class LabOpsAgentGraph:
    """Bounded LangGraph workflow around the existing provider and tools."""

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        builder = StateGraph(AgentGraphState)
        builder.add_node("prepare_context", orchestrator.graph_prepare_context)
        builder.add_node("retrieve_knowledge", orchestrator.graph_retrieve_knowledge)
        builder.add_node("call_model", orchestrator.graph_call_model)
        builder.add_node("execute_tools", orchestrator.graph_execute_tools)
        builder.add_node("finalize", orchestrator.graph_finalize)
        builder.add_edge(START, "prepare_context")
        builder.add_edge("prepare_context", "retrieve_knowledge")
        builder.add_edge("retrieve_knowledge", "call_model")
        builder.add_conditional_edges(
            "call_model",
            self._route_model_output,
            {"tools": "execute_tools", "answer": "finalize"},
        )
        builder.add_edge("execute_tools", "call_model")
        builder.add_edge("finalize", END)
        self.compiled = builder.compile()

    @staticmethod
    def _route_model_output(state):
        return "tools" if state.get("calls") else "answer"

    def invoke(self, initial_state):
        recursion_limit = (self.orchestrator.config.max_tool_rounds * 2) + 6
        return self.compiled.invoke(
            initial_state,
            config={"recursion_limit": recursion_limit},
        )

    @property
    def node_names(self):
        return set(self.compiled.get_graph().nodes)
