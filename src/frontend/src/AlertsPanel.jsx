import React from 'react';
import { BellRing, CheckCircle2, MapPin, ShieldAlert, AlertTriangle } from 'lucide-react';

const SEVERITY_STYLE = {
  CRITICAL: { badge: 'bg-red-500/15 text-red-300 border-red-500/40', icon: ShieldAlert, iconClass: 'text-red-400' },
  WARNING: { badge: 'bg-amber-500/15 text-amber-300 border-amber-500/40', icon: AlertTriangle, iconClass: 'text-amber-400' },
};

function timeAgo(epochSeconds) {
  const s = Math.max(0, Math.round(Date.now() / 1000 - epochSeconds));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export default function AlertsPanel({ alerts, rules, onAck, onLocate }) {
  const open = alerts.filter((a) => !a.acknowledged);
  const done = alerts.filter((a) => a.acknowledged);

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BellRing className="w-5 h-5 text-red-400" />
            Automated Alerts
          </h2>
          <p className="text-xs text-slate-400">
            Rules run on every fleet update. Critical alerts are also published to the SNS topic (email and dispatch queue).
          </p>
        </div>
        <span className="text-xs px-3 py-1 rounded-full border border-slate-700 bg-slate-900 text-slate-300">
          {open.length} open · {done.length} acknowledged
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-3">
          {open.length === 0 && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6 text-sm text-slate-400 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" /> No open alerts. All monitored conditions are within limits.
            </div>
          )}
          {open.map((a) => {
            const style = SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.WARNING;
            const Icon = style.icon;
            return (
              <div key={a.id} className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex gap-3">
                <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${style.iconClass}`} />
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-white">{a.title}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${style.badge}`}>{a.severity}</span>
                    {a.sns_message_id && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300">
                        SNS sent
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-300">
                    <span className="font-mono text-indigo-300">{a.vehicle_id}</span> · {a.location_name} · {timeAgo(a.created_at)}
                  </p>
                  <p className="text-xs text-slate-400">{a.detail}</p>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => onLocate(a.vehicle_id)}
                      className="text-[11px] px-2.5 py-1 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 flex items-center gap-1"
                    >
                      <MapPin className="w-3 h-3" /> Show on map
                    </button>
                    <button
                      onClick={() => onAck(a.id)}
                      className="text-[11px] px-2.5 py-1 rounded-lg border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10 flex items-center gap-1"
                    >
                      <CheckCircle2 className="w-3 h-3" /> Acknowledge
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {done.length > 0 && (
            <details className="bg-slate-900/40 border border-slate-800 rounded-xl p-3">
              <summary className="text-xs text-slate-400 cursor-pointer">Acknowledged ({done.length})</summary>
              <ul className="mt-2 space-y-1.5">
                {done.map((a) => (
                  <li key={a.id} className="text-xs text-slate-500">
                    <span className="font-mono">{a.vehicle_id}</span> — {a.title} · {timeAgo(a.created_at)}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-2 h-fit">
          <h3 className="text-sm font-semibold text-white">Active rules</h3>
          <ul className="space-y-1.5">
            {rules.map((r) => (
              <li key={r.id} className="text-xs text-slate-300 flex items-start gap-2">
                <span
                  className={`mt-1 w-2 h-2 rounded-full shrink-0 ${r.severity === 'CRITICAL' ? 'bg-red-400' : 'bg-amber-400'}`}
                />
                {r.title}
              </li>
            ))}
          </ul>
          <p className="text-[11px] text-slate-500 pt-1">
            Each rule alerts once per vehicle until the condition clears (or 15 minutes pass), so a persistent fault does not spam
            the notification topic.
          </p>
        </div>
      </div>
    </div>
  );
}
