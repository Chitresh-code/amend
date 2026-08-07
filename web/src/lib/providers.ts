// ponytail: static mirror of ENABLED_MODEL_PROVIDERS until GET /v1/models exists
// to serve this from the deployment's actual configured provider/model list.
export interface ProviderMeta {
  key: string;
  name: string;
  models: string[];
}

export const PROVIDERS: ProviderMeta[] = [
  { key: 'anthropic', name: 'Anthropic', models: ['claude-sonnet-4-5', 'claude-opus-4-1'] },
  { key: 'openai', name: 'OpenAI', models: ['gpt-5', 'gpt-5-mini'] },
  { key: 'gemini', name: 'Gemini', models: ['gemini-2.5-pro'] },
  { key: 'ollama', name: 'Ollama (local)', models: ['llama3.1'] },
];
