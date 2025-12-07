
from pathlib import Path
import pytest
from generate_synthetic_table.html_to_image import capture_html_as_image

def test_capture_html_as_image(tmp_path):
    html = """
    <html>
    <head>
        <style>
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid black; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h2>Test Table</h2>
        <table>
            <tr>
                <th>Name</th>
                <th>Age</th>
            </tr>
            <tr>
                <td>Alice</td>
                <td>30</td>
            </tr>
            <tr>
                <td>Bob</td>
                <td>25</td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    output_path = tmp_path / "test_table.png"
    capture_html_as_image(html, output_path)
    
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    print(f"Image saved to {output_path}")
