#!/bin/bash
# Deploy course-tracker to GitHub Pages
# Usage: ./deploy_github_pages.sh <github-username> <repo-name>

set -e

USERNAME="${1:-aonagiworks}"
REPO="${2:-course-tracker}"
DIR="/home/ec2-user/course-tracker"
BRANCH="gh-pages"

echo "Deploying to GitHub Pages: ${USERNAME}/${REPO}"

cd "$DIR"

# Init git if needed
if [ ! -d .git ]; then
  git init
  git remote add origin "https://github.com/${USERNAME}/${REPO}.git"
fi

# Create gh-pages branch
git checkout -B "$BRANCH"
git add index.html
git commit -m "Deploy course tracker $(date +%Y-%m-%d)" || true
git push -f origin "$BRANCH"

echo "Deployed! Live at: https://${USERNAME}.github.io/${REPO}/"
echo "Enable Pages in repo Settings → Pages → Source: gh-pages branch"