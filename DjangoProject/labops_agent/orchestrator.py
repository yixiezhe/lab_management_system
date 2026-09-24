import json
import logging
import time
import uuid
from dataclasses import dataclass

from equipment.time_control import get_controlled_today

from .exceptions import ToolProtocolError
from .llm.client import ResponsesClient
from .llm.prompts import SYSTEM_INSTRUCTIONS
from .rag import KnowledgeRetriever
from .services import (
    ConversationStateService,
    EquipmentContextService,
    ProcurementContextService,
)
from .tools import TOOL_DEFINITIONS, ToolRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentResult:
    answer: str
    domain: str
    tools: list
    request_id: str
    actions: list
    conversation_id: str = ""
    evidence: list = None
    retrieval: dict = None


class AgentOrchestrator:
    MAX_CALLS_PER_ROUND = 4

    def __init__(
        self,
        config,
        *,
        client=None,
        registry=None,
        tools=None,
        context_service=None,
        equipment_context_service=None,
        conversation_service=None,
        knowledge_retriever=None,
    ):
        self.config = config
        self.client = client or ResponsesClient(config)
        self.registry = registry or ToolRegistry()
        self.tools = tools if tools is not None else TOOL_DEFINITIONS
        self.context_service = context_service or ProcurementContextService()
        self.equipment_context_service = equipment_context_service or EquipmentContextService()
        self.conversation_service = conversation_service or ConversationStateService()
        self.knowledge_retriever = knowledge_retriever or KnowledgeRetriever()
        self._graph = None

    def run(self, actor, question, history=None, conversation_id=None):
        request_id = f"agt_{uuid.uuid4().hex[:16]}"
        started_at = time.monotonic()
        conversation = self.conversation_service.load_or_create(actor, conversation_id)
        initial_state = {
            "actor": actor,
            "question": question,
            "history": list(history or [])[-8:],
            "conversation": conversation,
            "round_index": 0,
            "traces": [],
            "actions": [],
            "domains": set(),
            "request_id": request_id,
            "evidence": [],
            "retrieval": {"route": "none", "status": "not_run", "evidence_count": 0},
        }
        try:
            if self.config.use_langgraph:
                state = self._get_graph().invoke(initial_state)
            else:
                state = self._run_legacy(initial_state)
            result = self._result_from_state(state, request_id, conversation)
            self._log_completion(request_id, result.tools, started_at, "success")
            return result
        except Exception:
            self._log_completion(request_id, initial_state["traces"], started_at, "error")
            raise

    def _get_graph(self):
        if self._graph is None:
            from .graph import LabOpsAgentGraph

            self._graph = LabOpsAgentGraph(self)
        return self._graph

    def graph_prepare_context(self, state):
        input_items = list(state.get("history") or [])[-8:]
        input_items.append({"role": "user", "content": state["question"]})
        instructions = (
            f"{SYSTEM_INSTRUCTIONS}\n"
            f"系统当前日期：{get_controlled_today().isoformat()}。"
        )

        saved_state = self.conversation_service.context_for_model(state["conversation"])
        if saved_state:
            instructions += (
                "\n以下是服务器为当前用户、当前会话保存的已解析业务字段。"
                "新消息明确修改某字段时覆盖旧值，其余字段可以继承；仍须调用工具校验：\n"
                + self._compact_json(saved_state)
            )
        procurement_context = self.context_service.prefetch(state["question"])
        if procurement_context:
            instructions += (
                "\n以下是后端在调用模型前检索到的采购上下文。只可作为候选信息，"
                "最终结果以工具校验为准：\n"
                + self._compact_json(procurement_context)
            )
        equipment_context = self.equipment_context_service.prefetch(
            state["question"], state["actor"]
        )
        if equipment_context:
            instructions += (
                "\n以下是后端从当前可见仪器中解析出的候选信息。"
                "口语中的序号可能是通道号，不得擅自拼入仪器名称：\n"
                + self._compact_json(equipment_context)
            )
        return {"input_items": input_items, "instructions": instructions}

    def graph_call_model(self, state):
        allow_tools = state["round_index"] < self.config.max_tool_rounds
        response = self.client.create(
            input_items=state["input_items"],
            tools=self.tools,
            tool_choice="auto" if allow_tools else "none",
            instructions=state["instructions"],
        )
        return {"response": response, "calls": self._extract_calls(response)}

    def graph_retrieve_knowledge(self, state):
        result = self.knowledge_retriever.retrieve(
            state["question"],
            actor=state["actor"],
            request_id=state.get("request_id", ""),
        )
        instructions = state["instructions"]
        prompt_context = result.prompt_context()
        if prompt_context:
            instructions += "\n\n" + prompt_context
        elif result.status in {"no_evidence", "unavailable"}:
            instructions += (
                "\n知识检索没有返回可靠依据。若用户询问制度、SOP、安全参数或注意事项，"
                "必须明确说明依据不足，不得使用常识补全；实时业务工具仍可正常使用。"
            )
        evidence = result.public_evidence()
        domains = set(state.get("domains") or set())
        if evidence:
            domains.update(self.knowledge_retriever.route_domains(state["question"]))
        return {
            "instructions": instructions,
            "evidence": evidence,
            "retrieval": {
                "route": result.route,
                "status": result.status,
                "evidence_count": len(evidence),
                "failure_kind": result.failure_kind,
            },
            "domains": domains,
        }

    def graph_execute_tools(self, state):
        if state["round_index"] >= self.config.max_tool_rounds:
            raise ToolProtocolError("模型超过了允许的工具调用轮次。")
        calls = state.get("calls") or []
        if len(calls) > self.MAX_CALLS_PER_ROUND:
            raise ToolProtocolError("模型单轮调用了过多工具。")

        input_items = list(state["input_items"])
        traces = list(state["traces"])
        actions = list(state["actions"])
        domains = set(state["domains"])
        for call in calls:
            result, arguments = self._execute_call(call, state["actor"], input_items)
            traces.append(result.trace())
            domains.add(result.domain)
            action = result.action()
            if action and not any(item.get("id") == action.get("id") for item in actions):
                actions.append(action)
            self.conversation_service.remember_tool_result(
                state["conversation"], result.name, arguments, result
            )
        return {
            "input_items": input_items,
            "traces": traces,
            "actions": actions,
            "domains": domains,
            "round_index": state["round_index"] + 1,
        }

    def graph_finalize(self, state):
        answer = self._extract_answer(state["response"])
        if not answer:
            raise ToolProtocolError("模型没有返回可展示的回答。")
        return {"answer": answer, "domain": self._resolve_domain(state["domains"])}

    def _run_legacy(self, state):
        state.update(self.graph_prepare_context(state))
        state.update(self.graph_retrieve_knowledge(state))
        for _ in range(self.config.max_tool_rounds + 1):
            state.update(self.graph_call_model(state))
            if state["calls"]:
                state.update(self.graph_execute_tools(state))
                continue
            state.update(self.graph_finalize(state))
            return state
        raise ToolProtocolError("智能查询流程未正常结束。")

    def _execute_call(self, call, actor, input_items):
        name = call.get("name")
        call_id = call.get("call_id")
        raw_arguments = call.get("arguments", "{}")
        if not name or not call_id:
            raise ToolProtocolError("模型返回了不完整的工具调用。")
        if isinstance(raw_arguments, dict):
            arguments = raw_arguments
            raw_arguments = self._compact_json(arguments)
        else:
            try:
                arguments = json.loads(raw_arguments)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ToolProtocolError("模型返回了无效的工具参数。") from exc
        if not isinstance(arguments, dict):
            raise ToolProtocolError("工具参数必须是 JSON 对象。")

        result = self.registry.execute(name, arguments, actor)
        input_items.extend(
            [
                {
                    "type": "function_call",
                    "name": name,
                    "arguments": raw_arguments,
                    "call_id": call_id,
                },
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": self._compact_json(result.for_model()),
                },
            ]
        )
        return result, arguments

    @staticmethod
    def _extract_calls(response):
        output = response.get("output")
        if not isinstance(output, list):
            raise ToolProtocolError("模型响应缺少 output 列表。")
        return [item for item in output if item.get("type") == "function_call"]

    @staticmethod
    def _extract_answer(response):
        if isinstance(response.get("output_text"), str):
            return response["output_text"].strip()
        parts = []
        for item in response.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content") or []:
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(content["text"])
        return "\n".join(parts).strip()

    @staticmethod
    def _resolve_domain(domains):
        business_domains = set(domains) & {"procurement", "equipment"}
        if len(business_domains) == 1:
            return next(iter(business_domains))
        if len(business_domains) > 1:
            return "mixed"
        return "general"

    @staticmethod
    def _compact_json(value):
        return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))

    @staticmethod
    def _result_from_state(state, request_id, conversation):
        return AgentResult(
            answer=state["answer"],
            domain=state["domain"],
            tools=state["traces"],
            request_id=request_id,
            actions=state["actions"],
            conversation_id=str(conversation.id),
            evidence=list(state.get("evidence") or []),
            retrieval=dict(state.get("retrieval") or {}),
        )

    @staticmethod
    def _log_completion(request_id, traces, started_at, status):
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        logger.info(
            "labops_agent request_id=%s status=%s tools=%s elapsed_ms=%s",
            request_id,
            status,
            len(traces),
            elapsed_ms,
        )
