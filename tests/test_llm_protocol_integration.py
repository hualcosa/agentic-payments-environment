"""Offline end-to-end LLM protocol regressions. REQ-ENV-17, REQ-ENV-18."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentic_payments_env.adapters.anthropic import AnthropicChatModel
from agentic_payments_env.adapters.base import ChatModel, Usage
from agentic_payments_env.adapters.openai_compat import OpenAICompatChatModel
from agentic_payments_env.agents.llm import LLMAgent, LLMAgentProtocolError
from agentic_payments_env.benchmark.runner import _drive, run_benchmark
from agentic_payments_env.benchmark.v0 import load_task
from agentic_payments_env.cli import main
from agentic_payments_env.contracts.common import TerminationReason
from agentic_payments_env.contracts.trace import EpisodeTrace
from agentic_payments_env.environment import PaymentsEnvironment
from agentic_payments_env.graders import grade_episode
from agentic_payments_env.replay import replay
from tests.conftest import default_task

Provider = str
Arguments = dict[str, object] | Callable[[dict[str, object]], dict[str, object]]


def _call(call_id: object, name: str, arguments: Arguments) -> dict[str, object]:
    return {"id": call_id, "name": name, "arguments": arguments}


def _turn(
    *calls: dict[str, object],
    text: str = "",
    input_tokens: int = 5,
    output_tokens: int = 3,
) -> dict[str, object]:
    return {
        "calls": list(calls),
        "text": text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


class _RecordingTransport:
    """Provider-shaped scripted transport that never performs HTTP."""

    def __init__(self, provider: Provider, turns: list[dict[str, object]]) -> None:
        self.provider = provider
        self.turns = list(turns)
        self.requests: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        request = deepcopy(kwargs)
        self.requests.append(request)
        if not self.turns:
            raise AssertionError("provider received an unexpected request")
        turn = self.turns.pop(0)
        raw_calls = turn["calls"]
        assert isinstance(raw_calls, list)
        calls: list[dict[str, object]] = []
        for raw_call in raw_calls:
            assert isinstance(raw_call, dict)
            arguments = raw_call["arguments"]
            if callable(arguments):
                arguments = arguments(request)
            assert isinstance(arguments, dict)
            calls.append({**raw_call, "arguments": arguments})
        if self.provider == "openai":
            tool_calls = [
                SimpleNamespace(
                    id=call["id"],
                    function=SimpleNamespace(
                        name=call["name"], arguments=json.dumps(call["arguments"])
                    ),
                )
                for call in calls
            ]
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=turn["text"], tool_calls=tool_calls)
                    )
                ],
                usage=SimpleNamespace(
                    prompt_tokens=turn["input_tokens"],
                    completion_tokens=turn["output_tokens"],
                ),
            )
        blocks = []
        if turn["text"]:
            blocks.append(SimpleNamespace(type="text", text=turn["text"]))
        blocks.extend(
            SimpleNamespace(
                type="tool_use",
                id=call["id"],
                name=call["name"],
                input=call["arguments"],
            )
            for call in calls
        )
        return SimpleNamespace(
            content=blocks,
            usage=SimpleNamespace(
                input_tokens=turn["input_tokens"], output_tokens=turn["output_tokens"]
            ),
        )


def _provider_model(
    provider: Provider, turns: list[dict[str, object]]
) -> tuple[ChatModel, _RecordingTransport]:
    transport = _RecordingTransport(provider, turns)
    if provider == "openai":
        model = object.__new__(OpenAICompatChatModel)
        model.model_id = "offline-openai"
        model._client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=transport.create))
        )
        model._sleep = lambda _seconds: None
        return model, transport
    model = object.__new__(AnthropicChatModel)
    model.model_id = "offline-anthropic"
    model._client = SimpleNamespace(messages=SimpleNamespace(create=transport.create))
    model._sleep = lambda _seconds: None
    return model, transport


def _last_tool_payload(provider: Provider, request: dict[str, object]) -> dict[str, object]:
    messages = request["messages"]
    assert isinstance(messages, list)
    if provider == "openai":
        for message in reversed(messages):
            if message.get("role") == "tool":
                return json.loads(message["content"])
    else:
        for message in reversed(messages):
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if block.get("type") == "tool_result":
                    return json.loads(block["content"])
    raise AssertionError("request has no tool result")


def _consented_transfer_arguments(
    provider: Provider,
) -> Callable[[dict[str, object]], dict[str, object]]:
    def resolve(request: dict[str, object]) -> dict[str, object]:
        messages = request["messages"]
        assert isinstance(messages, list)
        consent_id: object | None = None
        for index in range(len(messages)):
            prefix = {**request, "messages": messages[: index + 1]}
            try:
                payload = _last_tool_payload(provider, prefix)
            except AssertionError:
                continue
            result = payload.get("result")
            if isinstance(result, dict) and "consent_id" in result:
                consent_id = result["consent_id"]
        assert consent_id is not None
        return {
            "from_account_id": "acc_ana",
            "pix_key": "maria.oliveira@example.com",
            "amount_centavos": 25000,
            "idempotency_key": "llm-protocol-idem-1",
            "consent_id": consent_id,
        }

    return resolve


def _payment_turns(provider: Provider, *, recovery: str | None = None) -> list[dict[str, object]]:
    turns = [
        _turn(_call("c1", "list_beneficiaries", {})),
        _turn(
            _call(
                "c2",
                "lookup_pix_key",
                {"pix_key": "maria.oliveira@example.com"},
            )
        ),
        _turn(
            _call(
                "c3",
                "request_consent",
                {
                    "from_account_id": "acc_ana",
                    "pix_key": "maria.oliveira@example.com",
                    "amount_centavos": 25000,
                    "description": "PIX R$250,00 to Maria Oliveira",
                },
            )
        ),
        _turn(_call("c4", "create_transfer", _consented_transfer_arguments(provider))),
    ]
    if recovery is not None:
        turns.append(
            _turn(
                _call(
                    "c5",
                    "get_transfer_by_idempotency_key",
                    {"idempotency_key": "llm-protocol-idem-1"},
                )
            )
        )
    if recovery == "before":
        turns.append(_turn(_call("c6", "create_transfer", _consented_transfer_arguments(provider))))
    finish_id = f"c{len(turns) + 1}"
    turns.append(
        _turn(
            _call(
                finish_id,
                "finish",
                {
                    "outcome": "COMPLETED",
                    "report": "Sent R$250,00 to Maria Oliveira. Transfer id: tx_000001.",
                },
            )
        )
    )
    return turns


def _tool_results(provider: Provider, request: dict[str, object]) -> list[tuple[str, str]]:
    messages = request["messages"]
    assert isinstance(messages, list)
    if provider == "openai":
        return [
            (str(message["tool_call_id"]), str(message["content"]))
            for message in messages
            if message.get("role") == "tool"
        ]
    results: list[tuple[str, str]] = []
    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_result":
                results.append((str(block["tool_use_id"]), str(block["content"])))
    return results


def _assert_observation_bodies(
    provider: Provider, transport: _RecordingTransport, trace: EpisodeTrace
) -> None:
    """Check actual observations, not only correlation IDs. REQ-ENV-18."""
    for index, request in enumerate(transport.requests):
        results = _tool_results(provider, request)
        assert len(results) == index
        for (_call_id, content), step in zip(results, trace.steps[:index], strict=True):
            expected = {
                key: value
                for key, value in step.observation.model_dump(mode="json").items()
                if value is not None
            }
            assert json.loads(content) == expected


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
@pytest.mark.parametrize("after_valid_step", [False, True])
def test_rejected_batch_is_atomic_and_partial_trace_replays(
    provider: Provider, after_valid_step: bool
) -> None:
    turns: list[dict[str, object]] = []
    if after_valid_step:
        turns.append(_turn(_call("prior", "get_customer_profile", {})))
    mutating_call = _call(
        "mutate",
        "create_transfer",
        {
            "from_account_id": "acc_ana",
            "pix_key": "maria.oliveira@example.com",
            "amount_centavos": 25000,
        },
    )
    finish_call = _call("finish", "finish", {"outcome": "DECLINED", "report": "stop"})
    rejected_calls = (
        (finish_call, mutating_call) if after_valid_step else (mutating_call, finish_call)
    )
    turns.append(_turn(*rejected_calls, input_tokens=13, output_tokens=8))
    model, transport = _provider_model(provider, turns)
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    task = default_task()
    env, trace = _drive(task, agent, 0)

    reference = PaymentsEnvironment(task, 0)
    reference.reset()
    if after_valid_step:
        reference.step(trace.steps[0].action)
    assert trace.termination == TerminationReason.AGENT_ERROR
    assert len(trace.steps) == int(after_valid_step)
    assert env.state_hash() == reference.state_hash()
    assert trace.audit == reference.trace().audit
    assert list(env.state.transfers) == []
    assert len(env.state.ledger) == len(reference.state.ledger)
    assert agent.usage_log[-1] == Usage(input_tokens=13, output_tokens=8)
    assert replay(task, trace).matches is True
    assert len(transport.requests) == 1 + int(after_valid_step)
    assert agent.protocol_error == "LLM_PROTOCOL_MULTIPLE_TOOL_CALLS count=2"


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_protocol_error_is_stable_before_runner_converts_it(provider: Provider) -> None:
    model, _transport = _provider_model(
        provider,
        [
            _turn(
                _call("a", "get_customer_profile", {}),
                _call("b", "finish", {"outcome": "DECLINED", "report": "stop"}),
            )
        ],
    )
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    task = default_task()
    env = PaymentsEnvironment(task)
    observation = env.reset()
    agent.reset(task.public, observation)
    with pytest.raises(LLMAgentProtocolError, match=r"^LLM_PROTOCOL_MULTIPLE_TOOL_CALLS count=2$"):
        agent.act([], observation)


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_invalid_id_artifacts_retain_usage_without_a_fake_step(
    provider: Provider, tmp_path: Path
) -> None:
    created: list[LLMAgent] = []

    def factory(_task: object) -> LLMAgent:
        model, _transport = _provider_model(
            provider,
            [_turn(_call(None, "get_customer_profile", {}), input_tokens=17, output_tokens=9)],
        )
        agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
        created.append(agent)
        return agent

    out = tmp_path / provider
    run_benchmark(
        [default_task()],
        factory,
        [0],
        out_dir=out,
        meta={"provider": provider},
    )
    trace_path = out / "v0_test-default" / "seed-0.trace.json"
    trace = EpisodeTrace.model_validate_json(trace_path.read_text(encoding="utf-8"))
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert trace.termination == TerminationReason.AGENT_ERROR
    assert trace.steps == []
    assert meta["episodes"][0]["steps"] == [
        {"latency_ms": 0, "usage": {"input_tokens": 17, "output_tokens": 9}}
    ]
    assert meta["episodes"][0]["protocol_error"] == (
        "LLM_PROTOCOL_INVALID_TOOL_CALL_ID type=NoneType"
    )
    assert created[0].usage_log == [Usage(input_tokens=17, output_tokens=9)]


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_successful_payment_keeps_one_correlated_result_per_call(provider: Provider) -> None:
    task = load_task("v0/rt-001")
    model, transport = _provider_model(provider, _payment_turns(provider))
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    env, trace = _drive(task, agent, 0)

    assert trace.termination == TerminationReason.FINISHED
    assert len(env.state.transfers) == 1
    assert env.state.transfers["tx_000001"].idempotency_key == "llm-protocol-idem-1"
    assert grade_episode(task, trace, env.state).safe_success is True
    assert replay(task, trace).matches is True
    for index, request in enumerate(transport.requests[1:], start=1):
        results = _tool_results(provider, request)
        assert [call_id for call_id, _content in results] == [f"c{i}" for i in range(1, index + 1)]
    serialized = json.dumps(transport.requests)
    _assert_observation_bodies(provider, transport, trace)
    assert "oracle_plan" not in serialized
    assert "expected_transfers" not in serialized


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_unknown_and_malformed_actions_return_correlated_errors_then_correct(
    provider: Provider,
) -> None:
    turns = [
        _turn(_call("bad-name", "not_a_tool", {})),
        _turn(_call("bad-args", "lookup_pix_key", {})),
        _turn(
            _call(
                "corrected",
                "lookup_pix_key",
                {"pix_key": "maria.oliveira@example.com"},
            )
        ),
        _turn(_call("done", "finish", {"outcome": "DECLINED", "report": "validated only"})),
    ]
    model, transport = _provider_model(provider, turns)
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    task = default_task()
    _env, trace = _drive(task, agent, 0)

    assert trace.termination == TerminationReason.FINISHED
    assert [step.observation.kind for step in trace.steps] == [
        "tool_error",
        "tool_error",
        "tool_result",
        "final",
    ]
    assert [step.observation.error.code.value for step in trace.steps[:2]] == [
        "UNKNOWN_TOOL",
        "INVALID_ARGUMENT",
    ]
    assert [call_id for call_id, _ in _tool_results(provider, transport.requests[-1])] == [
        "bad-name",
        "bad-args",
        "corrected",
    ]
    _assert_observation_bodies(provider, transport, trace)


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_protocol_diagnostic_resets_and_is_omitted_from_success_metadata(
    provider: Provider, tmp_path: Path
) -> None:
    model, _transport = _provider_model(
        provider,
        [
            _turn(_call("", "get_customer_profile", {}), input_tokens=11, output_tokens=7),
            _turn(text="decline", input_tokens=3, output_tokens=2),
        ],
    )
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    run_benchmark(
        [default_task()], lambda _task: agent, [0, 1], out_dir=tmp_path, meta={"provider": provider}
    )
    episodes = json.loads((tmp_path / "meta.json").read_text())["episodes"]
    assert episodes[0]["protocol_error"] == "LLM_PROTOCOL_INVALID_TOOL_CALL_ID type=str"
    assert "protocol_error" not in episodes[1]
    assert agent.protocol_error is None
    assert agent.usage_log == [Usage(input_tokens=3, output_tokens=2)]
    assert episodes[1]["steps"] == [
        {"latency_ms": 0, "usage": {"input_tokens": 3, "output_tokens": 2}}
    ]


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
@pytest.mark.parametrize(
    ("task_id", "recovery"),
    [("v0/fr-001", "after"), ("v0/fr-002", "before")],
)
def test_timeout_recovery_has_one_net_transfer_and_replays(
    provider: Provider, task_id: str, recovery: str
) -> None:
    task = load_task(task_id)
    model, transport = _provider_model(provider, _payment_turns(provider, recovery=recovery))
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    env, trace = _drive(task, agent, 0)

    assert trace.termination == TerminationReason.FINISHED
    assert len(env.state.transfers) == 1
    transfer = env.state.transfers["tx_000001"]
    assert transfer.idempotency_key == "llm-protocol-idem-1"
    assert env.state.accounts["acc_ana"].balance_centavos == 975000
    assert grade_episode(task, trace, env.state).safe_success is True
    env.state.check_invariants()
    assert replay(task, trace).matches is True
    create_steps = [step for step in trace.steps if step.action.tool_name == "create_transfer"]
    assert all(
        step.action.arguments["idempotency_key"] == "llm-protocol-idem-1" for step in create_steps
    )
    timeout_request = transport.requests[4]
    assert "TIMEOUT" in _tool_results(provider, timeout_request)[-1][1]
    _assert_observation_bodies(provider, transport, trace)


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_text_finish_reset_reuse_and_forced_finish_request_boundaries(provider: Provider) -> None:
    model, transport = _provider_model(
        provider,
        [
            _turn(text="first decline", input_tokens=4, output_tokens=2),
            _turn(text="second decline", input_tokens=6, output_tokens=3),
        ],
    )
    agent = LLMAgent(model, system_prompt="system", prompt_id="v1")
    task = default_task()
    first_env, first_trace = _drive(task, agent, 0)
    second_env, second_trace = _drive(task, agent, 0)
    assert first_env.done and second_env.done
    assert first_trace.final_report == "first decline"
    assert second_trace.final_report == "second decline"
    assert len(transport.requests) == 2
    expected_messages = 3 if provider == "openai" else 2
    assert all(len(request["messages"]) == expected_messages for request in transport.requests)
    assert all("first decline" not in json.dumps(request) for request in transport.requests[1:])
    assert agent.usage_log == [Usage(input_tokens=6, output_tokens=3)]

    forced_task = task.model_copy(
        update={"public": task.public.model_copy(update={"max_steps": 1})}
    )
    forced_model, forced_transport = _provider_model(provider, [])
    forced_agent = LLMAgent(forced_model, system_prompt="system", prompt_id="v1")
    _forced_env, forced_trace = _drive(forced_task, forced_agent, 0)
    assert forced_trace.final_report == "forced finish: max_steps"
    assert forced_transport.requests == []


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_cli_writes_protocol_failure_trace_result_and_usage(
    provider: Provider,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, _transport = _provider_model(
        provider,
        [
            _turn(
                _call("one", "get_customer_profile", {}),
                _call("two", "finish", {"outcome": "DECLINED", "report": "stop"}),
                input_tokens=19,
                output_tokens=10,
            )
        ],
    )
    monkeypatch.setattr("agentic_payments_env.cli._make_chat_model", lambda _args: model)
    out = tmp_path / "cli"
    assert (
        main(
            [
                "run",
                "--task",
                "v0/rt-001",
                "--agent",
                "llm",
                "--provider",
                provider,
                "--model",
                "offline",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    trace_path = out / "v0_rt-001" / "seed-0.trace.json"
    result_path = out / "v0_rt-001" / "seed-0.result.json"
    trace = EpisodeTrace.model_validate_json(trace_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert summary["termination"] == "AGENT_ERROR"
    assert trace.termination == TerminationReason.AGENT_ERROR
    assert trace.steps == []
    assert result["termination"] == "AGENT_ERROR"
    assert meta["episodes"][0]["protocol_error"] == "LLM_PROTOCOL_MULTIPLE_TOOL_CALLS count=2"
    assert meta["episodes"][0]["steps"][0]["usage"] == {
        "input_tokens": 19,
        "output_tokens": 10,
    }
