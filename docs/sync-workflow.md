# Distribution → runtime sync workflow

This repo (`hermes-scaled-cs`) is the **distribution** — git-tracked, tagged,
and what you'd hand to a new team member. But Hermes actually runs each agent
out of `~/.hermes/profiles/<name>/`, which is **runtime** state — populated by
`hermes profile install` at initial bootstrap and never auto-updated when the
repo changes.

That gap is why a commit to this repo does NOT immediately reach Galileo or any
worker. You have to sync.

## The script

`scripts/sync-profiles.sh` is the one-way bridge: repo → live profile.

### What it syncs

For each profile present in BOTH `agents/<name>/` AND `~/.hermes/profiles/<name>/`:

| File / target                                              | Behaviour                                       |
| ---------------------------------------------------------- | ----------------------------------------------- |
| `SOUL.md`                                                  | Overwrite live with repo version                |
| `README.md`                                                | Overwrite live with repo version                |
| each `skills/<category>/<skill>/` present in repo          | Mirror with `--delete` *within that one skill*  |

### Skill-sync is per-skill, not skills-root

This is important. Hermes overlays the **global skill hub** (`~/.hermes/skills/`)
into each profile's `skills/` directory at runtime — that's how every profile
inherits `apple/`, `creative/`, `productivity/`, `software-development/`,
`yuanbao/`, plus the hub state files (`.hub/`, `.bundled_manifest`, etc.). The
overlay is invisible to most workflows but very visible to `rsync`.

The script therefore syncs each repo skill at its specific path
(e.g. `skills/autonomous-ai-agents/coordination-protocol/`) with `--delete`
scoped to that skill only. It never `rsync`s `skills/` or `skills/<category>/`
as a whole, so bundled hub skills are left alone.

Consequences of this design:
- **Files removed from a custom skill in the repo** → removed in live. Good.
- **A whole custom skill removed from the repo** → still lingers in live until
  you delete it manually. Acceptable — drift here is rare and visible.
- **Bundled skills (`apple/`, `creative/`, etc.)** → never touched.

### What it never touches

Anything Hermes writes to at runtime, or that holds per-deployment secrets/state:

- `config.yaml`, `config.yaml.bak.*` — live runtime config (the long YAML
  with personalities, gateway settings, etc.). Diverged from the small repo
  overlay on purpose.
- `.env` — credentials, environment overrides (including the Galileo SSH-fix).
- `state.db`, `state.db-shm`, `state.db-wal`, `kanban.db` — SQLite live state.
- `sessions/`, `memories/` — conversation/memory data.
- `cache/`, `audio_cache/`, `image_cache/`, `*_cache.json` — runtime caches.
- `auth.json`, `auth.lock` — Slack/etc. OAuth tokens.
- `gateway.pid`, `gateway.lock`, `gateway_state.json` — gateway runtime state.
- `logs/`, `sandboxes/`, `pairing/`, `plugins/`, `node/`, `bin/` — runtime
  install trees and ephemeral working dirs.
- `slack-manifest.json`, `channel_directory.json` — platform-specific live state.
- Global skill-hub overlay files inside `skills/` — see above.
- `ssh-fix-notes.md` and similar — per-deployment ops docs added at runtime.

## Standard workflow

```bash
# 1. Pull latest from the distribution.
cd ~/hermes-scaled-cs
git pull

# 2. Preview what would change.
./scripts/sync-profiles.sh --dry-run

# 3. Apply.
./scripts/sync-profiles.sh

# 4. Restart any updated profiles (the script prints the exact commands).
systemctl --user restart hermes-gateway-galileo.service
# ... etc per profile listed by the script
```

The script reports which profiles' synced files actually changed (not just
"sync ran") and prints the exact `systemctl` command per affected profile.
If a SOUL or skill file is byte-identical, that profile is reported as
in-sync and no restart prompt is emitted.

## Bootstrapping missing workers

When a profile in the repo (e.g. `hopper`) doesn't yet have a corresponding
`~/.hermes/profiles/<name>/` directory, the sync script ignores it by default
("not installed — skip"). To bring one online:

```bash
./scripts/sync-profiles.sh --install-missing
```

This calls `hermes profile install` for any agent in the repo without a live
profile, then syncs everything. It does NOT create the `~/.local/bin/<name>`
shim — copy the `tycho` shim pattern by hand if you want the bare-name
invocation (`<name> -z "..."`) rather than `hermes -p <name>`.

You can still use `scripts/install-all.sh` for the original "install
everything from scratch" case — `--install-missing` is the incremental path.

## Why not a git post-merge hook?

Considered but skipped:

- Hooks are easy to forget exist — a teammate cloning the repo doesn't
  inherit them and gets silent drift.
- The restart step is necessarily manual (live traffic decisions), so the
  hook can't be fully end-to-end anyway.
- The script is short enough to memorize and the dry-run gives a free
  preview.

If you want automation later, the script is hook-friendly — `git pull`
followed by `./scripts/sync-profiles.sh` in `.git/hooks/post-merge` works,
and the script remains the source of truth for what sync means.

## Why config.yaml is excluded

Galileo's live `config.yaml` is ~500 lines (full Hermes default config with
personalities, gateway, browser, etc.). The repo's `agents/galileo/config.yaml`
is intentionally a small overlay (just the model section) — it merges with
Hermes defaults at install time. Overwriting live with the overlay would wipe
every personality, browser setting, dashboard pref, etc.

If you ever need to update the repo overlay AND have it reach live: edit the
overlay, then for each affected profile do a one-shot manual `cp` (or a
careful YAML merge). This is rare enough not to deserve automation.

## Auditing drift

To check what's diverged for one profile:

```bash
diff -r --brief \
  ~/hermes-scaled-cs/agents/galileo/SOUL.md \
  ~/.hermes/profiles/galileo/SOUL.md

# Per-skill, since whole-tree diff includes the hub overlay:
diff -r --brief \
  ~/hermes-scaled-cs/agents/galileo/skills/autonomous-ai-agents/coordination-protocol/ \
  ~/.hermes/profiles/galileo/skills/autonomous-ai-agents/coordination-protocol/
```

Or trust the script:

```bash
./scripts/sync-profiles.sh --dry-run
```

## A note on what happened during the v1.2.2 design

An earlier draft of this script `rsync`ed all of `agents/<name>/skills/` into
`~/.hermes/profiles/<name>/skills/` with `--delete`. That looked clean against
the repo but, against the live runtime overlay, generated very large deletion
lists for every bundled skill in the global hub. The script as shipped is the
corrected version — it walks each repo skill individually and syncs only
inside it. If you ever see a sync output that includes deletions of `apple/`,
`creative/`, `yuanbao/`, etc., something has regressed; stop and inspect.
