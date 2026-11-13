import React, { useState, useEffect } from 'react';
import { Battery, Thermometer, ShieldAlert, Cpu, Navigation, Zap, RefreshCw, Lock, LogOut, BellRing, ShieldCheck } from 'lucide-react';

const INITIAL_FLEET = [
    { id: 'EV-9402', driver: 'Alex R.', battery: 14.5, temp: 48.2, status: 'Critical', diagnostics: 'High thermal stress detected under heavy acceleration uphill.' },
    { id: 'EV-1088', driver: 'Jordan M.', battery: 78.0, temp: 31.5, status: 'Optimal', diagnostics: 'Nominal city cruising.' },
    { id: 'EV-3310', driver: 'Sam K.', battery: 42.1, temp: 37.8, status: 'Warning', diagnostics: 'Elevated battery temp during rapid DC charging.' },
    { id: 'EV-7721', driver: 'Taylor B.', battery: 91.4, temp: 28.0, status: 'Optimal', diagnostics: 'Regenerative braking active on highway descent.' }
];

const COGNITO_REGION = 'us-east-1';
const COGNITO_CLIENT_ID = '60ljkjaia3u74terhhcto4n076';

export default function FleetPulseDashboard() {
    const [fleet, setFleet] = useState(INITIAL_FLEET);
    const [selectedVehicleId, setSelectedVehicleId] = useState(INITIAL_FLEET[0].id);
    const [lastSync, setLastSync] = useState('Live');
    const [aiRecommendation, setAiRecommendation] = useState('');
    const [snsStatus, setSnsStatus] = useState('');
    const [loading, setLoading] = useState(false);
    const [snsLoading, setSnsLoading] = useState(false);
    const [apiEndpoint, setApiEndpoint] = useState(
        typeof window !== 'undefined' ? window.location.origin : 'https://d3o21e293sq1am.cloudfront.net'
    );

    const [idToken, setIdToken] = useState(() => sessionStorage.getItem('fp_id_token') || '');
    const [operatorEmail, setOperatorEmail] = useState(() => sessionStorage.getItem('fp_email') || 'admin@fleetpulse.io');
    const [password, setPassword] = useState('');
    const [authError, setAuthError] = useState('');
    const [authLoading, setAuthLoading] = useState(false);

    const selectedVehicle = fleet.find((v) => v.id === selectedVehicleId) || fleet[0];

    useEffect(() => {
        if (!idToken) return;
        let active = true;
        const pollTelemetry = async () => {
            try {
                const res = await fetch(`${apiEndpoint}/telemetry/fleet`, {
                    headers: { 'Authorization': `Bearer ${idToken}` }
                });
                if (res.status === 401) {
                    handleLogout();
                    return;
                }
                if (res.ok && active) {
                    const data = await res.json();
                    if (data.vehicles) setFleet(data.vehicles);
                    setLastSync(new Date().toLocaleTimeString());
                }
            } catch (_) { }
        };
        pollTelemetry();
        const timer = setInterval(pollTelemetry, 5000);
        return () => { active = false; clearInterval(timer); };
    }, [idToken, apiEndpoint]);

    const handleLogin = async (e) => {
        e.preventDefault();
        setAuthLoading(true);
        setAuthError('');
        try {
            const res = await fetch(`https://cognito-idp.${COGNITO_REGION}.amazonaws.com/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-amz-json-1.1',
                    'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
                },
                body: JSON.stringify({
                    AuthFlow: 'USER_PASSWORD_AUTH',
                    ClientId: COGNITO_CLIENT_ID,
                    AuthParameters: {
                        USERNAME: operatorEmail,
                        PASSWORD: password
                    }
                })
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
        setAiRecommendation('');
        setSnsStatus('');
    };

    const triggerSnsAlert = async (vehicle) => {
        setSnsLoading(true);
        setSnsStatus('');
        try {
            const res = await fetch('/telemetry/alert-sns', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}`
                },
                body: JSON.stringify({
                    vehicle_id: vehicle.id,
                    battery_level: vehicle.battery,
                    temperature_celsius: vehicle.temp,
                    route_diagnostics: vehicle.diagnostics
                })
            });
            const contentType = res.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error("Received non-JSON response from server (possible proxy or routing error).");
            }
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'SNS alert failed');
            setSnsStatus(`SNS Alert Dispatched (MessageId: ${data.message_id.slice(0, 12)}...)`);
        } catch (err) {
            setSnsStatus(`SNS Error: ${err.message}`);
        } finally {
            setSnsLoading(false);
        }
    };

    const analyzeVehicleWithAI = async (vehicle) => {
        setLoading(true);
        setAiRecommendation('');
        try {
            const response = await fetch('/ai/dispatch-assistant', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}`
                },
                body: JSON.stringify({
                    vehicle_id: vehicle.id,
                    battery_charge: vehicle.battery,
                    battery_temp: vehicle.temp
                })
            });

            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error("Received non-JSON response from server (possible proxy or routing error).");
            }

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'API Error');
            }

            setAiRecommendation(data.recommendation);
        } catch (err) {
            setAiRecommendation(`Failed to fetch AI recommendation: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    if (!idToken) {
        return (
            <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
                <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
                    <div className="flex items-center gap-3 mb-6">
                        <Zap className="w-8 h-8 text-amber-400" />
                        <div>
                            <h1 className="text-xl font-bold text-white">FleetPulse Operations</h1>
                            <p className="text-xs text-slate-400">AWS WAF + CloudFront + Cognito Sign-In</p>
                        </div>
                    </div>
                    <form onSubmit={handleLogin} className="space-y-4">
                        <div>
                            <label className="block text-xs text-slate-400 mb-1">Operator Email</label>
                            <input
                                type="email"
                                required
                                value={operatorEmail}
                                onChange={(e) => setOperatorEmail(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
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
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
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
                            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            <Lock className="w-4 h-4" />
                            {authLoading ? 'Authenticating...' : 'Sign In with Cognito'}
                        </button>
                    </form>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6">
            <header className="flex flex-wrap justify-between items-center gap-4 mb-8 border-b border-slate-800 pb-4">
                <div className="flex items-center gap-3">
                    <Zap className="w-8 h-8 text-amber-400" />
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-white">FleetPulse Operations Command</h1>
                        <p className="text-sm text-slate-400">Live EV Telemetry Stream ({lastSync}) • OpenRouter AI & SNS Dispatch</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <input
                        type="text"
                        value={apiEndpoint}
                        onChange={(e) => setApiEndpoint(e.target.value)}
                        className="bg-slate-900 border border-slate-700 text-xs text-slate-200 px-3 py-1.5 rounded-lg w-64 focus:outline-none focus:border-amber-400"
                        placeholder="API Host URL"
                    />
                    <span className="flex items-center gap-1.5 text-xs bg-emerald-500/10 text-emerald-400 px-3 py-1.5 rounded-full border border-emerald-500/20 font-medium">
                        <ShieldCheck className="w-3.5 h-3.5" /> WAF + TLS + Cognito
                    </span>
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-1.5 text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700"
                    >
                        <LogOut className="w-3.5 h-3.5" /> Sign Out
                    </button>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-slate-200">
                        <Navigation className="w-5 h-5 text-indigo-400" /> Live EV Fleet ({fleet.length})
                    </h2>
                    <div className="space-y-3">
                        {fleet.map((v) => (
                            <div
                                key={v.id}
                                onClick={() => setSelectedVehicleId(v.id)}
                                className={`p-4 rounded-lg cursor-pointer border transition-all ${selectedVehicle.id === v.id
                                    ? 'bg-indigo-950/40 border-indigo-500'
                                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                                    }`}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <div>
                                        <span className="font-bold text-white text-base">{v.id}</span>
                                        <span className="text-xs text-slate-400 ml-2">({v.driver})</span>
                                    </div>
                                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${v.status === 'Critical' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                                        v.status === 'Warning' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                                            'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                        }`}>
                                        {v.status}
                                    </span>
                                </div>
                                <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                                    <div className="flex items-center gap-1">
                                        <Battery className="w-4 h-4 text-emerald-400" /> {v.battery}%
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Thermometer className="w-4 h-4 text-amber-400" /> {v.temp}°C
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-slate-200">
                        <ShieldAlert className="w-5 h-5 text-amber-400" /> Vehicle Telemetry Inspector
                    </h2>
                    {selectedVehicle && (
                        <div className="space-y-5">
                            <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                                <div className="text-xs text-slate-400 mb-1">Target Vehicle</div>
                                <div className="text-2xl font-bold text-white">{selectedVehicle.id}</div>
                                <div className="text-sm text-slate-400">Assigned Driver: {selectedVehicle.driver}</div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                                    <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                                        <Battery className="w-4 h-4 text-emerald-400" /> Battery Charge
                                    </div>
                                    <div className="text-2xl font-extrabold text-slate-100">{selectedVehicle.battery}%</div>
                                    <div className="w-full bg-slate-800 h-2 rounded-full mt-3 overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${selectedVehicle.battery < 20 ? 'bg-red-500' : 'bg-emerald-400'}`}
                                            style={{ width: `${selectedVehicle.battery}%` }}
                                        ></div>
                                    </div>
                                </div>
                                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                                    <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                                        <Thermometer className="w-4 h-4 text-amber-400" /> Battery Temp
                                    </div>
                                    <div className="text-2xl font-extrabold text-slate-100">{selectedVehicle.temp}°C</div>
                                    <div className="w-full bg-slate-800 h-2 rounded-full mt-3 overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${selectedVehicle.temp > 45 ? 'bg-red-500' : 'bg-amber-400'}`}
                                            style={{ width: `${Math.min(selectedVehicle.temp * 1.5, 100)}%` }}
                                        ></div>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                                <div className="text-xs text-slate-400 mb-2">Live Route Diagnostics</div>
                                <p className="text-sm text-slate-300 leading-relaxed bg-slate-950 p-3 rounded border border-slate-800">
                                    "{selectedVehicle.diagnostics}"
                                </p>
                            </div>
                            <div className="space-y-2.5">
                                <button
                                    onClick={() => analyzeVehicleWithAI(selectedVehicle)}
                                    disabled={loading}
                                    className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 disabled:opacity-50"
                                >
                                    {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Cpu className="w-5 h-5" />}
                                    Run AI Dispatch Recommendation
                                </button>
                                <button
                                    onClick={() => triggerSnsAlert(selectedVehicle)}
                                    disabled={snsLoading}
                                    className="w-full bg-red-600/90 hover:bg-red-500 text-white font-semibold py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    <BellRing className="w-4 h-4" />
                                    {snsLoading ? 'Publishing to Amazon SNS...' : 'Dispatch Amazon SNS Critical Alert'}
                                </button>
                                {snsStatus && (
                                    <div className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5 text-center">
                                        {snsStatus}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 flex flex-col">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-slate-200">
                        <Cpu className="w-5 h-5 text-indigo-400" /> AI Dispatch Assistant Output
                    </h2>
                    <div className="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-sm overflow-y-auto">
                        {loading ? (
                            <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-3">
                                <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
                                <span>Invoking OpenRouter (gpt-4o-mini)...</span>
                            </div>
                        ) : aiRecommendation ? (
                            <div className="text-slate-200 whitespace-pre-wrap leading-relaxed">
                                {aiRecommendation}
                            </div>
                        ) : (
                            <div className="h-full flex items-center justify-center text-slate-600 text-center text-xs">
                                Select a vehicle and click "Run AI Dispatch Recommendation" to generate live directives.
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}