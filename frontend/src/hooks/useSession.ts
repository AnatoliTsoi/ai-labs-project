import { useState, useEffect } from 'react';
import { generateSessionId } from '../api/agent';

const SESSION_KEY = 'concierge_session_id';

export function useSession() {
  const [sessionId] = useState<string>(() => {
    const stored = localStorage.getItem(SESSION_KEY);
    if (stored) return stored;

    const newId = generateSessionId();
    localStorage.setItem(SESSION_KEY, newId);
    return newId;
  });

  const resetSession = () => {
    const newId = generateSessionId();
    localStorage.setItem(SESSION_KEY, newId);
    window.location.reload();
  };

  return { sessionId, resetSession };
}
