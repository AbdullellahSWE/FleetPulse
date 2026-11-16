import React from 'react';

// Shows whether an AI answer came from a live Bedrock model or from the built-in simulation, and why.
export default function EngineBadge({ live, engine, reason, modelId }) {
  return (
    <span
      title={reason || modelId || ''}
      className={`text-[10px] px-2 py-0.5 rounded-full border font-medium inline-flex items-center gap-1 ${
        live
          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
          : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${live ? 'bg-emerald-400' : 'bg-amber-400'}`} />
      {live ? `${engine} · live` : 'Simulated (not a live model)'}
    </span>
  );
}
