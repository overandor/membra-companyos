#!/bin/bash
# MEMBRA CompanyOS — Batch push all repos to GitHub
# Usage: ./scripts/push_all.sh <GITHUB_TOKEN>
set -e

TOKEN="${1:-}"
if [ -z "$TOKEN" ]; then
    echo "Usage: ./scripts/push_all.sh <GITHUB_TOKEN>"
    echo "Generate token at: https://github.com/settings/tokens"
    exit 1
fi

GITHUB_USER="overandor"
REPOS=(
    "/Users/alep/membra-companyos:membra-companyos"
    "/Users/alep/Downloads:membra_db"
    "/Users/alep/Downloads/membra-sdk:membra"
    "/Users/alep/Downloads/tokenize-camera-app:tokenize-camera"
    "/Users/alep/Documents/flashloan-bench:flashloan-bench"
    "/Users/alep/Downloads/compute_llm_inference:compute-llm-inference"
    "/Users/alep/Downloads/membra_human_chain:membra-qr-gateway"
)

echo "=========================================="
echo "MEMBRA CompanyOS — Batch GitHub Push"
echo "=========================================="

for entry in "${REPOS[@]}"; do
    IFS=':' read -r local_path repo_name <<< "$entry"
    echo ""
    echo "[→] Pushing $repo_name..."
    cd "$local_path"
    git remote set-url origin "https://${TOKEN}@github.com/${GITHUB_USER}/${repo_name}.git" 2>/dev/null || true
    git push origin main 2>&1 && echo "    ✅ $repo_name pushed" || echo "    ⚠️  $repo_name had issues"
done

echo ""
echo "=========================================="
echo "Batch push complete!"
echo "=========================================="
