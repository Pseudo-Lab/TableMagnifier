from __future__ import annotations

import logging
import re
import json
from typing import Optional, Any, List, Tuple
from bs4 import BeautifulSoup
from json_repair import repair_json

try:
    import pandas as pd
    from pandasql import sqldf
    PANDAS_SQL_AVAILABLE = True
except ImportError:
    PANDAS_SQL_AVAILABLE = False
    pd = None  # type: ignore
    sqldf = None  # type: ignore

try:
    from langchain_experimental.tools import PythonREPLTool
    REPL_AVAILABLE = True
except ImportError:
    REPL_AVAILABLE = False
    PythonREPLTool = None  # type: ignore

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
    Robustly parse JSON from LLM output using json-repair.
    Handles markdown code blocks, trailing commas, and many common LLM malformations.
    """
    if not text:
        return None

    try:
        # json-repair로 복구 시도
        repaired = repair_json(text, return_objects=True)
        
        if isinstance(repaired, dict):
            return repaired
        elif isinstance(repaired, list) and len(repaired) > 0:
            # 리스트면 첫 번째 요소가 dict인지 확인
            if isinstance(repaired[0], dict):
                return repaired[0]
            return {"items": repaired}
        else:
            logger.warning(f"JSON repair returned unexpected type: {type(repaired)}")
            return None
            
    except Exception as e:
        logger.warning(f"Failed to parse JSON with json-repair: {e}")
        # Fallback 시도
        return _fallback_json_parse(text)


def _fallback_json_parse(text: str) -> Optional[dict[str, Any]]:
    """Fallback JSON parser when json-repair fails."""
    text = text.strip()
    
    # Remove markdown code blocks
    if "```" in text:
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            text = match.group(1)
    
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
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


def html_table_to_dataframe(html: str) -> Optional[Any]:
    """
    HTML 테이블을 Pandas DataFrame으로 변환.
    
    Args:
        html: HTML 테이블 문자열
        
    Returns:
        DataFrame 또는 None (변환 실패시)
    """
    if not PANDAS_SQL_AVAILABLE:
        logger.warning("pandas/pandasql not available, skipping DataFrame conversion")
        return None
    
    parsed = parse_html_table_to_json(html)
    if not parsed:
        return None
    
    try:
        headers = parsed["headers"]
        data = parsed["data"]
        
        # 컬럼명 정규화 (SQL 호환)
        clean_headers = []
        for i, h in enumerate(headers):
            # 공백, 특수문자를 언더스코어로 대체
            clean = re.sub(r'[^\w가-힣]', '_', str(h).strip())
            clean = re.sub(r'_+', '_', clean).strip('_')
            if not clean or clean[0].isdigit():
                clean = f"col_{i}"
            clean_headers.append(clean)
        
        # 중복 컬럼명 처리
        seen = {}
        final_headers = []
        for h in clean_headers:
            if h in seen:
                seen[h] += 1
                final_headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                final_headers.append(h)
        
        df = pd.DataFrame(data, columns=final_headers)
        return df
        
    except Exception as e:
        logger.error(f"DataFrame conversion failed: {e}")
        return None


def compare_tables_with_sql(
    original_html: str,
    synthetic_html: str,
) -> Tuple[bool, List[str]]:
    """
    원본 테이블과 합성 테이블을 SQL로 비교.
    
    Args:
        original_html: 원본 HTML 테이블
        synthetic_html: 합성 HTML 테이블
        
    Returns:
        (passed, issues): 검증 통과 여부와 발견된 문제 리스트
    """
    if not PANDAS_SQL_AVAILABLE:
        return True, ["pandas/pandasql not available, skipping SQL comparison"]
    
    issues = []
    
    # DataFrame 변환
    df_original = html_table_to_dataframe(original_html)
    df_synthetic = html_table_to_dataframe(synthetic_html)
    
    if df_original is None:
        issues.append("원본 테이블을 DataFrame으로 변환할 수 없습니다.")
        return False, issues
    
    if df_synthetic is None:
        issues.append("합성 테이블을 DataFrame으로 변환할 수 없습니다.")
        return False, issues
    
    # 1. 구조 검증: 행/열 수 비교
    orig_shape = df_original.shape
    synth_shape = df_synthetic.shape
    
    if orig_shape[1] != synth_shape[1]:
        issues.append(
            f"열 수 불일치: 원본={orig_shape[1]}, 합성={synth_shape[1]}"
        )
    
    if orig_shape[0] != synth_shape[0]:
        issues.append(
            f"행 수 불일치: 원본={orig_shape[0]}, 합성={synth_shape[0]}"
        )
    
    # 열 수가 다르면 SQL 비교 불가
    if orig_shape[1] != synth_shape[1]:
        return False, issues
    
    # 2. SQL 기반 데이터 검증
    try:
        # 컬럼명 통일 (비교를 위해)
        common_cols = [f"c{i}" for i in range(orig_shape[1])]
        df_original.columns = common_cols
        df_synthetic.columns = common_cols
        
        # 환경 설정 (sqldf에서 사용)
        env = {"df_original": df_original, "df_synthetic": df_synthetic}
        
        # 2-1. 숫자 컬럼 집계값 비교 (합계)
        numeric_cols = df_original.select_dtypes(include=['number']).columns.tolist()
        
        for col in numeric_cols:
            sum_query = f"""
            SELECT 
                (SELECT COALESCE(SUM(CAST({col} AS REAL)), 0) FROM df_original) as orig_sum,
                (SELECT COALESCE(SUM(CAST({col} AS REAL)), 0) FROM df_synthetic) as synth_sum
            """
            try:
                sum_result = sqldf(sum_query, env)
                orig_sum = sum_result.iloc[0]['orig_sum']
                synth_sum = sum_result.iloc[0]['synth_sum']
                
                if abs(orig_sum - synth_sum) > 0.01:  # 오차 허용
                    issues.append(
                        f"열 '{col}' 합계 불일치: 원본={orig_sum:.2f}, 합성={synth_sum:.2f}"
                    )
            except Exception:
                pass  # 숫자 변환 실패시 무시
        
        # 2-2. EXCEPT로 차이 레코드 검출 (SQLite 호환)
        all_cols_str = ", ".join(common_cols)
        diff_query = f"""
        SELECT {all_cols_str} FROM df_original
        EXCEPT
        SELECT {all_cols_str} FROM df_synthetic
        """
        try:
            diff_result = sqldf(diff_query, env)
            if len(diff_result) > 0:
                issues.append(
                    f"원본에만 있는 레코드: {len(diff_result)}개"
                )
                # 처음 3개 예시
                for idx, row in diff_result.head(3).iterrows():
                    issues.append(f"  - {dict(row)}")
        except Exception as e:
            logger.debug(f"EXCEPT query failed: {e}")
        
        # 반대 방향도 확인
        diff_query_reverse = f"""
        SELECT {all_cols_str} FROM df_synthetic
        EXCEPT
        SELECT {all_cols_str} FROM df_original
        """
        try:
            diff_result_reverse = sqldf(diff_query_reverse, env)
            if len(diff_result_reverse) > 0:
                issues.append(
                    f"합성에만 있는 레코드: {len(diff_result_reverse)}개"
                )
                for idx, row in diff_result_reverse.head(3).iterrows():
                    issues.append(f"  - {dict(row)}")
        except Exception as e:
            logger.debug(f"Reverse EXCEPT query failed: {e}")
            
    except Exception as e:
        logger.warning(f"SQL comparison failed: {e}")
        issues.append(f"SQL 비교 중 오류 발생: {e}")
    
    passed = len([i for i in issues if not i.startswith("  -")]) == 0
    return passed, issues


def compare_tables_with_repl(
    original_html: str,
    synthetic_html: str,
) -> Tuple[bool, List[str]]:
    """
    Pandas를 직접 사용하여 두 테이블을 비교.
    pandasql보다 더 유연한 비교 수행.
    
    Args:
        original_html: 원본 HTML 테이블
        synthetic_html: 합성 HTML 테이블
        
    Returns:
        (passed, issues): 검증 통과 여부와 발견된 문제 리스트
    """
    if not PANDAS_SQL_AVAILABLE:
        return True, ["pandas 사용 불가, 검증 스킵"]
    
    issues = []
    
    # DataFrame 변환
    df_original = html_table_to_dataframe(original_html)
    df_synthetic = html_table_to_dataframe(synthetic_html)
    
    if df_original is None or df_synthetic is None:
        return False, ["DataFrame 변환 실패"]
    
    try:
        # 1. Shape 비교
        if df_original.shape != df_synthetic.shape:
            issues.append(f"Shape 불일치: 원본={df_original.shape}, 합성={df_synthetic.shape}")
        
        # 2. 행 수 비교
        if len(df_original) != len(df_synthetic):
            issues.append(f"행 수 불일치: 원본={len(df_original)}, 합성={len(df_synthetic)}")
        
        # 3. 컬럼별 숫자 합계 비교
        for col in df_original.columns:
            if col in df_synthetic.columns:
                try:
                    orig_sum = pd.to_numeric(df_original[col], errors='coerce').sum()
                    synth_sum = pd.to_numeric(df_synthetic[col], errors='coerce').sum()
                    if pd.notna(orig_sum) and pd.notna(synth_sum):
                        if abs(orig_sum - synth_sum) > 0.01:
                            issues.append(f"컬럼 '{col}' 합계 불일치: 원본={orig_sum:.2f}, 합성={synth_sum:.2f}")
                except Exception:
                    pass
        
        # 4. 고유값 비교 (첫 번째 컬럼 기준)
        if len(df_original.columns) > 0 and len(df_synthetic.columns) > 0:
            orig_unique = set(df_original.iloc[:, 0].astype(str).tolist())
            synth_unique = set(df_synthetic.iloc[:, 0].astype(str).tolist())
            missing = orig_unique - synth_unique
            extra = synth_unique - orig_unique
            if missing:
                issues.append(f"누락된 항목: {list(missing)[:3]}")
            if extra:
                issues.append(f"추가된 항목: {list(extra)[:3]}")
                
    except Exception as e:
        logger.warning(f"REPL comparison failed: {e}")
        issues.append(f"비교 중 오류: {e}")
    
    return len(issues) == 0, issues
