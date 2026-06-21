# Cloudflare Advanced for Home Assistant

A secure, production-ready Home Assistant integration for Cloudflare. Monitor zone analytics, manage Zero Trust tunnels, control page rules, secure apps, and modify DNS records directly from Home Assistant.

## ✨ Features

- **Zone Analytics**: 
  - **Requests**: Real-time traffic insights.
  - **Bandwidth**: Data transfer metrics (in Megabytes).
  - **Threats Blocked**: See how many malicious requests were prevented.
  - **Unique Visitors**: Track visitor metrics.
  - **Certificate Expiration**: Monitor edge certificate expiry dates.
- **Zero Trust & Tunnels**: 
  - **Tunnel Status**: Monitor status (Connected/Healthy) for Cloudflare Tunnels.
  - **Details**: Track active connection counts and connector daemon versions.
  - **Gateway Policies**: Toggle Zero Trust DNS/HTTP policies on or off.
  - **Load Balancer Pools**: View health diagnostics for origin server distributions.
  - **Registrar Domains**: Track the expiration date of domains registered via Cloudflare.
- **Access Applications, Edge Workers & Pages**: 
  - **Access Apps**: Monitor active statuses for protected assets.
  - **Workers Deployment**: Get uptime diagnostics for deployed Cloudflare Workers.
  - **Pages Deployment**: Track the live deployment state of Cloudflare Pages.
  - **Turnstile Widgets**: Monitor mode configurations.
  - **Cloudflare Images**: Monitor stored vs allowed capacities.
- **Configurable Control**:
  - **Zone Settings**: Toggles for Development Mode, Always Use HTTPS, Automatic HTTPS Rewrites, IPv6 Compatibility, Rocket Loader, WebSockets, Brotli, Hotlink Protection, and Early Hints.
  - **Security Level**: Dropdown options to force immediate strictness (`off`, `essentially_off`, `low`, `medium`, `high`, `under_attack`).
  - **Page Rules**: Disable or enable individual URL filters.
  - **Email Routing**: Toggle custom email forwarding rules on or off.
  - **WAF Rules**: Toggle specific WAF Custom rules to secure origins.
  - **Cache Rules**: Toggle specific advanced caching behavior rules.
  - **Domain Auto-Renew**: Toggle domain registration auto-renewals safely.
  - **API Quota Monitoring**: Tracks remaining API requests and reset time to prevent rate limiting.
  - **Security Logs**: Tracks external attack properties (`Country`, `IP Address`, `Rule Triggered`).
- **Smart Tracking & Logic**:
  - **Automated DDNS Updates**: Automatically detects your router's public IP changes using `Home Assistant` networking infrastructure, seamlessly propagating changes onto mapped Zone A-Records.
  - **Cache Management**: Instantly purge your Cloudflare Zone Cache using custom hardware buttons.
