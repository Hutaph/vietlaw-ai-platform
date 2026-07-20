/**
 * Hằng số dùng chung cho toàn frontend.
 * Tách từ ChatInterface.tsx và ProviderSelector.tsx.
 */
import type { AIModel, InferenceProvider } from './types';

export interface LawCategory {
  id: string;
  label: string;
}

export const ALL_LAWS_CATEGORY = 'all';

export type ChatStorageMode = 'postgres' | 'browser';

export const CHAT_STORAGE_MODE: ChatStorageMode =
  process.env.NEXT_PUBLIC_CHAT_STORAGE_MODE?.trim().toLowerCase() === 'browser'
    ? 'browser'
    : 'postgres';

// Các lĩnh vực pháp luật được tách từ ba nhóm nghiệp vụ.
export const LAW_CATEGORIES = [
  {
    id: ALL_LAWS_CATEGORY,
    label: 'Tất cả các luật',
  },
  {
    id: 'LKDBDS_2023',
    label: 'Luật Kinh doanh bất động sản 2023',
  },
  {
    id: 'LTTPHS_2025',
    label: 'Luật Tương trợ tư pháp về hình sự 2025',
  },
  {
    id: 'LNO_2023',
    label: 'Luật Nhà ở 2023',
  },
  {
    id: 'LBVMT_2020',
    label: 'Luật Bảo vệ môi trường 2020',
  },
  {
    id: 'LXD_2014',
    label: 'Luật Xây dựng 2014',
  },
  {
    id: 'LDD_2024',
    label: 'Luật Đất đai 2024',
  },
  {
    id: 'LCC_2024',
    label: 'Luật Công chứng 2024',
  },
  {
    id: 'BLTTDS_2015',
    label: 'Bộ luật Tố tụng dân sự 2015',
  },
] as const satisfies readonly LawCategory[];

// Danh sách model AI hỗ trợ
export const AI_PROVIDERS: InferenceProvider[] = [
  { id: 'google', name: 'Google AI Studio', requiresApiKey: true, deploymentSupported: true },
  { id: 'huggingface', name: 'HuggingFace Router', requiresApiKey: true, deploymentSupported: true },
  { id: 'ollama', name: 'Ollama', requiresApiKey: false, deploymentSupported: false },
];

export const AI_MODELS: AIModel[] = [
  { id: 'gemini-3.1-flash-lite', provider: 'google', name: 'Gemini 3.1 Lite', fullName: 'Gemini 3.1 Flash-Lite' },
  { id: 'Qwen/Qwen2.5-7B-Instruct', provider: 'huggingface', name: 'Qwen 2.5', fullName: 'Qwen2.5 7B' },
  { id: 'meta-llama/Llama-3.1-8B-Instruct', provider: 'huggingface', name: 'Llama 3.1', fullName: 'Llama 3.1 8B' },
  { id: 'deepseek-ai/DeepSeek-R1-Distill-Llama-8B', provider: 'huggingface', name: 'DeepSeek R1', fullName: 'DeepSeek R1 8B' },
  { id: 'qwen2.5:7b-instruct', provider: 'ollama', name: 'Qwen Local', fullName: 'Qwen2.5 7B via Ollama' },
  { id: 'qwen2.5:1.5b', provider: 'ollama', name: 'Qwen Mini Local', fullName: 'Qwen2.5 1.5B via Ollama' },
];

// Model mặc định
export const DEFAULT_MODEL = 'gemini-3.1-flash-lite';

// LocalStorage keys
export const STORAGE_KEYS = {
  sessions: 'vietlaw_sessions',
  messages: 'vietlaw_messages',
  activeSessionId: 'vietlaw_active_session_id',
} as const;
