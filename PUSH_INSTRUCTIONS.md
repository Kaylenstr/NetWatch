# Push to GitHub and Docker Hub

Git is initialized and the initial commit is done. Complete the push with the commands below.

## GitHub

Replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub username and repo name.

```bash
cd release
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

If the repo uses `master` instead of `main`:

```bash
git branch -M master
git push -u origin master
```

## Docker Hub

Replace `YOUR_DOCKERHUB_USER` with your Docker Hub username. Run `docker login` first if needed.

```bash
cd release
docker build -t YOUR_DOCKERHUB_USER/netwatch:latest .
docker push YOUR_DOCKERHUB_USER/netwatch:latest
```

The image is already built locally as `netwatch:latest`. To push that:

```bash
docker tag netwatch:latest YOUR_DOCKERHUB_USER/netwatch:latest
docker push YOUR_DOCKERHUB_USER/netwatch:latest
```

## GitHub Wiki

Copy the contents of each file in `wiki/` to create wiki pages: Home, Installation, Configuration, Docker.
