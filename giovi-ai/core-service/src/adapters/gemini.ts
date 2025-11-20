import axios from "axios";

import { loadEnvironment } from "@config/env";

export interface GeminiResponse {
  text: string;
  toolCalls?: Array<{ name: string; arguments: Record<string, unknown> }>;
}

export class GeminiAdapter {
  private readonly apiKey: string;

  constructor() {
    const env = loadEnvironment();
    this.apiKey = env.GEMINI_API_KEY_SECRET ?? "";
  }

  async generate(prompt: string, context?: Record<string, unknown>): Promise<GeminiResponse> {
    if (!this.apiKey) {
      throw new Error("GEMINI_API_KEY_SECRET missing");
    }
    const response = await axios.post(
      "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
      {
        contents: [
          {
            role: "user",
            parts: [{ text: prompt }],
          },
        ],
        safetySettings: [{ category: "HARM_CATEGORY_HATE_SPEECH", threshold: "BLOCK_MEDIUM_AND_ABOVE" }],
        generationConfig: {
          temperature: 0.4,
        },
        ...(context ? { tools: context.tools } : {}),
      },
      {
        params: { key: this.apiKey },
      },
    );

    const text = response.data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    const toolCalls = response.data?.candidates?.[0]?.content?.parts?.[0]?.functionCall
      ? [
          {
            name: response.data.candidates[0].content.parts[0].functionCall.name,
            arguments: response.data.candidates[0].content.parts[0].functionCall.args ?? {},
          },
        ]
      : undefined;

    return { text, toolCalls };
  }
}

let geminiAdapterInstance: GeminiAdapter | null = null;

export function getGeminiAdapter() {
  if (!geminiAdapterInstance) {
    geminiAdapterInstance = new GeminiAdapter();
  }
  return geminiAdapterInstance;
}


