"""LangGraph flow for generating synthetic tables from Korean table images."""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, TypedDict, Callable, Optional

import fitz  # PyMuPDF
import yaml
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from .validators import (
    robust_json_parse,
    validate_html,
    parse_html_table_to_json,
    compare_tables_with_sql,
    compare_tables_with_repl,
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2  # 최대 재생성 시도 횟수
_PROMPTS_CACHE: Dict[str, Dict[str, str]] = {}  # 프롬프트 캐시 (YAML 파일 로딩 결과 저장)


class TableState(TypedDict, total=False):
    image_path: str
    image_paths: List[str]  # For multi-image inputs
    domain: str             # Domain for prompt customization
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
    token_usage: int                # QA 생성에 사용된 총 토큰 수


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
    llm: ChatOpenAI, prompt: str, image_urls: Optional[List[str]] = None, return_token_usage: bool = False) -> str:
    """Call the multi-modal LLM with optional multiple images.
    
    Args:
        llm: The LLM instance
        prompt: The text prompt
        image_urls: Optional list of image URLs
        return_token_usage: If True, returns tuple of (content, total_tokens)
    
    Returns:
        Response content string, or tuple of (content, total_tokens) if return_token_usage=True
    """

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
    response_content = response.content if isinstance(response.content, str) else json.dumps(response.content)
    
    if return_token_usage:
        # Extract token usage from response metadata
        token_usage = 0
        
        logger.info(f"=== TOKEN DEBUG START ===")
        logger.info(f"Response type: {type(response)}")
        logger.info(f"Has usage_metadata: {hasattr(response, 'usage_metadata')}")
        logger.info(f"Has response_metadata: {hasattr(response, 'response_metadata')}")
        
        # Try response.usage_metadata first (Gemini pool format)
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            logger.info(f"usage_metadata type: {type(usage)}")
            logger.info(f"usage_metadata value: {usage}")
            
            if isinstance(usage, dict):
                token_usage = usage.get('total_tokens', 0)
                if not token_usage:
                    token_usage = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
            else:
                token_usage = getattr(usage, 'total_tokens', 0)
                if not token_usage:
                    token_usage = getattr(usage, 'input_tokens', 0) + getattr(usage, 'output_tokens', 0)
            
            logger.info(f"Extracted token_usage from usage_metadata: {token_usage}")
        
        # Fallback: response.response_metadata (OpenAI format)
        if not token_usage and hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            logger.info(f"response_metadata: {metadata}")
            usage_metadata = metadata.get('usage', {})
            logger.info(f"usage from response_metadata: {usage_metadata}")
            
            token_usage = usage_metadata.get('total_tokens', 0)
            if not token_usage:
                token_usage = usage_metadata.get('prompt_tokens', 0) + usage_metadata.get('completion_tokens', 0)
            if not token_usage:
                token_usage = usage_metadata.get('input_tokens', 0) + usage_metadata.get('output_tokens', 0)
            
            logger.info(f"Extracted token_usage from response_metadata: {token_usage}")
        
        logger.info(f"Final token_usage: {token_usage}")
        logger.info(f"=== TOKEN DEBUG END ===")
        
        return response_content, token_usage
    
    return response_content


def _load_yaml_prompts(filename: str) -> Dict[str, str]:
    """Load prompts from a yaml file, with caching."""
    if filename in _PROMPTS_CACHE:
        return _PROMPTS_CACHE[filename]
    
    base_dir = Path(__file__).parent if "__file__" in globals() else Path.cwd()
    path = base_dir / "prompts" / filename
    
    if not path.exists():
        # Fallback for domain files that might not exist
        return {}
        
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(content, dict):
            return {}
        _PROMPTS_CACHE[filename] = content
        return content
    except Exception as e:
        # Log error?
        print(f"Error loading prompt file {filename}: {e}")
        return {}


def _load_prompt(name: str, domain: str | None = None) -> str:
    """
    Load a prompt by name, optionally overriding with domain-specific version.
    Loads from prompts/default.yaml and prompts/{domain}.yaml.
    """
    default_prompts = _load_yaml_prompts("default.yaml")
    
    prompt = default_prompts.get(name, "")
    
    if domain:
        domain_prompts = _load_yaml_prompts(f"{domain}.yaml")
        if name in domain_prompts:
            prompt = domain_prompts[name]
            
    if not prompt:
        # Fallback to old behavior: try reading text file directly? 
        # Or just raise error. The migration should be complete.
        raise ValueError(f"Prompt '{name}' not found in default.yaml or {domain}.yaml")
        
    return prompt


def image_to_html_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    def _node(state: TableState) -> TableState:
        logger.info("Entering node: image_to_html")
        
        # Load prompt dynamically
        prompt = _load_prompt("image_to_html", state.get("domain"))

        if state.get("errors"):
            return state

        # attempts 초기화
        attempts = int(state.get("attempts", 0))

        image_path = Path(state["image_path"])
        if not image_path.exists():
            errors = list(state.get("errors", []))
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
    pass # Prompt loaded inside node

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: validate_parsed_table")
        prompt_template = _load_prompt("validate_parsed_table", state.get("domain"))
        
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
    pass # Prompt loaded inside node

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: analyze_table")
        if state.get("errors"):
            return state

        prompt_template = _load_prompt("parse_contents", state.get("domain"))

        html = state.get("html_table")
        if not html:
            errors = list(state.get("errors", []))
            errors.append("No HTML table to analyze.")
            return {**state, "errors": errors}

        try:
            prompt = prompt_template.format(html=html)
        except KeyError as e:
            errors = list(state.get("errors", []))
            errors.append(f"Analysis prompt missing placeholder: {e}")
            return {**state, "errors": errors}

        summary = _call_llm(llm, prompt)
        return {**state, "table_summary": summary}

    return _node


def generate_synthetic_table_node(llm: ChatOpenAI) -> Callable[["TableState"], "TableState"]:
    """Create a node that generates a synthetic dataset with the same structure."""

    def _node(state: "TableState") -> "TableState":
        logger.info("Entering node: generate_synthetic_table")
        if state.get("errors"):
            return state
        
        prompt_template = _load_prompt("generate_synthetic_table", state.get("domain"))
        
        html = state.get("html_table")
        summary = state.get("table_summary")

        if not html:
            errors = list(state.get("errors", []))
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
            errors = list(state.get("errors", []))
            errors.append(f"Prompt template missing placeholder: {e}")
            return {**state, "errors": errors}

        synthetic_html = _call_llm(llm, prompt)
        return {**state, "synthetic_table": synthetic_html}

    return _node


def generate_synthetic_table_from_image_node(llm: ChatOpenAI) -> Callable[["TableState"], "TableState"]:
    """Generate synthetic table directly from image (for powerful models)."""

    def _node(state: "TableState") -> "TableState":
        logger.info("Entering node: generate_synthetic_table_from_image")
        if state.get("errors"):
            return state

        prompt_template = _load_prompt("generate_synthetic_table_from_image", state.get("domain"))

        image_path = Path(state["image_path"])
        if not image_path.exists():
            errors = list(state.get("errors", []))
            errors.append(f"Image not found: {image_path}")
            return {**state, "errors": errors}

        image_data_url = _encode_image(image_path)
        
        # Prompt doesn't have placeholders, it just expects the image
        prompt = prompt_template
        
        synthetic_html = _call_llm(llm, prompt, image_urls=[image_data_url])
        return {**state, "synthetic_table": synthetic_html}

    return _node




def self_reflection_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    """
    합성 테이블 품질 검증 노드.
    1단계: SQL 기반 객관적 비교 (Pandas + pandasql)
    2단계: LLM 기반 주관적 평가 (기존 로직)
    """

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: self_reflection")
        prompt_template = _load_prompt("self_reflection", state.get("domain"))
        prompt_template_image = _load_prompt("self_reflection_from_image", state.get("domain"))

        if state.get("errors"):
            return state

        synthetic_html = state.get("synthetic_table")
        html = state.get("html_table")
        image_path = Path(state["image_path"])

        if not synthetic_html:
            errors = list(state.get("errors", []))
            errors.append("Synthetic table generation failed.")
            return {**state, "errors": errors}

        # ============================================
        # 3단계 검증 체인: pandasql → REPL → G-Eval (LLM)
        # ============================================
        validation_issues = []
        validation_passed = True
        validation_method = None
        
        if html:
            # ---- 1단계: pandasql 기반 SQL 비교 ----
            logger.info("[1/3] Running pandasql-based table comparison...")
            sql_passed, sql_issues = compare_tables_with_sql(html, synthetic_html)
            
            if sql_passed:
                logger.info("[1/3] pandasql validation PASSED")
                validation_passed = True
                validation_method = "pandasql"
            else:
                logger.warning(f"[1/3] pandasql found {len(sql_issues)} issues, trying REPL...")
                
                # ---- 2단계: LangChain REPL 기반 비교 ----
                logger.info("[2/3] Running REPL-based table comparison...")
                repl_passed, repl_issues = compare_tables_with_repl(html, synthetic_html)
                
                if repl_passed:
                    logger.info("[2/3] REPL validation PASSED (pandasql issues were false positive)")
                    validation_passed = True
                    validation_method = "repl"
                else:
                    # 두 방법 모두 실패 → 구체적인 이슈와 함께 실패 반환
                    logger.warning(f"[2/3] REPL also found issues, will proceed to G-Eval (LLM)...")
                    validation_passed = False
                    validation_issues = sql_issues + repl_issues
                    validation_method = "failed_before_geval"
                    
                    # pandasql, REPL 모두 실패시 LLM에게 넘기기 전에 
                    # 명확한 구조적 오류면 바로 실패 처리
                    structural_issues = [i for i in validation_issues 
                                        if "행 수" in i or "열 수" in i or "Shape" in i]
                    
                    if structural_issues:
                        revision_instructions = "구조적 검증에서 문제가 발견되었습니다:\n" + "\n".join(structural_issues)
                        return {
                            **state,
                            "reflection": f"Structural validation failed",
                            "reflection_json": {
                                "passed": False,
                                "validation_method": "pandasql+repl",
                                "sql_issues": sql_issues,
                                "repl_issues": repl_issues,
                                "revision_instructions": revision_instructions,
                            },
                            "revision_instructions": revision_instructions,
                            "passed": False,
                        }
                    
                    # 구조는 맞지만 데이터 불일치 → LLM G-Eval로 최종 판단
                    logger.info("[3/3] Proceeding to G-Eval (LLM) for final judgment...")

        # ============================================
        # 3단계: G-Eval - LLM 기반 주관적 평가 (기존 로직)
        # ============================================
        # If we don't have the original HTML (direct path), use the image for reflection
        if not html:
            if not image_path.exists():
                 errors = list(state.get("errors", []))
                 errors.append("Original image missing for reflection.")
                 return {**state, "errors": errors}
            
            image_data_url = _encode_image(image_path)
            try:
                prompt = prompt_template_image.format(synthetic_html=synthetic_html)
            except KeyError as e:
                errors = list(state.get("errors", []))
                errors.append(f"Reflection prompt missing placeholder: {e}")
                return {**state, "errors": errors}
            
            reflection_text = _call_llm(llm, prompt, image_urls=[image_data_url])
        
        else:
            try:
                prompt = prompt_template.format(synthetic_html=synthetic_html, html=html)
            except KeyError as e:
                errors = list(state.get("errors", []))
                errors.append(f"Prompt template missing placeholder: {e}")
                return {**state, "errors": errors}

            reflection_text = _call_llm(llm, prompt)


        reflection_json = robust_json_parse(reflection_text)
        if reflection_json is None:
            errors = list(state.get("errors", []))
            errors.append("Self-reflection did not return valid JSON.")
            return {**state, "errors": errors, "reflection": reflection_text}

        passed = bool(reflection_json.get("passed", False))
        revision_instructions = reflection_json.get("revision_instructions", "")
        
        # 검증 결과를 reflection_json에 추가
        reflection_json["validation"] = {
            "method": validation_method if validation_method else "geval",
            "passed_early": validation_passed and validation_method in ["pandasql", "repl"],
            "issues": validation_issues,
        }
        
        # pandasql 또는 REPL에서 이미 통과했으면 LLM 결과 무시하고 통과 처리
        if validation_method in ["pandasql", "repl"]:
            passed = True
            revision_instructions = ""

        return {
            **state,
            "reflection": reflection_text,
            "reflection_json": reflection_json,
            "revision_instructions": revision_instructions,
            "passed": passed,
        }

    return _node


def revise_synthetic_table_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    pass # Prompt loaded inside node

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: revise_synthetic_table")
        prompt_template = _load_prompt("revise_synthetic_table", state.get("domain"))
        prompt_template_image = _load_prompt("revise_synthetic_table_from_image", state.get("domain"))

        if state.get("errors"):
            return state

        html = state.get("html_table")
        summary = state.get("table_summary")
        synthetic_html = state.get("synthetic_table")
        instructions = state.get("revision_instructions", "")
        image_path = Path(state["image_path"])

        if not synthetic_html:
            errors = list(state.get("errors", []))
            errors.append("No synthetic table to revise.")
            return {**state, "errors": errors}

        # Check if we are in the "direct generation" path (missing html/summary)
        if not html or not summary:
            # Use image-based revision
            if not image_path.exists():
                 errors = list(state.get("errors", []))
                 errors.append("Original image missing for revision.")
                 return {**state, "errors": errors}
            
            image_data_url = _encode_image(image_path)
            try:
                prompt = prompt_template_image.format(
                    synthetic_html=synthetic_html,
                    revision_instructions=instructions
                )
            except KeyError as e:
                errors = list(state.get("errors", []))
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
                errors = list(state.get("errors", []))
                errors.append(f"Revision prompt missing placeholder: {e}")
                return {**state, "errors": errors}

            new_synthetic_html = _call_llm(llm, prompt)

        attempts = int(state.get("attempts", 0)) + 1
        return {**state, "synthetic_table": new_synthetic_html, "attempts": attempts}

    return _node


def parse_synthetic_table_node(_llm: ChatOpenAI = None) -> Callable[[TableState], TableState]:
    """
    Create a node that parses the synthetic HTML table into JSON.

    Uses rule-based parsing (BeautifulSoup) instead of LLM for performance.
    LLM parameter is kept for backward compatibility but not used.
    """

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: parse_synthetic_table (rule-based)")
        if state.get("errors"):
            return state

        synthetic_html = state.get("synthetic_table")
        if not synthetic_html:
            errors = list(state.get("errors", []))
            errors.append("No synthetic table to parse.")
            return {**state, "errors": errors}

        # 규칙 기반 파싱 (LLM 호출 없음)
        parsed_json = parse_html_table_to_json(synthetic_html)

        if parsed_json is None:
            logger.warning("Rule-based parsing failed, table structure may be invalid")
            # 파싱 실패해도 에러로 처리하지 않음 (기존 동작 유지)

        return {**state, "synthetic_json": parsed_json}

    return _node


def generate_qa_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    """Generate QA pairs based on the synthetic table."""

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: generate_qa")
        prompt_template = _load_prompt("generate_qa", state.get("domain"))

        if state.get("errors"):
            return state

        synthetic_html = state.get("synthetic_table")
        if not synthetic_html:
            errors = list(state.get("errors", []))
            errors.append("No synthetic table for QA generation.")
            return {**state, "errors": errors}

        try:
            prompt = prompt_template.format(synthetic_html=synthetic_html)
        except KeyError as e:
            errors = list(state.get("errors", []))
            errors.append(f"QA prompt missing placeholder: {e}")
            return {**state, "errors": errors}

        response_text, token_usage = _call_llm(llm, prompt, return_token_usage=True)
        
        # Debug log for token usage
        logger.info(f"QA generation token usage: {token_usage}")
        
        response_json = robust_json_parse(response_text)

        qa_results = []
        if response_json and "qa_pairs" in response_json:
            qa_results = response_json["qa_pairs"]
        else:
             logger.warning("QA generation did not return valid JSON or 'qa_pairs' key.")

        logger.info(f"Returning token_usage: {token_usage}")
        return {**state, "qa_results": qa_results, "token_usage": token_usage}

    return _node


def generate_qa_from_image_node(llm: ChatOpenAI) -> Callable[[TableState], TableState]:
    """Generate QA pairs directly from image (QA-only mode)."""

    def _node(state: TableState) -> TableState:
        logger.info("Entering node: generate_qa_from_image")
        prompt_template = _load_prompt("generate_qa_from_image", state.get("domain"))

        if state.get("errors"):
            return state

        if state.get("image_paths"):
             image_paths = [Path(p) for p in state["image_paths"]]
        else:
            image_path = Path(state["image_path"])
            if not image_path.exists():
                errors = list(state.get("errors", []))
                errors.append(f"Image not found: {image_path}")
                return {**state, "errors": errors}
            image_paths = [image_path]

        image_data_urls = []
        for img_p in image_paths:
             if img_p.exists():
                 image_data_urls.append(_encode_image(img_p))
             else:
                 logger.warning(f"Skipping missing image in batch: {img_p}")

        prompt = prompt_template

        response_text, token_usage = _call_llm(llm, prompt, image_urls=image_data_urls, return_token_usage=True)
        
        # Debug log for token usage
        logger.info(f"QA generation token usage: {token_usage}")
        
        response_json = robust_json_parse(response_text)

        qa_results = []
        if response_json and "qa_pairs" in response_json:
            qa_results = response_json["qa_pairs"]
        else:
            logger.warning("QA generation from image did not return valid JSON or 'qa_pairs' key.")

        logger.info(f"Returning token_usage: {token_usage}")
        return {**state, "qa_results": qa_results, "token_usage": token_usage}

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
        errors = list(state.get("errors", []))
        errors.append(f"Failed to load HTML file: {e}")
        return {**state, "errors": errors}


def build_synthetic_table_graph(
    llm: ChatOpenAI,
    provider: str = "openai",
    qa_only: bool = False,
    skip_qa: bool = False,
) -> StateGraph:
    """
    Assemble the LangGraph pipeline.

    Args:
        llm: LLM instance
        provider: LLM provider name
        qa_only: If True, generate QA directly from image without synthetic data generation
        skip_qa: If True, skip QA generation after table generation (table only mode)
    """

    graph = StateGraph(TableState)

    if qa_only:
        # QA-only mode: 이미지에서 직접 QA 생성 (합성 데이터 생성 스킵)
        graph.add_node("generate_qa_from_image", generate_qa_from_image_node(llm))
        graph.add_edge(START, "generate_qa_from_image")
        graph.add_edge("generate_qa_from_image", END)
    else:
        # Full pipeline mode (or table-only mode if skip_qa=True)
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

        if not skip_qa:
            graph.add_node("generate_qa", generate_qa_node(llm))

        # Routing based on provider and input type
        def route_start(state: TableState) -> str:
            image_path = Path(state["image_path"])
            if image_path.suffix.lower() == ".html":
                return "load_html_input"

            # Powerful models go direct (멀티모달 지원 모델들)
            if provider in ["openai", "gemini", "gemini_pool", "claude"]:
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

        # Final edge: skip QA if requested
        if skip_qa:
            graph.add_edge("parse_synthetic_table", END)
        else:
            graph.add_edge("parse_synthetic_table", "generate_qa")
            graph.add_edge("generate_qa", END)

    return graph


from .llm_factory import get_llm

# 전역 체크포인터 저장소 (thread_id별 상태 관리)
_checkpointer_cache: Dict[str, SqliteSaver] = {}


def get_checkpointer(
    checkpoint_dir: str | None = None,
    use_memory: bool = False,
) -> MemorySaver | SqliteSaver:
    """
    체크포인터 인스턴스를 생성하거나 캐시에서 가져옵니다.

    Args:
        checkpoint_dir: SQLite 체크포인트 파일 저장 디렉토리 (None이면 기본 경로)
        use_memory: True면 인메모리 체크포인터 사용 (테스트용)

    Returns:
        체크포인터 인스턴스
    """
    if use_memory:
        return MemorySaver()

    if checkpoint_dir is None:
        base_dir = Path(__file__).parent.parent
        checkpoint_dir = str(base_dir / "checkpoints")

    # 디렉토리 생성
    checkpoint_path = Path(checkpoint_dir)
    checkpoint_path.mkdir(parents=True, exist_ok=True)

    db_path = str(checkpoint_path / "langgraph_checkpoints.db")

    if db_path not in _checkpointer_cache:
        _checkpointer_cache[db_path] = SqliteSaver.from_conn_string(db_path)
        logger.info(f"Created checkpointer at: {db_path}")

    return _checkpointer_cache[db_path]


def generate_thread_id(image_path: str) -> str:
    """
    이미지 경로 기반으로 고유한 thread_id 생성.

    Args:
        image_path: 입력 이미지 경로

    Returns:
        8자리 해시 기반 thread_id
    """
    import hashlib
    path_hash = hashlib.md5(image_path.encode()).hexdigest()[:8]
    return path_hash


def run_synthetic_table_flow(
    image_path: str,
    *,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    base_url: str | None = None,
    config_path: str | None = None,
    azure_deployment: str | None = None,
    azure_endpoint: str | None = None,
    qa_only: bool = False,
    skip_qa: bool = False,
    image_paths: List[str] | None = None,
    domain: str | None = None,
    # 체크포인팅 옵션
    enable_checkpointing: bool = False,
    thread_id: str | None = None,
    checkpoint_dir: str | None = None,
    resume: bool = False,
) -> TableState:
    """
    Run the synthetic table generation flow.

    Args:
        image_path: Path to the input image or HTML file
        provider: LLM provider (openai, azure, gemini, gemini_pool, claude, vllm)
        model: Model name
        temperature: Sampling temperature
        base_url: Custom base URL for vLLM
        config_path: Config path for gemini_pool
        azure_deployment: Azure OpenAI deployment name
        azure_endpoint: Azure OpenAI endpoint URL
        qa_only: If True, skip synthetic data generation and only generate QA from image
        skip_qa: If True, generate table only without QA generation
        image_paths: Optional list of image paths for multi-image processing
        domain: Optional domain for prompt customization (e.g. 'public')
        enable_checkpointing: 체크포인팅 활성화 여부
        thread_id: 체크포인트 식별자 (None이면 이미지 경로 기반 자동 생성)
        checkpoint_dir: 체크포인트 저장 디렉토리
        resume: True면 기존 체크포인트에서 재개 시도

    Returns:
        Final TableState with results
    """
    load_dotenv()

    llm = get_llm(
        provider=provider,
        model=model,
        temperature=temperature,
        base_url=base_url,
        config_path=config_path,
    )

    graph = build_synthetic_table_graph(llm, provider=provider, qa_only=qa_only, skip_qa=skip_qa)

    # 체크포인팅 설정
    if enable_checkpointing:
        checkpointer = get_checkpointer(checkpoint_dir)
        app = graph.compile(checkpointer=checkpointer)

        # thread_id 설정
        if thread_id is None:
            thread_id = generate_thread_id(image_path)

        run_config = {"configurable": {"thread_id": thread_id}}
        logger.info(f"Checkpointing enabled with thread_id: {thread_id}")

        # 재개 모드
        if resume:
            existing_state = get_checkpoint_state(thread_id, checkpoint_dir)
            if existing_state:
                logger.info(f"Resuming from checkpoint: {thread_id}")
                # 기존 상태에서 재개 (invoke에 None 전달하면 마지막 상태에서 계속)
                final_state: TableState = app.invoke(None, config=run_config)
                return final_state
            else:
                logger.warning(f"No checkpoint found for thread_id: {thread_id}, starting fresh")
    else:
        app = graph.compile()
        run_config = {}

    initial_state = {
        "image_path": image_path,
        "attempts": 0,
        "errors": [],
    }
    if image_paths:
        initial_state["image_paths"] = image_paths
    if domain:
        initial_state["domain"] = domain

    final_state: TableState = app.invoke(initial_state, config=run_config if enable_checkpointing else None)
    return final_state


def get_checkpoint_state(
    thread_id: str,
    checkpoint_dir: str | None = None,
) -> Optional[TableState]:
    """
    저장된 체크포인트 상태를 조회합니다.

    Args:
        thread_id: 체크포인트 식별자
        checkpoint_dir: 체크포인트 저장 디렉토리

    Returns:
        저장된 상태 또는 None
    """
    try:
        checkpointer = get_checkpointer(checkpoint_dir)
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = checkpointer.get(config)

        if checkpoint and "channel_values" in checkpoint:
            return checkpoint["channel_values"]
        return None
    except Exception as e:
        logger.warning(f"Failed to get checkpoint state: {e}")
        return None


def list_checkpoints(checkpoint_dir: str | None = None) -> List[Dict[str, Any]]:
    """
    저장된 모든 체크포인트 목록을 반환합니다.

    Args:
        checkpoint_dir: 체크포인트 저장 디렉토리

    Returns:
        체크포인트 정보 리스트
    """
    import sqlite3

    if checkpoint_dir is None:
        base_dir = Path(__file__).parent.parent
        checkpoint_dir = str(base_dir / "checkpoints")

    db_path = Path(checkpoint_dir) / "langgraph_checkpoints.db"

    if not db_path.exists():
        return []

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # LangGraph SQLite 스키마에서 체크포인트 조회
        cursor.execute("""
            SELECT DISTINCT thread_id, created_at, parent_id
            FROM checkpoints
            ORDER BY created_at DESC
        """)

        checkpoints = []
        for row in cursor.fetchall():
            checkpoints.append({
                "thread_id": row[0],
                "created_at": row[1],
                "parent_id": row[2],
            })

        conn.close()
        return checkpoints
    except Exception as e:
        logger.warning(f"Failed to list checkpoints: {e}")
        return []


def delete_checkpoint(
    thread_id: str,
    checkpoint_dir: str | None = None,
) -> bool:
    """
    특정 체크포인트를 삭제합니다.

    Args:
        thread_id: 삭제할 체크포인트의 thread_id
        checkpoint_dir: 체크포인트 저장 디렉토리

    Returns:
        삭제 성공 여부
    """
    import sqlite3

    if checkpoint_dir is None:
        base_dir = Path(__file__).parent.parent
        checkpoint_dir = str(base_dir / "checkpoints")

    db_path = Path(checkpoint_dir) / "langgraph_checkpoints.db"

    if not db_path.exists():
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Deleted checkpoint: {thread_id}")
        return deleted_count > 0
    except Exception as e:
        logger.error(f"Failed to delete checkpoint: {e}")
        return False


def clear_all_checkpoints(checkpoint_dir: str | None = None) -> int:
    """
    모든 체크포인트를 삭제합니다.

    Args:
        checkpoint_dir: 체크포인트 저장 디렉토리

    Returns:
        삭제된 체크포인트 수
    """
    import sqlite3

    if checkpoint_dir is None:
        base_dir = Path(__file__).parent.parent
        checkpoint_dir = str(base_dir / "checkpoints")

    db_path = Path(checkpoint_dir) / "langgraph_checkpoints.db"

    if not db_path.exists():
        return 0

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        count = cursor.fetchone()[0]

        cursor.execute("DELETE FROM checkpoints")
        cursor.execute("DELETE FROM writes")

        conn.commit()
        conn.close()

        logger.info(f"Cleared {count} checkpoints")
        return count
    except Exception as e:
        logger.error(f"Failed to clear checkpoints: {e}")
        return 0


def resume_from_checkpoint(
    thread_id: str,
    *,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    base_url: str | None = None,
    config_path: str | None = None,
    qa_only: bool = False,
    checkpoint_dir: str | None = None,
) -> Optional[TableState]:
    """
    체크포인트에서 실행을 재개합니다.

    Args:
        thread_id: 재개할 체크포인트의 thread_id
        provider: LLM provider
        model: Model name
        temperature: Sampling temperature
        base_url: Custom base URL for vLLM
        config_path: Config path for gemini_pool
        qa_only: QA-only 모드 여부
        checkpoint_dir: 체크포인트 저장 디렉토리

    Returns:
        최종 상태 또는 None (체크포인트 없음)
    """
    # 기존 체크포인트 확인
    existing_state = get_checkpoint_state(thread_id, checkpoint_dir)
    if not existing_state:
        logger.error(f"No checkpoint found for thread_id: {thread_id}")
        return None

    load_dotenv()

    llm = get_llm(
        provider=provider,
        model=model,
        temperature=temperature,
        base_url=base_url,
        config_path=config_path,
    )

    graph = build_synthetic_table_graph(llm, provider=provider, qa_only=qa_only)
    checkpointer = get_checkpointer(checkpoint_dir)
    app = graph.compile(checkpointer=checkpointer)

    run_config = {"configurable": {"thread_id": thread_id}}

    logger.info(f"Resuming execution from checkpoint: {thread_id}")
    final_state: TableState = app.invoke(None, config=run_config)

    return final_state


__all__ = [
    "TableState",
    "build_synthetic_table_graph",
    "run_synthetic_table_flow",
    # 체크포인팅 API
    "get_checkpointer",
    "generate_thread_id",
    "get_checkpoint_state",
    "list_checkpoints",
    "delete_checkpoint",
    "clear_all_checkpoints",
    "resume_from_checkpoint",
]
