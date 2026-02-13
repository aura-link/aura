# Cloudflare Configuration - Yesswera

## Account
- **Email:** Valenzuela.carloseduardo@gmail.com
- **Account ID:** 9972f748f0b0e766a4e6814243bf82ad

## Zones

### yesswera.com
- **Zone ID:** bbbc47ebb5e2df48634b5897a033b60c
- **Status:** Active
- **Nameservers:** maeve.ns.cloudflare.com, yahir.ns.cloudflare.com

## DNS Records (yesswera.com)

| Subdomain | Type | Target | Proxied |
|-----------|------|--------|---------|
| api.yesswera.com | CNAME | ca5574c6-7201-4e07-a4e2-cb29962392bb.cfargotunnel.com | Yes |
| expo.yesswera.com | CNAME | ca5574c6-7201-4e07-a4e2-cb29962392bb.cfargotunnel.com | Yes |
| files.yesswera.com | CNAME | 9705e431-b48f-4817-ba99-021f247c5488.cfargotunnel.com | Yes |
| metrics.yesswera.com | CNAME | 9705e431-b48f-4817-ba99-021f247c5488.cfargotunnel.com | Yes |
| www.yesswera.com | CNAME | 8dfb525a514b2c2a.vercel-dns-017.com | No |

## Cloudflare Tunnels

### Tunnel Principal (Yesswera API + Expo)
- **Tunnel ID:** ca5574c6-7201-4e07-a4e2-cb29962392bb
- **Servicios:**
  - api.yesswera.com → Backend API (puerto 3000)
  - expo.yesswera.com → Expo Metro bundler

### Tunnel Secundario (Files + Metrics)
- **Tunnel ID:** 9705e431-b48f-4817-ba99-021f247c5488
- **Servicios:**
  - files.yesswera.com
  - metrics.yesswera.com

## API Token (Claude Access)
- **Token ID:** 20172cebae3a5b54b489245322aa0d89
- **Permissions:** DNS Read/Edit, Zone Read, Cloudflare Tunnel Read
- **Status:** Active

## URLs Principales
- **API Backend:** https://api.yesswera.com/api/
- **Expo Metro:** https://expo.yesswera.com
- **Web (Vercel):** https://www.yesswera.com

## Verificar Estado
```bash
# API Ping
curl https://api.yesswera.com/api/ping

# Verificar túnel via API
curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/9972f748f0b0e766a4e6814243bf82ad/cfd_tunnel" \
  -H "Authorization: Bearer TOKEN"
```
