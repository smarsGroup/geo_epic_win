# Running GeoEPIC inside QGIS (Q-EPIC integration)

Status: **proposal, nothing implemented.** Branch `feat/q-epic`, cut from
`cross-platform-lowrisk` at `6eed4d5` on 2026-09-14, so the Windows/Linux
`EPICCONT` fixes are already in the base.

## The requirement

Q-EPIC (`Desktop/EPICModel_tools/Q-EPIC`) is a QGIS plugin that must be installed
from a single ZIP and then work with **nothing but QGIS** — no Conda, no pip step,
no second Python interpreter, no Redis. It runs EPIC itself.

The maintainer's added constraint, and the reason this document exists:

> I don't want to maintain two different GeoEPIC and Q-EPIC Python surfaces. I
> imagine GeoEPIC being pulled into the ZIP as-is and starting to work.

So the target is **one codebase, two install profiles** — not a port, not a fork,
and not an external interpreter.

## Why `geo_epic_win` cannot be vendored as it stands

Measured against QGIS 3.22.4 on Linux (2026-09-14), whose interpreter is the
system `/usr/bin/python3`:

| Blocker | Measured |
|---|---|
| Python pin | `pyproject.toml` has `requires-python = "==3.11.*"`; this QGIS runs **3.10.12**. pip refuses outright. |
| numpy | We pin `numpy<2.0.0`; QGIS ships **2.2.6**, and its GDAL bindings are compiled against it. Downgrading breaks QGIS itself. |
| Missing dependencies | **22 of our 38** are absent from QGIS's Python: geopandas, pandas, xarray, rasterio, sklearn, netCDF4, pyarrow, lmdb, redis, pebble, ee, pydap, pyogrio, SALib, us, affine, attrs, charset-normalizer, contourpy, pathspec, shortuuid, notebook. |
| Compiled wheels | geopandas, rasterio, netCDF4, pyarrow, lmdb and pygmo each carry their own GDAL/PROJ, which collide with QGIS's. The QGIS plugin repository also forbids binaries and caps packages at 20 MB. |
| Install target | QGIS's interpreter *is* the OS Python. Installing our stack into it mutates the user's system — the opposite of self-contained. |

Also worth recording: **`scipy` is present in QGIS but ABI-broken** against numpy
2.2.6 on this machine (`scipy.spatial.cKDTree` raises `numpy.dtype size changed`).
Nothing in the light core may depend on scipy.

## What the code actually needs

Full scan of the installed package, 6,951 lines, grouped by fate:

| Group | Lines | Fate |
|---|---|---|
| A · EPIC file writers/parsers — DLY, SOL, SIT, ACY/DGN, CROPCOM, PARM | 962 | **Must be dependency-light** |
| B · Model folder + run driver — `core/model.py`, `core/site.py`, `core/workspace.py`, `utils/misc.py` | 1,546 | **Must be dependency-light** |
| C · Soil retrieval, SDA REST | 389 | **Must be dependency-light** |
| D · OPC / management (`io/inputs/opc.py`, `opc/generate_opc.py`) | 902 | Deferred by Q-EPIC; light eventually |
| E · GEE fetch, DEM, SoilGrids | 901 | Q-EPIC already has its own QGIS-native EE client — see Q7 |
| F · Daymet NetCDF / AgERA5 / SSURGO gdb fetch paths | 525 | Not used by Q-EPIC; stay heavy |
| G · redis / lmdb / pebble pools and loggers | 859 | Stay heavy; Q-EPIC uses threads + plain files |
| H · Calibration (SALib, pygmo) | 261 | Stays heavy, Conda-only |
| I · Misc utils | 606 | Split case by case |

The run-critical core is **A + B + C ≈ 2,900 lines**, and it is much closer to
dependency-free than the import list suggests:

- **`core/model.py` (492) and `core/site.py` (266) touch pandas zero times.**
  That is the EPIC runner, the `EPICFILE`/`EPICCONT` writers and per-site logic.
- The whole run-critical core uses only **27 distinct pandas API members**, all
  ordinary: `read_csv` ×15, `DataFrame` ×13, `.values` ×25, `.columns` ×18,
  `.copy` ×18, `.astype` ×9, `.apply` ×8, `.append` ×7, `.loc` ×7, `read_fwf` ×4,
  `to_datetime` ×4, `groupby` ×2, `merge` ×3.
- **Only 7 genuine `pd.merge` calls exist in the entire package**, each a
  single-key left/outer join on a date or key column. (An earlier count of 127
  was wrong: it was matching `os.path.join` and `str.join`.)
- `geopandas` appears only as **`gpd.read_file` ×8** → OGR / `QgsVectorLayer`.
- `sklearn` appears **once**, `BallTree` in `utils/raster_utils.py` →
  `QgsSpatialIndex` (not scipy, see above).
- `ruamel.yaml` **is already present in QGIS**, so `io/config_parser.py` needs
  nothing.
- EPIC inputs are fixed-width text. `numpy.genfromtxt` plus format strings is the
  natural tool for them; the pandas layer is something to delete, not to
  reimplement.

## Design principle: one interface, several backends

Everywhere the two environments genuinely differ, the difference is isolated
behind **one interface with swappable backends**, rather than duplicated into two
code paths. The core calls the interface and never learns which backend it got.
This is what keeps a single codebase honest — it is applied in three places.

### 1. Earth Engine

Q-EPIC already has a working QGIS-native Earth Engine client (browser OAuth with
PKCE, REST `computePixels` and map tiles, all over `QgsNetworkAccessManager`, no
`earthengine-api`). GeoEPIC uses `earthengine-api`. Keeping both as-is re-creates
exactly the duplication this plan exists to remove.

```
    geoEpic.core  ──calls──▶  EarthEngineBackend  (interface)
                               ├── QgisEeBackend        (Q-EPIC: QGIS networking, REST)
                               └── EarthEngineApiBackend (CLI: earthengine-api)
```

The light core imports no Earth Engine library at all; the backend is injected by
whoever constructs the workspace. The interface is the small set of operations the
core actually needs — initialise, reduce a region, sample points, fetch an image
as an array — not a general EE wrapper.

### 2. Tabular data

Same treatment for pandas. The core stops importing pandas directly and calls a
narrow table interface; the backend is pandas where it is available, and our own
numpy implementation inside QGIS.

```
    geoEpic.core  ──calls──▶  Table  (interface)
                               ├── PandasTable  (Conda/CLI: thin wrapper over DataFrame)
                               └── NumpyTable   (QGIS: numpy + csv, stdlib only)
```

The scan makes the size tractable: the run-critical core uses **27 distinct pandas
members**, and the work is fixed-width text I/O — read a table, index columns,
cast, join on one key, write it back. The interface should be defined by what
those call sites need and nothing more; anything wider becomes a second pandas to
maintain.

Two rules keep it from rotting:

- The interface is **closed**. Adding a method is a deliberate change with a test
  in both backends, not something a caller does in passing.
- **Both backends run the same fixtures** in CI. A behavioural difference between
  `PandasTable` and `NumpyTable` is a failing test, not a user's bug report.

### 3. EPIC model files and the runner

`EPICModel`, and the `PARM` / `SIT` / `CROPCOM` / `EPICCONT` / `EPICFILE` handling
around it, gets a **common parent that does almost everything** and thin
subclasses that differ only where they must:

```
    EPICModel              (parent: all shared behaviour)
      ├── EPICModelWin       (.exe name, CREATE_NO_WINDOW, CRLF, path length)
      └── EPICModelLinux     (chmod +x, LF, /dev/shm scratch)
```

The parent owns the run loop, the model-folder copy, start date and duration,
output-type toggles, resume and timeout logic. The subclasses stay small and carry
only genuine platform facts. The same parent/subclass shape applies to the file
classes that have platform-specific quirks (line endings, in-place rewrites).

**One caveat to settle before writing the classes (Q14).** Two independent axes
are currently tangled in `core/model.py`, and only one of them is the OS:

| Axis | What varies | In today's code |
|---|---|---|
| **Operating system** | executable name/extension, `chmod +x`, `CREATE_NO_WINDOW`, line endings, path length, scratch location | `platform.system() != "Windows"` at `model.py:67` |
| **EPIC build layout** | `EPICFILE.DAT` entry count (17 vs 19), `EPICCONT.DAT` header rows (2 vs 3), line offsets into `PRNT*.DAT` | class constants `PF_TOG1 = 14`, `PF_TOG2 = 15`, `EC_IRR = 3`, `EC_NIT = 4` |

The bundled `assets/workspace_win/model` and geo-epic's Linux `EPIC1102` are
*different EPIC revisions* (Q-EPIC `docs/07_geoepic_review.md` §2), which is why
the win parser cannot read the Linux template — but that is a property of the
build, not of the OS. Folding layout into `EPICModelWin` / `EPICModelLinux` would
make it impossible to run a win-layout build on Linux, which is exactly what the
Wine harness does today and what a matched cross-platform pair (Q11) needs.

Recommended split: `EPICModelWin` / `EPICModelLinux` carry the OS facts as
proposed, plus a separate **layout descriptor** (those four constants and the
`EPICFILE` entry list) chosen by inspecting the model folder rather than by
`platform.system()`. Either subclass can then run either layout.

## v1 binary strategy: Windows EPIC everywhere, Wine on Linux

**Decided 2026-09-14.** v1 ships **one EPIC executable — the Windows build** — and
runs it under Wine on Linux. A native Linux binary is a later switch.

### What this buys

- **One EPIC revision, so identical numerics on both platforms.** The current
  blocker (Q11/B2) is that `assets/workspace_win/model` and geo-epic's Linux
  `EPIC1102` are different builds with incompatible `EPICFILE`/`EPICCONT`
  layouts. Shipping one binary removes that divergence entirely, and with it the
  risk of the same workspace producing different yields on different machines.
- **The layout axis becomes single-valued in v1.** This makes the Q14
  recommendation easier, not harder: keep layout as a descriptor, ship exactly
  one descriptor now, and adding the native Linux build later is a new descriptor
  rather than a refactor of the model classes.
- Halves the binary redistribution, packaging and CI-testing surface.

### The cost, stated plainly

**Wine cannot be bundled.** Measured on this machine: `libwine` alone is
**545 MB** installed, against a QGIS plugin repository cap of 20 MB and our own
< 25 MB budget. Wine is a system package, not a vendorable dependency.

So on Linux, v1 is "install QGIS, this ZIP, **and Wine**". That is a real
departure from the *nothing but QGIS* constraint in Q-EPIC `docs/00_goal.md`
(constraint 1), and the goal document must be amended to say so rather than left
contradicting the plan. It is a much milder ask than the Conda alternative — one
distro package instead of a 40-package scientific stack — and Windows users are
unaffected. Options if that trade is unacceptable:

| # | Option | Note |
|---|---|---|
| L1 | Linux users install Wine from their distro; the plugin detects it and explains how, with a Settings field for a non-standard path. | **Recommended for v1.** One `apt`/`dnf` command, no Python involvement. |
| L2 | Ship the native Linux ELF as well. | Blocked until a Linux build of the *same* EPIC revision as the `.exe` is obtained from the EPIC team. This is the v2 plan. |
| L3 | Bundle a trimmed Wine. | Not viable at 545 MB, and a support burden of its own. |
| L4 | Windows-only v1; Linux waits for L2. | Cleanest against the constraint, but leaves the maintainer's own platform unsupported. |

### Consequences for the runner

These follow from the decision and belong in the model classes, not in callers:

- **Judge a run by its outputs, not by its exit code.** `EPIC1102.exe` is known to
  crash `0xC0000374` on shutdown *after a complete, correct run*; under Wine the
  exit status is doubly unreliable. Success means the expected `.ACY`/`.DGN`
  exist and parse.
- **Console behaviour.** The existing Wine harness needed a pty (`script -qec`) to
  drive the executable; EPIC also pauses for input on error, so stdin must be fed
  regardless of platform.
- **`WINEPREFIX` placement.** Must not be the user's `~/.wine`. Put it under the
  QGIS profile or the workspace, created and `wineboot`-initialised on first run,
  so Q-EPIC never disturbs an existing Wine setup.
- **`EPICModelLinux` changes meaning in v1**: it is no longer "run the Linux ELF"
  but "run the Windows build under Wine". Worth naming the subclasses for what
  they do rather than for the host OS, so the native-binary switch later is
  additive.

### The risk that needs measuring before committing

Q-EPIC launches **one EPIC process per grid cell** — thousands of processes per
run — and its published throughput (`docs/05_benchmarks.md`: ~5 sites/s per
physical core, 0.06 s of per-site overhead) was measured with a native Linux
binary. Wine adds per-process startup cost and funnels concurrent processes
through a shared `wineserver`, neither of which that benchmark covers.

**Before this is locked in, re-run the 200-site benchmark under Wine at 1, 8 and
32 workers.** If per-site overhead rises materially or the `wineserver` serialises
the pool, the estimator constants in `05_benchmarks.md` are wrong on Linux and the
run-time estimate shown to users will be wrong with them. This is a measurement,
not a guess, and the harness already exists.

## Proposed shape

```
geoEpic/
  core/, io/        numpy + stdlib only; importable inside QGIS.
                    Vendored verbatim into the Q-EPIC ZIP.
  science/, gee/    pandas, sklearn, SALib, pygmo, xarray, rasterio.
                    Optional extras; Conda/pip users only.
```

`pip install geo_epic_win` keeps working exactly as today, with the extras
pulling the heavy stack. Q-EPIC's build copies the light subpackage into
`q_epic/_vendor/geoEpic/` **unchanged**. The plugin and the CLI execute the same
files; nobody maintains a second implementation.

## Options considered

| # | Option | Verdict |
|---|---|---|
| **A** | **Refactor upstream so the run-critical core is numpy+stdlib only behind the interfaces above, then vendor it as-is.** | **Recommended.** Keeps one codebase. ~2,900 lines touched, of which 758 already qualify. The pandas surface being removed is 27 ordinary members over fixed-width text I/O. |
| A′ | Keep the pandas idioms and ship a numpy-backed compat shim covering those 27 members (~300–500 lines). | Viable bridge, risky destination. `.apply` with arbitrary lambdas and `groupby` are where shims get fragile, and a 28th idiom appearing upstream fails on a user's machine rather than in CI. Only acceptable with the import guard below made mandatory. |
| B | Vendor the dependencies themselves into the ZIP. | Impossible. pandas/geopandas/rasterio/netCDF4/pyarrow/lmdb/pygmo are compiled wheels tied to a Python ABI and their own GDAL/PROJ; they collide with QGIS's and breach the repo's no-binaries rule and 20 MB cap. |
| C | Bundle a private Python interpreter in the ZIP. | Rejected. Same binary and size rules, and it is a second Python surface by another name. |
| D | Q-EPIC shells out to a user-installed Conda env. | Rejected by the maintainer: violates "nothing but QGIS". Works today (verified: QGIS 3.10 → `epic_win_env` 3.11 subprocess, rc 0), so it stays available as a developer convenience, never as the shipping path. |

## What keeps "as-is" honest

Vendoring alone does not prevent drift: an `import pandas` added to a core module
later would break the ZIP silently at a user's desk. Two guards, both cheap:

1. **Build-time import guard.** Q-EPIC's `scripts/build_plugin.py` walks the
   vendored tree and fails the build if any file imports outside an allowlist
   (stdlib, `numpy`, `qgis`, `osgeo`). The boundary becomes a rule, not a
   convention.
2. **Dual-interpreter test run.** The same fixtures execute under QGIS's Python
   (no pandas) and under `epic_win_env` (with it). Both green means the single
   codebase genuinely works in both. *This*, not the packaging, is what prevents
   the fork.

The vendored copy is pinned by tag and recorded in Q-EPIC's `metadata.txt`, so
"which GeoEPIC is in this ZIP" is always answerable.

## Open questions

Each has a proposed default so work can start without blocking.

| # | Question | Proposed default |
|---|---|---|
| Q1 | ~~Base branch~~ **Decided 2026-09-14:** `feat/q-epic` is cut from `cross-platform-lowrisk` (`6eed4d5`), not `main`, so the `EPICCONT` and platform fixes are in the base. Still open: whether that branch merges to `main` before or after this work lands. | Merge it to `main` first, so this branch is not the only route for those fixes. |
| Q2 | Package boundary. Does the light core stay at `geoEpic.core` / `geoEpic.io` with heavy code moved out, or does a new namespace (`geoEpic.light`) appear and the old paths become shims? | Keep `geoEpic.core` / `geoEpic.io` as the light names and move heavy code to `geoEpic.science`; preserve old import paths via re-exports for one release. |
| Q3 | Option A (remove pandas from the core) or A′ (compat shim)? | **A.** A′ only as a temporary bridge, and only with the import guard in place. |
| Q4 | Python floor. `requires-python` is `==3.11.*`; QGIS ships 3.9–3.12 depending on build. | Light core targets **3.9+** with no `match`, no `X | Y` unions. The heavy extras may keep a tighter pin. |
| Q5 | numpy range. We pin `<2.0.0`; QGIS 3.22 here has 2.2.6, other QGIS builds have 1.x. | Light core must work on **both 1.x and 2.x**; no pin. CI covers both. |
| Q6 | Vendoring mechanism: git subtree, submodule, or a build-time copy from a pinned sdist? | Build-time copy from a pinned tag, so the Q-EPIC repo stays free of GeoEPIC history and the pin is visible in one place. |
| Q7 | ~~Earth Engine duplication~~ **Decided 2026-09-14:** one `EarthEngineBackend` interface with two backends (`QgisEeBackend`, `EarthEngineApiBackend`); the light core imports no EE library. Still open: the exact operation set the interface exposes. | Derive it from the call sites in group E rather than designing a general EE wrapper. |
| Q8 | `shortuuid` (used in `core/site.py`, `utils/misc.py`) and `ruamel.yaml`. | `ruamel.yaml` is already in QGIS — use it. Replace `shortuuid` with stdlib `uuid`; it is pure-Python but not worth a vendored dependency. |
| Q9 | Concurrency. The light core must not import `pebble` or `redis`. | Injectable executor, defaulting to `concurrent.futures.ThreadPoolExecutor`; the heavy profile may pass a pebble pool. |
| Q10 | Test fixtures. What proves the ported writers/parsers still produce byte-identical EPIC files? | Round-trip fixtures captured from current GeoEPIC output, committed here and run by both interpreters. Needed **before** any refactor. |
| Q11 | **EPIC binaries.** Redistribution permission is **granted** (maintainer, 2026-09-14) — this closes the long-standing blocker in Q-EPIC `docs/06_distribution.md`. Still open: file the written terms; decide which builds ship; resolve that the current Windows `.exe` and Linux ELF are *different EPIC revisions* with incompatible `EPICCONT`/`EPICFILE` layouts (see Q-EPIC `docs/07_geoepic_review.md` §2, B2). | Record the permission text under `docs/legal/`; obtain a matching Windows/Linux pair of one revision before shipping. |
| Q12 | Calibration inside QGIS. Needs sklearn, SALib, pygmo, none of which can be vendored. | Out of scope for Q-EPIC v1 (already a non-goal in Q-EPIC `docs/00_goal.md`). Stays a Conda-only capability. |
| Q13 | Does the OPC group (D, 902 lines) join the light core, and when? | After Q-EPIC's management design is settled; `io/inputs/opc.py` is the single largest module and its pandas use is not yet surveyed in detail. |
| Q14 | **Model class hierarchy.** `EPICModelWin` / `EPICModelLinux` under a common parent is agreed. Open: whether EPIC **build layout** (`PF_TOG1/2`, `EC_IRR/EC_NIT`, `EPICFILE` entry count, `EPICCONT` header rows) is folded into those subclasses or kept separate. | **Separate layout descriptor**, selected by inspecting the model folder, so either OS can run either layout — needed for the Wine harness and for a matched binary pair. |
| Q15 | **Table interface scope.** Which of the 27 pandas members become interface methods, and which call sites get rewritten instead? | Rewrite rather than widen wherever a call site is one-off; `.apply` with arbitrary lambdas and `groupby` should not enter the interface. |
| Q16 | Must `PandasTable` and `NumpyTable` agree on dtype and NaN behaviour exactly, or only on the values EPIC files can hold? | Only on what EPIC files can hold (fixed-width numerics and short strings); assert that in the shared fixtures. |
| Q17 | **Wine as a Linux dependency.** Bundling is impossible (545 MB). Does v1 accept "QGIS + ZIP + Wine" on Linux, and how is Q-EPIC `docs/00_goal.md` constraint 1 amended? | Option L1: require the distro's Wine, detect it at startup, explain it clearly, allow a custom path in Settings. Amend the goal doc to scope "nothing but QGIS" to Windows for v1. |
| Q18 | **Wine throughput.** Does per-process Wine overhead or a shared `wineserver` change the ~5 sites/s per core figure the run-time estimator is built on? | Unknown — **measure before locking the decision**: 200-site benchmark under Wine at 1, 8 and 32 workers, compared against the native figures. |
| Q19 | `WINEPREFIX` location and first-run initialisation. | Under the QGIS profile, `wineboot`-initialised on first use; never the user's `~/.wine`. |
| Q20 | Subclass naming now that `EPICModelLinux` means "Windows build under Wine" in v1 and "native ELF" later. | Name for behaviour, e.g. `EPICModelNative` / `EPICModelWine`, so the later native Linux build is an addition rather than a rename. |

## Explicit non-goals for this branch

- No behaviour change to the CLI or to existing Conda workflows.
- No calibration, phenology or notebook work.
- No new dependencies of any kind.

## Next step

Q1 and Q7 are settled, and the v1 binary strategy is decided (Windows build, Wine
on Linux). Run the **Q18 Wine benchmark first** — it is cheap, the harness exists,
and a bad result changes the packaging decision rather than the code. Then answer
Q3 (option A or the A′ shim), Q14 (layout as a descriptor or inside the
subclasses), Q15 (table interface scope) and Q17 (how the goal document is
amended), and capture the Q10 round-trip fixtures **before** touching any writer,
parser or model class.
Nothing else should start until those fixtures exist: they are the only evidence
that swapping a backend has not changed a byte of EPIC input.
