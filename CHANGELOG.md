# CHANGELOG

<!-- version list -->

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
