import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const constants = readFileSync(resolve(process.cwd(), 'lib/constants.ts'), 'utf8');
const sessions = readFileSync(resolve(process.cwd(), 'hooks/use-chat-sessions.ts'), 'utf8');
const chatInterface = readFileSync(resolve(process.cwd(), 'components/chat/ChatInterface.tsx'), 'utf8');

if (!constants.includes('NEXT_PUBLIC_CHAT_STORAGE_MODE')) {
  throw new Error('Frontend chat storage mode environment variable is missing');
}

if (!sessions.includes("CHAT_STORAGE_MODE === 'browser'")) {
  throw new Error('Session hook does not branch on browser chat storage mode');
}

if (!sessions.includes('restoreLocalSnapshot(localSnapshot)')) {
  throw new Error('Browser mode does not restore the local session snapshot');
}

if (!chatInterface.includes("CHAT_STORAGE_MODE === 'browser'")) {
  throw new Error('Chat UI does not expose browser-local storage behavior');
}

console.log('Chat storage mode verification passed.');
