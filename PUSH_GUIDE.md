# MEMBRA CompanyOS — Push Guide

## Status
All code is committed locally. GitHub push requires a fresh personal access token.

## Your Repositories

| Repo | Local Path | GitHub URL |
|------|-----------|------------|
| membra-companyos | `/Users/alep/membra-companyos` | `github.com/overandor/membra-companyos` |
| membra_db | `/Users/alep/Downloads` | `github.com/overandor/membra_db` |
| membra-sdk | `/Users/alep/Downloads/membra-sdk` | `github.com/nutclosedAI/membra` |
| tokenize-camera-app | `/Users/alep/Downloads/tokenize-camera-app` | `github.com/overandor/tokenize-camera` |
| flashloan-bench | `/Users/alep/Documents/flashloan-bench` | `github.com/overandor/flashloan-bench` |
| compute-llm-inference | `/Users/alep/Downloads/compute_llm_inference` | `github.com/overandor/compute-llm-inference` |
| membra_human_chain | `/Users/alep/Downloads/membra_human_chain` | `github.com/overandor/membra-qr-gateway` |

## Step 1 — Generate Fresh GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`
4. Copy the token (starts with `ghp_`)

## Step 2 — Push membra-companyos (master repo)

```bash
cd /Users/alep/membra-companyos
git remote set-url origin https://<NEW_TOKEN>@github.com/overandor/membra-companyos.git
git push origin main
```

## Step 3 — Push all repos (batch)

```bash
TOKEN="<NEW_TOKEN>"

# membra-companyos
cd /Users/alep/membra-companyos && git push origin main

# Downloads (membra_db)
cd /Users/alep/Downloads && git remote set-url origin https://${TOKEN}@github.com/overandor/membra_db.git && git push origin main --force

# membra-sdk
cd /Users/alep/Downloads/membra-sdk && git push origin main

# tokenize-camera-app
cd /Users/alep/Downloads/tokenize-camera-app && git push origin main

# flashloan-bench
cd /Users/alep/Documents/flashloan-bench && git push origin main

# compute_llm_inference
cd /Users/alep/Downloads/compute_llm_inference && git remote set-url origin https://${TOKEN}@github.com/overandor/compute-llm-inference.git && git push origin main

# membra_human_chain
cd /Users/alep/Downloads/membra_human_chain && git push origin main
```

## Alternative — SSH (Recommended)

Generate SSH keys once, never deal with tokens again:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/id_membra
cat ~/.ssh/id_membra.pub
```

Copy the public key to https://github.com/settings/keys

Then update remotes:

```bash
cd /Users/alep/membra-companyos
git remote set-url origin git@github.com:overandor/membra-companyos.git
git push origin main
```

## Last Commit Summary

```
feat: 6 novel LLM integration patterns bridging frontend ↔ backend
docs: README — 6 LLM Bridge patterns with endpoint reference
```

Files added:
- `backend/app/services/llm_bridge.py` — Core LLM bridge service
- `backend/app/api/llm.py` — 6 REST endpoints
- `frontend/lib/llm.ts` — Frontend API client
- `frontend/app/page.tsx` — Interactive dashboard
