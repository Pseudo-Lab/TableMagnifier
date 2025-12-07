import pytest
from generate_synthetic_table.validators import robust_json_parse, validate_html

def test_robust_json_parse_valid():
    assert robust_json_parse('{"a": 1}') == {"a": 1}

def test_robust_json_parse_markdown():
    text = """
    Here is the json:
    ```json
    {
        "key": "value"
    }
    ```
    """
    assert robust_json_parse(text) == {"key": "value"}

def test_robust_json_parse_markdown_no_lang():
    text = """
    ```
    {"x": [1, 2]}
    ```
    """
    assert robust_json_parse(text) == {"x": [1, 2]}

def test_robust_json_parse_dirty():
    text = "Sure! {\"a\": 1} is the answer."
    assert robust_json_parse(text) == {"a": 1}

def test_validate_html_valid():
    html = "<table><tr><td>Cell</td></tr></table>"
    assert validate_html(html) is True

def test_validate_html_invalid_structure():
    html = "<div>Not a table</div>"
    assert validate_html(html) is False

def test_validate_html_empty():
    assert validate_html("") is False
