"""Tool-call-first LLM agents for workbook evaluation."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from table_env_bench.env.actions import WorkbookAction, parse_action


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

_MODEL_PRICING_USD_PER_1M: tuple[tuple[str, dict[str, float | None]], ...] = (
    ("gpt-5-nano", {"input": 0.05, "cached_input": 0.005, "output": 0.40}),
    ("gpt-5-mini", {"input": 0.25, "cached_input": 0.025, "output": 2.00}),
    ("gpt-5-pro", {"input": 15.00, "cached_input": None, "output": 120.00}),
    ("gpt-5", {"input": 1.25, "cached_input": 0.125, "output": 10.00}),
    ("gpt-4.1-mini", {"input": 0.40, "cached_input": 0.10, "output": 1.60}),
    ("gpt-4.1", {"input": 2.00, "cached_input": 0.50, "output": 8.00}),
    ("gpt-4o-mini", {"input": 0.15, "cached_input": 0.075, "output": 0.60}),
    ("gpt-4o", {"input": 2.50, "cached_input": 1.25, "output": 10.00}),
)

_EMPTY_OBJECT_SCHEMA = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
_BASE_ACTION_TOOL_SPECS: tuple[dict[str, Any], ...] = (
    {
        "name": "select_sheet",
        "description": "Select a workbook sheet by visible sheet tab name.",
        "parameters": {
            "type": "object",
            "properties": {"sheet": {"type": "string"}},
            "required": ["sheet"],
            "additionalProperties": False,
        },
    },
    {"name": "next_page", "description": "Go to the next page in the current sheet.", "parameters": _EMPTY_OBJECT_SCHEMA},
    {"name": "prev_page", "description": "Go to the previous page in the current sheet.", "parameters": _EMPTY_OBJECT_SCHEMA},
    {"name": "zoom_in", "description": "Zoom in on the viewport.", "parameters": _EMPTY_OBJECT_SCHEMA},
    {"name": "zoom_out", "description": "Zoom out on the viewport.", "parameters": _EMPTY_OBJECT_SCHEMA},
    {"name": "pan_up", "description": "Pan the viewport upward.", "parameters": _EMPTY_OBJECT_SCHEMA},
    {"name": "pan_down", "description": "Pan the viewport downward.", "parameters": _EMPTY_OBJECT_SCHEMA},
    {"name": "pan_left", "description": "Pan the viewport left.", "parameters": _EMPTY_OBJECT_SCHEMA},
    {"name": "pan_right", "description": "Pan the viewport right.", "parameters": _EMPTY_OBJECT_SCHEMA},
    {
        "name": "click_region",
        "description": "Click a viewport region using integer x and y screen coordinates.",
        "parameters": {
            "type": "object",
            "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
            "required": ["x", "y"],
            "additionalProperties": False,
        },
    },
    {
        "name": "submit_answer",
        "description": "Submit the final answer text exactly as it should be entered.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
    },
)


class LLMClient(Protocol):
    model: str
    base_url: str
    provider_mode: str
    reasoning_effort: str | None

    def complete(self, *, instructions: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        ...


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
        if match:
            stripped = match.group(1)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(stripped)
        if not match:
            raise ValueError("Model response does not contain a JSON object") from None
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Model response JSON must be an object")
    return payload


def parse_llm_action(text: str) -> WorkbookAction:
    payload = _extract_json_object(text)
    action_payload = payload.get("action", payload)
    if not isinstance(action_payload, dict):
        raise ValueError("Action payload must be an object")
    return parse_action(action_payload)


def serialize_observation(observation: dict[str, Any], info: dict[str, Any]) -> str:
    visible_choice_ids = extract_visible_choice_ids(observation)
    state = {
        "question": observation["question"],
        "remaining_action_budget": observation["remaining_action_budget"],
        "current_sheet_name": observation["current_sheet_name"],
        "current_sheet_index": observation["current_sheet_index"],
        "current_page_index": observation["current_page_index"],
        "page_count_in_sheet": observation["page_count_in_sheet"],
        "sheet_tabs": observation["sheet_tabs"],
        "action_history_summary": observation["action_history_summary"],
        "episode_id": info["episode_id"],
        "family": info["family"],
        "level": info["level"],
        "template_id": info.get("template_id"),
        "track": info.get("track"),
    }
    lines = [
        "State JSON:",
        json.dumps(state, ensure_ascii=False, indent=2),
    ]
    if visible_choice_ids:
        lines.extend(
            [
                "",
                f"Visible answer choices on this page: {', '.join(visible_choice_ids)}",
                "If you use submit_answer now, text must be exactly one visible choice id and nothing else.",
            ]
        )
    if observation.get("viewport_image_png_base64"):
        lines.append("")
        lines.append("Viewport image is attached as PNG.")
    elif observation.get("viewport_svg"):
        lines.append("")
        lines.append("Viewport SVG:")
        lines.append(str(observation["viewport_svg"]))
    return "\n".join(lines)


def extract_visible_choice_ids(observation: dict[str, Any]) -> list[str]:
    scene = observation.get("viewport_scene") or {}
    page = scene.get("page") or {}
    visible: list[str] = []
    for region in page.get("regions", []) or []:
        if region.get("role") != "answer_choice":
            continue
        metadata = region.get("metadata") or {}
        choice_id = str(metadata.get("choice_id") or "").strip()
        if not choice_id:
            match = re.search(r"([A-Z0-9]+)$", str(region.get("label") or "").upper())
            if match:
                choice_id = match.group(1)
        if choice_id and choice_id not in visible:
            visible.append(choice_id)
    return visible


def _normalize_submit_answer_text(text: str, allowed_choices: list[str]) -> str:
    stripped = text.strip()
    if not allowed_choices:
        if not stripped:
            raise ValueError("submit_answer requires non-empty text")
        return stripped

    canonical_by_upper = {choice.upper(): choice for choice in allowed_choices}
    upper = stripped.upper()
    if upper in canonical_by_upper:
        return canonical_by_upper[upper]

    unique_matches: list[str] = []
    for choice in allowed_choices:
        pattern = rf"(?<![A-Z0-9])(?:선택지\s*)?{re.escape(choice.upper())}(?![A-Z0-9])"
        if re.search(pattern, upper):
            if choice not in unique_matches:
                unique_matches.append(choice)
    if len(unique_matches) == 1:
        return unique_matches[0]
    raise ValueError(
        "submit_answer must use exactly one visible choice id: "
        + ", ".join(allowed_choices)
    )


def workbook_action_tools(*, provider_mode: str, answer_choices: list[str] | None = None) -> list[dict[str, Any]]:
    answer_choices = list(answer_choices or [])
    tool_specs: list[dict[str, Any]] = []
    for spec in _BASE_ACTION_TOOL_SPECS:
        if spec["name"] != "submit_answer":
            tool_specs.append(spec)
            continue
        submit_spec = {
            "name": spec["name"],
            "description": (
                "Submit the final answer."
                if not answer_choices
                else "Submit the final answer using exactly one visible choice id and nothing else."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"} if not answer_choices else {"type": "string", "enum": answer_choices}
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        }
        tool_specs.append(submit_spec)
    if provider_mode == "responses":
        return [
            {
                "type": "function",
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["parameters"],
                "strict": True,
            }
            for spec in tool_specs
        ]
    return [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
        for spec in tool_specs
    ]


def normalize_usage(usage: dict[str, Any] | None) -> dict[str, int]:
    usage = usage or {}
    input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0)
    output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
    cached_input_tokens = int(
        usage.get("cached_input_tokens")
        or (
            (usage.get("input_tokens_details", {}) or usage.get("prompt_tokens_details", {}) or {}).get("cached_tokens", 0)
        )
        or 0
    )
    reasoning_tokens = int(
        usage.get("reasoning_tokens")
        or (
            (usage.get("output_tokens_details", {}) or usage.get("completion_tokens_details", {}) or {}).get("reasoning_tokens", 0)
        )
        or 0
    )
    total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens) or 0)
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
    }


def estimate_usage_cost_usd(model: str, usage: dict[str, Any] | None) -> float | None:
    normalized = normalize_usage(usage)
    pricing = None
    for prefix, candidate in _MODEL_PRICING_USD_PER_1M:
        if model == prefix or model.startswith(f"{prefix}-"):
            pricing = candidate
            break
    if pricing is None:
        return None
    input_tokens = normalized["input_tokens"]
    cached_input_tokens = min(normalized["cached_input_tokens"], input_tokens)
    uncached_input_tokens = max(input_tokens - cached_input_tokens, 0)
    cached_rate = pricing["cached_input"] if pricing["cached_input"] is not None else pricing["input"]
    cost = (uncached_input_tokens * float(pricing["input"])) / 1_000_000
    cost += (cached_input_tokens * float(cached_rate)) / 1_000_000
    cost += (normalized["output_tokens"] * float(pricing["output"])) / 1_000_000
    return round(cost, 8)


def _is_official_openai_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url if "://" in base_url else f"https://{base_url}")
    return (parsed.hostname or "").lower() == "api.openai.com"


def _load_dotenv_if_present(path: str | os.PathLike[str] = ".env") -> None:
    env_path = Path(path)
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


def _chat_message_content(content: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    parts: list[dict[str, Any]] = []
    for part in content:
        if part["type"] == "text":
            parts.append({"type": "text", "text": part["text"]})
        elif part["type"] == "image":
            parts.append({"type": "image_url", "image_url": {"url": part["image_url"]}})
        else:
            raise ValueError(f"Unsupported message content part: {part['type']}")
    return parts


def _responses_message_content(content: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    parts: list[dict[str, Any]] = []
    for part in content:
        if part["type"] == "text":
            parts.append({"type": "input_text", "text": part["text"]})
        elif part["type"] == "image":
            parts.append({"type": "input_image", "image_url": part["image_url"]})
        else:
            raise ValueError(f"Unsupported message content part: {part['type']}")
    return parts


def _normalize_chat_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw_call in message.get("tool_calls", []) or []:
        function = raw_call.get("function", {})
        arguments = function.get("arguments") or "{}"
        parsed_arguments = json.loads(arguments)
        if not isinstance(parsed_arguments, dict):
            raise ValueError("Tool call arguments must decode to an object")
        normalized.append(
            {
                "id": raw_call.get("id"),
                "name": function.get("name"),
                "arguments": parsed_arguments,
            }
        )
    return normalized


def _normalize_responses_tool_calls(output: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in output:
        if item.get("type") != "function_call":
            continue
        arguments = item.get("arguments") or "{}"
        parsed_arguments = json.loads(arguments)
        if not isinstance(parsed_arguments, dict):
            raise ValueError("Tool call arguments must decode to an object")
        normalized.append(
            {
                "id": item.get("call_id") or item.get("id"),
                "name": item.get("name"),
                "arguments": parsed_arguments,
            }
        )
    return normalized


def _extract_responses_assistant_text(output: list[dict[str, Any]]) -> str:
    fragments: list[str] = []
    for item in output:
        if item.get("type") != "message":
            continue
        for content_part in item.get("content", []) or []:
            if content_part.get("type") in {"output_text", "text"}:
                fragments.append(str(content_part.get("text", "")))
    return "\n".join(fragment for fragment in fragments if fragment)


@dataclass
class OpenAICompatibleClient:
    model: str
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    timeout_s: float = 60.0
    temperature: float = 0.0
    max_output_tokens: int = 400
    reasoning_effort: str | None = "minimal"
    provider_mode: str = field(init=False)
    _client: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self.provider_mode = "responses" if _is_official_openai_base_url(self.base_url) else "chat_completions"
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_s,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    @classmethod
    def from_env(
        cls,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        reasoning_effort: str | None = "minimal",
        max_output_tokens: int = 400,
    ) -> "OpenAICompatibleClient":
        _load_dotenv_if_present()
        resolved_key = os.environ.get(api_key_env)
        if not resolved_key:
            raise ValueError(f"Missing API key env var: {api_key_env}")
        return cls(
            model=model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=resolved_key,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def complete(self, *, instructions: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if self.provider_mode == "responses":
            return self._complete_via_responses(instructions=instructions, messages=messages, tools=tools)
        return self._complete_via_chat(instructions=instructions, messages=messages, tools=tools)

    def _complete_via_responses(
        self,
        *,
        instructions: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": [
                {"role": message["role"], "content": _responses_message_content(message["content"])}
                for message in messages
            ],
            "tools": tools,
            "tool_choice": "required",
            "parallel_tool_calls": False,
            "max_output_tokens": self.max_output_tokens,
        }
        if self.reasoning_effort and self.model.startswith("gpt-5"):
            payload["reasoning"] = {"effort": self.reasoning_effort}
        elif not self.model.startswith("gpt-5"):
            payload["temperature"] = self.temperature
        response = self._client.post("responses", json=payload)
        response.raise_for_status()
        body = response.json()
        output = body.get("output", []) or []
        usage = normalize_usage(body.get("usage"))
        finish_reason = None
        incomplete = body.get("incomplete_details") or {}
        if incomplete.get("reason"):
            finish_reason = str(incomplete["reason"])
        return {
            "tool_calls": _normalize_responses_tool_calls(output),
            "assistant_text": _extract_responses_assistant_text(output),
            "usage": usage,
            "finish_reason": finish_reason,
            "provider_mode": self.provider_mode,
            "response_status": body.get("status"),
            "raw_response": body,
        }

    def _complete_via_chat(
        self,
        *,
        instructions: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                *[
                    {"role": message["role"], "content": _chat_message_content(message["content"])}
                    for message in messages
                ],
            ],
            "tools": tools,
            "tool_choice": "required",
            "parallel_tool_calls": False,
            "max_completion_tokens": self.max_output_tokens,
        }
        if not self.model.startswith("gpt-5"):
            payload["temperature"] = self.temperature
        response = self._client.post("chat/completions", json=payload)
        response.raise_for_status()
        body = response.json()
        choice = body["choices"][0]
        message = choice.get("message", {})
        return {
            "tool_calls": _normalize_chat_tool_calls(message),
            "assistant_text": str(message.get("content", "")),
            "usage": normalize_usage(body.get("usage")),
            "finish_reason": choice.get("finish_reason"),
            "provider_mode": self.provider_mode,
            "response_status": choice.get("finish_reason"),
            "raw_response": body,
        }


@dataclass
class LLMAgent:
    client: LLMClient
    name: str = "llm"
    prompt_template_version: str = "v2-tool-calls"
    max_parse_retries: int = 2
    system_prompt: str = field(init=False)
    traces: list[dict[str, Any]] = field(init=False, default_factory=list)
    total_latency_ms: float = field(init=False, default=0.0)
    total_usage: dict[str, int] = field(init=False, default_factory=dict)
    parse_retry_count: int = field(init=False, default=0)
    tool_retry_count: int = field(init=False, default=0)
    total_estimated_cost_usd: float = field(init=False, default=0.0)
    has_priced_steps: bool = field(init=False, default=False)
    last_error: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.system_prompt = (
            "You are evaluating an interactive Visual TableQA workbook benchmark. "
            "Inspect the rendered workbook evidence and choose exactly one next action by calling exactly one provided tool. "
            "Do not write prose. Do not call multiple tools. "
            "Only submit an answer when you are ready to finish the episode. "
            "When answer choices are visible, submit_answer.text must be exactly one visible choice id such as A, B, C, or D."
        )

    def reset(self, observation: dict[str, Any], info: dict[str, Any]) -> None:
        self.traces = []
        self.total_latency_ms = 0.0
        self.total_usage = {}
        self.parse_retry_count = 0
        self.tool_retry_count = 0
        self.total_estimated_cost_usd = 0.0
        self.has_priced_steps = False
        self.last_error = None

    def act(self, observation: dict[str, Any], info: dict[str, Any]) -> WorkbookAction:
        prompt = serialize_observation(observation, info)
        visible_choice_ids = extract_visible_choice_ids(observation)
        image_base64 = observation.get("viewport_image_png_base64")
        user_parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        image_bytes = 0
        if image_base64:
            user_parts.append({"type": "image", "image_url": f"data:image/png;base64,{image_base64}"})
            image_bytes = len(image_base64) * 3 // 4
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_parts}]
        tools = workbook_action_tools(
            provider_mode=getattr(self.client, "provider_mode", "chat_completions"),
            answer_choices=visible_choice_ids,
        )
        last_exception: Exception | None = None
        for attempt in range(self.max_parse_retries + 1):
            started_at = time.perf_counter()
            response = self.client.complete(instructions=self.system_prompt, messages=messages, tools=tools)
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            usage = normalize_usage(response.get("usage"))
            self.total_latency_ms += latency_ms
            self._accumulate_usage(usage)
            finish_reason = response.get("finish_reason")
            estimated_cost = estimate_usage_cost_usd(getattr(self.client, "model", ""), usage)
            if estimated_cost is not None:
                self.total_estimated_cost_usd += estimated_cost
                self.has_priced_steps = True
            try:
                action, tool_call = self._parse_response_action(response, visible_choice_ids=visible_choice_ids)
                self.traces.append(
                    {
                        "step_index": len(self.traces) + 1,
                        "action": action.to_dict(),
                        "tool_name": tool_call["name"] if tool_call is not None else action.type,
                        "tool_arguments": dict(tool_call["arguments"]) if tool_call is not None else action.to_dict(),
                        "provider_mode": response.get("provider_mode"),
                        "response_status": response.get("response_status"),
                        "finish_reason": finish_reason,
                        "latency_ms": round(latency_ms, 3),
                        "usage": usage,
                        "estimated_cost_usd": estimated_cost,
                        "prompt_char_count": len(prompt),
                        "image_bytes": image_bytes,
                    }
                )
                return action
            except Exception as exc:  # pragma: no cover - exercised via retry path
                last_exception = exc
                self.parse_retry_count += 1
                self.tool_retry_count += 1
                self.last_error = str(exc)
                messages = [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            "The previous response was invalid because it did not contain exactly one valid tool call. "
                            f"Error: {exc}. "
                            + (
                                f"If you submit an answer on this page, use exactly one of these choice ids: {', '.join(visible_choice_ids)}. "
                                if visible_choice_ids
                                else ""
                            )
                            + "Call exactly one valid tool with valid arguments now."
                        ),
                    },
                ]
                if attempt == self.max_parse_retries:
                    break
        raise ValueError(f"LLM action parsing failed after retries: {last_exception}") from last_exception

    def _parse_response_action(
        self,
        response: dict[str, Any],
        *,
        visible_choice_ids: list[str] | None = None,
    ) -> tuple[WorkbookAction, dict[str, Any] | None]:
        visible_choice_ids = list(visible_choice_ids or [])
        tool_calls = list(response.get("tool_calls", []) or [])
        if len(tool_calls) == 1:
            tool_call = tool_calls[0]
            arguments = dict(tool_call.get("arguments") or {})
            if tool_call.get("name") == "submit_answer":
                arguments["text"] = _normalize_submit_answer_text(str(arguments.get("text") or ""), visible_choice_ids)
            action = parse_action({"type": tool_call.get("name"), **arguments})
            return action, tool_call
        if len(tool_calls) > 1:
            raise ValueError("Model returned multiple tool calls for a single step")
        assistant_text = str(response.get("assistant_text", "") or "")
        if assistant_text.strip():
            action = parse_llm_action(assistant_text)
            if action.type == "submit_answer":
                action = WorkbookAction(
                    type="submit_answer",
                    text=_normalize_submit_answer_text(str(action.text or ""), visible_choice_ids),
                )
            return action, None
        raise ValueError("Model response did not contain a valid tool call")

    def _accumulate_usage(self, usage: dict[str, Any]) -> None:
        for key, value in usage.items():
            if isinstance(value, int):
                self.total_usage[key] = self.total_usage.get(key, 0) + value

    def run_metadata(self) -> dict[str, Any]:
        model_name = getattr(self.client, "model", None)
        base_url = getattr(self.client, "base_url", None)
        provider_mode = getattr(self.client, "provider_mode", None)
        reasoning_effort = getattr(self.client, "reasoning_effort", None)
        estimated_cost = round(self.total_estimated_cost_usd, 8) if self.has_priced_steps else None
        return {
            "model_config": {
                "model": model_name,
                "base_url": base_url,
                "prompt_template_version": self.prompt_template_version,
            },
            "response_mode": "tool_calls",
            "provider_mode": provider_mode,
            "reasoning_effort": reasoning_effort,
            "llm_trace": list(self.traces),
            "usage": dict(self.total_usage),
            "latency_ms": round(self.total_latency_ms, 3),
            "finish_reason": self.traces[-1]["finish_reason"] if self.traces else None,
            "parse_retry_count": self.parse_retry_count,
            "tool_retry_count": self.tool_retry_count,
            "estimated_cost_usd": estimated_cost,
            "api_error": self.last_error,
        }
