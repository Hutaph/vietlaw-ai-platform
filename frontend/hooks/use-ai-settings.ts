'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  AI_SETTINGS_STORAGE_KEY,
  AI_SETTINGS_UPDATED_EVENT,
  AISettings,
  DEFAULT_AI_SETTINGS,
  normalizeAISettings,
  persistAISettings,
  readAISettings,
} from '@/lib/ai-settings';

export function useAISettings() {
  const [settings, setSettingsState] = useState<AISettings>(DEFAULT_AI_SETTINGS);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    setSettingsState(readAISettings());
    setIsLoaded(true);

    const syncSettings = (event: Event) => {
      if (event instanceof CustomEvent && event.detail) {
        setSettingsState(normalizeAISettings(event.detail));
      } else {
        setSettingsState(readAISettings());
      }
    };

    const syncStorage = (event: StorageEvent) => {
      if (event.key === AI_SETTINGS_STORAGE_KEY) setSettingsState(readAISettings());
    };

    window.addEventListener(AI_SETTINGS_UPDATED_EVENT, syncSettings);
    window.addEventListener('storage', syncStorage);
    return () => {
      window.removeEventListener(AI_SETTINGS_UPDATED_EVENT, syncSettings);
      window.removeEventListener('storage', syncStorage);
    };
  }, []);

  const setSettings = useCallback((next: AISettings | ((current: AISettings) => AISettings)) => {
    setSettingsState(current => {
      const resolved = typeof next === 'function' ? next(current) : next;
      return persistAISettings(resolved);
    });
  }, []);

  const resetSettings = useCallback(() => {
    setSettingsState(persistAISettings(DEFAULT_AI_SETTINGS));
  }, []);

  return { settings, setSettings, resetSettings, isLoaded };
}
