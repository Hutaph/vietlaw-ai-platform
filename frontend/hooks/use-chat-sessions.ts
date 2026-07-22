/**
 * Hook that owns chat session state and persistence.
 * This keeps ChatInterface focused on rendering and request orchestration.
 */
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import type { ChatSession, Message } from '@/lib/types';
import { CHAT_STORAGE_MODE, STORAGE_KEYS } from '@/lib/constants';

const createSessionId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

interface DbMessage {
  id: string;
  role: string;
  content: string;
  contextUsed?: Message['contextUsed'];
}

const mapDbMessage = (m: DbMessage): Message => ({
  id: m.id,
  role: m.role as 'user' | 'assistant',
  content: m.content,
  contextUsed: m.contextUsed || []
});

interface DbSession {
  session_id: string;
  title?: string;
  updated_at?: string;
  message_count?: number | string;
}

interface LocalChatSnapshot {
  sessions: ChatSession[];
  messages: Record<string, Message[]>;
  activeSessionId: string | null;
}

const parseJsonItem = <T,>(value: string | null, fallback: T): T => {
  if (!value) return fallback;
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
};

const readLocalChatSnapshot = (): LocalChatSnapshot => ({
  sessions: parseJsonItem<ChatSession[]>(localStorage.getItem(STORAGE_KEYS.sessions), []),
  messages: parseJsonItem<Record<string, Message[]>>(localStorage.getItem(STORAGE_KEYS.messages), {}),
  activeSessionId: localStorage.getItem(STORAGE_KEYS.activeSessionId),
});

const sessionFromLocalMessages = (id: string, messages: Message[]): ChatSession => {
  const firstUserMessage = messages.find(message => message.role === 'user');
  const lastMessage = messages.at(-1);
  const titleSource = firstUserMessage?.content || 'Cuộc trò chuyện mới';
  return {
    id,
    title: titleSource.substring(0, 30) + (titleSource.length > 30 ? '...' : ''),
    lastMessage: lastMessage?.content || '',
    timestamp: Number(id) || Date.now(),
  };
};

const getLocalSessionsWithMessages = ({ sessions, messages }: LocalChatSnapshot): ChatSession[] => {
  const sessionById = new Map(sessions.map(session => [session.id, session]));
  return Object.entries(messages)
    .filter(([, sessionMessages]) => sessionMessages.length > 0)
    .map(([id, sessionMessages]) => sessionById.get(id) || sessionFromLocalMessages(id, sessionMessages));
};

const warnRecoverableSessionsIssue = (message: string, details?: unknown) => {
  if (process.env.NODE_ENV !== 'production') {
    console.warn(`[Chat Sessions] ${message}`, details ?? '');
  }
};

const chooseCompleteMessages = (cached: Message[] | undefined, dbMessages: Message[]) => {
  if (!cached || dbMessages.length >= cached.length) {
    return dbMessages;
  }
  return cached;
};

export function useChatSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [isSessionsListLoading, setIsSessionsListLoading] = useState(true);
  const [messagesBySession, setMessagesBySession] = useState<Record<string, Message[]>>({});
  const [isMounted, setIsMounted] = useState(false);
  const sessionLoadSeqRef = useRef(0);

  const stateRef = useRef({ sessions, currentSessionId, messagesBySession });
  useEffect(() => {
    stateRef.current = { sessions, currentSessionId, messagesBySession };
  }, [sessions, currentSessionId, messagesBySession]);

  const currentMessages = currentSessionId
    ? messagesBySession[currentSessionId] || []
    : [];

  // --- Create a new session ---
  const handleNewChat = useCallback(() => {
    const { currentSessionId, messagesBySession } = stateRef.current;
    
    // Reuse the current empty session instead of creating another placeholder.
    if (currentSessionId && (!messagesBySession[currentSessionId] || messagesBySession[currentSessionId].length === 0)) {
      return;
    }

    const newId = createSessionId();
    setCurrentSessionId(newId);
    localStorage.setItem(STORAGE_KEYS.activeSessionId, newId);
    setMessagesBySession(prev => ({ ...prev, [newId]: [] }));
  }, []);

  // --- Select a session ---
  const handleSelectSession = useCallback(async (id: string) => {
    const { currentSessionId, messagesBySession } = stateRef.current;
    if (id === currentSessionId) return;

    const loadSeq = ++sessionLoadSeqRef.current;
    setCurrentSessionId(id);
    localStorage.setItem(STORAGE_KEYS.activeSessionId, id);

    if (CHAT_STORAGE_MODE === 'browser') {
      return;
    }

    const cachedMessages = messagesBySession[id];
    if (!cachedMessages) {
      setIsSessionLoading(true);
    }

    try {
      const res = await fetch(`/api/chat/session/${id}/messages`);
      if (res.ok) {
        const dbMsgs = await res.json() as DbMessage[];
        const dbMessages = dbMsgs.map(mapDbMessage);
        setMessagesBySession(prev => ({
          ...prev,
          [id]: chooseCompleteMessages(prev[id], dbMessages)
        }));
      } else if (!cachedMessages) {
        warnRecoverableSessionsIssue(`Messages API returned ${res.status}; keeping local state for session ${id}.`);
        setMessagesBySession(prev => ({ ...prev, [id]: [] }));
      }
    } catch (err) {
      warnRecoverableSessionsIssue(`Messages API is unavailable; keeping local state for session ${id}.`, err);
      if (!cachedMessages) {
        setMessagesBySession(prev => ({ ...prev, [id]: [] }));
      }
    } finally {
      if (sessionLoadSeqRef.current === loadSeq) {
        setIsSessionLoading(false);
      }
    }
  }, []);

  // --- Delete a session ---
  const handleDeleteSession = useCallback((id: string) => {
    if (CHAT_STORAGE_MODE === 'postgres') {
      // Fire-and-forget backend deletion; the local UI updates immediately.
      fetch(`/api/chat/session/${id}`, { method: 'DELETE' })
        .then(res => {
          if (!res.ok) console.warn(`[Delete Session] Backend returned ${res.status} for session ${id}`);
        })
        .catch(err => {
          warnRecoverableSessionsIssue(`Delete session API is unavailable; removed local session ${id}.`, err);
        });
    }

    const { currentSessionId, sessions, messagesBySession } = stateRef.current;
    const remaining = sessions.filter(s => s.id !== id);

    // Remove messages for the deleted session.
    const nextMessages = { ...messagesBySession };
    delete nextMessages[id];
    setMessagesBySession(nextMessages);

    if (currentSessionId === id) {
      if (remaining.length > 0) {
        setCurrentSessionId(remaining[0].id);
        localStorage.setItem(STORAGE_KEYS.activeSessionId, remaining[0].id);
        setSessions(remaining);
      } else {
        // Create a fresh empty session without adding it to the visible history.
        const newId = createSessionId();
        nextMessages[newId] = [];
        setMessagesBySession({ ...nextMessages });
        setCurrentSessionId(newId);
        localStorage.setItem(STORAGE_KEYS.activeSessionId, newId);
        setSessions([]);
      }
    } else {
      setSessions(remaining);
    }
  }, []);

  // --- Add a message to the current session ---
  const addMessage = useCallback((message: Message) => {
    if (!currentSessionId) return;
    setMessagesBySession(prev => ({
      ...prev,
      [currentSessionId]: [...(prev[currentSessionId] || []), message],
    }));

    setSessions(prev => {
      const idx = prev.findIndex(s => s.id === currentSessionId);
      if (idx === -1) {
        return [{
          id: currentSessionId,
          title: message.content.substring(0, 40) + (message.content.length > 40 ? '...' : ''),
          lastMessage: message.content,
          timestamp: Date.now()
        }, ...prev];
      }
      return prev.map(s =>
        s.id === currentSessionId
          ? { ...s, lastMessage: message.content, timestamp: Date.now() }
          : s
      );
    });
  }, [currentSessionId]);

  // --- Update a message ---
  const updateMessage = useCallback((sessionId: string, messageId: string, updates: Partial<Message>) => {
    setMessagesBySession(prev => {
      const sessionMessages = prev[sessionId];
      if (!sessionMessages) return prev;
      return {
        ...prev,
        [sessionId]: sessionMessages.map(m => m.id === messageId ? { ...m, ...updates } : m)
      };
    });
  }, []);

  // --- Update the current session title ---
  const updateSessionTitle = useCallback((title: string) => {
    if (!currentSessionId) return;
    setSessions(prev =>
      prev.map(s =>
        s.id === currentSessionId
          ? { ...s, title: title.substring(0, 30) + (title.length > 30 ? '...' : '') }
          : s
      )
    );
  }, [currentSessionId]);

  // --- Load sessions from DB/API on mount ---
  useEffect(() => {
    setIsMounted(true);

    const restoreLocalSnapshot = (snapshot: LocalChatSnapshot) => {
      const localSessions = getLocalSessionsWithMessages(snapshot)
        .sort((a, b) => b.timestamp - a.timestamp);

      setSessions(localSessions);
      setMessagesBySession(snapshot.messages);

      if (snapshot.activeSessionId && snapshot.messages[snapshot.activeSessionId]) {
        setCurrentSessionId(snapshot.activeSessionId);
        localStorage.setItem(STORAGE_KEYS.activeSessionId, snapshot.activeSessionId);
        return;
      }

      if (localSessions.length > 0) {
        setCurrentSessionId(localSessions[0].id);
        localStorage.setItem(STORAGE_KEYS.activeSessionId, localSessions[0].id);
        return;
      }

      handleNewChat();
    };

    const loadFromDB = async () => {
      const localSnapshot = readLocalChatSnapshot();

      if (CHAT_STORAGE_MODE === 'browser') {
        restoreLocalSnapshot(localSnapshot);
        setIsSessionLoading(false);
        setIsSessionsListLoading(false);
        return;
      }

      try {
        const res = await fetch('/api/chat/sessions');
        if (!res.ok) {
          const body = await res.text().catch(() => '');
          warnRecoverableSessionsIssue(`Sessions API returned ${res.status}; using local history.`, body.slice(0, 160));
          restoreLocalSnapshot(localSnapshot);
          return;
        }

        const dbSessions = await res.json() as DbSession[];
        if (!Array.isArray(dbSessions)) {
          warnRecoverableSessionsIssue('Sessions API returned an unexpected payload; using local history.');
          restoreLocalSnapshot(localSnapshot);
          return;
        }

        const filteredSessions = dbSessions.filter(s => Number(s.message_count || 0) > 0);
        const dbMessageCounts = Object.fromEntries(
          filteredSessions.map(s => [s.session_id, Number(s.message_count || 0)])
        ) as Record<string, number>;

        let loadedSessions: ChatSession[] = filteredSessions.map(dbSession => ({
          id: dbSession.session_id,
          title: dbSession.title || 'Cuộc trò chuyện mới',
          lastMessage: '',
          timestamp: dbSession.updated_at ? new Date(dbSession.updated_at).getTime() : Date.now(),
        }));

        loadedSessions.sort((a, b) => b.timestamp - a.timestamp);

        const loadedSessionIds = new Set(loadedSessions.map(session => session.id));
        const localSessions = getLocalSessionsWithMessages(localSnapshot);
        for (const localSession of localSessions) {
          if (!loadedSessionIds.has(localSession.id)) {
            loadedSessions.push(localSession);
            loadedSessionIds.add(localSession.id);
          }
        }
        loadedSessions.sort((a, b) => b.timestamp - a.timestamp);

        const canRestoreActive = Boolean(
          localSnapshot.activeSessionId && loadedSessions.some(s => s.id === localSnapshot.activeSessionId)
        );
        const activeId = canRestoreActive && localSnapshot.activeSessionId
          ? localSnapshot.activeSessionId
          : loadedSessions[0]?.id || createSessionId();
        const activeSessionExists = loadedSessions.some(s => s.id === activeId);
        const initialMessages: Record<string, Message[]> = {
          ...localSnapshot.messages,
          [activeId]: localSnapshot.messages[activeId] || [],
        };

        setSessions(loadedSessions);
        setMessagesBySession(initialMessages);
        setCurrentSessionId(activeId);
        localStorage.setItem(STORAGE_KEYS.activeSessionId, activeId);

        const cachedActiveMessages = localSnapshot.messages[activeId];
        const shouldFetchActiveMessages =
          activeSessionExists &&
          (!cachedActiveMessages || (dbMessageCounts[activeId] || 0) > cachedActiveMessages.length);

        if (shouldFetchActiveMessages) {
          setIsSessionLoading(true);
          const messagesRes = await fetch(`/api/chat/session/${activeId}/messages`);
          if (messagesRes.ok) {
            const dbMsgs = await messagesRes.json() as DbMessage[];
            const dbMessages = dbMsgs.map(mapDbMessage);
            setMessagesBySession(prev => ({
              ...prev,
              [activeId]: chooseCompleteMessages(prev[activeId], dbMessages)
            }));
          }
        }
        setIsSessionLoading(false);
      } catch (err) {
        warnRecoverableSessionsIssue('Sessions API is unavailable; using local history.', err);
        restoreLocalSnapshot(localSnapshot);
      } finally {
        setIsSessionLoading(false);
        setIsSessionsListLoading(false);
      }
    };

    loadFromDB();
  }, [handleNewChat]);

  // --- Persist valid local state changes ---
  useEffect(() => {
    if (isMounted) {
      const validSessions = sessions.filter(s => messagesBySession[s.id] && messagesBySession[s.id].length > 0);
      // Store only valid session messages to avoid orphaned local history.
      const validMessages: Record<string, Message[]> = {};
      validSessions.forEach(s => { validMessages[s.id] = messagesBySession[s.id]; });
      localStorage.setItem(STORAGE_KEYS.sessions, JSON.stringify(validSessions));
      localStorage.setItem(STORAGE_KEYS.messages, JSON.stringify(validMessages));
      if (currentSessionId) {
        localStorage.setItem(STORAGE_KEYS.activeSessionId, currentSessionId);
      }
    }
  }, [sessions, messagesBySession, currentSessionId, isMounted]);

  return {
    sessions,
    currentSessionId,
    currentMessages,
    isMounted,
    handleNewChat,
    handleSelectSession,
    handleDeleteSession,
    addMessage,
    updateMessage,
    updateSessionTitle,
    isSessionLoading,
    isSessionsListLoading,
  };
}
