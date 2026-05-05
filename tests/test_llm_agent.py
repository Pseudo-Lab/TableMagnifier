from table_env_bench.baselines import LLMAgent, run_episode
from table_env_bench.baselines.llm_agent import (
    estimate_usage_cost_usd,
    extract_visible_choice_ids,
    parse_llm_action,
    serialize_observation,
    workbook_action_tools,
)
from table_env_bench.env.actions import WorkbookAction
from table_env_bench.env.environment import WorkbookEnv


class FakeLLMClient:
    model = "gpt-5-nano"
    base_url = "https://fake.local/v1"
    provider_mode = "chat_completions"
    reasoning_effort = "minimal"

    def __init__(self, responses):
        self._responses = list(responses)

    def complete(self, *, instructions, messages, tools):
        payload = self._responses.pop(0)
        return payload


def test_parse_llm_action_accepts_nested_action_payload() -> None:
    action = parse_llm_action('{"action":{"type":"select_sheet","sheet":"질의"}}')
    assert action == WorkbookAction(type="select_sheet", sheet="질의")


def test_parse_llm_action_recovers_from_fenced_json() -> None:
    action = parse_llm_action("```json\n{\"type\":\"next_page\"}\n```")
    assert action == WorkbookAction(type="next_page")


def test_parse_llm_action_accepts_text_field_when_it_names_action() -> None:
    action = parse_llm_action('{"text":"Click_region","x":210,"y":260}')
    assert action == WorkbookAction(type="click_region", x=210.0, y=260.0)


def test_estimate_usage_cost_supports_known_models() -> None:
    usage = {"input_tokens": 1000, "cached_input_tokens": 200, "output_tokens": 500, "reasoning_tokens": 100, "total_tokens": 1500}
    cost = estimate_usage_cost_usd("gpt-5-nano", usage)
    assert cost == 0.000241


def test_llm_agent_retries_invalid_response_and_records_metadata() -> None:
    env = WorkbookEnv(family="report_scope_reconciliation", level=1, seed=0, template_id="merged_scope_cell", mode="human")
    agent = LLMAgent(
        client=FakeLLMClient(
            [
                {
                    "tool_calls": [],
                    "assistant_text": "",
                    "usage": {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13},
                    "finish_reason": "stop",
                    "provider_mode": "chat_completions",
                    "response_status": "stop",
                },
                {
                    "tool_calls": [{"id": "call-1", "name": "select_sheet", "arguments": {"sheet": "선택"}}],
                    "assistant_text": "",
                    "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
                    "finish_reason": "stop",
                    "provider_mode": "chat_completions",
                    "response_status": "stop",
                },
                {
                    "tool_calls": [{"id": "call-2", "name": "submit_answer", "arguments": {"text": "B"}}],
                    "assistant_text": "",
                    "usage": {"input_tokens": 9, "output_tokens": 4, "total_tokens": 13},
                    "finish_reason": "stop",
                    "provider_mode": "chat_completions",
                    "response_status": "stop",
                },
            ]
        )
    )
    result = run_episode(env, agent)
    metadata = result.run_metadata

    assert result.prediction == "B"
    assert result.evaluation.correctness.value == 1.0
    assert metadata["model_config"]["model"] == "gpt-5-nano"
    assert metadata["response_mode"] == "tool_calls"
    assert metadata["parse_retry_count"] == 1
    assert metadata["tool_retry_count"] == 1
    assert metadata["usage"]["total_tokens"] == 40
    assert len(metadata["llm_trace"]) == 2
    assert metadata["estimated_cost_usd"] is not None
    assert metadata["llm_trace"][0]["tool_name"] == "select_sheet"
    assert metadata["llm_trace"][1]["tool_name"] == "submit_answer"


def test_serialize_observation_includes_svg_and_state() -> None:
    env = WorkbookEnv(family="report_scope_reconciliation", level=1, seed=0, template_id="merged_scope_cell", mode="human")
    observation, info = env.reset()
    prompt = serialize_observation(observation, info)
    assert "Viewport image is attached as PNG." in prompt
    assert observation["viewport_image_png_base64"]
    assert observation["question"] in prompt
    assert info["episode_id"] in prompt


def test_extract_visible_choice_ids_from_query_page() -> None:
    env = WorkbookEnv(family="report_scope_reconciliation", level=1, seed=0, template_id="merged_scope_cell", mode="human")
    env.reset()
    observation, _, _, _, _ = env.step(WorkbookAction(type="select_sheet", sheet="선택"))
    assert extract_visible_choice_ids(observation) == ["A", "B", "C", "D"]


def test_extract_visible_choice_ids_falls_back_for_sanitized_agent_scene() -> None:
    env = WorkbookEnv(family="report_scope_reconciliation", level=1, seed=0, template_id="merged_scope_cell")
    env.reset()
    observation, _, _, _, _ = env.step(WorkbookAction(type="select_sheet", sheet="선택"))
    assert extract_visible_choice_ids(observation) == []


def test_workbook_action_tools_restrict_submit_answer_to_visible_choices() -> None:
    tools = workbook_action_tools(provider_mode="chat_completions", answer_choices=["A", "B", "C", "D"])
    submit_tool = next(tool for tool in tools if tool["function"]["name"] == "submit_answer")
    assert submit_tool["function"]["parameters"]["properties"]["text"]["enum"] == ["A", "B", "C", "D"]


def test_workbook_action_tools_omits_submit_enum_without_visible_choices() -> None:
    tools = workbook_action_tools(provider_mode="chat_completions", answer_choices=[])
    submit_tool = next(tool for tool in tools if tool["function"]["name"] == "submit_answer")
    assert "enum" not in submit_tool["function"]["parameters"]["properties"]["text"]


def test_llm_agent_normalizes_submit_answer_choice_label() -> None:
    env = WorkbookEnv(family="report_scope_reconciliation", level=1, seed=0, template_id="merged_scope_cell", mode="human")
    agent = LLMAgent(
        client=FakeLLMClient(
            [
                {
                    "tool_calls": [{"id": "call-1", "name": "select_sheet", "arguments": {"sheet": "선택"}}],
                    "assistant_text": "",
                    "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
                    "finish_reason": "stop",
                    "provider_mode": "chat_completions",
                    "response_status": "stop",
                },
                {
                    "tool_calls": [{"id": "call-2", "name": "submit_answer", "arguments": {"text": "선택지 B"}}],
                    "assistant_text": "",
                    "usage": {"input_tokens": 9, "output_tokens": 4, "total_tokens": 13},
                    "finish_reason": "stop",
                    "provider_mode": "chat_completions",
                    "response_status": "stop",
                },
            ]
        )
    )
    result = run_episode(env, agent)
    assert result.prediction == "B"
    assert result.evaluation.correctness.value == 1.0


def test_llm_agent_retries_invalid_submit_answer_when_choices_are_visible() -> None:
    env = WorkbookEnv(family="report_scope_reconciliation", level=1, seed=0, template_id="merged_scope_cell", mode="human")
    agent = LLMAgent(
        client=FakeLLMClient(
            [
                {
                    "tool_calls": [{"id": "call-1", "name": "select_sheet", "arguments": {"sheet": "선택"}}],
                    "assistant_text": "",
                    "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
                    "finish_reason": "stop",
                    "provider_mode": "chat_completions",
                    "response_status": "stop",
                },
                {
                    "tool_calls": [{"id": "call-2", "name": "submit_answer", "arguments": {"text": "정답은 둘째 선택지입니다"}}],
                    "assistant_text": "",
                    "usage": {"input_tokens": 9, "output_tokens": 4, "total_tokens": 13},
                    "finish_reason": "stop",
                    "provider_mode": "chat_completions",
                    "response_status": "stop",
                },
                {
                    "tool_calls": [{"id": "call-3", "name": "submit_answer", "arguments": {"text": "B"}}],
                    "assistant_text": "",
                    "usage": {"input_tokens": 9, "output_tokens": 4, "total_tokens": 13},
                    "finish_reason": "stop",
                    "provider_mode": "chat_completions",
                    "response_status": "stop",
                },
            ]
        )
    )
    result = run_episode(env, agent)
    metadata = result.run_metadata
    assert result.prediction == "B"
    assert metadata["parse_retry_count"] == 1
    assert metadata["tool_retry_count"] == 1
