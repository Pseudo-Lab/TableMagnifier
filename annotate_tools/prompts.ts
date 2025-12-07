export const TABLE_ANALYSIS_PROMPT = `
    You are an expert in analyzing tables. Your task is to process an image containing a table with Korean text.
    1.  Perform OCR to accurately extract all text from the table. Preserve the structure and content as closely as possible.
    2.  Based on the extracted text, generate a set of 5 to 7 insightful question-and-answer pairs that cover the key information in the table.
    3.  Return the result as a single JSON object.
  `;
