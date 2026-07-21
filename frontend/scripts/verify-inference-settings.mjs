import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const aiSettings = readFileSync(resolve(process.cwd(), 'lib/ai-settings.ts'), 'utf8');
const chatInterface = readFileSync(resolve(process.cwd(), 'components/chat/ChatInterface.tsx'), 'utf8');
const adminSettings = readFileSync(resolve(process.cwd(), 'components/admin/SystemSettingsTab.tsx'), 'utf8');

for (const role of ['answer', 'rewriter', 'summarizer']) {
  if (!aiSettings.includes(`${role}:`)) {
    throw new Error(`Missing inference role setting: ${role}`);
  }
}

if (!aiSettings.includes('toRuntimeInferenceConfig')) {
  throw new Error('Missing runtime inference config serializer');
}

if (!chatInterface.includes('inferenceConfig: toRuntimeInferenceConfig(aiSettings)')) {
  throw new Error('Chat requests do not include runtime inference config');
}

if (aiSettings.includes('credentials,') || aiSettings.includes('providerCredentials')) {
  throw new Error('Runtime inference config must not include browser credentials');
}

if (adminSettings.includes('placeholder="API key"') || adminSettings.includes('type="password"')) {
  throw new Error('Admin settings must not render provider API key inputs');
}

console.log('Inference settings verification passed.');
