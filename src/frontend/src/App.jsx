import React, { useState, useEffect, useRef } from 'react';
import {
  Battery,
  Thermometer,
  ShieldAlert,
  Cpu,
  Navigation,
  Zap,
  RefreshCw,
  Lock,
  LogOut,
  BellRing,
  ShieldCheck,
  WifiOff,
  Wifi,
  ChevronRight,
  Activity,
} from 'lucide-react';

// ─── Seed Data ────────────────────────────────────────────────────────────────
const INITIAL_FLEET = [
  {
    id: 'EV-9402',
    driver: 'Alex R.',
    battery: 14.5,
    temp: 48.2,
    status: 'Critical',
    diagnostics: 'High thermal stress detected under heavy acceleration uphill.',
  },
  {
    id: 'EV-1088',
    driver: 'Jordan M.',
    battery: 78.0,
    temp: 31.5,
    status: 'Optimal',
    diagnostics: 'Nominal city cruising.',
  },
  {
    id: 'EV-3310',
    driver: 'Sam K.',
    battery: 42.1,
    temp: 37.8,
    status: 'Warning',
    diagnostics: 'Elevated battery temp during rapid DC charging.',
  },
  {
    id: 'EV-7721',
    driver: 'Taylor B.',
    battery: 91.4,
    temp: 28.0,
    status: 'Optimal',
    diagnostics: 'Regenerative braking active on highway descent.',
  },
];

const COGNITO_REGION = 'us-east-1';
const COGNITO_CLIENT_ID = '60ljkjaia3u74terhhcto4n076';

// ─── Simulated AI Fallback ─────────────────────────────────────────────────────
function generateFallbackResponse(vehicleId, battery, temp, diagnostics) {
  const isLowBattery = battery < 20;
  const isHighTemp = temp > 45;
  const isCritical = isLowBattery || isHighTemp;

  const urgency = isCritical ? '🔴 CRITICAL' : battery < 50 || temp > 38 ? '🟡 WARNING' : '🟢 OPTIMAL';
  const action = isLowBattery
    ? 'IMMEDIATE CHARGING REQUIRED — Route vehicle to nearest fast-charge depot.'
    : isHighTemp
    ? 'THERMAL COOLING PROTOCOL — Reduce load and initiate active battery cooling.'
    : battery < 50
    ? 'ADVISORY — Schedule charge within next 2 operational hours.'
    : 'No immediate action required. Vehicle is operating within safe parameters.';

  const eta = isLowBattery ? '< 15 min to nearest depot' : isHighTemp ? 'Immediate thermal response' : '2–4 hours optimal window';

  return `╔══════════════════════════════════════════╗
║   AI DISPATCH RECOMMENDATION [SIMULATED]  ║
╚══════════════════════════════════════════╝

Vehicle:    ${vehicleId}
Status:     ${urgency}
Timestamp:  ${new Date().toISOString()}

─── Telemetry Analysis ───────────────────

  Battery Level : ${battery.toFixed(1)}% ${isLowBattery ? '⚠ CRITICALLY LOW' : ''}
  Battery Temp  : ${temp.toFixed(1)}°C ${isHighTemp ? '⚠ OVERTEMPERATURE' : ''}
  Diagnostics   : ${diagnostics}

─── Recommended Action ──────────────────

  ${action}

─── Route & ETA Estimate ────────────────

  ETA Window: ${eta}

─── Risk Assessment ─────────────────────

${
  isCritical
    ? `  HIGH RISK — Continued operation without intervention may result in:
  • Battery cell degradation (irreversible capacity loss)
  • Thermal runaway risk above 60°C
  • Stranded vehicle scenario if charge drops below 5%`
    : battery < 50 || temp > 38
    ? `  MODERATE RISK — Monitor closely:
  • Efficiency drops ~18% in this charge-temp range
  • Recommend pre-emptive scheduling before next route`
    : `  LOW RISK — Vehicle cleared for continued dispatch.
  • All systems nominal
  • Projected range: sufficient for 3+ additional routes`
}

─── Dispatch Directive ───────────────────

  Issued by:  FleetPulse AI Engine (Gemini-Pro via OpenRouter)
  Confidence: ${isCritical ? '97.4%' : '94.1%'} (Bayesian telemetry model v2.3)
  Override:   Contact Fleet Manager for manual override

[SIMULATED — Connect API tunnel for live inference]`;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function statusColors(status) {
  if (status === 'Critical') return 'bg-red-500/20 text-red-400 border-red-500/30';
  if (status === 'Warning') return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
  return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
}

function batteryColor(pct) {
  if (pct < 20) return 'bg-red-500';
  if (pct < 50) return 'bg-amber-400';
  return 'bg-emerald-400';
}

function tempColor(c) {
  if (c > 45) return 'bg-red-500';
  if (c > 38) return 'bg-amber-400';
  return 'bg-blue-400';
}

function clamp(val, min, max) {
  return Math.max(min, Math.min(max, Number(val)));
}

// ─── Loading Dots ─────────────────────────────────────────────────────────────
function LoadingDots({ label }) {
  const [dots, setDots] = useState('');
  useEffect(() => {
    const id = setInterval(() => setDots((d) => (d.length >= 3 ? '' : d + '.')), 400);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="flex flex-col items-center justify-center gap-4 h-full text-slate-400">
      <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
      <span className="font-mono text-sm">
        {label}
        {dots}
      </span>
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="inline-block w-2 h-2 rounded-full bg-indigo-500 animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Gauge Bar ────────────────────────────────────────────────────────────────
function GaugeBar({ pct, colorClass }) {
  return (
    <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
        style={{ width: `${clamp(pct, 0, 100)}%` }}
      />
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function FleetPulseDashboard() {
  const [fleet, setFleet] = useState(INITIAL_FLEET);
  const [selectedVehicleId, setSelectedVehicleId] = useState(INITIAL_FLEET[0].id);
  const [lastSync, setLastSync] = useState('Live');
  const [aiOutput, setAiOutput] = useState('');
  const [snsStatus, setSnsStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [snsLoading, setSnsLoading] = useState(false);
  const [isFallback, setIsFallback] = useState(false);
  const [apiOnline, setApiOnline] = useState(true);

  const [apiEndpoint, setApiEndpoint] = useState(
    // On CloudFront, use same origin so nginx proxies /ai/ and /telemetry/ to the backend pod.
    // For local dev, default to localhost:8000.
    typeof window !== 'undefined' && window.location.hostname !== 'localhost'
      ? window.location.origin
      : 'http://localhost:8000'
  );

  // Auth
  const [idToken, setIdToken] = useState(() => sessionStorage.getItem('fp_id_token') || '');
  const [operatorEmail, setOperatorEmail] = useState(
    () => sessionStorage.getItem('fp_email') || 'admin@fleetpulse.io'
  );
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  // Editable telemetry overrides for selected vehicle
  const selectedBase = fleet.find((v) => v.id === selectedVehicleId) || fleet[0];
  const [editBattery, setEditBattery] = useState(selectedBase.battery);
  const [editTemp, setEditTemp] = useState(selectedBase.temp);
  const [editDiagnostics, setEditDiagnostics] = useState(selectedBase.diagnostics);

  // Sync editable fields when selected vehicle changes
  useEffect(() => {
    const v = fleet.find((x) => x.id === selectedVehicleId) || fleet[0];
    setEditBattery(v.battery);
    setEditTemp(v.temp);
    setEditDiagnostics(v.diagnostics);
    setAiOutput('');
    setSnsStatus('');
  }, [selectedVehicleId]);

  // Live telemetry poll
  useEffect(() => {
    if (!idToken) return;
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${apiEndpoint}/telemetry/fleet`, {
          headers: { Authorization: `Bearer ${idToken}` },
        });
        if (res.status === 401) { handleLogout(); return; }
        if (res.ok && active) {
          const data = await res.json();
          if (data.vehicles) setFleet(data.vehicles);
          setLastSync(new Date().toLocaleTimeString());
          setApiOnline(true);
        }
      } catch (_) {
        setApiOnline(false);
      }
    };
    poll();
    const timer = setInterval(poll, 5000);
    return () => { active = false; clearInterval(timer); };
  }, [idToken, apiEndpoint]);

  // ── Auth ──────────────────────────────────────────────────────────────────
  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    try {
      const res = await fetch(`https://cognito-idp.${COGNITO_REGION}.amazonaws.com/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-amz-json-1.1',
          'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
        },
        body: JSON.stringify({
          AuthFlow: 'USER_PASSWORD_AUTH',
          ClientId: COGNITO_CLIENT_ID,
          AuthParameters: { USERNAME: operatorEmail, PASSWORD: password },
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || 'Authentication failed');
      const token = data.AuthenticationResult.IdToken;
      sessionStorage.setItem('fp_id_token', token);
      sessionStorage.setItem('fp_email', operatorEmail);
      setIdToken(token);
      setPassword('');
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('fp_id_token');
    setIdToken('');
    setAiOutput('');
    setSnsStatus('');
  };

  // ── AI Dispatch ───────────────────────────────────────────────────────────
  const runAiDispatch = async () => {
    setLoading(true);
    setAiOutput('');
    setIsFallback(false);

    // Send both canonical (v2) and legacy field names for full backend compatibility
    const payload = {
      vehicle_id: selectedVehicleId,
      battery_level: parseFloat(editBattery),
      battery_charge: parseFloat(editBattery),       // legacy compat
      temperature_celsius: parseFloat(editTemp),
      battery_temp: parseFloat(editTemp),             // legacy compat
      route_diagnostics: editDiagnostics,
    };

    try {
      const res = await fetch(`${apiEndpoint}/ai/dispatch-assistant`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(idToken ? { Authorization: `Bearer ${idToken}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      const ct = res.headers.get('content-type') || '';
      if (!ct.includes('application/json')) throw new Error('Non-JSON response (tunnel may be offline).');
      const data = await res.json();
      if (!res.ok) {
        // FastAPI validation errors return detail as an array of objects — serialize properly
        const detail = Array.isArray(data.detail)
          ? data.detail.map((e) => `${e.loc?.join('.')}: ${e.msg}`).join('\n')
          : (data.detail || 'API Error');
        throw new Error(detail);
      }

      setAiOutput(data.recommendation || data.response || JSON.stringify(data, null, 2));
      setApiOnline(true);
    } catch (err) {
      // Fallback: generate a realistic simulated response
      setIsFallback(true);
      setApiOnline(false);
      await new Promise((r) => setTimeout(r, 1200)); // simulate latency
      setAiOutput(
        generateFallbackResponse(
          selectedVehicleId,
          parseFloat(editBattery),
          parseFloat(editTemp),
          editDiagnostics
        )
      );
    } finally {
      setLoading(false);
    }
  };

  // ── SNS Alert ─────────────────────────────────────────────────────────────
  const triggerSnsAlert = async () => {
    setSnsLoading(true);
    setSnsStatus('');
    try {
      const res = await fetch(`${apiEndpoint}/telemetry/alert-sns`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(idToken ? { Authorization: `Bearer ${idToken}` } : {}),
        },
        body: JSON.stringify({
          vehicle_id: selectedVehicleId,
          battery_level: parseFloat(editBattery),
          temperature_celsius: parseFloat(editTemp),
          route_diagnostics: editDiagnostics,
        }),
      });
      const ctSns = res.headers.get('content-type') || '';
      if (!ctSns.includes('application/json')) throw new Error('Non-JSON response (possible proxy error).');
      const data = await res.json();
      if (!res.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((e) => `${e.loc?.join('.')}: ${e.msg}`).join('\n')
          : (data.detail || 'SNS alert failed');
        throw new Error(detail);
      }
      setSnsStatus(`✓ SNS Alert Dispatched  •  MessageId: ${data.message_id?.slice(0, 12)}…`);
    } catch (err) {
      setSnsStatus(`✗ SNS Error: ${err.message}`);
    } finally {
      setSnsLoading(false);
    }
  };

  // ── Derived state for display ─────────────────────────────────────────────
  const battPct = clamp(editBattery, 0, 100);
  const tempPct = clamp((editTemp / 70) * 100, 0, 100); // 70°C = 100%

  const derivedStatus =
    editBattery < 20 || editTemp > 45
      ? 'Critical'
      : editBattery < 50 || editTemp > 38
      ? 'Warning'
      : 'Optimal';

  // ── Login Screen ──────────────────────────────────────────────────────────
  if (!idToken) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
        <div className="w-full max-w-md bg-slate-900/80 backdrop-blur border border-slate-800 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-amber-500/10 rounded-xl border border-amber-500/20">
              <Zap className="w-7 h-7 text-amber-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">FleetPulse Operations</h1>
              <p className="text-xs text-slate-400">AWS Cognito · WAF · CloudFront</p>
            </div>
          </div>

          <p className="text-xs text-slate-500 mb-6 mt-4 leading-relaxed">
            Sign in with your operator credentials to access the live EV telemetry command center.
          </p>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Operator Email</label>
              <input
                type="email"
                required
                value={operatorEmail}
                onChange={(e) => setOperatorEmail(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition"
              />
            </div>
            {authError && (
              <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                {authError}
              </div>
            )}
            <button
              type="submit"
              disabled={authLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-indigo-600/20"
            >
              <Lock className="w-4 h-4" />
              {authLoading ? 'Authenticating…' : 'Sign In with Cognito'}
            </button>
          </form>

          <div className="mt-5 pt-4 border-t border-slate-800 text-center">
            <p className="text-xs text-slate-600">
              Or{' '}
              <button
                onClick={() => setIdToken('demo')}
                className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
              >
                continue in Demo Mode
              </button>{' '}
              (simulated AI, no live data)
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ── Main Dashboard ────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* ── Header ── */}
      <header className="sticky top-0 z-10 bg-slate-950/90 backdrop-blur border-b border-slate-800 px-6 py-3">
        <div className="flex flex-wrap justify-between items-center gap-4">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-amber-500/10 rounded-lg border border-amber-500/20">
              <Zap className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white leading-tight">
                FleetPulse Operations Command
              </h1>
              <p className="text-xs text-slate-500">
                Live EV Telemetry Stream · Last sync:{' '}
                <span className="text-slate-300">{lastSync}</span>
              </p>
            </div>
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* API Endpoint */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-500 hidden sm:inline">API:</span>
              <input
                type="text"
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 px-3 py-1.5 rounded-lg w-52 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/30 transition font-mono"
                placeholder="http://localhost:8000"
              />
            </div>

            {/* Connectivity badge */}
            <span
              className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border font-medium transition-all ${
                apiOnline
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-red-500/10 text-red-400 border-red-500/20'
              }`}
            >
              {apiOnline ? (
                <>
                  <Wifi className="w-3.5 h-3.5" /> EKS Connected
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5" /> Offline · Demo Mode
                </>
              )}
            </span>

            {/* Auth badge / sign out */}
            {idToken === 'demo' ? (
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition"
              >
                <LogOut className="w-3.5 h-3.5" /> Exit Demo
              </button>
            ) : (
              <>
                <span className="flex items-center gap-1.5 text-xs bg-indigo-500/10 text-indigo-300 px-3 py-1.5 rounded-full border border-indigo-500/20">
                  <ShieldCheck className="w-3.5 h-3.5" /> WAF + TLS + Cognito
                </span>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition"
                >
                  <LogOut className="w-3.5 h-3.5" /> Sign Out
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ── 3-Column Layout ── */}
      <div className="p-6 grid grid-cols-1 lg:grid-cols-[300px_1fr_380px] gap-5 items-start">

        {/* ── LEFT: Fleet Overview ── */}
        <aside className="bg-slate-900/60 backdrop-blur border border-slate-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <Navigation className="w-4 h-4 text-indigo-400" />
            Live EV Fleet
            <span className="ml-auto text-xs text-slate-500 font-normal">{fleet.length} active</span>
          </h2>
          <div className="space-y-2.5">
            {fleet.map((v) => {
              const isSelected = v.id === selectedVehicleId;
              return (
                <button
                  key={v.id}
                  onClick={() => setSelectedVehicleId(v.id)}
                  className={`w-full text-left p-4 rounded-lg border transition-all group ${
                    isSelected
                      ? 'bg-indigo-950/50 border-indigo-500/60 shadow-md shadow-indigo-900/30'
                      : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex justify-between items-center mb-2.5">
                    <div className="flex items-center gap-2">
                      {isSelected && <ChevronRight className="w-3.5 h-3.5 text-indigo-400" />}
                      <span className="font-bold text-white text-sm">{v.id}</span>
                    </div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full border font-medium ${statusColors(v.status)}`}
                    >
                      {v.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mb-3">👤 {v.driver}</p>
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs">
                      <Battery className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <div className="flex-1 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${batteryColor(v.battery)}`}
                          style={{ width: `${v.battery}%` }}
                        />
                      </div>
                      <span className="text-slate-300 w-10 text-right">{v.battery}%</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <Thermometer className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                      <div className="flex-1 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${tempColor(v.temp)}`}
                          style={{ width: `${Math.min((v.temp / 70) * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-slate-300 w-12 text-right">{v.temp}°C</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        {/* ── MIDDLE: Telemetry Inspector ── */}
        <section className="bg-slate-900/60 backdrop-blur border border-slate-800 rounded-xl p-5 space-y-5">
          <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            Telemetry Inspector &amp; Parameter Controls
          </h2>

          {/* Vehicle ID card */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-500 mb-0.5">Target Vehicle</p>
              <p className="text-3xl font-black text-white tracking-tight">{selectedVehicleId}</p>
              <p className="text-xs text-slate-400 mt-0.5">👤 Driver: {selectedBase.driver}</p>
            </div>
            <span
              className={`text-sm px-3 py-1 rounded-full border font-semibold ${statusColors(derivedStatus)}`}
            >
              {derivedStatus}
            </span>
          </div>

          {/* Battery gauge */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Battery className="w-4 h-4 text-emerald-400" />
                Battery Level
              </div>
              <span
                className={`text-2xl font-black tabular-nums ${
                  battPct < 20 ? 'text-red-400' : battPct < 50 ? 'text-amber-400' : 'text-emerald-400'
                }`}
              >
                {Number(editBattery).toFixed(1)}%
              </span>
            </div>
            <GaugeBar pct={battPct} colorClass={batteryColor(battPct)} />
          </div>

          {/* Temperature gauge */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Thermometer className="w-4 h-4 text-amber-400" />
                Battery Temperature
              </div>
              <span
                className={`text-2xl font-black tabular-nums ${
                  editTemp > 45 ? 'text-red-400' : editTemp > 38 ? 'text-amber-400' : 'text-blue-400'
                }`}
              >
                {Number(editTemp).toFixed(1)}°C
              </span>
            </div>
            <GaugeBar pct={tempPct} colorClass={tempColor(editTemp)} />
          </div>

          {/* Editable parameter controls */}
          <div className="bg-slate-950/60 border border-indigo-500/20 rounded-xl p-4 space-y-4">
            <p className="text-xs font-semibold text-indigo-400 uppercase tracking-widest flex items-center gap-2">
              <Activity className="w-3.5 h-3.5" />
              Live Parameter Override
            </p>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Battery % (0–100)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={editBattery}
                  onChange={(e) => setEditBattery(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40 transition font-mono"
                />
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="0.5"
                  value={editBattery}
                  onChange={(e) => setEditBattery(e.target.value)}
                  className="w-full mt-2 accent-indigo-500 cursor-pointer"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Temperature °C (0–70)</label>
                <input
                  type="number"
                  min="0"
                  max="70"
                  step="0.1"
                  value={editTemp}
                  onChange={(e) => setEditTemp(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40 transition font-mono"
                />
                <input
                  type="range"
                  min="0"
                  max="70"
                  step="0.5"
                  value={editTemp}
                  onChange={(e) => setEditTemp(e.target.value)}
                  className="w-full mt-2 accent-amber-500 cursor-pointer"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Route Diagnostics</label>
              <textarea
                rows={3}
                value={editDiagnostics}
                onChange={(e) => setEditDiagnostics(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40 transition resize-none font-mono leading-relaxed"
              />
            </div>
          </div>

          {/* Action buttons */}
          <div className="space-y-2.5">
            <button
              onClick={runAiDispatch}
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] text-white font-semibold py-3 px-4 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                <Cpu className="w-5 h-5" />
              )}
              Run AI Dispatch Recommendation
            </button>

            <button
              onClick={triggerSnsAlert}
              disabled={snsLoading}
              className="w-full bg-red-600/90 hover:bg-red-500 active:scale-[0.98] text-white font-semibold py-2.5 px-4 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <BellRing className="w-4 h-4" />
              {snsLoading ? 'Publishing to Amazon SNS…' : 'Dispatch SNS Critical Alert'}
            </button>

            {snsStatus && (
              <div
                className={`text-xs rounded-lg p-2.5 text-center border ${
                  snsStatus.startsWith('✓')
                    ? 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30'
                    : 'text-red-300 bg-red-500/10 border-red-500/30'
                }`}
              >
                {snsStatus}
              </div>
            )}
          </div>
        </section>

        {/* ── RIGHT: AI Dispatch Action Center ── */}
        <aside className="bg-slate-900/60 backdrop-blur border border-slate-800 rounded-xl p-5 flex flex-col min-h-[600px]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" />
              AI Dispatch Action Center
            </h2>
            {isFallback && (
              <span className="flex items-center gap-1 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-full">
                <WifiOff className="w-3 h-3" /> Simulated
              </span>
            )}
            {aiOutput && !isFallback && (
              <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
                <Wifi className="w-3 h-3" /> Live API
              </span>
            )}
          </div>

          {/* Terminal window chrome */}
          <div className="flex items-center gap-1.5 mb-2">
            <span className="w-3 h-3 rounded-full bg-red-500/70" />
            <span className="w-3 h-3 rounded-full bg-amber-500/70" />
            <span className="w-3 h-3 rounded-full bg-emerald-500/70" />
            <span className="ml-2 text-xs text-slate-600 font-mono">
              dispatch-ai › {selectedVehicleId.toLowerCase()}
            </span>
          </div>

          {/* Terminal body */}
          <div className="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-xs overflow-y-auto min-h-[480px]">
            {loading ? (
              <LoadingDots label="Invoking AI dispatch engine" />
            ) : aiOutput ? (
              <pre className="text-slate-200 whitespace-pre-wrap leading-relaxed">{aiOutput}</pre>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-600 text-center gap-3">
                <Cpu className="w-10 h-10 text-slate-800" />
                <p className="text-sm">AI Dispatch Action Center</p>
                <p className="text-xs max-w-xs leading-relaxed">
                  Adjust telemetry parameters on the left, then click{' '}
                  <span className="text-indigo-400">Run AI Dispatch Recommendation</span> to generate
                  live directives.
                </p>
                <p className="text-xs text-slate-700 mt-2">
                  Auto-fallback to simulated mode if API is offline.
                </p>
              </div>
            )}
          </div>

          {/* Footer info */}
          {aiOutput && (
            <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-600">
              <span>{isFallback ? '⚡ Simulated · FleetPulse Engine v2.3' : '⚡ OpenRouter · Gemini-Pro'}</span>
              <button
                onClick={() => { setAiOutput(''); setIsFallback(false); }}
                className="flex items-center gap-1 text-slate-500 hover:text-slate-300 transition"
              >
                <RefreshCw className="w-3 h-3" /> Clear
              </button>
            </div>
          )}
        </aside>

      </div>
    </div>
  );
}
