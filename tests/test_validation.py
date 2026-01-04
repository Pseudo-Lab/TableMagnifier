"""3단계 검증 체인 테스트 스크립트 (standalone)"""

import re
import logging
from typing import Optional, Any, List, Tuple
from bs4 import BeautifulSoup

# pandas/pandasql import
try:
    import pandas as pd
    from pandasql import sqldf
    PANDAS_SQL_AVAILABLE = True
except ImportError:
    PANDAS_SQL_AVAILABLE = False
    pd = None
    sqldf = None

# REPL import
try:
    from langchain_experimental.tools import PythonREPLTool
    REPL_AVAILABLE = True
except ImportError:
    REPL_AVAILABLE = False
    PythonREPLTool = None

logger = logging.getLogger(__name__)


def parse_html_table_to_json(html: str) -> Optional[dict]:
    """HTML 테이블을 JSON으로 파싱"""
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return None

        rows = table.find_all("tr")
        if not rows:
            return None

        max_cols = 0
        for row in rows:
            cols = sum(int(cell.get("colspan", 1)) for cell in row.find_all(["td", "th"]))
            max_cols = max(max_cols, cols)

        if max_cols == 0:
            return None

        grid = []
        for row_idx, row in enumerate(rows):
            while len(grid) <= row_idx:
                grid.append([None] * max_cols)

            col_idx = 0
            for cell in row.find_all(["td", "th"]):
                while col_idx < max_cols and grid[row_idx][col_idx] is not None:
                    col_idx += 1

                if col_idx >= max_cols:
                    break

                cell_text = cell.get_text(strip=True)
                colspan = int(cell.get("colspan", 1))
                rowspan = int(cell.get("rowspan", 1))

                for r in range(rowspan):
                    for c in range(colspan):
                        target_row = row_idx + r
                        target_col = col_idx + c
                        while len(grid) <= target_row:
                            grid.append([None] * max_cols)
                        if target_col < max_cols:
                            grid[target_row][target_col] = cell_text

                col_idx += colspan

        raw_rows = [[cell if cell is not None else "" for cell in row] for row in grid]
        if not raw_rows:
            return None

        has_header = bool(rows[0].find_all("th"))
        
        if has_header and len(raw_rows) > 1:
            headers = raw_rows[0]
            data = raw_rows[1:]
        else:
            headers = [f"col_{i+1}" for i in range(len(raw_rows[0]))]
            data = raw_rows

        return {"headers": headers, "data": data, "raw_rows": raw_rows}
    except Exception as e:
        logger.error(f"HTML parsing failed: {e}")
        return None


def html_table_to_dataframe(html: str) -> Optional[Any]:
    """HTML 테이블을 DataFrame으로 변환"""
    if not PANDAS_SQL_AVAILABLE:
        return None
    
    parsed = parse_html_table_to_json(html)
    if not parsed:
        return None
    
    try:
        headers = parsed["headers"]
        data = parsed["data"]
        
        clean_headers = []
        for i, h in enumerate(headers):
            clean = re.sub(r'[^\w가-힣]', '_', str(h).strip())
            clean = re.sub(r'_+', '_', clean).strip('_')
            if not clean or clean[0].isdigit():
                clean = f"col_{i}"
            clean_headers.append(clean)
        
        seen = {}
        final_headers = []
        for h in clean_headers:
            if h in seen:
                seen[h] += 1
                final_headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                final_headers.append(h)
        
        return pd.DataFrame(data, columns=final_headers)
    except Exception as e:
        logger.error(f"DataFrame conversion failed: {e}")
        return None


def compare_tables_with_sql(original_html: str, synthetic_html: str) -> Tuple[bool, List[str]]:
    """pandasql로 두 테이블 비교"""
    if not PANDAS_SQL_AVAILABLE:
        return True, ["pandas/pandasql not available"]
    
    issues = []
    
    df_original = html_table_to_dataframe(original_html)
    df_synthetic = html_table_to_dataframe(synthetic_html)
    
    if df_original is None:
        return False, ["원본 테이블 변환 실패"]
    if df_synthetic is None:
        return False, ["합성 테이블 변환 실패"]
    
    orig_shape = df_original.shape
    synth_shape = df_synthetic.shape
    
    if orig_shape[1] != synth_shape[1]:
        issues.append(f"열 수 불일치: 원본={orig_shape[1]}, 합성={synth_shape[1]}")
    
    if orig_shape[0] != synth_shape[0]:
        issues.append(f"행 수 불일치: 원본={orig_shape[0]}, 합성={synth_shape[0]}")
    
    if orig_shape[1] != synth_shape[1]:
        return False, issues
    
    try:
        common_cols = [f"c{i}" for i in range(orig_shape[1])]
        df_original.columns = common_cols
        df_synthetic.columns = common_cols
        
        env = {"df_original": df_original, "df_synthetic": df_synthetic}
        
        numeric_cols = df_original.select_dtypes(include=['number']).columns.tolist()
        
        for col in numeric_cols:
            try:
                sum_query = f"""
                SELECT 
                    (SELECT COALESCE(SUM(CAST({col} AS REAL)), 0) FROM df_original) as orig_sum,
                    (SELECT COALESCE(SUM(CAST({col} AS REAL)), 0) FROM df_synthetic) as synth_sum
                """
                sum_result = sqldf(sum_query, env)
                orig_sum = sum_result.iloc[0]['orig_sum']
                synth_sum = sum_result.iloc[0]['synth_sum']
                
                if abs(orig_sum - synth_sum) > 0.01:
                    issues.append(f"열 '{col}' 합계 불일치: 원본={orig_sum:.2f}, 합성={synth_sum:.2f}")
            except:
                pass
                
    except Exception as e:
        issues.append(f"SQL 비교 오류: {e}")
    
    passed = len([i for i in issues if not i.startswith("  -")]) == 0
    return passed, issues


def compare_tables_with_repl(original_html: str, synthetic_html: str) -> Tuple[bool, List[str]]:
    """REPL로 두 테이블 비교"""
    if not REPL_AVAILABLE or not PANDAS_SQL_AVAILABLE:
        return True, ["REPL 사용 불가"]
    
    df_original = html_table_to_dataframe(original_html)
    df_synthetic = html_table_to_dataframe(synthetic_html)
    
    if df_original is None or df_synthetic is None:
        return False, ["DataFrame 변환 실패"]
    
    issues = []
    
    try:
        # Shape 비교
        if df_original.shape != df_synthetic.shape:
            issues.append(f"Shape 불일치: 원본={df_original.shape}, 합성={df_synthetic.shape}")
        
        # 행 수 비교
        if len(df_original) != len(df_synthetic):
            issues.append(f"행 수 불일치: 원본={len(df_original)}, 합성={len(df_synthetic)}")
        
        # 숫자 컬럼 합계 비교
        for col in df_original.columns:
            if col in df_synthetic.columns:
                try:
                    orig_sum = pd.to_numeric(df_original[col], errors='coerce').sum()
                    synth_sum = pd.to_numeric(df_synthetic[col], errors='coerce').sum()
                    if pd.notna(orig_sum) and pd.notna(synth_sum):
                        if abs(orig_sum - synth_sum) > 0.01:
                            issues.append(f"컬럼 '{col}' 합계 불일치: 원본={orig_sum:.2f}, 합성={synth_sum:.2f}")
                except:
                    pass
                    
    except Exception as e:
        issues.append(f"REPL 비교 오류: {e}")
    
    return len(issues) == 0, issues

print("=" * 60)
print("3단계 검증 체인 테스트")
print("=" * 60)

# 패키지 상태 확인
print(f"\n📦 패키지 상태:")
print(f"  - pandas/pandasql: {'✅ 사용 가능' if PANDAS_SQL_AVAILABLE else '❌ 없음'}")
print(f"  - langchain REPL: {'✅ 사용 가능' if REPL_AVAILABLE else '❌ 없음'}")

# 테스트용 HTML 테이블
original_html = """
<table>
    <thead>
        <tr><th>이름</th><th>나이</th><th>점수</th></tr>
    </thead>
    <tbody>
        <tr><td>김철수</td><td>25</td><td>85</td></tr>
        <tr><td>이영희</td><td>30</td><td>92</td></tr>
        <tr><td>박민수</td><td>28</td><td>78</td></tr>
    </tbody>
</table>
"""

# 테스트 1: 동일한 테이블 비교 (PASS 예상)
print("\n" + "=" * 60)
print("테스트 1: 동일한 테이블 비교 (PASS 예상)")
print("=" * 60)

identical_synthetic = """
<table>
    <tr><th>이름</th><th>나이</th><th>점수</th></tr>
    <tr><td>김철수</td><td>25</td><td>85</td></tr>
    <tr><td>이영희</td><td>30</td><td>92</td></tr>
    <tr><td>박민수</td><td>28</td><td>78</td></tr>
</table>
"""

print("\n[1/3] pandasql 검증...")
passed, issues = compare_tables_with_sql(original_html, identical_synthetic)
print(f"  결과: {'✅ PASS' if passed else '❌ FAIL'}")
if issues:
    print(f"  이슈: {issues}")

print("\n[2/3] REPL 검증...")
passed, issues = compare_tables_with_repl(original_html, identical_synthetic)
print(f"  결과: {'✅ PASS' if passed else '❌ FAIL'}")
if issues:
    print(f"  이슈: {issues}")

# 테스트 2: 행 수가 다른 테이블 (FAIL 예상)
print("\n" + "=" * 60)
print("테스트 2: 행 수가 다른 테이블 (FAIL 예상)")
print("=" * 60)

different_rows = """
<table>
    <tr><th>이름</th><th>나이</th><th>점수</th></tr>
    <tr><td>김철수</td><td>25</td><td>85</td></tr>
    <tr><td>이영희</td><td>30</td><td>92</td></tr>
</table>
"""

print("\n[1/3] pandasql 검증...")
passed, issues = compare_tables_with_sql(original_html, different_rows)
print(f"  결과: {'✅ PASS' if passed else '❌ FAIL'}")
if issues:
    for issue in issues[:5]:
        print(f"  - {issue}")

print("\n[2/3] REPL 검증...")
passed, issues = compare_tables_with_repl(original_html, different_rows)
print(f"  결과: {'✅ PASS' if passed else '❌ FAIL'}")
if issues:
    for issue in issues[:5]:
        print(f"  - {issue}")

# 테스트 3: 숫자 값이 다른 테이블 (FAIL 예상)
print("\n" + "=" * 60)
print("테스트 3: 숫자 값이 다른 테이블 (FAIL 예상)")
print("=" * 60)

different_values = """
<table>
    <tr><th>이름</th><th>나이</th><th>점수</th></tr>
    <tr><td>김철수</td><td>25</td><td>90</td></tr>
    <tr><td>이영희</td><td>30</td><td>95</td></tr>
    <tr><td>박민수</td><td>28</td><td>80</td></tr>
</table>
"""

print("\n[1/3] pandasql 검증...")
passed, issues = compare_tables_with_sql(original_html, different_values)
print(f"  결과: {'✅ PASS' if passed else '❌ FAIL'}")
if issues:
    for issue in issues[:5]:
        print(f"  - {issue}")

print("\n[2/3] REPL 검증...")
passed, issues = compare_tables_with_repl(original_html, different_values)
print(f"  결과: {'✅ PASS' if passed else '❌ FAIL'}")
if issues:
    for issue in issues[:5]:
        print(f"  - {issue}")

# DataFrame 변환 테스트
print("\n" + "=" * 60)
print("DataFrame 변환 테스트")
print("=" * 60)

df = html_table_to_dataframe(original_html)
if df is not None:
    print(f"\n변환된 DataFrame:")
    print(df)
    print(f"\nShape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
else:
    print("❌ DataFrame 변환 실패")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)
