import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = process.cwd();
const chatInterface = readFileSync(resolve(root, 'components/chat/ChatInterface.tsx'), 'utf8');
const chatMessage = readFileSync(resolve(root, 'components/chat/ChatMessage.tsx'), 'utf8');
const processingTrace = readFileSync(resolve(root, 'components/chat/ChatProcessingTrace.tsx'), 'utf8');
const legalSources = readFileSync(resolve(root, 'components/chat/LegalSources.tsx'), 'utf8');
const emptyState = readFileSync(resolve(root, 'components/chat/ChatEmptyState.tsx'), 'utf8');
const advancedSettings = readFileSync(resolve(root, 'components/chat/AdvancedSettings.tsx'), 'utf8');
const providerSelector = readFileSync(resolve(root, 'components/chat/ProviderSelector.tsx'), 'utf8');
const proxyRoute = readFileSync(resolve(root, 'app/api/chat/route.ts'), 'utf8');

for (const label of [
  'Đang phân tích câu hỏi',
  'Đang tra cứu căn cứ pháp lý',
  'Đang chọn lọc thông tin phù hợp',
  'Đang tổng hợp câu trả lời',
  'Tra cứu hoàn tất',
  'Xem quá trình',
  'Ẩn quá trình',
]) {
  if (!processingTrace.includes(label)) {
    throw new Error(`Missing processing label: ${label}`);
  }
}

if (chatInterface.includes('isLoading && !streamingText')) {
  throw new Error('Large loading skeleton should not be used for active chat processing');
}

if (!chatInterface.includes("event.type === 'context'") || !chatInterface.includes('setStreamingContext(fullContext)')) {
  throw new Error('Context events must render sources before answer completion');
}

if (!chatInterface.includes("event.type === 'token'") || !chatInterface.includes("setProcessingStage('generating')")) {
  throw new Error('Token events must move processing into generation stage');
}

if (!chatInterface.includes('abortControllerRef.current.abort()') || !proxyRoute.includes('signal: req.signal')) {
  throw new Error('Cancel must abort the client stream and proxy fetch');
}

if (!chatMessage.includes('LegalSourcesTrigger') || !legalSources.includes('{deduped.length}')) {
  throw new Error('Assistant messages must render compact legal source trigger with dynamic deduplicated count');
}

if (!legalSources.includes('rounded-full') || !legalSources.includes('min-w-6') || !legalSources.includes('h-6')) {
  throw new Error('Legal source count must render as a centered rounded badge');
}

if (!legalSources.includes('aria-label={`Mở ${deduped.length} căn cứ pháp lý`}')) {
  throw new Error('Legal source trigger must expose an accessible count label');
}

if (!legalSources.includes('dedupeLegalSources') || !legalSources.includes('LegalSourceList')) {
  throw new Error('Legal sources must share deduplication and render full cards in the side panel');
}

if (!chatInterface.includes('id="legal-sources-panel"') || !chatInterface.includes('LegalSourceList sources={drawerContext}')) {
  throw new Error('Legal sources trigger must open the existing side panel');
}

if (legalSources.includes('contextUsed.length') || legalSources.includes('retrieval score') || legalSources.includes('reranker score')) {
  throw new Error('Legal sources UI must not expose counts or scores');
}

if (legalSources.includes('md:grid-cols-2') || legalSources.includes('Mở bảng bên')) {
  throw new Error('Legal source cards should not render as an inline grid or separate open-panel button');
}

if (!processingTrace.includes('collapsed = true') || !processingTrace.includes('aria-controls={detailsId}')) {
  throw new Error('Processing trace must support collapsed-by-default expanded details');
}

if (processingTrace.includes('onCancel') || processingTrace.includes('Dừng trả lời')) {
  throw new Error('Processing trace must not render a duplicate stop control');
}

if (!chatInterface.includes('abortControllerRef.current.abort()') || !chatInterface.includes('aria-label="Dừng trả lời"')) {
  throw new Error('Composer stop control must remain available');
}

if (chatInterface.includes('Tùy chọn') || chatInterface.includes('isComposerSettingsOpen')) {
  throw new Error('Composer must show inference controls directly, without a Tùy chọn gate');
}

if (!advancedSettings.includes('Tham số') || !providerSelector.includes('selectedProvider?.name')) {
  throw new Error('Composer must expose parameter and provider/model summary directly');
}

if (!emptyState.includes('Tra cứu pháp luật dễ dàng hơn')) {
  throw new Error('Empty state must use the legal search onboarding copy');
}

for (const forbidden of [
  'VietLaw BGE-M3',
  'đang embedding',
  'đang reranking',
  'đang gọi Qdrant',
  'chain-of-thought',
  'suy luận nội bộ',
  'retrieval score',
  'reranker score',
]) {
  const haystack = [processingTrace, legalSources, emptyState, chatMessage].join('\n');
  if (haystack.includes(forbidden)) {
    throw new Error(`User-facing chat UI contains forbidden technical text: ${forbidden}`);
  }
}

console.log('Chat UX verification passed.');
