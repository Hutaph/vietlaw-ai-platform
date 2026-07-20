import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const aiSettings = readFileSync(resolve(process.cwd(), 'lib/ai-settings.ts'), 'utf8');
const setupModal = readFileSync(resolve(process.cwd(), 'components/chat/InferenceSetupModal.tsx'), 'utf8');
const chatInterface = readFileSync(resolve(process.cwd(), 'components/chat/ChatInterface.tsx'), 'utf8');

for (const role of ['answer', 'rewriter', 'summarizer']) {
  if (!aiSettings.includes(`${role}:`)) {
    throw new Error(`Missing inference role setting: ${role}`);
  }
}

if (!aiSettings.includes('AI_SESSION_CREDENTIALS_STORAGE_KEY')) {
  throw new Error('Missing session-only credential storage support');
}

if (!aiSettings.includes('toRuntimeInferenceConfig')) {
  throw new Error('Missing runtime inference config serializer');
}

if (!chatInterface.includes('inferenceConfig: toRuntimeInferenceConfig(aiSettings)')) {
  throw new Error('Chat requests do not include runtime inference config');
}

if (!setupModal.includes('Tra cứu căn cứ pháp lý được quản lý an toàn bởi máy chủ')) {
  throw new Error('Setup modal must explain server-managed legal retrieval without technical internals');
}

if (setupModal.includes('type="text"') && setupModal.includes('API key')) {
  throw new Error('Provider API key inputs should not be plain text');
}

console.log('Inference settings verification passed.');
