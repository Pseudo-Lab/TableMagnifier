"""LangGraph flow for generating synthetic tables from Korean table images."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Dict, List, TypedDict, Callable, Optional

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from dotenv import load_dotenv


MAX_ATTEMPTS = 2  # 최대 재생성 시도 횟수


class TableState(TypedDict, total=False):
    image_path: str
    html_table: str
    table_summary: str
    synthetic_table: str
    reflection: str                 # LLM이 준 원문(디버그용)
    reflection_json: dict           # 구조화된 평가 결과
    revision_instructions: str      # 재생성 지시
    attempts: int                   # 재생성 횟수
    passed: bool                    # 평가 통과 여부
    errors: List[str]
    synthetic_json: dict            # 파싱된 합성 데이터 JSON



def _encode_image(image_path: Path) -> str:
    """Return the image encoded as a data URL."""

    mime = "image/png"
    suffix = image_path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    elif suffix == ".gif":
        mime = "image/gif"

    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def _call_llm(
    llm: ChatOpenAI, prompt: str, image_urls: Optional[List[str]] = None) -> str:
    """Call the multi-modal LLM with optional multiple images."""

    content: List[Dict] = [{"type": "text", "text": prompt}]

    if image_urls:
        for url in image_urls:
            if url:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": url
                    }
                })

    response = llm.invoke([HumanMessage(content=content)])
    return response.content if isinstance(response.content, str) else json.dumps(response.content)


def _load_prompt(name: str) -> str:
    """Load a prompt text from the prompts directory."""
    # __file__ 없는 환경(노트북) 대비
    base_dir = Path(__file__).parent if "__file__" in globals() else Path.cwd()
    prompt_path = base_dir / "prompts" / f"{name}.txt"
    try:
        return prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}") from e


def image_to_html_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    prompt = _load_prompt("image_to_html")

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: image_to_html")
        
        if state.get("errors"):
            return state

        # attempts 초기화
        attempts = int(state.get("attempts", 0))

        image_path = Path(state["image_path"])
        if not image_path.exists():
            errors = state.get("errors", [])
            errors.append(f"Image not found: {image_path}")
            return {**state, "errors": errors, "attempts": attempts}

        image_data_url = _encode_image(image_path)
        html = _call_llm(llm, prompt, image_urls=[image_data_url])
        return {**state, "html_table": html, "attempts": attempts}

    return _node


def parse_contents_node(llm: ChatOpenAI) -> Callable[["TableState"], "TableState"]:
    """Create a node that summarizes the table contents."""

    prompt_template = _load_prompt("parse_contents")

    def _node(state: "TableState") -> "TableState":
        logger.info("Entering node: parse_contents")
        if state.get("errors"):
            return state
        html = state.get("html_table")
        if not html:
            errors = state.get("errors", [])
            errors.append("Missing HTML table representation.")
            return {**state, "errors": errors}

        # format 중 KeyError 방지 (템플릿에 {html} 없는 경우 등)
        try:
            prompt = prompt_template.format(html=html)
        except KeyError as e:
            errors = state.get("errors", [])
            errors.append(f"Prompt template missing placeholder: {e}")
            return {**state, "errors": errors}

        summary = _call_llm(llm, prompt)
        return {**state, "table_summary": summary}

    return _node


def generate_synthetic_table_node(llm: ChatOpenAI) -> Callable[["TableState"], "TableState"]:
    """Create a node that generates a synthetic dataset with the same structure."""

    prompt_template = _load_prompt("generate_synthetic_table")

    def _node(state: "TableState") -> "TableState":
        logger.info("Entering node: generate_synthetic_table")
        if state.get("errors"):
            return state
        html = state.get("html_table")
        summary = state.get("table_summary")

        if not html or not summary:
            errors = state.get("errors", [])
            errors.append("Insufficient information to generate synthetic table.")
            return {**state, "errors": errors}

        try:
            prompt = prompt_template.format(html=html, summary=summary)
        except KeyError as e:
            errors = state.get("errors", [])
            errors.append(f"Prompt template missing placeholder: {e}")
            return {**state, "errors": errors}

        synthetic_html = _call_llm(llm, prompt)
        return {**state, "synthetic_table": synthetic_html}

    return _node


from .validators import robust_json_parse, validate_html
import logging

logger = logging.getLogger(__name__)

def _safe_parse_json(text: str) -> Optional[dict]:
    """Deprecated: Use validators.robust_json_parse instead."""
    return robust_json_parse(text)


def self_reflection_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    prompt_template = _load_prompt("self_reflection")

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: self_reflection")
        if state.get("errors"):
            return state

        synthetic_html = state.get("synthetic_table")
        if not synthetic_html:
            errors = state.get("errors", [])
            errors.append("Synthetic table generation failed.")
            return {**state, "errors": errors}

        try:
            prompt = prompt_template.format(synthetic_html=synthetic_html)
        except KeyError as e:
            errors = state.get("errors", [])
            errors.append(f"Prompt template missing placeholder: {e}")
            return {**state, "errors": errors}

        reflection_text = _call_llm(llm, prompt)


        reflection_json = _safe_parse_json(reflection_text)
        if reflection_json is None:
            errors = state.get("errors", [])
            errors.append("Self-reflection did not return valid JSON.")
            return {**state, "errors": errors, "reflection": reflection_text}

        passed = bool(reflection_json.get("passed", False))
        revision_instructions = reflection_json.get("revision_instructions", "")

        return {
            **state,
            "reflection": reflection_text,
            "reflection_json": reflection_json,
            "revision_instructions": revision_instructions,
            "passed": passed,
        }

    return _node


def revise_synthetic_table_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    prompt_template = _load_prompt("revise_synthetic_table")

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: revise_synthetic_table")
        if state.get("errors"):
            return state

        html = state.get("html_table")
        summary = state.get("table_summary")
        synthetic_html = state.get("synthetic_table")
        instructions = state.get("revision_instructions", "")

        if not html or not summary or not synthetic_html:
            errors = state.get("errors", [])
            errors.append("Insufficient info for revision.")
            return {**state, "errors": errors}

        try:
            prompt = prompt_template.format(
                html=html,
                summary=summary,
                synthetic_html=synthetic_html,
                revision_instructions=instructions,
            )
        except KeyError as e:
            errors = state.get("errors", [])
            errors.append(f"Revision prompt missing placeholder: {e}")
            return {**state, "errors": errors}

        new_synthetic_html = _call_llm(llm, prompt)
        attempts = int(state.get("attempts", 0)) + 1
        return {**state, "synthetic_table": new_synthetic_html, "attempts": attempts}

    return _node


def parse_synthetic_table_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    """Create a node that parses the synthetic HTML table into JSON."""

    prompt_template = _load_prompt("parse_synthetic_table")

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: parse_synthetic_table")
        if state.get("errors"):
            return state

        synthetic_html = state.get("synthetic_table")
        if not synthetic_html:
            errors = state.get("errors", [])
            errors.append("No synthetic table to parse.")
            return {**state, "errors": errors}

        try:
            prompt = prompt_template.format(synthetic_html=synthetic_html)
        except KeyError as e:
            errors = state.get("errors", [])
            errors.append(f"Parse prompt missing placeholder: {e}")
            return {**state, "errors": errors}

        json_text = _call_llm(llm, prompt)
        parsed_json = _safe_parse_json(json_text)
        
        if parsed_json is None:
             # 파싱 실패 시 에러보다는 경고/빈값 처리 혹은 재시도 로직? 
             # 여기서는 일단 에러로 처리하지 않고 raw text만 남기거나 함.
             # 하지만 사용자 요청은 "파싱을 진행해두려고 해" 이므로
             # 최대한 파싱된 결과를 원함.
             # robust_json_parse가 실패하면 None임.
             pass

        return {**state, "synthetic_json": parsed_json}

    return _node



def route_after_reflection(state: TableState) -> str:
    passed = state.get("passed", False)
    attempts = int(state.get("attempts", 0))


    if passed:
        return "parse_synthetic_table"
    if attempts >= MAX_ATTEMPTS:
        return "parse_synthetic_table"  # 실패했더라도 파싱 시도 (혹은 END)
    return "revise_synthetic_table"




def build_synthetic_table_graph(llm: ChatOpenAI) -> StateGraph:
    """Assemble the LangGraph pipeline with reflection-based regeneration loop."""

    graph = StateGraph(TableState)

    graph.add_node("image_to_html", image_to_html_node(llm))
    graph.add_node("parse_contents", parse_contents_node(llm))
    graph.add_node("generate_synthetic_table", generate_synthetic_table_node(llm))

    graph.add_node("self_reflection", self_reflection_node(llm))
    graph.add_node("revise_synthetic_table", revise_synthetic_table_node(llm))
    graph.add_node("parse_synthetic_table", parse_synthetic_table_node(llm))


    graph.add_edge(START, "image_to_html")
    graph.add_edge("image_to_html", "parse_contents")
    graph.add_edge("parse_contents", "generate_synthetic_table")
    graph.add_edge("generate_synthetic_table", "self_reflection")

    graph.add_conditional_edges(
        "self_reflection",
        route_after_reflection,
        {
            "parse_synthetic_table": "parse_synthetic_table",
            "revise_synthetic_table": "revise_synthetic_table",
        },
    )

    # revise 후 다시 reflection으로
    graph.add_edge("revise_synthetic_table", "self_reflection")
    
    # 파싱 후 종료
    graph.add_edge("parse_synthetic_table", END)


    return graph


from .llm_factory import get_llm

def run_synthetic_table_flow(
    image_path: str,
    *,
    provider: str = "openai",
    model: str = "gpt-4.1-mini",
    temperature: float = 0.2,
    base_url: str | None = None,
) -> TableState:
    load_dotenv()
    
    # Provider check is done in runner, but good to have here too or rely on factory
    llm = get_llm(
        provider=provider,
        model=model,
        temperature=temperature,
        base_url=base_url,
    )
    
    app = build_synthetic_table_graph(llm).compile()

    final_state: TableState = app.invoke({
        "image_path": image_path,
        "attempts": 0,   # ✅ 시작 시 명시
        "errors": [],
    })
    return final_state


__all__ = [
    "TableState",
    "build_synthetic_table_graph",
    "run_synthetic_table_flow",
]
