#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
printf 'Docker Hub username: '
IFS= read -r username
if [ -z "$username" ]; then
  echo 'Docker Hub username is required' >&2
  exit 1
fi
printf 'Docker image release version [1.0.0]: '
IFS= read -r version
version=${version:-1.0.0}
docker login -u "$username"
docker build -t "$username/tinytuya-zabbix:$version" -t "$username/tinytuya-zabbix:latest" .
docker push "$username/tinytuya-zabbix:$version"
docker push "$username/tinytuya-zabbix:latest"
printf 'Published docker.io/%s/tinytuya-zabbix:%s and :latest\n' "$username" "$version"
