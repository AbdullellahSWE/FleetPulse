// Cognito sign-in without an SDK: the User Pool "USER_PASSWORD_AUTH" flow is a plain HTTPS JSON call.
// Tokens live in sessionStorage (cleared when the tab closes). The API verifies the signature on every request.

const SESSION_KEY = 'fp_session';

export async function fetchAuthConfig(apiEndpoint) {
  const res = await fetch(`${apiEndpoint}/auth/config`);
  if (!res.ok) throw new Error(`Auth configuration unavailable (HTTP ${res.status})`);
  return res.json();
}

export function parseJwt(token) {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(payload)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(json);
  } catch (_) {
    return {};
  }
}

async function cognitoCall(config, target, body) {
  const res = await fetch(`https://cognito-idp.${config.region}.amazonaws.com/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-amz-json-1.1',
      'X-Amz-Target': `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const code = (data.__type || '').split('#').pop();
    const friendly = {
      NotAuthorizedException: 'Incorrect email or password.',
      UserNotFoundException: 'Incorrect email or password.',
      UserNotConfirmedException: 'This account has not been confirmed yet.',
      PasswordResetRequiredException: 'A password reset is required for this account.',
      TooManyRequestsException: 'Too many attempts. Please wait a moment and try again.',
      LimitExceededException: 'Too many attempts. Please wait a moment and try again.',
    };
    const err = new Error(friendly[code] || data.message || `Sign-in failed (${code || res.status})`);
    err.code = code;
    throw err;
  }
  return data;
}

function toSession(result, previous) {
  const idToken = result.IdToken;
  const claims = parseJwt(idToken);
  return {
    idToken,
    refreshToken: result.RefreshToken || previous?.refreshToken || null,
    expiresAt: (claims.exp || 0) * 1000,
    email: claims.email || claims['cognito:username'] || 'user',
    groups: claims['cognito:groups'] || [],
    devBypass: false,
  };
}

export async function signIn(config, username, password) {
  const data = await cognitoCall(config, 'InitiateAuth', {
    AuthFlow: 'USER_PASSWORD_AUTH',
    ClientId: config.client_id,
    AuthParameters: { USERNAME: username, PASSWORD: password },
  });
  if (data.ChallengeName) {
    throw new Error(`This account must complete a "${data.ChallengeName}" step before signing in. Ask an administrator to reset it.`);
  }
  return toSession(data.AuthenticationResult);
}

export async function refreshSession(config, session) {
  if (!session?.refreshToken) throw new Error('Session expired. Please sign in again.');
  const data = await cognitoCall(config, 'InitiateAuth', {
    AuthFlow: 'REFRESH_TOKEN_AUTH',
    ClientId: config.client_id,
    AuthParameters: { REFRESH_TOKEN: session.refreshToken },
  });
  return toSession(data.AuthenticationResult, session);
}

export function devSession() {
  return { idToken: 'demo', refreshToken: null, expiresAt: 0, email: 'dev@fleetpulse.local', groups: ['FleetAdmins'], devBypass: true };
}

export function loadSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

export function saveSession(session) {
  if (session) sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  else sessionStorage.removeItem(SESSION_KEY);
}

export function isExpiringSoon(session, marginMs = 60000) {
  return !!session && !session.devBypass && session.expiresAt - Date.now() < marginMs;
}
