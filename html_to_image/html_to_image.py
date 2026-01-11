!pip install -q google-genai imgkit
!apt-get -y install wkhtmltopdf
# 한글 폰트 설치
!apt-get update
!apt-get install -y fonts-noto-cjk
!fc-cache -fv

import os
from google import genai
from google.genai import types
from google.colab import files
from IPython.display import Image as ColabImage, display
import imgkit

# 여기에 본인 Gemini API 키 입력
os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

image_path = '/content/drive/MyDrive/TableMagnifier/Academic/Table/A_origin_0/A_table_0.png' # 업로드한 이미지 경로

prompt = """
You are converting a picture of a table into a clean HTML document.

Requirements:
- Look at the image and detect the table structure (rows, columns, header cells, merged cells if any).
- Output a full HTML document (<html>...</html>).
- In the <head> section, include this TailwindCSS CDN link ONLY (no other CSS):

<link
  href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css"
  rel="stylesheet"
/>

- In the <body>, center the table on a light gray background, and wrap it in a white card with padding, rounded corners, and shadow using Tailwind classes.
- Style the table to look as similar as reasonably possible to the original:
  - borders between cells
  - header background slightly different
  - text alignment similar to the image
- Use ONLY Tailwind utility classes, do not write <style> tags or custom CSS.
- Return ONLY valid HTML (no backticks, no markdown, no explanations).
"""

# 파일을 Gemini에 업로드 (이미지 파일도 파일로 취급)
uploaded_file = client.files.upload(file=image_path)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        prompt,
        uploaded_file,
    ],
)
# html 코드 추출 및 저장
html_code = response.text
html_filename = "table_tailwind.html"
with open(html_filename, "w", encoding="utf-8") as f:
    f.write(html_code)
print(f"HTML이 {html_filename} 파일로 저장되었습니다.")
files.download(html_filename)  # 원하면 HTML도 내려받아서 브라우저에서 열어보기
html_filename = "table_tailwind.html"
with open(html_filename, "w", encoding="utf-8") as f:
    f.write(html_code)

# HTML을 이미지로 변환
config = imgkit.config(wkhtmltoimage="/usr/bin/wkhtmltoimage")
output_img = "table_rendered.png"
imgkit.from_file(html_filename, output_img, config=config)
print("렌더링된 이미지 파일:", output_img)
display(ColabImage(filename=output_img))
files.download(output_img)