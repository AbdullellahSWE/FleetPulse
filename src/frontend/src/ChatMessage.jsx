import React from 'react';
import { Bot, User, AlertTriangle } from 'lucide-react';
import EngineBadge from './EngineBadge.jsx';

export default function ChatMessage({ m }) {
  const isUser = m.role === 'user';
  return (
    <div className={`flex gap-2.5 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${m.error ? 'bg-red-500/15' : 'bg-indigo-500/15'}`}>
          {m.error ? <AlertTriangle className="w-4 h-4 text-red-400" /> : <Bot className="w-4 h-4 text-indigo-300" />}
        </div>
      )}
      <div className="max-w-[82%] space-y-1.5">
        <div
          className={`rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-indigo-600 text-white rounded-br-sm'
              : m.error
              ? 'bg-red-500/10 border border-red-500/30 text-red-200 rounded-bl-sm'
              : 'bg-slate-800 text-slate-100 rounded-bl-sm'
          }`}
        >
          {m.content}
        </div>
        {m.meta && (
          <div className="flex flex-wrap items-center gap-2">
            <EngineBadge live={m.meta.live} engine={m.meta.engine} reason={m.meta.reason} modelId={m.meta.modelId} />
            {m.meta.source === 'fallback' && <span className="text-[10px] text-slate-500">demo data</span>}
          </div>
        )}
        {m.meta && !m.meta.live && m.meta.reason && <p className="text-[10.5px] text-amber-400/90">Why: {m.meta.reason}</p>}
      </div>
      {isUser && (
        <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-slate-200" />
        </div>
      )}
    </div>
  );
}
