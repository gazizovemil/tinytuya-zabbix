# Публикация исходников в GitHub и образа в Docker Hub

Есть два способа опубликовать образ: через GitHub Actions (предпочтительно) или вручную с TNAS. **Не отправляй в Git Local Key, `devices.json`, Tuya API Secret и `.env`.**

## 1. Создание GitHub-репозитория

Открой <https://github.com/new> под своим аккаунтом и создай **пустой публичный** репозиторий `tinytuya-zabbix`. Не добавляй новый README, LICENSE или `.gitignore`, они уже в комплекте.

Из каталога с исходниками запусти:

```sh
./scripts/push-git.sh
```

Скрипт запросит HTTPS-адрес GitHub-репозитория, выполнит `git init` (если нужно), коммит и `git push` в `main`. Авторизация — штатными средствами Git. Токены и пароли не вводятся в сам скрипт. Если Git потребует имя автора, настрой `git config --global user.name` и `git config --global user.email` на своей машине.

## 2А. Публикация в Docker Hub через GitHub Actions

1. Войди в <https://hub.docker.com> и создай публичный репозиторий с именем `tinytuya-zabbix` в своём аккаунте (или включи автоматическое создание при push, если поддерживается).
2. Создай в Docker Hub **Personal Access Token** с правами на push этого репозитория.
3. На GitHub открой **Settings → Secrets and variables → Actions** и добавь:
   - **Repository variable:** `DOCKERHUB_USERNAME` — имя твоего Docker Hub аккаунта;
   - **Repository secret:** `DOCKERHUB_TOKEN` — токен Docker Hub.
4. После успешного `git push` и CI создай версионный тег:

```sh
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions запустит сборку под **linux/amd64** и **linux/arm64**, а затем отправит теги `1.0.0` и `latest` в Docker Hub. Убедись, что workflow завершился успешно в разделе **Actions**, а теги действительно появились в Docker Hub. Для будущих релизов используй новую версию, не перезаписывай существующие теги.

> Образ не появится в Docker Hub, пока workflow реально не соберёт и не опубликует его.

## 2Б. Публикация вручную с TNAS

Если хочется собрать и отправить образ самостоятельно:

```sh
./scripts/push-dockerhub.sh
```

Скрипт запросит Docker Hub username, выполнит интерактивный `docker login`, локальный `docker build`, затем отправит теги `1.0.0` и `latest`. В отличие от GitHub Actions, он собирает образ под текущую архитектуру компьютера. Для твоего TNAS на Intel это `linux/amd64`.

## 3. Использование опубликованного образа

Добавь в **локальный**, исключённый из Git файл `.env` значение `DOCKERHUB_USERNAME` своего аккаунта, затем:

```sh
docker compose -f compose.hub.yaml pull
docker compose -f compose.hub.yaml up -d
```

В исходниках и готовом образе нет Device ID, IP и Local Key розетки — они берутся только из локальной конфигурации. Публичный релиз не должен содержать персональные настройки.
