> rc.4 primary workflow: [stage-free review inside Isaac](first-use.md).
> The minimal Kit launcher below is the optional legacy worker route, not live in-app A/B.

# Distribution candidate quick start — English

Target: Windows, an already installed Isaac Sim 4.5 SDK (Kit 106.5, Python 3.10,
OpenUSD 22.11), working NVIDIA RTX GPU access. The SDK and its license are separate.
This candidate does not download/install/upgrade them. Full Isaac application support
is not qualified. See [support](distribution-support.md). Project license is pending.

## 1. Extract and diagnose

Use a new folder, including paths with spaces if desired. Keep outputs outside it.
Compare `Get-FileHash <archive.zip> -Algorithm SHA256` with its sidecar checksum, then
extract with the normal archive tool. In the extracted package root:

```powershell
$sdk = '<existing Isaac Sim 4.5 SDK directory>'
$python = Join-Path $sdk 'kit/python/python.exe'
& $python -B .\review_kit.py verify
& $python -B .\review_kit.py --sdk $sdk doctor
```

Doctor checks the existing runtime ABI, bundled libraries/template and a read-only
NVIDIA health query. It does not qualify native rendering by itself or repair anything.
All commands return nonzero for errors; stop and read their error identifier.

## 2. Create and compare the public sample

Choose an existing writable parent folder. `sample`, `compare` and `launch` workspace
destinations must be **new** and outside the extracted package. Prior files are never
overwritten. The public rack is authored by this project, independent of factory data.

```powershell
$parent = '<existing writable output directory>'
$sample = Join-Path $parent 'review-sample'
& $python -B .\review_kit.py --sdk $sdk sample --workspace $sample
& $python -B .\review_kit.py --sdk $sdk compare --before "$sample/snapshot-A/manifest.json" --after "$sample/snapshot-B/manifest.json" --workspace "$parent/review-comparison"
```

Open `review-comparison/review.html` offline or inspect `review.json`. A is before/right
at `(0,0.2,0)m`; B is current/left at `(0,0,0)m`; delta is `(0,-0.2,0)m`.
Changed does not mean defective; clash remains unknown and policy has no thresholds
unless configured through the engine CLI. Code 0 is not a clearance/safety verdict.

## 3. Open minimal Kit and save evidence

```powershell
& $python -B .\review_kit.py --sdk $sdk launch --data $sample --workspace "$parent/review-session"
```

The launcher copies the verified small project payload into `review-session/runtime`
so Kit-generated caches stay in the private session and the original package stays
unchanged. This is a local working copy, with no SDK/runtime installation.
The new minimal host compares the sample, saves JSON/HTML to `review-session/reports`,
selects the rack and opens current B plus the translucent green old-A helper and
right evidence panel. Use **View A/B**, search, optional focus and ghost toggles.
To save another comparison, choose a new output folder in the host panel and press
**Save results**. Input snapshot bundles are refused as export destinations. Compare
again after changing inputs; stale comparison evidence cannot be exported.

Close review and then close the minimal host normally. The launcher requires normal
host exit plus worker preservation confirmation. Ctrl+C/timeout is containment, not a
clean acceptance pass. Private workspace logs stay local; do not upload them blindly.

For an automated **real GPU/GUI** first-run smoke check, add `--smoke --timeout 300`
and use another new session directory. It renders A/B, checks the camera and helper,
saves evidence, closes both processes and writes `session-result.json` and
`process-result.json`. A PNG or CPU test alone does not certify UI behavior.

`launch.ps1 -Sdk $sdk -Action launch -Data $sample -Workspace <new-folder>` is an optional
wrapper. If local script policy blocks it, use the direct SDK Python commands above;
do not change security settings. No system installation or administrator access is needed.

## Common errors

| Identifier | Next step |
| --- | --- |
| PACKAGE_HASH / PACKAGE_FILES | Extract a fresh verified copy; keep outputs elsewhere. |
| SDK_REQUIRED / SDK_VERSION / ABI_UNQUALIFIED | Select the existing qualified SDK, not system Python or another version. |
| GPU_DIAGNOSTIC | Check GPU access locally; the tool does not fix drivers. |
| WORKSPACE_LOCATION / file exists | Choose a new directory outside the package with an existing writable parent. |
| KIT_EXIT / timeout | Inspect the private session result/logs. Do not treat forced containment as normal exit. |

Building from source: `python tools/package_candidate.py <new-archive.zip>` creates a
versioned, deterministic candidate payload and reports its SHA-256. Rebuild twice in
the same toolchain to verify byte identity. Use `python -m unittest discover -s tests -v`
with OpenUSD and the optional test dependencies for CPU checks. CPU CI is separate from
manual/installed-SDK GPU smoke acceptance; neither certifies the full Isaac application.
