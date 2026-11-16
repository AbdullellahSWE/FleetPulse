import React, { useEffect, useRef, useState } from 'react';
import { Bot, Send, Sparkles, RefreshCw } from 'lucide-react';
import ChatMessage from './ChatMessage.jsx';

const SUGGESTIONS = [
  'Which trucks need attention right now?',
  'Which vehicles are inside a low-emission zone?',
  'Who has the lowest battery?',
  'Summarize open alerts and what to do first.',
];

export default function ChatAssistant({ apiEndpoint, authHeader, onUnauthorized }) {
  const [messages, setMessages] = useState([]); // {role, content, meta?, error?}
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  const send = async (text) => {
    const question = (text ?? input).trim();
    if (!question || busy) return;
    const next = [...messages, { role: 'user', content: question }];
    setMessages(next);
    setInput('');
    setBusy(true);
    try {
      const res = await fetch(`${apiEndpoint}/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        // Last 12 turns only (errors excluded); the server grounds every answer in the live fleet snapshot
        body: JSON.stringify({
          messages: next
            .filter((m) => !m.error)
            .slice(-12)
            .map(({ role, content }) => ({ role, content })),
        }),
      });
      if (res.status === 401) {
        onUnauthorized?.();
        throw new Error('Your session has expired. Please sign in again.');
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join('; ') : data.detail;
        throw new Error(detail || `Request failed (HTTP ${res.status})`);
      }
      setMessages([
        ...next,
        {
          role: 'assistant',
          content: data.reply,
          meta: { live: data.live, engine: data.engine, reason: data.fallback_reason, modelId: data.model_id, source: data.data_source },
        },
      ]);
    } catch (err) {
      setMessages([...next, { role: 'assistant', content: err.message, error: true }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-2xl flex flex-col h-[520px]">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-amber-300" />
        <h3 className="text-sm font-semibold text-white">Dispatch Assistant</h3>
        <span className="text-[11px] text-slate-500">Answers use live fleet telemetry</span>
        {messages.length > 0 && (
          <button onClick={() => setMessages([])} className="ml-auto text-[11px] text-slate-400 hover:text-slate-200 underline underline-offset-2">
            Clear
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-xs text-slate-400">Try one of these:</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="text-[11px] px-3 py-1.5 rounded-full border border-slate-700 text-slate-300 hover:bg-slate-800 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <ChatMessage key={i} m={m} />
        ))}

        {busy && (
          <div className="flex gap-2.5">
            <div className="w-7 h-7 rounded-full bg-indigo-500/15 flex items-center justify-center">
              <Bot className="w-4 h-4 text-indigo-300" />
            </div>
            <div className="bg-slate-800 rounded-2xl rounded-bl-sm px-3.5 py-2.5 text-xs text-slate-400 flex items-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="p-3 border-t border-slate-800 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          maxLength={1000}
          placeholder="Ask about faults, LEZ status, batteries, alerts…"
          className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl px-3.5 flex items-center gap-1.5 text-xs font-semibold transition"
        >
          <Send className="w-3.5 h-3.5" /> Send
        </button>
      </form>
    </div>
  );
}
