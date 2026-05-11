# Private deployment options (free-first)

## Recommended architecture

For free + robust access control, use:

1. Streamlit app hosting
2. External identity/access gate

Best practical choices:

- Option A (simple): Streamlit Community Cloud + app-level login (this repo now supports it)
- Option B (stronger security): Local/server Streamlit + Cloudflare Tunnel + Cloudflare Access

---

## Option A: Streamlit Community Cloud + app login

### 1) Push this repo to GitHub

- Create a GitHub repository
- Push current project

### 2) Deploy on Streamlit Community Cloud

- Go to Streamlit Community Cloud
- Connect GitHub
- Select this repo and `app.py`

### 3) Configure secrets

In app settings -> Secrets, paste one of the following.

### Single user (backward compatible)
```toml
[auth]
enabled = true
username = "admin"
password = "your-strong-password"
```

### Multiple allowed users (recommended for allow-list)
```toml
[auth]
enabled = true
users = { "alice" = "pw1", "bob" = "pw2" }
```

### 4) Behavior

- App opens login form first
- Only valid username/password can enter
- Sidebar has Sign out button

### Notes

- This is practical and free.
- Security is app-level, not network-level.
- Use strong password and rotate periodically.

---

## Option B: Cloudflare Tunnel + Cloudflare Access (more secure)

### Why this is stronger

- Access is blocked before app layer
- Allow-list specific emails/domains
- One-time code / SSO policies available

### Basic flow

1. Run Streamlit on your machine/server
2. Expose with Cloudflare Tunnel
3. Protect route with Cloudflare Access policy (only invited users)

### Cost

- Cloudflare free tier usually sufficient for small private team use

---

## Which one should you pick?

- Need fastest setup: Option A
- Need stricter private access with user allow-list: Option B

If you want, we can do Option A first (10-20 min), then upgrade to Option B.
