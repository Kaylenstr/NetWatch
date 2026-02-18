# Push to GitHub and Docker Hub

This file explains how to publish. Delete it before pushing if you prefer.

## GitHub

**Option A: This folder is your repo**

```bash
cd release
git init
git remote add origin https://github.com/yourusername/your-repo.git
git add .
git commit -m "Initial release"
git push -u origin main
```

**Option B: Copy into existing repo**

Copy all files from `release/` (except this file) into your repo root, then:

```bash
git add .
git commit -m "Release"
git push
```

## GitHub Wiki

The `wiki/` folder contains markdown for wiki pages. On GitHub: repo → Wiki → create each page, paste content from the corresponding `.md` file. Start with Home, then Installation, Configuration, Docker.

## Docker Hub

```bash
docker build -t yourusername/netwatch:latest .
docker login
docker push yourusername/netwatch:latest
```

Replace `yourusername` with your Docker Hub username.
