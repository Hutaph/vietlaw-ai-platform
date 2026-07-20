import { AI_MODELS, AI_PROVIDERS, DEFAULT_MODEL } from './constants';
import type {
  InferenceProviderId,
  InferenceRoleId,
  InferenceRoleSetting,
  InferenceRoleSettings,
  ProviderCredentialSettings,
} from './types';

export interface AISettings {
  model: string;
  temperature: number;
  maxTokens: number;
  topK: number;
  candidateK: number;
  cacheThreshold: number;
  maxSubqueries: number;
  historyMessages: number;
  contextTokenBudget: number;
  maxCitations: number;
  llmTimeout: number;
  streaming: boolean;
  useHistoryForRewriter: boolean;
  enableQueryRewriter: boolean;
  enableReranker: boolean;
  enableSemanticCache: boolean;
  enableMemory: boolean;
  providerCredentials: ProviderCredentialSettings;
  roles: InferenceRoleSettings;
  useSameModelForHelperRoles: boolean;
  useServerFallbacks: boolean;
}

export const AI_SETTINGS_STORAGE_KEY = 'vietlaw_ai_settings';
export const AI_SESSION_CREDENTIALS_STORAGE_KEY = 'vietlaw_ai_session_credentials';
export const AI_SETTINGS_UPDATED_EVENT = 'vietlaw-ai-settings-updated';

const DEFAULT_ROLE: InferenceRoleSetting = {
  provider: 'google',
  model: DEFAULT_MODEL,
};

export const DEFAULT_AI_SETTINGS: AISettings = {
  model: DEFAULT_MODEL,
  temperature: 0.3,
  maxTokens: 1024,
  topK: 5,
  candidateK: 10,
  cacheThreshold: 0.95,
  maxSubqueries: 3,
  historyMessages: 4,
  contextTokenBudget: 6000,
  maxCitations: 5,
  llmTimeout: 300,
  streaming: true,
  useHistoryForRewriter: true,
  enableQueryRewriter: true,
  enableReranker: true,
  enableSemanticCache: true,
  enableMemory: true,
  providerCredentials: {
    google: { apiKey: '', remember: true },
    huggingface: { apiKey: '', remember: true },
  },
  roles: {
    answer: { ...DEFAULT_ROLE },
    rewriter: { ...DEFAULT_ROLE },
    summarizer: { ...DEFAULT_ROLE },
  },
  useSameModelForHelperRoles: true,
  useServerFallbacks: true,
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

export function getModelProvider(modelId: string): InferenceProviderId {
  return AI_MODELS.find(model => model.id === modelId)?.provider ?? 'huggingface';
}

export function isProviderSupported(provider: string): provider is InferenceProviderId {
  return AI_PROVIDERS.some(item => item.id === provider);
}

export function getModelsForProvider(provider: InferenceProviderId) {
  return AI_MODELS.filter(model => model.provider === provider);
}

function normalizeRole(value: Partial<InferenceRoleSetting> | null | undefined): InferenceRoleSetting {
  const provider = isProviderSupported(String(value?.provider ?? ''))
    ? value?.provider as InferenceProviderId
    : getModelProvider(String(value?.model ?? DEFAULT_MODEL));
  const fallbackModel = getModelsForProvider(provider)[0]?.id ?? DEFAULT_MODEL;
  const model = AI_MODELS.some(item => item.provider === provider && item.id === value?.model)
    ? String(value?.model)
    : fallbackModel;
  return { provider, model };
}

function normalizeCredentials(value: Partial<ProviderCredentialSettings> | null | undefined): ProviderCredentialSettings {
  return {
    google: {
      apiKey: typeof value?.google?.apiKey === 'string' ? value.google.apiKey : '',
      remember: value?.google?.remember ?? true,
    },
    huggingface: {
      apiKey: typeof value?.huggingface?.apiKey === 'string' ? value.huggingface.apiKey : '',
      remember: value?.huggingface?.remember ?? true,
    },
  };
}

function mergeSessionCredentials(settings: AISettings): AISettings {
  if (typeof window === 'undefined') return settings;
  try {
    const raw = window.sessionStorage.getItem(AI_SESSION_CREDENTIALS_STORAGE_KEY);
    if (!raw) return settings;
    const sessionCredentials = normalizeCredentials(JSON.parse(raw));
    const currentGoogle = settings.providerCredentials.google ?? { apiKey: '', remember: true };
    const currentHuggingFace = settings.providerCredentials.huggingface ?? { apiKey: '', remember: true };
    return {
      ...settings,
      providerCredentials: {
        ...settings.providerCredentials,
        google: sessionCredentials.google?.apiKey
          ? { ...currentGoogle, apiKey: sessionCredentials.google.apiKey }
          : currentGoogle,
        huggingface: sessionCredentials.huggingface?.apiKey
          ? { ...currentHuggingFace, apiKey: sessionCredentials.huggingface.apiKey }
          : currentHuggingFace,
      },
    };
  } catch {
    return settings;
  }
}

export function normalizeAISettings(value: Partial<AISettings> | null | undefined): AISettings {
  const legacyModel = typeof value?.model === 'string' && value.model ? value.model : DEFAULT_AI_SETTINGS.model;
  const answer = normalizeRole(value?.roles?.answer ?? {
    provider: getModelProvider(legacyModel),
    model: legacyModel,
  });
  const useSameModelForHelperRoles = value?.useSameModelForHelperRoles ?? DEFAULT_AI_SETTINGS.useSameModelForHelperRoles;
  const roles = {
    answer,
    rewriter: useSameModelForHelperRoles ? { ...answer } : normalizeRole(value?.roles?.rewriter),
    summarizer: useSameModelForHelperRoles ? { ...answer } : normalizeRole(value?.roles?.summarizer),
  };

  return {
    model: roles.answer.model,
    temperature: clamp(Number(value?.temperature ?? DEFAULT_AI_SETTINGS.temperature), 0, 1),
    maxTokens: Math.round(clamp(Number(value?.maxTokens ?? DEFAULT_AI_SETTINGS.maxTokens), 100, 4000)),
    topK: Math.round(clamp(Number(value?.topK ?? DEFAULT_AI_SETTINGS.topK), 1, 20)),
    candidateK: Math.round(clamp(Number(value?.candidateK ?? DEFAULT_AI_SETTINGS.candidateK), 10, 100)),
    cacheThreshold: clamp(Number(value?.cacheThreshold ?? DEFAULT_AI_SETTINGS.cacheThreshold), 0.8, 0.99),
    maxSubqueries: Math.round(clamp(Number(value?.maxSubqueries ?? DEFAULT_AI_SETTINGS.maxSubqueries), 1, 5)),
    historyMessages: Math.round(clamp(Number(value?.historyMessages ?? DEFAULT_AI_SETTINGS.historyMessages), 0, 10)),
    contextTokenBudget: Math.round(clamp(Number(value?.contextTokenBudget ?? DEFAULT_AI_SETTINGS.contextTokenBudget), 1000, 16000)),
    maxCitations: Math.round(clamp(Number(value?.maxCitations ?? DEFAULT_AI_SETTINGS.maxCitations), 1, 10)),
    llmTimeout: Math.round(clamp(Number(value?.llmTimeout ?? DEFAULT_AI_SETTINGS.llmTimeout), 30, 300)),
    streaming: value?.streaming ?? DEFAULT_AI_SETTINGS.streaming,
    useHistoryForRewriter: value?.useHistoryForRewriter ?? DEFAULT_AI_SETTINGS.useHistoryForRewriter,
    enableQueryRewriter: value?.enableQueryRewriter ?? DEFAULT_AI_SETTINGS.enableQueryRewriter,
    enableReranker: value?.enableReranker ?? DEFAULT_AI_SETTINGS.enableReranker,
    enableSemanticCache: value?.enableSemanticCache ?? DEFAULT_AI_SETTINGS.enableSemanticCache,
    enableMemory: value?.enableMemory ?? DEFAULT_AI_SETTINGS.enableMemory,
    providerCredentials: normalizeCredentials(value?.providerCredentials),
    roles,
    useSameModelForHelperRoles,
    useServerFallbacks: value?.useServerFallbacks ?? DEFAULT_AI_SETTINGS.useServerFallbacks,
  };
}

export function readAISettings(): AISettings {
  if (typeof window === 'undefined') return DEFAULT_AI_SETTINGS;

  try {
    const raw = window.localStorage.getItem(AI_SETTINGS_STORAGE_KEY);
    const settings = raw ? normalizeAISettings(JSON.parse(raw)) : DEFAULT_AI_SETTINGS;
    return mergeSessionCredentials(settings);
  } catch {
    return DEFAULT_AI_SETTINGS;
  }
}

function splitCredentialStorage(settings: AISettings) {
  const google = settings.providerCredentials.google ?? { apiKey: '', remember: true };
  const huggingface = settings.providerCredentials.huggingface ?? { apiKey: '', remember: true };
  const localSettings: AISettings = {
    ...settings,
    providerCredentials: {
      ...settings.providerCredentials,
      google: google.remember ? google : { ...google, apiKey: '' },
      huggingface: huggingface.remember ? huggingface : { ...huggingface, apiKey: '' },
    },
  };

  const sessionCredentials: ProviderCredentialSettings = {
    google: google.remember
      ? { apiKey: '', remember: true }
      : google,
    huggingface: huggingface.remember
      ? { apiKey: '', remember: true }
      : huggingface,
  };

  return { localSettings, sessionCredentials };
}

export function persistAISettings(settings: AISettings): AISettings {
  const normalized = normalizeAISettings(settings);
  const { localSettings, sessionCredentials } = splitCredentialStorage(normalized);
  window.localStorage.setItem(AI_SETTINGS_STORAGE_KEY, JSON.stringify(localSettings));
  window.sessionStorage.setItem(AI_SESSION_CREDENTIALS_STORAGE_KEY, JSON.stringify(sessionCredentials));
  window.dispatchEvent(new CustomEvent(AI_SETTINGS_UPDATED_EVENT, { detail: normalized }));
  return normalized;
}

export function clearInferenceSettings() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(AI_SETTINGS_STORAGE_KEY);
  window.sessionStorage.removeItem(AI_SESSION_CREDENTIALS_STORAGE_KEY);
  window.dispatchEvent(new CustomEvent(AI_SETTINGS_UPDATED_EVENT, { detail: DEFAULT_AI_SETTINGS }));
}

export function isProviderCredentialReady(settings: AISettings, provider: InferenceProviderId): boolean {
  const providerMeta = AI_PROVIDERS.find(item => item.id === provider);
  if (!providerMeta?.requiresApiKey) return true;
  return Boolean(settings.providerCredentials[provider]?.apiKey?.trim());
}

export function isInferenceConfigured(settings: AISettings): boolean {
  return Boolean(settings.roles.answer?.model && isProviderCredentialReady(settings, settings.roles.answer.provider));
}

export function setRoleByModel(settings: AISettings, role: InferenceRoleId, modelId: string): AISettings {
  const provider = getModelProvider(modelId);
  const next = {
    ...settings,
    roles: {
      ...settings.roles,
      [role]: { provider, model: modelId },
    },
  };
  if (role === 'answer') {
    next.model = modelId;
    if (settings.useSameModelForHelperRoles) {
      next.roles.rewriter = { provider, model: modelId };
      next.roles.summarizer = { provider, model: modelId };
    }
  }
  return normalizeAISettings(next);
}

export function toRuntimeInferenceConfig(settings: AISettings) {
  const credentials = Object.fromEntries(
    Object.entries(settings.providerCredentials)
      .filter(([, credential]) => credential?.apiKey?.trim())
      .map(([provider, credential]) => [provider, { apiKey: credential?.apiKey?.trim() }]),
  );

  return {
    credentials,
    roles: settings.roles,
    useServerFallbacks: settings.useServerFallbacks,
  };
}
