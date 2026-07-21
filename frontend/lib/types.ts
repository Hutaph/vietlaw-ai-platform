/**
 * Shared TypeScript interfaces cho toàn bộ frontend.
 * Tách từ các component để tránh circular imports và dễ tái sử dụng.
 */

// --- Chat Message ---
export interface DocumentChunk {
  content: string;
  metadata: {
    id?: string;
    source?: string;
    dieu?: string;
    khoan?: string;
    diem?: string;
    law?: string;
  };
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  contextUsed?: DocumentChunk[];
  feedback?: 1 | -1;
  processingStage?: 'idle' | 'analyzing' | 'searching' | 'selecting' | 'generating' | 'completed' | 'cancelled' | 'error';
}

// --- Chat Session ---
export interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: number;
}

// --- Model ---
export interface AIModel {
  id: string;
  name: string;
  fullName: string;
  provider: InferenceProviderId;
}

export type InferenceProviderId = 'google' | 'huggingface' | 'ollama';
export type InferenceRoleId = 'answer' | 'rewriter' | 'summarizer';

export interface InferenceProvider {
  id: InferenceProviderId;
  name: string;
  deploymentSupported: boolean;
}

export interface InferenceRoleSetting {
  provider: InferenceProviderId;
  model: string;
}

export type InferenceRoleSettings = Record<InferenceRoleId, InferenceRoleSetting>;

// --- API ---
export interface ChatApiRequest {
  messages: { role: string; content: string }[];
  model: string;
  category: string;
  temperature?: number;
  maxTokens?: number;
  topK?: number;
  candidateK?: number;
  cacheThreshold?: number;
  maxSubqueries?: number;
  historyMessages?: number;
  contextTokenBudget?: number;
  maxCitations?: number;
  llmTimeout?: number;
  streaming?: boolean;
  useHistoryForRewriter?: boolean;
  enableQueryRewriter?: boolean;
  enableReranker?: boolean;
  enableSemanticCache?: boolean;
  enableMemory?: boolean;
  inferenceConfig?: {
    roles?: Partial<Record<InferenceRoleId, InferenceRoleSetting>>;
    useServerFallbacks?: boolean;
  };
}

export interface ChatApiResponse {
  text: string;
  contextUsed: DocumentChunk[];
}

// --- Feedback ---
export interface FeedbackPayload {
  message_id: string;
  session_id: string;
  user_query?: string;
  ai_response?: string;
  context_used?: DocumentChunk[];
  feedback_type: 1 | -1;
  reason?: string;
  comment?: string;
  model_used?: string;
}
