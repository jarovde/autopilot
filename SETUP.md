# Autopilot Setup (5 minuten)

## Wat het doet
Elke maandag 09:00: Claude schrijft een artikel → auto-post op Dev.to → jij verdient via affiliate links.
Kost ~€0.03 per artikel aan API kosten.

## Stap 1 — Accounts aanmaken
1. **Dev.to account**: https://dev.to/enter — maak account, ga naar Settings → Account → DEV Community API Keys → New Key
2. **Dev.to Partner Program**: https://dev.to/partnerships — aanmelden voor revenue share op je artikelen

## Stap 2 — GitHub repo aanmaken
```bash
cd /home/agent2012/autopilot
git init
git add .
git commit -m "init autopilot"
# Maak repo op github.com en push:
git remote add origin https://github.com/JOUW_USERNAME/autopilot.git
git push -u origin main
```

## Stap 3 — Secrets instellen in GitHub
Ga naar je repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret naam       | Waarde                        |
|-------------------|-------------------------------|
| `ANTHROPIC_API_KEY` | sk-ant-... (van console.anthropic.com) |
| `DEVTO_API_KEY`     | dev_... (van Dev.to settings)  |

## Stap 4 — Affiliate links instellen
Bewerk `pipeline/topics.py`, vervang in `AFFILIATE_LINKS`:
- `digitalocean`: maak account op digitalocean.com/partners → krijg jouw referral link

## Stap 5 — Test handmatig
Ga naar je GitHub repo → Actions → "Auto Publish Article" → Run workflow

## Daarna: volledig passief
- Elke maandag: nieuw artikel live
- 20 topics = 20 weken content
- Meer topics toevoegen in `pipeline/topics.py`

## Inkomsten
- **Dev.to Partner Program**: betaalt per 1000 views (~$1-5)
- **Affiliate links**: DigitalOcean betaalt $25-100 per signup
- **Indirect**: traffic naar je Gumroad starter kit

Met goede SEO-artikelen over Claude/AI kan je na 3-6 maanden €100-500/maand passief verdienen.
