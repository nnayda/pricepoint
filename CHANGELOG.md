# CHANGELOG

<!-- version list -->

## v1.0.0-dev.15 (2026-03-13)

### Bug Fixes

- **helm**: Add fsGroup to redfin PVC pods for shared file access
  ([`2a37e15`](https://github.com/nnayda/pricepoint/-/commit/2a37e15635b58a60a09970db1a8ab6116e790a92))


## v1.0.0-dev.14 (2026-03-13)

### Bug Fixes

- **airflow**: Upgrade to 3.1.8 to fix LocalExecutor task execution failures
  ([`a22c8d0`](https://github.com/nnayda/pricepoint/-/commit/a22c8d08db9d25e900b2fec32a561e60d1256177))


## v1.0.0-dev.13 (2026-03-13)

### Bug Fixes

- **helm**: Mount redfin PVC on API pod for file uploads
  ([`9abb7e7`](https://github.com/nnayda/pricepoint/-/commit/9abb7e76dda3ab07b1ce717045167edd568aedcf))


## v1.0.0-dev.12 (2026-03-13)

### Bug Fixes

- **airflow**: Add dag-processor deployment for Airflow 3.x
  ([`7464122`](https://github.com/nnayda/pricepoint/-/commit/7464122ed027d1a30e150f16e9ba79bc428542c1))


## v1.0.0-dev.11 (2026-03-13)

### Bug Fixes

- **helm**: Make redfin PVC access mode configurable
  ([`1c16aaa`](https://github.com/nnayda/pricepoint/-/commit/1c16aaa02438f1e8956666129ba5e5329281122c))

- **helm**: Only mount dags emptyDir when git-sync is enabled
  ([`8420c38`](https://github.com/nnayda/pricepoint/-/commit/8420c38d974148cb501644760c1cc80196ab72c2))


## v1.0.0-dev.10 (2026-03-13)

### Bug Fixes

- **helm**: Use uv run for alembic migration init container
  ([`405ae22`](https://github.com/nnayda/pricepoint/-/commit/405ae2225faf65652d5ac3c06bd6c187dc4acf02))


## v1.0.0-dev.9 (2026-03-13)

### Bug Fixes

- **helm**: Move db migrations from hook to init container
  ([`dfcf034`](https://github.com/nnayda/pricepoint/-/commit/dfcf034a22188c64a8c3678bad2c917de67e56a5))


## v1.0.0-dev.8 (2026-03-13)

### Bug Fixes

- **helm**: Fix martin config to match v1.x schema
  ([`3c357b2`](https://github.com/nnayda/pricepoint/-/commit/3c357b2082af8e787164080727bae6975a1a7950))


## v1.0.0-dev.7 (2026-03-13)

### Bug Fixes

- **helm**: Update martin config format for v1.x
  ([`d6c4d94`](https://github.com/nnayda/pricepoint/-/commit/d6c4d94f87fbae01d4b07973d46ca8ce7f8140cd))


## v1.0.0-dev.6 (2026-03-13)

### Bug Fixes

- **helm**: Update martin image tag to nightly
  ([`dce0cf5`](https://github.com/nnayda/pricepoint/-/commit/dce0cf55ebd0c3bb2ae79e5a188f4ba639df4ec7))

- **osrm**: Split init container to fix wget not found on EOL Debian Stretch
  ([`81cd93c`](https://github.com/nnayda/pricepoint/-/commit/81cd93c1cb52341e56ab61a7bf38bab9eb14e556))


## v1.0.0-dev.5 (2026-03-13)

### Bug Fixes

- **helm**: Fix subchart conflicts, image tags, and airflow command
  ([`524bb87`](https://github.com/nnayda/pricepoint/-/commit/524bb873b62a116b505c89dc393f2c381e45f40f))

- **helm**: Switch airflow from KubernetesExecutor to LocalExecutor
  ([`2fc2f53`](https://github.com/nnayda/pricepoint/-/commit/2fc2f5360300771fee257e80c364bb17bbbfb02f))


## v1.0.0-dev.4 (2026-03-12)

### Bug Fixes

- **helm**: Rename configmap from -config to -app-config to avoid naming conflicts
  ([`ec9756d`](https://github.com/nnayda/pricepoint/-/commit/ec9756db231d2ff1f2298cdf52d0667deb0af9c3))


## v1.0.0-dev.3 (2026-03-12)

### Bug Fixes

- **ci**: Remove performance-test job from pipeline
  ([`1ed9611`](https://github.com/nnayda/pricepoint/-/commit/1ed9611f11b7b6885ef54fe483fdb3937de447fe))


## v1.0.0-dev.2 (2026-03-12)

### Bug Fixes

- **ci**: Remove needs dependency on semantic_release from tag-only jobs
  ([`223ca09`](https://github.com/nnayda/pricepoint/-/commit/223ca09d7c1ce20d761136acf3be11fc3269d189))


## v1.0.0-dev.1 (2026-03-12)

- Initial Release
