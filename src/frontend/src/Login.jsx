import React, { useEffect, useState } from 'react';
import { Compass, Lock, RefreshCw, AlertTriangle } from 'lucide-react';
import { devSession, fetchAuthConfig, signIn } from './auth.js';

export default function Login({ apiEndpoint, onSignedIn }) {
  const [config, setConfig] = useState(null);
  const [configError, setConfigError] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetchAuthConfig(apiEndpoint)
      .then((c) => active && setConfig(c))
      .catch((e) => active && setConfigError(e.message));
    return () => {
      active = false;
    };
  }, [apiEndpoint]);

  const submit = async (e) => {
    e.preventDefault();
    if (!config?.configured) return;
    setBusy(true);
    setError('');
    try {
      onSignedIn(await signIn(config, email.trim(), password));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl p-7 space-y-5 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
            <Compass className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">FleetPulse</h1>
            <p className="text-xs text-slate-400">Sign in to the operations dashboard</p>
          </div>
        </div>

        {configError && (
          <div className="flex gap-2 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
            <AlertTriangle className="w-4 h-4 shrink-0" /> {configError}
          </div>
        )}
        {config && !config.configured && (
          <div className="flex gap-2 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            Authentication is not configured on the server (COGNITO_USER_POOL_ID / COGNITO_CLIENT_ID).
          </div>
        )}

        <div className="space-y-3">
          <label className="block text-xs text-slate-400">
            Email
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </label>
          <label className="block text-xs text-slate-400">
            Password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </label>
        </div>

        {error && <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-2.5">{error}</p>}

        <button
          type="submit"
          disabled={busy || !config?.configured}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2 transition"
        >
          {busy ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
          Sign in
        </button>

        {config?.dev_bypass && (
          <button
            type="button"
            onClick={() => onSignedIn(devSession())}
            className="w-full text-xs text-slate-400 hover:text-slate-200 underline underline-offset-2"
          >
            Continue in local dev mode (server has AUTH_DEV_BYPASS enabled)
          </button>
        )}
      </form>
    </div>
  );
}
