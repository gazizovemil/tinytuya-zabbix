#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
printf 'GitHub repository HTTPS URL (create an empty repository first): '
IFS= read -r url
case "$url" in
  https://github.com/*/*.git|https://github.com/*/*) ;;
  *) printf 'Only a GitHub HTTPS repository URL is accepted.\n' >&2; exit 1;;
esac
if [ ! -d .git ]; then
  git init -b main
fi
git add -A
git diff --cached --quiet || git commit -m 'Initial release: TinyTuya Zabbix monitor'
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$url"
else
  git remote add origin "$url"
fi
git push -u origin main
