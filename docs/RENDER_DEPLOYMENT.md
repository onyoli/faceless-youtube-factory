# Render Deployment Guide

Deploy Faceless YouTube Factory to Render (free tier).

## Limitations

| Feature | Free Tier |
|---------|-----------|
| Web Services | 750 hrs/month |
| Sleep | After 15 min inactive |
| RAM | 512 MB |
| Persistent Disk | ❌ No |

> ⚠️ Free tier is limited. Videos stored temporarily will be lost on restart.

---

## Step 1: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with GitHub (recommended)
3. No credit card required

---

## Step 2: Create PostgreSQL Database

1. Dashboard → **New** → **PostgreSQL**
2. Configure:
   - Name: `youtube-factory-db`
   - Region: Choose closest to you
   - Plan: **Free**
3. Click **Create Database**
4. Copy the **Internal Database URL**

---

## Step 3: Deploy Backend

1. Dashboard → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:

| Setting | Value |
|---------|-------|
| Name | `youtube-factory-api` |
| Root Directory | `backend` |
| Runtime | Docker |
| Dockerfile Path | `Dockerfile.cpu` |
| Plan | Free |

4. Add **Environment Variables**:

```
DATABASE_URL=<Internal Database URL from Step 2>
GROQ_API_KEY=your_groq_key
HF_TOKEN=your_huggingface_token
TOKEN_ENCRYPTION_KEY=your_fernet_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
OAUTH_REDIRECT_URI=https://youtube-factory-api.onrender.com/api/v1/youtube/callback
FRONTEND_URL=https://youtube-factory-web.onrender.com
CLERK_SECRET_KEY=your_clerk_secret
DEBUG=false
```

5. Click **Create Web Service**

---

## Step 4: Deploy Frontend

1. Dashboard → **New** → **Web Service**
2. Connect same repo
3. Configure:

| Setting | Value |
|---------|-------|
| Name | `youtube-factory-web` |
| Root Directory | `frontend` |
| Runtime | Docker |
| Plan | Free |

4. Add **Environment Variables**:

```
NEXT_PUBLIC_API_URL=https://youtube-factory-api.onrender.com
NEXT_PUBLIC_WS_URL=wss://youtube-factory-api.onrender.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
```

5. Click **Create Web Service**

---

## Step 5: Update OAuth Redirect

In Google Cloud Console:
1. Go to APIs & Services → Credentials
2. Edit your OAuth client
3. Add Authorized redirect URI:
   ```
   https://youtube-factory-api.onrender.com/api/v1/youtube/callback
   ```

---

## Step 6: Update Clerk

In Clerk Dashboard:
1. Go to your application
2. Add to allowed origins:
   ```
   https://youtube-factory-web.onrender.com
   ```

---

## Using with n8n

Since Render free tier sleeps, your n8n workflow should:

1. First make a "wake up" request to `/health`
2. Wait 30 seconds
3. Then call `/auto-generate`

See `docs/N8N_AUTOMATION.md` for workflow setup.

---

## Troubleshooting

### Service Sleeping
Free tier sleeps after 15 min. First request takes 30-60s to wake.

### Out of Memory
Video generation needs RAM. If failing, consider:
- Paid tier ($7/month for 1GB RAM)
- Using Railway instead (more generous free tier)

### Database Connection
Ensure you're using the **Internal** database URL, not external.
