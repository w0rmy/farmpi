# Database transition and PR reconciliation — 27 September 2026

> **Historical transition record.** Retained as development evidence. It describes the state and decisions at the date in the title and is not a current-state authority. See [the documentation index](README.md) for current guides.

## What happened

[PR #10](https://github.com/w0rmy/farmpi/pull/10), branch `refactor/clean-managed-node-baseline`, was merged on 27 September at 03:52:32 UTC (16:52:32 NZDT). Its 33 commits end at `88043152c993ef455cbcb5d78a408672206c707b`. Main is merge commit `394c52d6ea68d43245aed0ab6d0f76ecf545806b`.

[PR #11](https://github.com/w0rmy/farmpi/pull/11), branch `feature/clean-operational-node-model`, remained open and conflicting at inspection, with 39 commits ending at `2e40f71a972def30ab99b31d57f8dbaa144b4b5f`. Both branches started at `7ddf927b297fdc36767b37998cf5816c256bbf34`. There are no shared post-base commit IDs and no patch-equivalent commits according to `git cherry`; the overlap is independently implemented behavior, not the same commits merged twice.

PR #10 changes 27 files; #11 changes 25. They touch 18 of the same files; a non-mutating three-way merge reports 16 conflicted files. This replacement starts directly at the merged main commit and does not replay the 39 commits.

## Reconciliation decisions

| Area | Decision |
| --- | --- |
| Clean database, FP IDs, farmer names, schema-v2 modes, ESP32 simulation | Already implemented by #10; retained rather than reimplemented. |
| `measurement_modes_json`, mixed samples, historical location, current-mode reporting | Preserve #10 throughout backend, database, firmware and API. Do not replace with #11's separate-source sample strategy. |
| Android | Preserve #10's compact list, Node Detail and separate location-creation endpoint. Remove mode controls as Jeremy requested; metadata-only saves omit modes and preserve the stored map. |
| Console control | Port #11's `configure-node-modes`, adapted to the retained API. |
| LIVE driver support | Add #11's separate live-capability advertisement and server/firmware validation. Missing advertisement means no LIVE support. |
| Simulator | Extend #10's six-key generator to all 13 catalogue measurements; retain persistent sequence and mixed-sample provenance. |
| Demo data | Preserve the empty operational seed; recover the legacy dataset into `demo-seed.sql` with an explicit loader. Normal setup/update now apply schema only. |
| Reset | Preserve #10's existing backup/reset implementation and `--yes-really-reset` interface; do not replace it with #11's competing `--yes` implementation. No reset was executed. |
| Tests | Keep #10's regression suite; add integration coverage for the reconciled boundary. Correct the two failures reproduced on untouched main. |
| Documents | Preserve merged history; update current contracts and append this evidence record. Do not copy #11's contradictory schema or source-format descriptions. |

The #11 schema begins with literal backslash-n sequences in its opening comment, which would comment out the first table declaration. That file was not imported. Only the valid additive LIVE capability column was applied to main's schema.

## Operational use

```bash
.venv/bin/python scripts/configure-node-modes FP-001 soil_moisture_pct=SIMULATED
sudo bash scripts/load-demo-data  # only for an intentional legacy demo dataset
```

No command above resets the operational database. The existing destructive reset remains a separate manual workflow (`sudo bash scripts/reset-operational-database --yes-really-reset`), never part of a normal update. This reconciliation did not connect to or change the deployed database.

Apply the additive schema before running the new backend. When upgrading from #10's six-key firmware, let the new firmware contact FarmPi, then save modes through the console so a complete 13-key configuration is generated. Change old unsupported LIVE selections to OFF or SIMULATED. LIVE needs an implemented driver added to the firmware's LIVE list. Simulation does not satisfy T01 physical-acquisition evidence.

## Exact file/commit overlap

The table lists every commit on each branch that touched each overlapping path after the common base. Links identify the full commits; conflict status comes from `git merge-tree` at the recorded tips.

| File | Three-way conflict | PR #10 commits | PR #11 commits |
| --- | --- | --- | --- |
| `README.md` | Yes | [0582d00](https://github.com/w0rmy/farmpi/commit/0582d006818864df963c1f516566ca56a4a2c776) | [2f0e94c](https://github.com/w0rmy/farmpi/commit/2f0e94cb25b2a71ec305e6a62026dc701ffbb3e8) |
| `app/managed_ingest.py` | Yes | [a21e4fd](https://github.com/w0rmy/farmpi/commit/a21e4fd1e47010b30e6a349b4de5f1e74a5cb33e) | [e241450](https://github.com/w0rmy/farmpi/commit/e241450294dac77af6e7d3f6c39b29f98d0eaf37), [f6cb961](https://github.com/w0rmy/farmpi/commit/f6cb961420aee2e1857ee23625eb6f58cc31bae6) |
| `app/node_api.py` | Yes | [e696ef8](https://github.com/w0rmy/farmpi/commit/e696ef8611409399fca18057344bbc9776071eab), [e7efb7a](https://github.com/w0rmy/farmpi/commit/e7efb7a0caa6114061671cab1a17b50b0f49fd5d) | [4ea9686](https://github.com/w0rmy/farmpi/commit/4ea968613d8cf72469bd6a722db7dbcc82f66fba) |
| `app/node_config.py` | Yes | [5b26580](https://github.com/w0rmy/farmpi/commit/5b26580d723fe92c92690a1a8113d943149d55eb) | [a4937a6](https://github.com/w0rmy/farmpi/commit/a4937a69bd1c10a3f4b3b35d20eb392f5038a1d2) |
| `clients/android/app/src/main/java/nz/farmpi/client/NodesUi.kt` | Yes | [3c65b0f](https://github.com/w0rmy/farmpi/commit/3c65b0f50b80f49a4519bfe02965d41a93e5d60d) | [5d343cd](https://github.com/w0rmy/farmpi/commit/5d343cd42ec2f1ab1edb989221c219c2e4debdcd), [42ef907](https://github.com/w0rmy/farmpi/commit/42ef907ddbdace9c2e12130b72779147fd42e8fb), [7f3d7ca](https://github.com/w0rmy/farmpi/commit/7f3d7ca0dfd23535ab717b323c8997957740baf8) |
| `config/database/schema.sql` | No | [f11bac6](https://github.com/w0rmy/farmpi/commit/f11bac6482184a4599881c4eea69c5c9f5461976) | [5afdd2b](https://github.com/w0rmy/farmpi/commit/5afdd2b3483378cd12d291daebeee3da6a8a0085) |
| `docs/android-client.md` | Yes | [1690f6d](https://github.com/w0rmy/farmpi/commit/1690f6d66573073bf8eb456f6c973ede727bf13b) | [c7c5e31](https://github.com/w0rmy/farmpi/commit/c7c5e31f035291c2a56311388c4281a9e52386e0), [f39e9f0](https://github.com/w0rmy/farmpi/commit/f39e9f0f0ff80c519f1385d3727adc0a52456249) |
| `docs/architecture.md` | Yes | [c757929](https://github.com/w0rmy/farmpi/commit/c757929254752acf4bba9aaa9d6a3c5dabc7c596) | [1cd9434](https://github.com/w0rmy/farmpi/commit/1cd9434e20cdeff88cd6b5483c3cae250493bb67) |
| `docs/data-and-api.md` | Yes | [4190e73](https://github.com/w0rmy/farmpi/commit/4190e739de907e4078b6599542e574f56790b11b) | [cdf5567](https://github.com/w0rmy/farmpi/commit/cdf55672fa7e8768262849caba6f24c8e06d9459) |
| `docs/development-record.md` | No | [42e3fe2](https://github.com/w0rmy/farmpi/commit/42e3fe2883a04c5b79d4060f4f530a743c7f271e) | [28dc922](https://github.com/w0rmy/farmpi/commit/28dc9228ae0a24113c6e7b5d2060bccb2534526a), [30ea54e](https://github.com/w0rmy/farmpi/commit/30ea54ee55711e12c10e316bb8988ea4c5a875a6) |
| `docs/s3-node-bringup.md` | Yes | [e38bc39](https://github.com/w0rmy/farmpi/commit/e38bc399f86f481693eb457c3ff289600c13661c) | [cded5cd](https://github.com/w0rmy/farmpi/commit/cded5cda79df1cb3aba448297b2d85f503641c4d), [aa36605](https://github.com/w0rmy/farmpi/commit/aa366050d13dca78161866efb9a09e3b81a75c99) |
| `docs/testing-and-evaluation.md` | Yes | [888313a](https://github.com/w0rmy/farmpi/commit/888313a4b9edc01188c4b8539fe0b62c2376a47f) | [710f39a](https://github.com/w0rmy/farmpi/commit/710f39a9c89c810516707e57b85632a65fd17ea9) |
| `firmware/esp32-s3-node/board_profile.h` | Yes | [37e8962](https://github.com/w0rmy/farmpi/commit/37e896232ac05f0591103f5759fa20da527437a3) | [4e7ed7c](https://github.com/w0rmy/farmpi/commit/4e7ed7cbc906a910d18b0cceca5eaa3700fbe7fc) |
| `firmware/esp32-s3-node/esp32-s3-node.ino` | Yes | [7dcd640](https://github.com/w0rmy/farmpi/commit/7dcd640d34669b1ebed8f1a6f553b4ec8e092ceb) | [5b0f35e](https://github.com/w0rmy/farmpi/commit/5b0f35e76fd40f878b4e58aedc3fa52106d94cb3), [667442a](https://github.com/w0rmy/farmpi/commit/667442a8f48c9b4c5be4d6dea4db8da2b844e6b1) |
| `scripts/reset-operational-database` | Yes | [b9d0c95](https://github.com/w0rmy/farmpi/commit/b9d0c953ee0908624f686f33c09c73bcbed4aca1), [cb0a91b](https://github.com/w0rmy/farmpi/commit/cb0a91b8c0107f4b230adbc294c5ef38ed40306d) | [b80830a](https://github.com/w0rmy/farmpi/commit/b80830a49e394168c2d62076be91461149ef18f4), [bf693b6](https://github.com/w0rmy/farmpi/commit/bf693b63110eb1763cb5194dbea88227a7fa119a) |
| `scripts/setup-database` | Yes | [08bee1d](https://github.com/w0rmy/farmpi/commit/08bee1db6518a98d18eace4c1a14cefbc8bbcf76) | [5d90210](https://github.com/w0rmy/farmpi/commit/5d90210e7c2b1c5b42f72249792e1f8b5d2ba666) |
| `tests/test_database_migration.py` | Yes | [a352a5d](https://github.com/w0rmy/farmpi/commit/a352a5dc3edbd81a7f87d58e8016c493cf6e2f3e), [8804315](https://github.com/w0rmy/farmpi/commit/88043152c993ef455cbcb5d78a408672206c707b) | [30abd48](https://github.com/w0rmy/farmpi/commit/30abd48b82b20e8cda04a00a17abea65f628ce3f), [c3f4108](https://github.com/w0rmy/farmpi/commit/c3f410815beb37d988c1987e26a983adaeaf9b28) |
| `tests/test_node_management.py` | Yes | [e04ba17](https://github.com/w0rmy/farmpi/commit/e04ba17925fe1ba19bb096348bd1fbdd1cfff9dc), [6fee87d](https://github.com/w0rmy/farmpi/commit/6fee87d0a64cd84acc61364151770cf43ab28e70) | [1afeb42](https://github.com/w0rmy/farmpi/commit/1afeb426f151e89abadc30b0caff498544c530be), [46350d2](https://github.com/w0rmy/farmpi/commit/46350d29a9990022ade17d3ba45041f974451960), [a83e104](https://github.com/w0rmy/farmpi/commit/a83e1042325933de42d04f1f4b4d4d25358ec73d) |

### Files changed only by #10 (preserved)

- `app/farm_data.py`
- `app/ingest_api.py`
- `app/sensor_ingest.py`
- `clients/android/app/src/main/java/nz/farmpi/client/MainActivity.kt`
- `config/database/seed.sql`
- `docs/diagrams/database-erd.mmd`
- `docs/raspberry-pi-deployment.md`
- `firmware/esp32-s3-node/README.md`
- `tests/test_sensor_ingest.py`

### Files changed only by #11 (reviewed for missing work)

- `docs/README.md`
- `docs/database-transition-2026-09-27.md`
- `docs/diagrams/managed-node-configuration.mmd`
- `docs/s3-implementation-plan.md`
- `scripts/apply-database-schema`
- `scripts/configure-node-modes`
- `scripts/load-demo-data`

## PR #10 commit inventory

- [5b26580](https://github.com/w0rmy/farmpi/commit/5b26580d723fe92c92690a1a8113d943149d55eb) — Model node sensors as OFF SIMULATED or LIVE
- [e696ef8](https://github.com/w0rmy/farmpi/commit/e696ef8611409399fca18057344bbc9776071eab) — Separate node identity location names and sensor modes
- [f11bac6](https://github.com/w0rmy/farmpi/commit/f11bac6482184a4599881c4eea69c5c9f5461976) — Store per-measurement live or simulated provenance
- [028e657](https://github.com/w0rmy/farmpi/commit/028e657e283e83d23e6768685eafdcc08df20b51) — Stop seeding synthetic paddocks into operational database
- [08bee1d](https://github.com/w0rmy/farmpi/commit/08bee1db6518a98d18eace4c1a14cefbc8bbcf76) — Describe clean operational database baseline
- [b9d0c95](https://github.com/w0rmy/farmpi/commit/b9d0c953ee0908624f686f33c09c73bcbed4aca1) — Add backed-up clean database reset helper
- [94efcc9](https://github.com/w0rmy/farmpi/commit/94efcc9822faa73fcb1f66421cdc3b130e2d91cd) — Persist provenance for each reported measurement
- [a21e4fd](https://github.com/w0rmy/farmpi/commit/a21e4fd1e47010b30e6a349b4de5f1e74a5cb33e) — Validate managed telemetry against per-sensor modes
- [2f578dd](https://github.com/w0rmy/farmpi/commit/2f578ddcc673a7318c052a139ca29950651703cf) — Expose measurement provenance in ingest acknowledgements
- [458a1cd](https://github.com/w0rmy/farmpi/commit/458a1cdb60a7c6b9ae59fbd3cd1381d4c8f83360) — Carry sensor provenance into current and historical evidence
- [04bb2a2](https://github.com/w0rmy/farmpi/commit/04bb2a21c02d43c73607f0ccf5dab604ca7bb5a1) — Allow Android node flow to create farmer-named locations
- [3c65b0f](https://github.com/w0rmy/farmpi/commit/3c65b0f50b80f49a4519bfe02965d41a93e5d60d) — Use farmer locations and per-sensor mode controls in Nodes
- [37e8962](https://github.com/w0rmy/farmpi/commit/37e896232ac05f0591103f5759fa20da527437a3) — Expose six standard sensor modes in S3 profile
- [7dcd640](https://github.com/w0rmy/farmpi/commit/7dcd640d34669b1ebed8f1a6f553b4ec8e092ceb) — Run node-local simulation through managed telemetry path
- [e04ba17](https://github.com/w0rmy/farmpi/commit/e04ba17925fe1ba19bb096348bd1fbdd1cfff9dc) — Test clean node modes locations and provenance
- [a352a5d](https://github.com/w0rmy/farmpi/commit/a352a5dc3edbd81a7f87d58e8016c493cf6e2f3e) — Test clean operational database reset contract
- [0f17e8f](https://github.com/w0rmy/farmpi/commit/0f17e8ff4ebaf8ac176f325166a87acf646f87e8) — Assert per-measurement simulator provenance
- [6fee87d](https://github.com/w0rmy/farmpi/commit/6fee87d0a64cd84acc61364151770cf43ab28e70) — Fix mode configuration regression coverage
- [31999a0](https://github.com/w0rmy/farmpi/commit/31999a041c4604d45071cbac96cea6908349fd9e) — Resolve provenance per measurement without SQL JSON dependency
- [ca8c080](https://github.com/w0rmy/farmpi/commit/ca8c08081ebeb57617730447e2a1dec6f5bfe29f) — Document managed node modes and identity boundaries
- [4190e73](https://github.com/w0rmy/farmpi/commit/4190e739de907e4078b6599542e574f56790b11b) — Document clean database sensor modes and farmer locations
- [e38bc39](https://github.com/w0rmy/farmpi/commit/e38bc399f86f481693eb457c3ff289600c13661c) — Update S3 bring-up for clean baseline and sensor modes
- [42e3fe2](https://github.com/w0rmy/farmpi/commit/42e3fe2883a04c5b79d4060f4f530a743c7f271e) — Record managed-node database transition judgement
- [e370a2f](https://github.com/w0rmy/farmpi/commit/e370a2f95348e07dc29fcd8bcc71052fdb93f759) — Show node name and measurement provenance in ERD
- [e7efb7a](https://github.com/w0rmy/farmpi/commit/e7efb7a0caa6114061671cab1a17b50b0f49fd5d) — Keep node reporting state aligned with current sensor mode
- [2aedb61](https://github.com/w0rmy/farmpi/commit/2aedb61b7018b9bd85d6fa1e82920471d55e0159) — Keep capability answers honest about sensor modes
- [1690f6d](https://github.com/w0rmy/farmpi/commit/1690f6d66573073bf8eb456f6c973ede727bf13b) — Align Android Nodes docs with managed sensor modes
- [0582d00](https://github.com/w0rmy/farmpi/commit/0582d006818864df963c1f516566ca56a4a2c776) — Align README with clean managed-node baseline
- [c757929](https://github.com/w0rmy/farmpi/commit/c757929254752acf4bba9aaa9d6a3c5dabc7c596) — Describe OFF simulated live node architecture
- [3686f47](https://github.com/w0rmy/farmpi/commit/3686f47d7d9456bc73b288a64a4cfd2ac206253e) — Document clean database transition deployment path
- [888313a](https://github.com/w0rmy/farmpi/commit/888313a4b9edc01188c4b8539fe0b62c2376a47f) — Update acceptance for managed sensor modes
- [cb0a91b](https://github.com/w0rmy/farmpi/commit/cb0a91b8c0107f4b230adbc294c5ef38ed40306d) — Use MariaDB native dump command for reset archive
- [8804315](https://github.com/w0rmy/farmpi/commit/88043152c993ef455cbcb5d78a408672206c707b) — Match reset archive test to mariadb-dump

## PR #11 commit inventory

- [a4937a6](https://github.com/w0rmy/farmpi/commit/a4937a69bd1c10a3f4b3b35d20eb392f5038a1d2) — feat: add per-measurement OFF SIMULATED LIVE modes
- [4ea9686](https://github.com/w0rmy/farmpi/commit/4ea968613d8cf72469bd6a722db7dbcc82f66fba) — feat: separate node identity location and sensor modes
- [e241450](https://github.com/w0rmy/farmpi/commit/e241450294dac77af6e7d3f6c39b29f98d0eaf37) — feat: validate managed telemetry against sensor mode
- [5afdd2b](https://github.com/w0rmy/farmpi/commit/5afdd2b3483378cd12d291daebeee3da6a8a0085) — db: add live acquisition capability metadata
- [5d90210](https://github.com/w0rmy/farmpi/commit/5d90210e7c2b1c5b42f72249792e1f8b5d2ba666) — db: stop auto-loading synthetic demo data
- [21ed5b7](https://github.com/w0rmy/farmpi/commit/21ed5b73ffdff8328427e048fbf2c630ca03e6d6) — db: keep normal schema updates data-neutral
- [262f16e](https://github.com/w0rmy/farmpi/commit/262f16ed845e8756c1765c96d287aac51f91ae1f) — db: add explicit synthetic demo loader
- [b80830a](https://github.com/w0rmy/farmpi/commit/b80830a49e394168c2d62076be91461149ef18f4) — db: add backed-up clean operational reset
- [4e7ed7c](https://github.com/w0rmy/farmpi/commit/4e7ed7cbc906a910d18b0cceca5eaa3700fbe7fc) — firmware: separate simulated and live capabilities
- [5b0f35e](https://github.com/w0rmy/farmpi/commit/5b0f35e76fd40f878b4e58aedc3fa52106d94cb3) — firmware: add per-sensor simulation mode and sparse telemetry
- [1afeb42](https://github.com/w0rmy/farmpi/commit/1afeb426f151e89abadc30b0caff498544c530be) — test: cover node simulation and live modes
- [46350d2](https://github.com/w0rmy/farmpi/commit/46350d29a9990022ade17d3ba45041f974451960) — test: validate clean node identities modes and named locations
- [30abd48](https://github.com/w0rmy/farmpi/commit/30abd48b82b20e8cda04a00a17abea65f628ce3f) — test: enforce clean operational database workflow
- [5d343cd](https://github.com/w0rmy/farmpi/commit/5d343cd42ec2f1ab1edb989221c219c2e4debdcd) — android: add named locations and per-sensor modes
- [c3f4108](https://github.com/w0rmy/farmpi/commit/c3f410815beb37d988c1987e26a983adaeaf9b28) — test: fix explicit demo loader contract
- [2417c4c](https://github.com/w0rmy/farmpi/commit/2417c4c2ce30e781154913023afe5a97425d4ef3) — android: opt in to node location flow layout
- [f6cb961](https://github.com/w0rmy/farmpi/commit/f6cb961420aee2e1857ee23625eb6f58cc31bae6) — ingest: clarify managed sample validation
- [bf693b6](https://github.com/w0rmy/farmpi/commit/bf693b63110eb1763cb5194dbea88227a7fa119a) — db: document explicit reset invocation
- [759ec6a](https://github.com/w0rmy/farmpi/commit/759ec6a981058b1525e93ab9eb0d195e307b7a33) — docs: record clean managed-node database transition
- [28dc922](https://github.com/w0rmy/farmpi/commit/28dc9228ae0a24113c6e7b5d2060bccb2534526a) — docs: record database transition and Jeremy design corrections
- [42ef907](https://github.com/w0rmy/farmpi/commit/42ef907ddbdace9c2e12130b72779147fd42e8fb) — android: submit modes only for supported measurements
- [667442a](https://github.com/w0rmy/farmpi/commit/667442a8f48c9b4c5be4d6dea4db8da2b844e6b1) — firmware: read location epoch explicitly
- [cdf5567](https://github.com/w0rmy/farmpi/commit/cdf55672fa7e8768262849caba6f24c8e06d9459) — docs: describe named locations and per-sensor modes
- [cded5cd](https://github.com/w0rmy/farmpi/commit/cded5cda79df1cb3aba448297b2d85f503641c4d) — docs: update S3 bring-up for clean mode-based model
- [2f0e94c](https://github.com/w0rmy/farmpi/commit/2f0e94cb25b2a71ec305e6a62026dc701ffbb3e8) — docs: align README with clean operational data model
- [a83e104](https://github.com/w0rmy/farmpi/commit/a83e1042325933de42d04f1f4b4d4d25358ec73d) — test: fix managed mode test syntax and provenance
- [8fc89e4](https://github.com/w0rmy/farmpi/commit/8fc89e406eaa4774926f2280cba72a8c98be8886) — docs: update managed-node diagram for source modes
- [a363eb6](https://github.com/w0rmy/farmpi/commit/a363eb67d9b32a7b55158f933aa7d67bc759a256) — docs: index operational database transition
- [cd3655f](https://github.com/w0rmy/farmpi/commit/cd3655fbcea547d2d0d2be8b1645a74571803bea) — docs: align S3 plan with source modes
- [710f39a](https://github.com/w0rmy/farmpi/commit/710f39a9c89c810516707e57b85632a65fd17ea9) — docs: update managed telemetry acceptance modes
- [1cd9434](https://github.com/w0rmy/farmpi/commit/1cd9434e20cdeff88cd6b5483c3cae250493bb67) — docs: align architecture with OFF SIMULATED LIVE model
- [c7c5e31](https://github.com/w0rmy/farmpi/commit/c7c5e31f035291c2a56311388c4281a9e52386e0) — docs: describe node detail and sensor mode UX
- [aa36605](https://github.com/w0rmy/farmpi/commit/aa366050d13dca78161866efb9a09e3b81a75c99) — docs: correct managed simulation acceptance wording
- [19a0c2e](https://github.com/w0rmy/farmpi/commit/19a0c2e2e317530bd7bba23e8254db079f3d4087) — tools: add console-only node mode configuration
- [7f3d7ca](https://github.com/w0rmy/farmpi/commit/7f3d7ca0dfd23535ab717b323c8997957740baf8) — android: keep sensor source modes console-only
- [4e5a889](https://github.com/w0rmy/farmpi/commit/4e5a8899cb09849d7fdce627c8be8338f48238ab) — docs: record console-only sensor mode control
- [f39e9f0](https://github.com/w0rmy/farmpi/commit/f39e9f0f0ff80c519f1385d3727adc0a52456249) — docs: make node source modes read-only on Android
- [30ea54e](https://github.com/w0rmy/farmpi/commit/30ea54ee55711e12c10e316bb8988ea4c5a875a6) — docs: record Jeremy console-only mode boundary
- [2e40f71](https://github.com/w0rmy/farmpi/commit/2e40f71a972def30ab99b31d57f8dbaa144b4b5f) — tools: document Python invocation for node modes

## Reconciliation validation (27 September 2026)

- Untouched main: 147 Python tests, two failures reproduced (legacy simulated-provenance fallback and obsolete missing-sensor wording assertion).
- Replacement: 155 Python tests pass, including metadata-only mode preservation, missing LIVE capability rejection, mixed-sample provenance, current-mode reporting and console-helper behavior.
- Python compilation and console-helper help invocation pass. Bash syntax checks pass individually for setup, schema update, demo loader and the unchanged reset helper. Git whitespace validation passes.
- Android and ESP32 builds were not run: an Android SDK and Arduino CLI were not available in this workspace. MariaDB DDL/demo-loader execution and two-board hardware validation remain outstanding. The SQLite integration adapter does not validate MariaDB syntax.
- No merge, deployment, database reset or hardware flash was performed. Review as a draft until those environment-specific checks are complete.
