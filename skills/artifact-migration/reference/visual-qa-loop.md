# Visual-QA loop (screenshot → diff → fix)

The **render gate for the generative-app build** (the default). A Generative app has no
diff-able native cells, so the *rendered app* is how you verify look & feel. This loop
renders the app headlessly with a **persistent browser profile the customer logs into
once**, diffs it panel-by-panel against the original artifact, and feeds the notebook agent
surgical fixes until parity.

> **⚠️ The numbers are NOT part of this diff — and this is the big difference from the
> Tableau/Mode version of this loop.** There, a value mismatch against the source meant a
> bug. **Here, a value mismatch is usually the migration working**: real warehouse data has
> replaced the artifact's invented figures, so of course the numbers differ. Diff
> **layout, styling, labels, formats and interactions** against the artifact; verify
> **numbers against the gated SQL cells** ([`sql-review.md`](sql-review.md)) and nowhere
> else.
>
> **Never** send a `continue` fix asking the agent to make a number match the artifact.
> That instruction reverses the entire skill, and the agent will comply — with a hardcoded
> constant. If a number looks wrong, the question is *"does it match the gated cell?"*, not
> *"does it match the mockup?"*

> **Not a credential-entry step.** The agent never types a password. The *customer* logs in
> **once**, in a headed browser, into a local profile that persists. Every later round
> reuses that saved session and is fully headless.

## One-time setup (Phase 0)

**Two profiles, two one-time logins** — Hex, and claude.ai for private artifacts:

```bash
pip install playwright && playwright install chromium    # once
python scripts/hex_shots.py      --login                  # headed: customer signs into Hex
python scripts/artifact_shots.py --login                  # headed: customer signs into claude.ai
```

After that, capture is one command per URL:

```bash
python scripts/artifact_shots.py "<artifact_url>" -o working/shots/source.png     # the design reference
python scripts/hex_shots.py      "<hex_app_url>"  -o working/shots/migrated.png   # the migration
```

- **Artifacts render at their own URL.** Public/shared ones may not need the login at all —
  try a capture first; only run `--login` if you hit a sign-in wall.
- **Local `.html` export?** Skip the login entirely: `python scripts/artifact_shots.py
  "file:///abs/path/to/artifact.html" -o working/shots/source.png`. Cheapest path when you
  already saved the source to `artifact_exports/`.
- **Hex unpublished drafts** show a URL lock screen. `hex_shots.py` opens the editor
  directly and clicks **App builder** to reveal the rendered app without publishing.
- **Full-app capture:** both pages are inner scroll containers; the scripts capture the app
  canvas element, falling back to `full_page`. If a capture looks clipped, that's the first
  thing to check.
- **Capture both themes if the artifact defined dark mode** — `--theme dark` sets
  `prefers-color-scheme`. Artifacts almost always ship both; the migration shouldn't lose
  one silently.
- **Capture mobile if the artifact was responsive** — `--viewport 390x844`.

## The loop

Repeat until the diff is clean — typically **2–3 rounds** (fewer than the BI migrations,
because the source's styling values came across exactly rather than being reconstructed).
Never assume a fix landed; **re-screenshot and re-diff every round.**

```
1. screenshot the Hex app (headless)  +  the source artifact
2. diff panel-by-panel — for each section, compare:
     • layout / position / relative size / section order
     • colors vs. the styling-spec hex codes (light AND dark)
     • titles, labels, axis + legend text, empty states
     • number/date FORMATS (currency, decimals, %, date granularity) — format, not value
     • filter + parameter wiring (does changing an input move the right panels?)
     • Stub panels render their empty state — NOT a value
   ⚠️ do NOT compare the values themselves — those are gated by the SQL review
3. zero discrepancies? → EXIT (hand to human for final confirm)
   else → continue
4. send ONE coherent fix batch:  hex thread continue <thread_id> "<numbered fix list>"
5. wait for IDLE, then go to 1
```

### Diffing well

- **Read the image pair and compare per-panel against a fixed checklist** — a whole-image
  pixel diff is noisy (fonts/antialiasing differ) and misses semantic errors. Go section by
  section.
- **Colors diff against the styling spec, not the screenshot.** You have the artifact's
  literal `:root` hex codes; check the rendered app against *those*. Cheap and exact.
- **Keep each `continue` batch surgical and numbered** — one coherent set per round ("1.
  the KPI band should be 3 columns, not 4; 2. revenue should be currency with 0 decimals;
  3. series colors are #4C6EF5/#F59F00, not the defaults"). Vague or sprawling prompts make
  the agent thrash.
- **⚠️ Watch for the app re-acquiring data.** If a panel's numbers change between rounds
  without a SQL cell changing, the agent may have embedded or "corrected" data in the app
  code. Re-run the mock-constant sweep ([`sql-review.md`](sql-review.md) §5) — don't just
  fix the visual.
- **A Stub panel showing numbers is a gate failure, not a visual bug.** Escalate to the
  grounding gate rather than fixing it cosmetically.

## Exit

The loop exits when a round produces zero discrepancies. Then do the **final human
confirm**: hand the customer the app link + the original artifact side-by-side.

⚠️ **Brief them before they look:** *"The layout should match; the numbers are supposed to
be different — those are now real."* Without that sentence, the first reaction to a correct
migration is reliably "the numbers are wrong." Have the gated cell values ready to show.

## Cheat-sheet

- Setup once: `pip install playwright && playwright install chromium`, then `hex_shots.py --login` and (if needed) `artifact_shots.py --login`.
- Capture migrated: `python scripts/hex_shots.py "<url>" -o working/shots/migrated.png`.
- Capture source: `python scripts/artifact_shots.py "<url or file://…>" -o working/shots/source.png`.
- Fix: `hex thread continue <thread_id> "<numbered fix list>"` → re-capture → re-diff.
- **Diff layout/styling/formats — never values.** Values are the SQL gate's job.
- Profiles live in `working/hex-screenshot-profile/` and `working/artifact-screenshot-profile/` (gitignored); never commit them.
