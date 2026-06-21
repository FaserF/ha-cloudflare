# Services

The integration provides powerful actions for deployment management.

## `cloudflare_advanced.purge_cache`

Purges files stored on edge cache layers.

- **`zone_id`**: (Required) Unique identifier of the domain zone.
- **`purge_everything`**: (Optional) Clears all cached elements if True (default: `true`).
- **`files`**: (Optional) Specify exact asset URLs to selectively wipe.

## `cloudflare_advanced.update_dns_record`

Updates IP targets.

- **`zone_id`**: (Required) Target Cloudflare Zone.
- **`record_id`**: (Required) Cloudflare record reference.
- **`name`**: (Required) Record name string (e.g. `sub.example.com`).
- **`type`**: (Required) Protocol format (`A`, `CNAME`, `AAAA`).
- **`content`**: (Required) Upstream destination.

## `cloudflare_advanced.create_dns_record`

Constructs completely new entries.

- **`zone_id`**: (Required) Domain reference.
- **`name`**: (Required) Title endpoint string.
- **`type`**: (Required) Schema type.
- **`content`**: (Required) IP binding.
