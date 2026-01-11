import { GoogleGenAI, Type } from "@google/genai";
import { AnalysisResult } from '../types';
import { TABLE_ANALYSIS_PROMPT } from '../prompts';

const fileToGenerativePart = (base64Data: string, mimeType: string) => {
  return {
    inlineData: {
      data: base64Data,
      mimeType,
    },
  };
};

export async function analyzeImage(apiKey: string, base64Image: string, mimeType: string): Promise<AnalysisResult> {
  if (!apiKey) {
    throw new Error("API key is missing.");
  }
  
  const ai = new GoogleGenAI({ apiKey });
  const model = 'gemini-2.5-flash';

  const imagePart = fileToGenerativePart(base64Image, mimeType);

  const prompt = TABLE_ANALYSIS_PROMPT;

  const schema = {
    type: Type.OBJECT,
    properties: {
      ocrResult: {
        type: Type.STRING,
        description: "The full text extracted from the table in the image, preserving formatting like newlines.",
      },
      qaSet: {
        type: Type.ARRAY,
        description: "A set of question and answer pairs derived from the table's content.",
        items: {
          type: Type.OBJECT,
          properties: {
            question: {
              type: Type.STRING,
              description: "A question about the content of the table.",
            },
            answer: {
              type: Type.STRING,
              description: "The corresponding answer based on the table's content.",
            },
          },
          required: ["question", "answer"],
        },
      },
    },
    required: ["ocrResult", "qaSet"],
  };

  try {
    const response = await ai.models.generateContent({
      model,
      contents: { parts: [{ text: prompt }, imagePart] },
      config: {
        responseMimeType: "application/json",
        responseSchema: schema,
      },
    });

    const responseText = response.text.trim();
    const result = JSON.parse(responseText);

    return result as AnalysisResult;

  } catch (error) {
    console.error("Error analyzing image with Gemini:", error);
    if (error instanceof Error && /API.?key.?not.?valid/i.test(error.message)) {
      throw new Error("Your API key is not valid. Please check it and try again.");
    }
    throw new Error("Failed to analyze the image. The AI model could not process the request.");
  }
}
