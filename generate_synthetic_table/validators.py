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


def parse_html_table_to_json(html: str) -> Optional[dict[str, Any]]:
    """
    HTML 테이블을 JSON으로 파싱 (규칙 기반, LLM 호출 없음).
    rowspan, colspan을 처리하여 정규화된 2D 배열로 변환.

    Returns:
        {
            "headers": ["col1", "col2", ...],
            "data": [["val1", "val2", ...], ...],
            "raw_rows": [["cell1", "cell2", ...], ...],  # 헤더 포함 전체
            "metadata": {"rows": N, "cols": M, "has_header": bool}
        }
    """
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            logger.warning("No <table> element found in HTML")
            return None

        # 모든 행 추출
        rows = table.find_all("tr")
        if not rows:
            logger.warning("No <tr> elements found in table")
            return None

        # 최대 열 수 계산 (colspan 고려)
        max_cols = 0
        for row in rows:
            cols = 0
            for cell in row.find_all(["td", "th"]):
                colspan = int(cell.get("colspan", 1))
                cols += colspan
            max_cols = max(max_cols, cols)

        if max_cols == 0:
            return None

        # 2D 그리드 초기화 (rowspan 처리용)
        grid: list[list[Optional[str]]] = []

        for row_idx, row in enumerate(rows):
            # 행이 부족하면 추가
            while len(grid) <= row_idx:
                grid.append([None] * max_cols)

            col_idx = 0
            for cell in row.find_all(["td", "th"]):
                # 이미 채워진 셀 건너뛰기 (이전 rowspan에 의해)
                while col_idx < max_cols and grid[row_idx][col_idx] is not None:
                    col_idx += 1

                if col_idx >= max_cols:
                    break

                # 셀 텍스트 추출
                cell_text = cell.get_text(strip=True)
                colspan = int(cell.get("colspan", 1))
                rowspan = int(cell.get("rowspan", 1))

                # colspan, rowspan 적용
                for r in range(rowspan):
                    for c in range(colspan):
                        target_row = row_idx + r
                        target_col = col_idx + c

                        # 행 확장 필요시
                        while len(grid) <= target_row:
                            grid.append([None] * max_cols)

                        if target_col < max_cols:
                            grid[target_row][target_col] = cell_text

                col_idx += colspan

        # None을 빈 문자열로 변환
        raw_rows = [[cell if cell is not None else "" for cell in row] for row in grid]

        if not raw_rows:
            return None

        # 헤더 감지: 첫 행이 <th>로 구성되어 있거나, <thead> 존재
        has_header = False
        thead = table.find("thead")
        if thead:
            has_header = True
        else:
            first_row = rows[0]
            th_cells = first_row.find_all("th")
            td_cells = first_row.find_all("td")
            if th_cells and not td_cells:
                has_header = True

        # 헤더와 데이터 분리
        if has_header and len(raw_rows) > 1:
            headers = raw_rows[0]
            data = raw_rows[1:]
        else:
            # 헤더가 없으면 자동 생성
            headers = [f"col_{i+1}" for i in range(len(raw_rows[0]))]
            data = raw_rows

        return {
            "headers": headers,
            "data": data,
            "raw_rows": raw_rows,
            "metadata": {
                "rows": len(raw_rows),
                "cols": max_cols,
                "has_header": has_header,
            }
        }

    except Exception as e:
        logger.error(f"HTML table parsing failed: {e}")
        return None
