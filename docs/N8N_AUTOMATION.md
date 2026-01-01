# n8n Workflow for Automated Video Generation

Use n8n Cloud (free) to schedule automated video creation.

## Setup

### 1. Create n8n Cloud Account
- Go to [n8n.io/cloud](https://n8n.io/cloud)
- Sign up (no credit card required)
- Free tier: 5 active workflows

### 2. Get Your Auth Token
1. Log into your app at `https://your-app.onrender.com`
2. Open browser DevTools → Network tab
3. Make any API request and copy the `Authorization: Bearer <token>` header
4. Save this token for n8n

---

## Create Workflow

### Step 1: Schedule Trigger
- Add **Schedule Trigger** node
- Set cron: `0 2 * * *` (10 AM Philippine time)

### Step 2: HTTP Request
- Add **HTTP Request** node
- Configure:

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `https://your-app.onrender.com/api/v1/projects/auto-generate` |
| Authentication | Header Auth |
| Header Name | Authorization |
| Header Value | `Bearer YOUR_CLERK_TOKEN` |
| Body Type | JSON |

**Body:**
```json
{
  "topic_category": "surprising science facts that most people don't know",
  "video_format": "vertical",
  "auto_upload": true
}
```

### Step 3: (Optional) Notification
- Add **Slack/Discord/Email** node to notify when video starts generating

---

## Example Categories

Change `topic_category` to customize your content:

| Niche | Topic Category |
|-------|----------------|
| Science | "mind-blowing science facts" |
| History | "fascinating historical events most people don't know" |
| Psychology | "psychology tricks that actually work" |
| Money | "money habits of wealthy people" |
| Motivation | "daily motivation and success mindset" |
| Tech | "cool technology facts and innovations" |

---

## Workflow JSON (Import)

Copy and import in n8n:

```json
{
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [{"field": "cronExpression", "expression": "0 2 * * *"}]
        }
      },
      "name": "Daily 10AM PH",
      "type": "n8n-nodes-base.scheduleTrigger",
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "https://your-app.onrender.com/api/v1/projects/auto-generate",
        "method": "POST",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {"name": "topic_category", "value": "surprising science facts"},
            {"name": "video_format", "value": "vertical"},
            {"name": "auto_upload", "value": "={{true}}"}
          ]
        }
      },
      "name": "Create Video",
      "type": "n8n-nodes-base.httpRequest",
      "position": [450, 300]
    }
  ],
  "connections": {
    "Daily 10AM PH": {
      "main": [[{"node": "Create Video", "type": "main", "index": 0}]]
    }
  }
}
```

---

## Troubleshooting

### Token Expired
Clerk tokens expire. For production, set up a separate API key system or use Clerk's long-lived tokens.

### Workflow Not Running
- Check n8n execution history
- Verify your Render app is awake (free tier sleeps after 15 min)
- Add a "wake up" HTTP request before the main request
