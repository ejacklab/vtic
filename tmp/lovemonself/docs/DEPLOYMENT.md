# MoneyFlow Deployment Guide

Step-by-step deployment instructions for the MoneyFlow platform.

## Components

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend | Firebase Hosting | ejai.ai |
| Backend | Cloud Run | api-gateway-197629616256.asia-southeast1.run.app |
| Database | Firestore | — |

## Prerequisites

- Google Cloud account with billing enabled
- Firebase project (can be the same GCP project)
- `gcloud` CLI installed and authenticated
- `firebase` CLI installed

```bash
# Install gcloud CLI
# See: https://cloud.google.com/sdk/docs/install

# Install Firebase CLI
npm install -g firebase-tools

# Authenticate
gcloud auth login
firebase login
```

---

## Frontend Deployment (Firebase Hosting)

### Configuration

The `firebase.json` in `ejai-landing-page` is pre-configured:

```json
{
  "hosting": {
    "source": ".",
    "frameworksBackend": {
      "region": "us-central1"
    }
  },
  "firestore": {
    "rules": "firestore.rules",
    "indexes": "firestore.indexes.json"
  }
}
```

### Set Environment Variables

Before deployment, configure environment variables:

**Option 1: Firebase Console**

1. Go to Firebase Console → Your Project → Hosting
2. Set environment variables in the dashboard

**Option 2: `.env.local` (for local dev)**

Create `.env.local` in project root:

```env
NEXT_PUBLIC_FIREBASE_API_KEY=your-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
NEXT_PUBLIC_FIREBASE_APP_ID=your-app-id
NEXT_PUBLIC_API_GATEWAY_URL=https://api-gateway-197629616256.asia-southeast1.run.app
```

### Deploy

```bash
cd ejai-landing-page

# Install dependencies
npm install

# Build for production
npm run build

# Deploy hosting only
firebase deploy --only hosting

# Or deploy everything (hosting + firestore)
firebase deploy
```

### CI/CD (Optional)

Currently, deployment is manual via CLI. To set up GitHub Actions:

1. Generate a Firebase CI token:
   ```bash
   firebase login:ci
   ```

2. Add `FIREBASE_TOKEN` to GitHub repository secrets

3. Create `.github/workflows/firebase-hosting-merge.yml`:

```yaml
name: Deploy to Firebase Hosting

on:
  push:
    branches:
      - main

jobs:
  build_and_deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm run build

      - uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: ${{ secrets.GITHUB_TOKEN }}
          firebaseServiceAccount: ${{ secrets.FIREBASE_SERVICE_ACCOUNT }}
          channelId: live
          projectId: your-project-id
```

---

## Backend Deployment (Cloud Run)

### Current Deployment

The backend is already live at:
```
https://api-gateway-197629616256.asia-southeast1.run.app
```

### Prerequisites

1. **Service Account** with roles:
   - `roles/datastore.user` — Firestore read/write
   - `roles/firebaseauth.admin` — Verify ID tokens

2. **Service Account Key** (JSON) stored securely

### Deploy New Version

```bash
cd lovemonself/backend

# Set project
gcloud config set project YOUR_GCP_PROJECT_ID

# Deploy
gcloud run deploy moneyflow-backend \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated
```

### Set Environment Variables

```bash
gcloud run deploy moneyflow-backend \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars "MFL_FIREBASE_PROJECT_ID=your-project-id" \
  --set-env-vars "MFL_CONNECT_BASE_URL=https://ejai.ai"
```

### Mount Service Account (Recommended)

Use Cloud Secret Manager for credentials:

```bash
# Create secret
gcloud secrets create firebase-creds \
  --data-file=./service-account.json

# Grant Cloud Run access to the secret
gcloud secrets add-iam-policy-binding firebase-creds \
  --member serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role roles/secretmanager.secretAccessor

# Deploy with secret mounted
gcloud run deploy moneyflow-backend \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-secrets "MFL_FIREBASE_CREDENTIALS_PATH=/secrets/firebase-creds"
```

### Alternative: Environment Variable (Not Recommended for Production)

```bash
# Store JSON as base64 in env var
CREDENTIALS_B64=$(base64 -w 0 service-account.json)

gcloud run deploy moneyflow-backend \
  --set-env-vars "MFL_FIREBASE_CREDENTIALS_JSON=${CREDENTIALS_B64}"
```

---

## Firestore Deployment

### Security Rules

Deploy rules from `ejai-landing-page/firestore.rules`:

```bash
cd ejai-landing-page
firebase deploy --only firestore:rules
```

### Indexes

Deploy indexes from `ejai-landing-page/firestore.indexes.json`:

```bash
firebase deploy --only firestore:indexes
```

### Current Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /messages/{messageId} {
      // Public can create messages (contact form)
      allow create: if request.resource.data.keys().hasAll(['name', 'email', 'message', 'createdAt'])
                    && request.resource.data.name is string
                    && request.resource.data.name.size() > 0
                    && request.resource.data.name.size() <= 100
                    && request.resource.data.email is string
                    && request.resource.data.email.size() > 5
                    && request.resource.data.email.size() <= 100
                    && request.resource.data.message is string
                    && request.resource.data.message.size() > 0
                    && request.resource.data.message.size() <= 1000;

      // No public read/update/delete
      allow read, update, delete: if false;
    }
  }
}
```

---

## Environment Checklist

### Frontend (`ejai-landing-page`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | ✅ | Firebase API key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | ✅ | e.g., `project.firebaseapp.com` |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | ✅ | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | ⬜ | e.g., `project.appspot.com` |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | ⬜ | FCM sender ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | ✅ | Firebase app ID |
| `NEXT_PUBLIC_API_GATEWAY_URL` | ✅ | Backend URL |

### Backend (`lovemonself/backend`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MFL_FIREBASE_PROJECT_ID` | ✅ | — | GCP project ID |
| `MFL_FIREBASE_CREDENTIALS_PATH` | ✅ | — | Path to service account JSON |
| `MFL_CONNECT_BASE_URL` | ✅ | `https://moneyflow.app` | Frontend URL |
| `MFL_DEVICE_CODE_TTL_SECONDS` | ⬜ | `300` | Device code expiry |
| `MFL_POLL_INTERVAL_SECONDS` | ⬜ | `5` | Polling interval |
| `MFL_SLOW_DOWN_THRESHOLD` | ⬜ | `10` | Polls before slow_down |
| `MFL_SLOW_DOWN_INTERVAL` | ⬜ | `10` | Interval after slow_down |
| `MFL_TOKEN_TTL_DAYS` | ⬜ | `365` | Token validity |
| `MFL_DEBUG` | ⬜ | `False` | Debug mode |

---

## Deployment Verification

### Frontend

```bash
# Check if site is accessible
curl -I https://ejai.ai

# Check connect page
curl -I https://ejai.ai/connect
```

### Backend

```bash
# Health check
curl https://api-gateway-197629616256.asia-southeast1.run.app/health

# API info
curl https://api-gateway-197629616256.asia-southeast1.run.app/api
```

### Full Flow Test

```bash
# Install CLI
pip install mfl

# Run connect flow
mfl connect finan
```

---

## Rollback

### Cloud Run

```bash
# List revisions
gcloud run revisions list --service moneyflow-backend --region asia-southeast1

# Rollback to previous revision
gcloud run services update-traffic moneyflow-backend \
  --to-revisions PREVIOUS_REVISION=100 \
  --region asia-southeast1
```

### Firebase Hosting

```bash
# List release history
firebase hosting:channel:list

# Rollback to previous release
firebase hosting:rollback
```

---

## Monitoring

### Cloud Run Logs

```bash
# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=moneyflow-backend" \
  --limit 50 \
  --region asia-southeast1
```

### Firebase Console

- **Hosting** → View deployment history
- **Firestore** → View usage and rules
- **Authentication** → View sign-in activity

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) — System architecture overview
- [Backend README](../backend/README.md) — Backend setup and API docs
