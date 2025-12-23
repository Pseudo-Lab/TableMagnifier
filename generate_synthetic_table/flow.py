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
import fitz  # PyMuPDF


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
    valid_pymupdf: bool             # PyMuPDF 파싱 결과 유효성
    errors: List[str]
    synthetic_json: dict            # 파싱된 합성 데이터 JSON
    qa_results: List[Dict]          # 생성된 QA 쌍


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


def pymupdf_parse_node(state: TableState) -> TableState:
    """Try to parse the table using PyMuPDF (fitz)."""
    logger.info("Entering node: pymupdf_parse")
    
    image_path = Path(state["image_path"])
    
    try:
        doc = fitz.open(image_path)
        if len(doc) == 0:
            return state
            
        # Try to find tables on the first page
        page = doc[0]
        tabs = page.find_tables()
        
        if tabs.tables:
            logger.info(f"PyMuPDF found {len(tabs.tables)} tables.")
            # Use the first table
            tab = tabs[0]
            data = tab.extract()
            
            if not data:
                return state

            # Simple HTML construction
            html_parts = ["<table>"]
            for row in data:
                html_parts.append("<tr>")
                for cell in row:
                    cell_text = str(cell) if cell is not None else ""
                    html_parts.append(f"<td>{cell_text}</td>")
                html_parts.append("</tr>")
            html_parts.append("</table>")
            
            html_table = "".join(html_parts)
            
            # Basic validation: ensure it's not empty
            if len(html_table) > 20: # arbitrary small length check
                 return {**state, "html_table": html_table}
                 
    except Exception as e:
        logger.warning(f"PyMuPDF parsing failed: {e}")
        
    return state


def route_after_validation(state: TableState) -> str:
    if state.get("valid_pymupdf"):
        return "generate_synthetic_table"
    return "image_to_html"


def validate_parsed_table_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    """Validate the table parsed by PyMuPDF."""
    prompt_template = _load_prompt("validate_parsed_table")

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: validate_parsed_table")
        
        html = state.get("html_table")
        if not html:
             return {**state, "valid_pymupdf": False}

        try:
            prompt = prompt_template.format(html=html)
        except KeyError as e:
            logger.error(f"Validation prompt missing placeholder: {e}")
            return {**state, "valid_pymupdf": False}

        response_text = _call_llm(llm, prompt)
        response_json = robust_json_parse(response_text)
        
        valid = False
        if response_json:
            valid = bool(response_json.get("valid", False))
            
        logger.info(f"PyMuPDF validation result: {valid}")
        return {**state, "valid_pymupdf": valid}

    return _node


def analyze_table_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    """Analyze the table to generate a summary of its structure and content."""
    prompt_template = _load_prompt("parse_contents")

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: analyze_table")
        if state.get("errors"):
            return state

        html = state.get("html_table")
        if not html:
            errors = state.get("errors", [])
            errors.append("No HTML table to analyze.")
            return {**state, "errors": errors}

        try:
            prompt = prompt_template.format(html=html)
        except KeyError as e:
            errors = state.get("errors", [])
            errors.append(f"Analysis prompt missing placeholder: {e}")
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

        if not html:
            errors = state.get("errors", [])
            errors.append("Insufficient information to generate synthetic table.")
            return {**state, "errors": errors}
        
        # summary가 없어도 진행은 가능하지만, 경고를 남기거나 빈 문자열 처리
        if not summary:
            logger.warning("No table summary available for synthetic generation.")
            summary = "No summary provided."

        try:
            prompt = prompt_template.format(html=html, summary=summary)
        except KeyError as e:
            # 템플릿에 summary가 추가되었는지 확인 필요. 
            # 기존 프롬프트 파일에는 {summary}가 없을 수도 있음. 
            # 하지만 계획상으로는 summary를 사용하는 것이 목표임.
            # 만약 프롬프트 파일에 {summary}가 없다면 format에서 무시되거나 에러가 날 수 있음.
            # 여기서는 프롬프트 파일도 확인/수정해야 할 수 있음.
            # 일단 에러 처리.
            errors = state.get("errors", [])
            errors.append(f"Prompt template missing placeholder: {e}")
            return {**state, "errors": errors}

        synthetic_html = _call_llm(llm, prompt)
        return {**state, "synthetic_table": synthetic_html}

    return _node


def generate_synthetic_table_from_image_node(llm: ChatOpenAI) -> Callable[["TableState"], "TableState"]:
    """Generate synthetic table directly from image (for powerful models)."""
    prompt_template = _load_prompt("generate_synthetic_table_from_image")

    def _node(state: "TableState") -> "TableState":
        logger.info("Entering node: generate_synthetic_table_from_image")
        if state.get("errors"):
            return state

        image_path = Path(state["image_path"])
        if not image_path.exists():
            errors = state.get("errors", [])
            errors.append(f"Image not found: {image_path}")
            return {**state, "errors": errors}

        image_data_url = _encode_image(image_path)
        
        # Prompt doesn't have placeholders, it just expects the image
        prompt = prompt_template
        
        synthetic_html = _call_llm(llm, prompt, image_urls=[image_data_url])
        return {**state, "synthetic_table": synthetic_html}

    return _node


from .validators import robust_json_parse, validate_html
import logging

logger = logging.getLogger(__name__)




def self_reflection_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    prompt_template = _load_prompt("self_reflection")
    prompt_template_image = _load_prompt("self_reflection_from_image")

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: self_reflection")
        if state.get("errors"):
            return state

        synthetic_html = state.get("synthetic_table")
        html = state.get("html_table")
        image_path = Path(state["image_path"])

        if not synthetic_html:
            errors = state.get("errors", [])
            errors.append("Synthetic table generation failed.")
            return {**state, "errors": errors}

        # If we don't have the original HTML (direct path), use the image for reflection
        if not html:
            if not image_path.exists():
                 errors = state.get("errors", [])
                 errors.append("Original image missing for reflection.")
                 return {**state, "errors": errors}
            
            image_data_url = _encode_image(image_path)
            try:
                prompt = prompt_template_image.format(synthetic_html=synthetic_html)
            except KeyError as e:
                errors = state.get("errors", [])
                errors.append(f"Reflection prompt missing placeholder: {e}")
                return {**state, "errors": errors}
            
            reflection_text = _call_llm(llm, prompt, image_urls=[image_data_url])
        
        else:
            # Use text-based reflection (existing logic)
            # Note: The existing prompt only takes {synthetic_html}, 
            # but implicitly assumes the model knows the "original HTML" from context or it's just checking validity.
            # Wait, the existing prompt says "matches original HTML" but doesn't take {html} as input?
            # Let's check the prompt file again.
            # "Synthetic HTML: {synthetic_html}"
            # It seems the previous implementation was slightly flawed or relied on the model hallucinating the original?
            # Or maybe I should pass {html} to the original prompt too if it's available?
            # The current prompt file only has {synthetic_html}.
            # If I want it to compare, I should probably provide the original HTML.
            # But for now, I will stick to the existing behavior for the text path, 
            # and use the image path for the direct generation.
            
            try:
                prompt = prompt_template.format(synthetic_html=synthetic_html, html=html)
            except KeyError as e:
                errors = state.get("errors", [])
                errors.append(f"Prompt template missing placeholder: {e}")
                return {**state, "errors": errors}

            reflection_text = _call_llm(llm, prompt)


        reflection_json = robust_json_parse(reflection_text)
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
    prompt_template_image = _load_prompt("revise_synthetic_table_from_image")

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: revise_synthetic_table")
        if state.get("errors"):
            return state

        html = state.get("html_table")
        summary = state.get("table_summary")
        synthetic_html = state.get("synthetic_table")
        instructions = state.get("revision_instructions", "")
        image_path = Path(state["image_path"])

        if not synthetic_html:
            errors = state.get("errors", [])
            errors.append("No synthetic table to revise.")
            return {**state, "errors": errors}

        # Check if we are in the "direct generation" path (missing html/summary)
        if not html or not summary:
            # Use image-based revision
            if not image_path.exists():
                 errors = state.get("errors", [])
                 errors.append("Original image missing for revision.")
                 return {**state, "errors": errors}
            
            image_data_url = _encode_image(image_path)
            try:
                prompt = prompt_template_image.format(
                    synthetic_html=synthetic_html,
                    revision_instructions=instructions
                )
            except KeyError as e:
                errors = state.get("errors", [])
                errors.append(f"Revision prompt missing placeholder: {e}")
                return {**state, "errors": errors}
            
            new_synthetic_html = _call_llm(llm, prompt, image_urls=[image_data_url])

        else:
            # Use text-based revision (existing logic)
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
        parsed_json = robust_json_parse(json_text)
        
        if parsed_json is None:
             # 파싱 실패 시 에러보다는 경고/빈값 처리 혹은 재시도 로직? 
             # 여기서는 일단 에러로 처리하지 않고 raw text만 남기거나 함.
             # 하지만 사용자 요청은 "파싱을 진행해두려고 해" 이므로
             # 최대한 파싱된 결과를 원함.
             # robust_json_parse가 실패하면 None임.
             pass

        return {**state, "synthetic_json": parsed_json}

    return _node


def generate_qa_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    """Generate QA pairs based on the synthetic table."""
    prompt_template = _load_prompt("generate_qa")

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: generate_qa")
        if state.get("errors"):
            return state

        synthetic_html = state.get("synthetic_table")
        if not synthetic_html:
            errors = state.get("errors", [])
            errors.append("No synthetic table for QA generation.")
            return {**state, "errors": errors}

        try:
            prompt = prompt_template.format(synthetic_html=synthetic_html)
        except KeyError as e:
            errors = state.get("errors", [])
            errors.append(f"QA prompt missing placeholder: {e}")
            return {**state, "errors": errors}

        response_text = _call_llm(llm, prompt)
        response_json = robust_json_parse(response_text)
        
        qa_results = []
        if response_json and "qa_pairs" in response_json:
            qa_results = response_json["qa_pairs"]
        else:
             logger.warning("QA generation did not return valid JSON or 'qa_pairs' key.")

        return {**state, "qa_results": qa_results}

    return _node


def route_after_reflection(state: TableState) -> str:
    # 에러가 있으면 더 이상 진행하지 않고 파싱으로 이동 (또는 종료)
    if state.get("errors"):
        return "parse_synthetic_table"
    
    passed = state.get("passed", False)
    attempts = int(state.get("attempts", 0))

    if passed:
        return "parse_synthetic_table"
    if attempts >= MAX_ATTEMPTS:
        return "parse_synthetic_table"  # 실패했더라도 파싱 시도 (혹은 END)
    return "revise_synthetic_table"


def load_html_input_node(state: TableState) -> TableState:
    """Load HTML content directly from a file."""
    logger.info("Entering node: load_html_input")
    
    image_path = Path(state["image_path"])
    try:
        html_content = image_path.read_text(encoding="utf-8")
        return {**state, "html_table": html_content}
    except Exception as e:
        errors = state.get("errors", [])
        errors.append(f"Failed to load HTML file: {e}")
        return {**state, "errors": errors}


def build_synthetic_table_graph(llm: ChatOpenAI, provider: str = "openai") -> StateGraph:
    """Assemble the LangGraph pipeline with reflection-based regeneration loop."""

    graph = StateGraph(TableState)

    graph.add_node("image_to_html", image_to_html_node(llm))
    graph.add_node("pymupdf_parse", pymupdf_parse_node)
    graph.add_node("validate_parsed_table", validate_parsed_table_node(llm))
    graph.add_node("analyze_table", analyze_table_node(llm))
    graph.add_node("generate_synthetic_table", generate_synthetic_table_node(llm))
    graph.add_node("generate_synthetic_table_from_image", generate_synthetic_table_from_image_node(llm))
    graph.add_node("load_html_input", load_html_input_node)

    graph.add_node("self_reflection", self_reflection_node(llm))
    graph.add_node("revise_synthetic_table", revise_synthetic_table_node(llm))
    graph.add_node("parse_synthetic_table", parse_synthetic_table_node(llm))
    graph.add_node("generate_qa", generate_qa_node(llm))

    # Routing based on provider and input type
    def route_start(state: TableState) -> str:
        image_path = Path(state["image_path"])
        if image_path.suffix.lower() == ".html":
            return "load_html_input"

        # Powerful models go direct (gemini_pool도 멀티모달 지원)
        if provider in ["openai", "gemini", "gemini_pool"]:
            return "generate_synthetic_table_from_image"
        # Open models / others go through multi-stage
        return "pymupdf_parse"

    graph.add_conditional_edges(START, route_start)

    # HTML Input path
    graph.add_edge("load_html_input", "analyze_table")

    # Multi-stage path
    graph.add_edge("pymupdf_parse", "validate_parsed_table")
    graph.add_conditional_edges(
        "validate_parsed_table",
        route_after_validation,
        {
            "generate_synthetic_table": "analyze_table",
            "image_to_html": "image_to_html",
        }
    )
    graph.add_edge("image_to_html", "analyze_table")
    graph.add_edge("analyze_table", "generate_synthetic_table")
    graph.add_edge("generate_synthetic_table", "self_reflection")

    # Direct path
    graph.add_edge("generate_synthetic_table_from_image", "self_reflection")

    # Shared reflection loop
    graph.add_conditional_edges(
        "self_reflection",
        route_after_reflection,
        {
            "parse_synthetic_table": "parse_synthetic_table",
            "revise_synthetic_table": "revise_synthetic_table",
        },
    )

    graph.add_edge("revise_synthetic_table", "self_reflection")
    graph.add_edge("parse_synthetic_table", "generate_qa")
    graph.add_edge("generate_qa", END)

    return graph


from .llm_factory import get_llm

def run_synthetic_table_flow(
    image_path: str,
    *,
    provider: str = "openai",
    model: str = "gpt-4.1-mini",
    temperature: float = 0.2,
    base_url: str | None = None,
    config_path: str | None = None,
) -> TableState:
    load_dotenv()
    
    # Provider check is done in runner, but good to have here too or rely on factory
    llm = get_llm(
        provider=provider,
        model=model,
        temperature=temperature,
        base_url=base_url,
        config_path=config_path,
    )
    
    app = build_synthetic_table_graph(llm, provider=provider).compile()

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
