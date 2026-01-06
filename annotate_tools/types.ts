
export interface QAPair {
  question: string;
  answer: string;
}

export interface AnalysisResult {
  ocrResult: string;
  qaSet: QAPair[];
}

export interface TableGenerationResult {
  image_path: string;
  html_table: string;
  synthetic_table: string;
  synthetic_json: any;
  qa_results: any[];
}
