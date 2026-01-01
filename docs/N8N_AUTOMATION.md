# n8n Automation Guide

Use n8n to schedule automated video creation when your PC is off.

## Architecture

```
n8n Cloud (free) → Your Backend API (Railway/Render) → YouTube
     ↓
  Scheduled trigger at 10 AM
     ↓
  HTTP Request to create project
     ↓
  Video generated & uploaded automatically
```

---

## Setup

### 1. Sign up for n8n Cloud

1. Go to [n8n.io/cloud](https://n8n.io/cloud)
2. Create free account (no card needed)
3. You get 5 free active workflows

### 2. Create Workflow

1. Click **Add Workflow**
2. Add nodes in this order:

#### Node 1: Schedule Trigger
- Type: **Schedule Trigger**
- Settings:
  - Rule: `0 2 * * *` (10 AM Philippine time)

#### Node 2: HTTP Request (Generate Topic)
- Type: **HTTP Request**
- Settings:
  - Method: `POST`
  - URL: `https://api.groq.com/openai/v1/chat/completions`
  - Headers:
    - `Authorization`: `Bearer YOUR_GROQ_API_KEY`
    - `Content-Type`: `application/json`
  - Body (JSON):
```json
{
  "model": "llama-3.3-70b-versatile",
  "messages": [
    {
      "role": "user",
      "content": "Generate a unique, engaging topic for a short YouTube video about surprising science facts. Return ONLY the topic, one line, no quotes."
    }
  ],
  "temperature": 0.9
}
```

#### Node 3: HTTP Request (Create Project)
- Type: **HTTP Request**
- Settings:
  - Method: `POST`
  - URL: `https://your-backend.railway.app/api/v1/projects`
  - Headers:
    - `Authorization`: `Bearer YOUR_CLERK_TOKEN`
    - `Content-Type`: `application/json`
  - Body (JSON):
```json
{
  "title": "Auto: {{ $json.choices[0].message.content }}",
  "script_prompt": "{{ $json.choices[0].message.content }}",
  "auto_upload": true,
  "video_format": "vertical"
}
```

### 3. Activate Workflow

Click **Active** toggle → Your workflow runs daily!

---

## Getting Your Clerk Token

For the Authorization header, you need a long-lived Clerk token:

1. Login to your app at `https://your-frontend.railway.app`
2. Open browser DevTools → Network tab
3. Make any API request and copy the `Authorization` header value

**Note:** For production, consider creating a service account or API key system.

---

## Alternative: Simple Cron (No Topic Generation)

If you have predefined topics, use this simpler workflow:

```
Schedule Trigger → HTTP Request (Create Project)
```

With topics rotated from a list:
```json
{
  "title": "Daily Video",
  "script_prompt": "5 surprising facts about [your niche]",
  "auto_upload": true
}
```

---

## Cron Examples

| Time (Philippine) | Cron Expression |
|-------------------|-----------------|
| 10:00 AM | `0 2 * * *` |
| 8:00 PM | `0 12 * * *` |
| 6:00 AM | `0 22 * * *` (prev day UTC) |
| Every 6 hours | `0 */6 * * *` |
