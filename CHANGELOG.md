# CHANGELOG

<!-- version list -->

## v1.0.0-dev.51 (2026-03-20)

### Bug Fixes

- Add SOURCE_HASH build-arg to bust Docker layer cache for source copies
  ([`1ec3834`](https://github.com/nnayda/pricepoint/-/commit/1ec3834fcaf0104a1d6e8d181e153a4609b14141))


## v1.0.0-dev.50 (2026-03-20)

### Bug Fixes

- Handle leap year dates in YoY economic indicator lookup
  ([`1793bd2`](https://github.com/nnayda/pricepoint/-/commit/1793bd25ec8dc09a8b3f8befc2290a0e17217567))


## v1.0.0-dev.49 (2026-03-20)

### Bug Fixes

- Use expanded training matrix for hyperparameter tuning
  ([`570c154`](https://github.com/nnayda/pricepoint/-/commit/570c15467a117aca8a6ef55c2d448304323a0dc5))


## v1.0.0-dev.48 (2026-03-19)

### Features

- Expand training dataset with multi-sale records per property
  ([`dcc513f`](https://github.com/nnayda/pricepoint/-/commit/dcc513f212a8465734fdf7e4456599a90331f0bb))


## v1.0.0-dev.47 (2026-03-18)

### Bug Fixes

- Add chart-version annotation to force pod restarts on releases
  ([`8914eac`](https://github.com/nnayda/pricepoint/-/commit/8914eacf1a1a423b868a9b6f3820ff387ab2e2a5))


## v1.0.0-dev.46 (2026-03-18)

### Bug Fixes

- Convert Decimal to float in feature store to fix JSON serialization
  ([`eca6c14`](https://github.com/nnayda/pricepoint/-/commit/eca6c14306231aebe62a64f8e9ff6cd6e6b3222e))


## v1.0.0-dev.45 (2026-03-18)

### Bug Fixes

- Allow FEATURE_CATALOG.md through .dockerignore
  ([`ae440e5`](https://github.com/nnayda/pricepoint/-/commit/ae440e5356d31e29ee36777ce6cb6886f6f6a211))


## v1.0.0-dev.44 (2026-03-18)

### Bug Fixes

- Copy FEATURE_CATALOG.md into API container image
  ([`650eeaf`](https://github.com/nnayda/pricepoint/-/commit/650eeafc59004876442dd5a705be45c327049c2b))

- Dashboard bugs — schools assigned filter, tract boundary, SHAP loading, tax assessment
  ([`41e4ff4`](https://github.com/nnayda/pricepoint/-/commit/41e4ff4fd215a9f23b3d86d6fd66f79f1e1d827f))

### Features

- Show listings, photos analyzed, and data sources on landing page
  ([`929d3ca`](https://github.com/nnayda/pricepoint/-/commit/929d3cab6f555fee943053fc91d45d21594af5d9))


## v1.0.0-dev.43 (2026-03-18)

### Bug Fixes

- **helm**: Add standard Ingress fallback for Martin tile routing
  ([`08213c9`](https://github.com/nnayda/pricepoint/-/commit/08213c9a82181fb9783a29ad2316153423ba3774))


## v1.0.0-dev.42 (2026-03-18)

### Bug Fixes

- Add missing GROUP BY columns for correlated subquery in comparables SQL
  ([`caebf4c`](https://github.com/nnayda/pricepoint/-/commit/caebf4cb5c44284c147d88ea8e492d3251054ef4))

- **helm**: Add Cache-Control headers to Martin tile responses
  ([`75dd39a`](https://github.com/nnayda/pricepoint/-/commit/75dd39a8ed0c35697d980d448cdb246ab8666487))

- **helm**: Use Traefik IngressRoute CRD for Martin tile routing
  ([`3e7daf8`](https://github.com/nnayda/pricepoint/-/commit/3e7daf88e82869c35d210bd3322626cd708f26a1))


## v1.0.0-dev.41 (2026-03-18)

### Bug Fixes

- Regenerate API types for model methodology endpoints
  ([`bcac2ce`](https://github.com/nnayda/pricepoint/-/commit/bcac2ce6a0a9329515b6966199ed0b2aabbb7f98))

### Features

- Add model methodology page with MLflow proxy endpoints (NND-24)
  ([`a7e3d95`](https://github.com/nnayda/pricepoint/-/commit/a7e3d9508b0d430ed091d96ecaf673def18a7dd7))


## v1.0.0-dev.40 (2026-03-17)

### Bug Fixes

- **helm**: Revert to auto_publish so Martin includes property columns
  ([`9477f8b`](https://github.com/nnayda/pricepoint/-/commit/9477f8b8f5ff5ccdad7fab8f1fcc23c81cc0f16a))

### Features

- Add comparable sales features for XGBoost model
  ([`e870df6`](https://github.com/nnayda/pricepoint/-/commit/e870df6722bda0a9a4009e7f7e0ba4afbd2f72c4))


## v1.0.0-dev.39 (2026-03-17)

### Bug Fixes

- **helm**: Add geometry_type to Martin explicit table config
  ([`7499821`](https://github.com/nnayda/pricepoint/-/commit/74998218825a5b54880ba7b7a42243364e71edb3))


## v1.0.0-dev.38 (2026-03-17)

### Features

- Add ANALYZE DAG for tile-serving tables after data loads
  ([`b65866a`](https://github.com/nnayda/pricepoint/-/commit/b65866a9e01497fe1146bb0f5ca159bc1c3cad59))

### Performance Improvements

- **helm**: Restrict Martin to only frontend-needed tile sources
  ([`330ed64`](https://github.com/nnayda/pricepoint/-/commit/330ed642ad9303ca75c4a1d899793c1fad4b195f))


## v1.0.0-dev.37 (2026-03-17)

### Bug Fixes

- **helm**: Specify public schema in Martin auto_publish config
  ([`65523aa`](https://github.com/nnayda/pricepoint/-/commit/65523aad9b0d03ef9239bbf2ca2253aab59a5497))


## v1.0.0-dev.36 (2026-03-17)

### Bug Fixes

- **helm**: Update MLflow health probes for static prefix
  ([`63f0b39`](https://github.com/nnayda/pricepoint/-/commit/63f0b396e9b38965f8a4fe7461267e0e91188617))


## v1.0.0-dev.35 (2026-03-17)

### Bug Fixes

- **helm**: Add MLflow static prefix and use latest valuations
  ([`c994069`](https://github.com/nnayda/pricepoint/-/commit/c994069ed2595174154d4bf9df1fd0f6586b6e06))


## v1.0.0-dev.34 (2026-03-17)

### Bug Fixes

- **training**: Provide explicit MLflow signature to avoid categorical dtype errors
  ([`330d6b3`](https://github.com/nnayda/pricepoint/-/commit/330d6b33c229adef3098d3735988698ef5d66dcb))


## v1.0.0-dev.33 (2026-03-17)

### Bug Fixes

- Convert place_names table to LOGGED after atomic swap
  ([`5a590c7`](https://github.com/nnayda/pricepoint/-/commit/5a590c7cd12b486453d9800a95e5937f594b5d59))

- **api**: Regenerate TypeScript types for neighborhood schema changes
  ([`afee24d`](https://github.com/nnayda/pricepoint/-/commit/afee24dacfb9969d36e2fade7ebe15d3743c7c31))

- **comparables**: Fix navbar overlap and remove auto-search on criteria change
  ([`ae0afc8`](https://github.com/nnayda/pricepoint/-/commit/ae0afc8ba0682a51f1451d8b983ce5f55bd7d022))

- **helm**: Add path rewriting for Martin tile ingress
  ([`9f19454`](https://github.com/nnayda/pricepoint/-/commit/9f194540aa37f60e30f037c42b77af3b0eba515d))

- **training**: Add AWS credentials to Helm chart and restore categorical dtypes in MLflow logging
  ([`9b4607e`](https://github.com/nnayda/pricepoint/-/commit/9b4607e86a609dc67e0911a8fd25bc7d256ca42b))

### Features

- **comparables**: Add "View property" link to navigate to dashboard from comp columns
  ([`5f1d692`](https://github.com/nnayda/pricepoint/-/commit/5f1d6922b40bb4fb3508cdde44ba40daa55231fd))

- **neighborhood**: Add sold date, property link, and census tract boundary to price map
  ([`926be2c`](https://github.com/nnayda/pricepoint/-/commit/926be2c1ce6124353c8dd596a31de9bad8ca7484))


## v1.0.0-dev.32 (2026-03-16)

### Bug Fixes

- **training**: Retain boolean/object features and fix MLflow DNS rebinding
  ([`95b3a41`](https://github.com/nnayda/pricepoint/-/commit/95b3a41f53f2d19824b3de3257a31737155d5a9c))


## v1.0.0-dev.31 (2026-03-16)

### Bug Fixes

- **scoring**: Persist failed scoring records to DB and fix ETA calculation
  ([`e49fd74`](https://github.com/nnayda/pricepoint/-/commit/e49fd74c39b5346f18e2f165b0058e96cb57c686))


## v1.0.0-dev.30 (2026-03-15)

### Bug Fixes

- **dag**: Wrap ST_MakeValid with ST_CollectionExtract to preserve column type
  ([`85786dc`](https://github.com/nnayda/pricepoint/-/commit/85786dc6ffa3ab4bab178acc0fece54e919bae94))


## v1.0.0-dev.29 (2026-03-15)

### Bug Fixes

- **dag**: Batch greenspace_region_metrics queries and validate geometries upfront
  ([`b798739`](https://github.com/nnayda/pricepoint/-/commit/b798739e971f68573260d88115ca973e71669668))


## v1.0.0-dev.28 (2026-03-15)

### Bug Fixes

- **dag**: Handle DB connection loss in school gold builder and add model indexes
  ([`ee05925`](https://github.com/nnayda/pricepoint/-/commit/ee05925e5b5c07954b970eca5d1c2758035a32e5))


## v1.0.0-dev.27 (2026-03-15)

### Performance Improvements

- **dag**: Optimize school gold builder with bulk queries and spatial indexes
  ([`f996413`](https://github.com/nnayda/pricepoint/-/commit/f996413de6451618bb124180c86e8bb4ca6673a8))


## v1.0.0-dev.26 (2026-03-15)

### Bug Fixes

- **helm,dag**: Add imagePullPolicy Always and missing DAG dependency
  ([`f8fca13`](https://github.com/nnayda/pricepoint/-/commit/f8fca1358080abdadd5214d9b6e52f1bb41d6ed4))


## v1.0.0-dev.25 (2026-03-15)

### Bug Fixes

- **dag**: Handle overlapping school districts in gold builder
  ([`75f21ec`](https://github.com/nnayda/pricepoint/-/commit/75f21ec5d53f9b6e0a91ea55b781d97d8b5ab46f))


## v1.0.0-dev.24 (2026-03-14)

### Bug Fixes

- **helm**: Add fsGroup to dag-processor and webserver for shared logs PVC
  ([`5b2bbbb`](https://github.com/nnayda/pricepoint/-/commit/5b2bbbb7a025f30d374c61f55a2ab0844fff4544))


## v1.0.0-dev.23 (2026-03-14)

### Bug Fixes

- **helm**: Add shared PVC for Airflow logs so webserver can read task logs
  ([`35e3280`](https://github.com/nnayda/pricepoint/-/commit/35e3280c403d1ffe8e58f2d5349cbc5aec38ac47))


## v1.0.0-dev.22 (2026-03-13)

### Bug Fixes

- **dag**: Add ST_MakeValid to ST_Intersects JOIN predicates in greenspace metrics
  ([`4a7f616`](https://github.com/nnayda/pricepoint/-/commit/4a7f616212e384b9a4e28b849e75224aeb0bfb19))


## v1.0.0-dev.21 (2026-03-13)

### Bug Fixes

- **dag**: Use ST_MakeValid in greenspace metrics to handle invalid geometries
  ([`e7a3de4`](https://github.com/nnayda/pricepoint/-/commit/e7a3de40bac377f0f1d481400562eae3c14490bb))


## v1.0.0-dev.20 (2026-03-13)

### Bug Fixes

- **helm**: Set scheduler pod hostname for log server DNS resolution
  ([`05221b7`](https://github.com/nnayda/pricepoint/-/commit/05221b77b745a96fdc7b6733cc8de3bc4e7eb98a))


## v1.0.0-dev.19 (2026-03-13)

### Bug Fixes

- **helm**: Use world-writable perms on redfin PVC for NFS client access
  ([`0b66c49`](https://github.com/nnayda/pricepoint/-/commit/0b66c4903c2becc80bfec87e923fcd40b3058d00))


## v1.0.0-dev.18 (2026-03-13)

### Bug Fixes

- **helm**: Add scheduler log service for task log viewing
  ([`69b45e3`](https://github.com/nnayda/pricepoint/-/commit/69b45e3c8b0f6538e2694f3cfa1cad5e949cc88b))


## v1.0.0-dev.17 (2026-03-13)

### Bug Fixes

- **helm**: Chown redfin PVC directory group to fsGroup for NFS access
  ([`aedcb95`](https://github.com/nnayda/pricepoint/-/commit/aedcb95f1b84a210c6a3f4ec0c8df48907c72fe2))

- **helm**: Remove /v1 from Airflow execution API server URL
  ([`9f92ec7`](https://github.com/nnayda/pricepoint/-/commit/9f92ec75abb19af436127c9f62419b3ce4022bcf))


## v1.0.0-dev.16 (2026-03-13)

### Bug Fixes

- **helm**: Add init container to chmod redfin PVC directory for NFS access
  ([`c1026f2`](https://github.com/nnayda/pricepoint/-/commit/c1026f2d30883a4a57367f3629d6ebc208401b58))


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
