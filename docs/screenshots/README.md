# Screenshots

Drop PNG screenshots here with these exact filenames so the main README renders them:

| Filename | What to capture |
|----------|-----------------|
| `arena.png` | Incident Arena with a scenario SELECTED (blue ring + SELECTED badge) |
| `decision.png` | Decision Observatory showing the Decider choice + confidence bars + latency |
| `resource-graph.png` | Resource Graph with the affected node glowing red (e.g. Database for DB Exhaustion) |
| `recovery.png` | Recovery Timeline after approval → "✓ Recovered (simulated)" |
| `time-machine.png` | Incident Time Machine replay comparison table |

## How to capture (macOS)
1. Start all three services (Decider, backend with `AEGIS_ENABLE_BEDROCK=1`, frontend).
2. Open the dashboard, run **Bad Deployment** end to end, then **Database Connection Exhaustion**.
3. Press ⌘⇧4, then Space, then click a browser window — or drag to select a region.
4. Save/rename the file to the name above and place it in this folder.
5. `git add docs/screenshots/*.png && git commit && git push` — GitHub will render them in the README.

Keep images under ~1 MB each (crop to the relevant panel). PNG preferred.
