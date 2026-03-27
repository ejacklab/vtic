# MoneyFlow Architecture

System architecture overview for MoneyFlow — a personal finance tracking platform with AI agents.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MONEYFLOW SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐       │
│  │              │     │                  │     │                    │       │
│  │   User       │────▶│   ejai.ai        │────▶│   FastAPI Backend  │       │
│  │  (Browser)   │     │   (Next.js 16)   │     │   (Cloud Run)      │       │
│  │              │     │                  │     │                    │       │
│  └──────────────┘     └────────┬─────────┘     └─────────┬──────────┘       │
│                                │                         │                   │
│                                │ /connect                │ /api/*            │
│                                │ /dashboard              │                   │
│                                ▼                         ▼                   │
│                         ┌──────────────────────────────────────┐             │
│                         │                                      │             │
│                         │         Google Cloud Firestore       │             │
│                         │                                      │             │
│                         │   • device_codes (auth flow)         │             │
│                         │   • tokens (API tokens)              │             │
│                         │   • users (user profiles)            │             │
│                         │   • messages (contact form)          │             │
│                         │                                      │             │
│                         └──────────────────────────────────────┘             │
│                                                                              │
│  ┌──────────────┐     ┌──────────────────┐                                  │
│  │              │     │                  │                                  │
│  │   User       │────▶│   mfl CLI        │                                  │
│  │  (Terminal)  │     │   (Python)       │                                  │
│  │              │     │                  │                                  │
│  └──────────────┘     └────────┬─────────┘                                  │
│                                │                                            │
│                                │ mfl connect finan                          │
│                                │ (opens browser → /connect)                 │
│                                │                                            │
│                                ▼                                            │
│                       Device Code Flow                                      │
│                       (polls /api/connect/poll)                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Overview

### 1. Frontend (ejai.ai)

**Repository:** `yi1jack0/ejai-landing-page`

| Page | Purpose |
|------|---------|
| `/` | Landing page with product info and contact form |
| `/connect` | Device code authentication for CLI tools |
| `/dashboard/api-keys` | Token management for authenticated users |

**Tech Stack:**
- Next.js 16 (App Router)
- TypeScript
- Tailwind CSS v4
- Firebase Auth (Google OAuth)

### 2. Backend (API Gateway)

**Repository:** `yi1jack0/lovemonself/backend`

**Live URL:** `https://api-gateway-197629616256.asia-southeast1.run.app`

**Tech Stack:**
- FastAPI (Python 3.10+)
- Firestore (via firebase-admin)
- slowapi (rate limiting)
- Pydantic v2 (validation)

### 3. CLI Tool (mfl)

**Repository:** `yi1jack0/mfl`

**PyPI Package:** `mfl`

```bash
# Install
pip install mfl

# Connect an agent
mfl connect finan
```

## Backend Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, CORS, rate limiting
│   ├── config.py                  # Settings via pydantic-settings
│   ├── firebase_client.py         # Firebase Admin SDK init
│   ├── models/
│   │   └── schemas.py             # Pydantic request/response models
│   ├── routes/
│   │   ├── connect.py             # /api/connect/* endpoints
│   │   └── tokens.py              # /api/user/tokens/* endpoints
│   └── services/
│       ├── device_code_service.py # Device code flow logic
│       └── token_service.py       # Token CRUD operations
└── tests/
    ├── conftest.py
    ├── test_connect.py
    └── test_tokens.py
```

### Routes

| Router | Prefix | Purpose |
|--------|--------|---------|
| `connect_router` | `/api/connect` | Device code OAuth flow |
| `tokens_router` | `/api/user` | Token management |

### Services

| Service | Responsibility |
|---------|----------------|
| `DeviceCodeService` | Create/poll/complete device codes |
| `TokenService` | CRUD for API tokens, rate limiting |

## Data Model

### Firestore Collections

#### `device_codes`

Stores device authorization codes for CLI authentication.

```typescript
{
  device_code: string,      // Internal code (long, random)
  user_code: string,        // 6-digit code user sees
  status: string,           // "pending" | "completed" | "expired"
  agent: string,            // Agent name (e.g., "finan")
  agent_version: string,    // Agent version
  device_id: string,        // Device identifier
  user_id: string | null,   // Firebase UID (after completion)
  created_at: timestamp,
  expires_at: timestamp,
  completed_at: timestamp | null,
  token_id: string | null,  // Reference to created token
  token_delivered: boolean  // CLI received the token
}
```

#### `tokens`

Stores API tokens for authenticated users.

```typescript
{
  token_id: string,         // Unique identifier
  user_id: string,          // Firebase UID
  token_hash: string,       // Hashed token (not raw)
  label: string,            // User-defined label
  source: string,           // "device_code" | "dashboard"
  agent: string | null,     // Agent name (if from device flow)
  created_at: timestamp,
  expires_at: timestamp,
  last_used_at: timestamp | null,
  revoked_at: timestamp | null
}
```

#### `users`

User profiles (optional, for future use).

```typescript
{
  user_id: string,          // Firebase UID
  email: string,
  display_name: string | null,
  created_at: timestamp,
  last_login_at: timestamp
}
```

#### `messages`

Contact form submissions from landing page.

```typescript
{
  name: string,             // Max 100 chars
  email: string,            // Max 100 chars
  message: string,          // Max 1000 chars
  createdAt: timestamp
}
```

## Authentication Flow

### Frontend Auth (Firebase)

Users authenticate via Firebase Google OAuth:

1. User clicks "Sign in with Google"
2. Firebase handles OAuth popup
3. Frontend receives Firebase ID token
4. Token stored in browser session
5. ID token sent in `Authorization: Bearer` header for API calls

### CLI Auth (Device Code Grant)

For CLI tools without browser access, we use OAuth 2.0 Device Authorization Grant (RFC 8628):

```
┌─────────┐                          ┌─────────┐                    ┌───────────┐
│   CLI   │                          │  API    │                    │ Firestore │
└────┬────┘                          └────┬────┘                    └─────┬─────┘
     │                                    │                               │
     │ POST /api/connect/start            │                               │
     │───────────────────────────────────▶│                               │
     │                                    │ Create device_code            │
     │                                    │──────────────────────────────▶│
     │ { device_code, user_code, url }    │                               │
     │◀───────────────────────────────────│                               │
     │                                    │                               │
     │ Open browser to url                │                               │
     │                                    │                               │
     │                                    │ GET /api/connect/validate     │
     │                                    │◀──────────────────────────────│
     │                                    │ { valid: true }               │
     │                                    │──────────────────────────────▶│
     │                                    │                               │
     │                                    │ POST /api/connect/complete    │
     │                                    │◀──────────────────────────────│
     │                                    │ (with Firebase ID token)      │
     │                                    │                               │
     │                                    │ Update device_code            │
     │                                    │ Create token                  │
     │                                    │──────────────────────────────▶│
     │                                    │                               │
     │ GET /api/connect/poll              │                               │
     │───────────────────────────────────▶│                               │
     │                                    │ Check status                  │
     │                                    │──────────────────────────────▶│
     │ { status: "completed", token }     │                               │
     │◀───────────────────────────────────│                               │
     │                                    │                               │
```

**Slow Down Mechanism:**

To prevent abuse, the poll endpoint implements RFC 8628 `slow_down`:

1. After N polls (configurable via `MFL_SLOW_DOWN_THRESHOLD`)
2. Response includes `status: "slow_down"` with increased `interval`
3. CLI must wait longer before next poll

## Key Environment Variables

### Frontend (ejai-landing-page)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase API key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase auth domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase app ID |
| `NEXT_PUBLIC_API_GATEWAY_URL` | Backend API URL |

### Backend (lovemonself/backend)

| Variable | Default | Description |
|----------|---------|-------------|
| `MFL_FIREBASE_PROJECT_ID` | — | GCP project ID (required) |
| `MFL_FIREBASE_CREDENTIALS_PATH` | — | Path to service account JSON |
| `MFL_CONNECT_BASE_URL` | `https://moneyflow.app` | Frontend URL for connect flow |
| `MFL_DEVICE_CODE_TTL_SECONDS` | `300` | Device code expiry (5 min) |
| `MFL_POLL_INTERVAL_SECONDS` | `5` | Default polling interval |
| `MFL_SLOW_DOWN_THRESHOLD` | `10` | Polls before slow_down |
| `MFL_TOKEN_TTL_DAYS` | `365` | Token validity period |

## Security Considerations

1. **Token Hashing** — Raw tokens are never stored; only hashed versions
2. **Rate Limiting** — Device code endpoints are rate-limited by IP/device
3. **Firestore Rules** — Contact form is write-only for public users
4. **CORS** — Configured for production domain
5. **Input Validation** — All inputs validated via Pydantic schemas

## Related Documentation

- [Backend README](../backend/README.md) — Detailed backend setup and API docs
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Deployment guide for all components
