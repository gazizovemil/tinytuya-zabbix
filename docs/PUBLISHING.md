# Publishing source code and Docker image (English)

This project has **two ways** to publish. Never commit a Local Key, API Secret, `devices.json`, or `.env`.

## 1. GitHub source repository

Create an **empty public repository** named `tinytuya-zabbix` using your GitHub account at <https://github.com/new>. Do not initialize it with another README, license, or .gitignore: these files are already included.

From the extracted project directory, run:

```sh
./scripts/push-git.sh
```

The script asks for the GitHub HTTPS URL, initializes the repository if needed, commits the public files, and pushes to the `main` branch. Git authentication is managed by your local git credentials; a password or token is **never** entered into the script. If Git asks for an author identity, configure it on your own machine using `git config --global user.name` and `git config --global user.email`.

## 2A. Recommended: Docker Hub via GitHub Actions

1. Create an account at <https://hub.docker.com> and create (or allow auto-creation of) public repository `tinytuya-zabbix` in your Docker Hub namespace.
2. In Docker Hub, create a **personal access token** with permission to push to that repository.
3. On GitHub, open **Settings → Secrets and variables → Actions**:
   - **Repository variable:** `DOCKERHUB_USERNAME` — your Docker Hub account name.
   - **Repository secret:** `DOCKERHUB_TOKEN` — the Docker Hub access token.
4. Once the initial commit is pushed and the GitHub Actions CI succeeds, create a release tag:

```sh
git tag v1.0.0
git push origin v1.0.0
```

The workflow `.github/workflows/publish.yml` then builds **linux/amd64** and **linux/arm64** images and publishes the `1.0.0` and `latest` tags to Docker Hub. Check the Actions run and the Docker Hub repository to verify that publishing succeeded. Reuse an updated semantic version for subsequent releases; do not force-push existing release tags.

> The first release does not exist until the tag workflow runs successfully. Simply adding a workflow file does not publish a Docker image.

## 2B. Alternative: manual push from your Docker-capable machine

Run:

```sh
./scripts/push-dockerhub.sh
```

The script asks for your Docker Hub username, logs in using Docker CLI, builds for the machine's **native architecture**, and pushes `1.0.0` and `latest`. This path is useful if GitHub Actions is unavailable, but unlike CI it does not automatically build multiple architectures.

## 3. Use published image

Edit your local untracked `.env` to include `DOCKERHUB_USERNAME` for your own account, then run:

```sh
docker compose -f compose.hub.yaml pull
docker compose -f compose.hub.yaml up -d
```

CI/publishing operations have no access to your local device's `devices.json`. Secrets are deliberately excluded from the repository and image.
