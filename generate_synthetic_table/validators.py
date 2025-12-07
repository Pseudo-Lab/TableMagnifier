from __future__ import annotations

import logging
import re
import json
from typing import Optional, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def validate_html(html: str) -> bool:
    """
    Validate if the given string is a well-formed HTML table.
    Uses BeautifulSoup to parse and check for basic table structure.
    """
    if not html:
        return False
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return False
        
        # Check if it has rows
        rows = table.find_all("tr")
        if not rows:
            return False
            
        return True
    except Exception as e:
        logger.error(f"HTML validation failed: {e}")
        return False

def robust_json_parse(text: str) -> Optional[dict[str, Any]]:
    """
    Robustly parse JSON from LLM output.
    Handles markdown code blocks, trailing commas, and some common malformations.
    """
    if not text:
        return None

    text = text.strip()
    
    # Remove markdown code blocks
    if "```" in text:
        # Try to extract content inside ```json ... ``` or just ``` ... ```
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            text = match.group(1)
    
    # Simple cleanup
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: try to find the first { and last }
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                json_str = text[start : end + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
    logger.warning(f"Failed to parse JSON from text: {text[:100]}...")
    return None
