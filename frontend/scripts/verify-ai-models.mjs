import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const constantsPath = resolve(process.cwd(), 'lib/constants.ts');
const source = readFileSync(constantsPath, 'utf8');

const requiredModels = [
  'gemini-3.1-flash-lite',
];

for (const model of requiredModels) {
  if (!source.includes(`id: '${model}'`)) {
    throw new Error(`Missing AI model option: ${model}`);
  }
}

if (source.includes("id: 'google/gemma-4-31B-it'")) {
  throw new Error('Unverified Gemma 4 31B model option must not be enabled');
}

if (source.includes("id: 'gemini-2.5-flash-lite'")) {
  throw new Error('Deprecated Gemini 2.5 Flash-Lite model option must not be enabled');
}

console.log('AI model catalog verification passed.');
