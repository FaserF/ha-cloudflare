# Configuration

Adding your Cloudflare account is entirely done via the UI. **No YAML configuration is required.**

1. Navigate to **Settings > Devices & Services** in Home Assistant.
2. Click **Add Integration** and search for **Cloudflare Advanced**.
3. Choose Authentication:
   - **API Token (Recommended)**: Generate a secure scoped token.
   - **Legacy Credentials**: E-Mail address + Global API Key.
4. Select which active domain zones you wish to initialize.

---

## 🛡️ Security & Scopes

To use the recommended API Token method, you must generate a token in your Cloudflare account.

You can jump directly to the [Cloudflare API Tokens Dashboard](https://dash.cloudflare.com/profile/api-tokens) or follow these steps manually:
1. Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. In the top right, click on your **Profile Icon** and select **My Profile**.
3. Go to the **API Tokens** tab.
4. Click **Create Token** and select **Create Custom Token**.

For a comprehensive step-by-step tutorial, refer to the official [Cloudflare Token Creation Guide](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/).

Ensure your generated API Token follows the **Principle of Least Privilege**. Grant access solely to the required scopes for your selected domains:

### Required Scopes (Zone-level)
- `Analytics` (Read) - For traffic & security metrics.
- `Zone` (Read) - For zone discovery and metadata.
- `Zone Settings` (Read/Edit) - For performance and network toggles.
- `Page Rules` (Read/Edit) - For URL filter management.
- `DNS` (Read/Edit) - For DDNS updates and record control.
- `Firewall Services` (Read/Edit) - For custom WAF rule toggles.
- `Cache Rules` (Read/Edit) - For advanced Cache rules.
- `Email Routing` (Read/Edit) - For email forwarding rule control.
- `Cache Purge` (Edit) - For manual cache clearing.

### Optional Scopes (Account-level)
- `Cloudflare Zero Trust` (Read/Edit) - For Tunnels and Gateway policies.
- `Workers Scripts` (Read) - For Worker status tracking.
- `Cloudflare Pages` (Read) - For project deployment status.
- `Cloudflare Images` (Read) - For storage capacity monitoring.
- `Load Balancing` (Read) - For health diagnostics of LB pools.
- `Registrar` (Read/Edit) - For domain management and auto-renew toggles.
