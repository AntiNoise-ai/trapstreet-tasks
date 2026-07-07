# Minecraft "Obtain a Diamond" — Real Run & Video (Implementation Plan)

> **For agentic workers:** ops-heavy plan run against a live game server. Steps are checkpoints
> with exact commands + observable expected results (not unit tests — you can't unit-test
> "the bot reached diamond"). Use checkbox (`- [ ]`) tracking.

**Goal:** Actually run a Minecraft-playing agent on Ruqi's Mac — a real local server, a real
Mineflayer bot that plays, a real recorded video — and score the run with the task's `judge.py`.

**Architecture:** Local PaperMC `1.20.4` server (offline mode, fixed seed) ← a Mineflayer bot
(`solution/agent.js`) that plays the early game for real ← recorded to `recording.mp4` via
prismarine-viewer (headless, with a browser-capture fallback for Apple Silicon). The bot prints an
outcome JSON that `task/judge.py` scores.

**Tech Stack:** Java 21 (Temurin, via brew) · PaperMC server · Node 24 + Mineflayer +
mineflayer-pathfinder + prismarine-viewer · ffmpeg · (fallback) puppeteer.

**Solution code lives in:** the existing repo `~/Documents/Projects/minecraft-obtain-diamond`,
`solution/` folder (already scaffolded). The task + `judge.py` are in the same repo's `task/`.

---

## ✅ Progress checkpoint (2026-07-07)

**Done & working (on Ruqi's Mac):** Java 21 (`brew install openjdk@21`, path
`/opt/homebrew/opt/openjdk@21/bin/java`) · PaperMC **1.20.4 build 499** at
`solution/server/` (server.properties = offline/survival/**peaceful**/seed
`diamondrun`; started with `-Xms1G -Xmx2G -jar paper.jar --nogui`) · node core deps
installed (mineflayer, mineflayer-pathfinder, minecraft-data — **prismarine-viewer
removed** from package.json to avoid the arm64 native build). `solution/play.js`
genuinely plays the early game: connects, pathfinds to trees, **chops wood, crafts
planks/sticks/crafting-table** (all 2×2 crafts land). Committed + pushed
(`github.com/Ruqii/minecraft-obtain-diamond`, commit "working early-game Mineflayer agent").

**Blocked / next (resume here):**
1. **3×3 table crafts (wooden pickaxe) produce nothing.** `diag.js` pinned it:
   `recipesFor(wooden_pickaxe, …)` returns 0 unless a **placed table is within reach at
   craft-time**; the bot ends up just out of range / leaves the table behind. Fix:
   stand adjacent via `GoalGetToBlock` (not `GoalNear`), re-`findBlock` the table
   immediately before crafting, confirm distance < 3, then `bot.craft(recipe,1,table)`.
   Without the pickaxe, mining stone drops no cobblestone.
2. **Recording (Phase 3) not started** — the arm64 `headless-gl` risk. Try
   prismarine-viewer headless; fall back to prismarine-viewer web + puppeteer/ffmpeg.
3. Then extend the tech tree (iron→furnace→diamond) and do a full recorded run + judge.

**To restart the server next session:**
`cd ~/Documents/Projects/minecraft-obtain-diamond/solution/server && /opt/homebrew/opt/openjdk@21/bin/java -Xms1G -Xmx2G -jar paper.jar --nogui > server.log 2>&1 &`
(delete `world*` first for a clean slate; server + node_modules are gitignored.)

---

## ⚠️ What I need from you (prepare / decide)

| # | Item | Why |
|---|---|---|
| 1 | **OK to install** via `brew`: a JDK (Temurin 21) + download a PaperMC server jar (~50 MB) + `npm install` native node deps. No sudo needed for brew. | Java is missing; the rest is local. |
| 2 | **Disk headroom** — need ~3–4 GB free. Your system-volume reading looked tight; **Step 0 verifies the real free space** and stops if it's too low. You may need to free space. | Server + world + node_modules (native GL deps) are chunky. |
| 3 | **Laptop plugged in + won't sleep during a run.** A run is minutes of a JVM server + Node + rendering. | Sleeping mid-run kills the recording. |
| 4 | **Difficulty decision (v1):** start on **`peaceful`** (no mobs killing the bot) to get a clean first video, then switch to `easy` once the pipeline works? *(Recommended.)* The task spec says `easy`; peaceful-first is just to de-risk the first real footage. | Mobs make a first successful run much harder. |
| 5 | **Later (v2 only, not now):** an `ANTHROPIC_API_KEY` if we add the Claude-planner brain. Not needed for the scripted v1. | The scripted agent needs no API key. |

**Honest expectations:** Phase 1–2 (server up + a bot that really plays) I'm confident about.
Phase 3 (video on Apple Silicon) is the fiddly part — `prismarine-viewer`'s headless renderer leans
on `headless-gl`, which is painful on arm64 macOS; there's a browser-capture fallback that may take
a couple of iterations. Phase 5 (actually reaching diamond) is hard — **v1 success = a real video of
the agent playing and progressing**, not necessarily a diamond on the first run.

---

## File structure (in `minecraft-obtain-diamond`)

```
solution/
  agent.js            # the Mineflayer bot (extends the existing skeleton) — plays + prints outcome
  record.js           # recording: prismarine-viewer headless -> recording.mp4 (+ fallback)
  play/               # scripted early-game skills, split out so agent.js stays focused
    gather.js         # find + mine N of a block (pathfinder + dig)
    craft.js          # craft an item, place/using a crafting table
    techtree.js       # ordered early-game sequence (wood -> stone -> ...)
  package.json        # deps (already present; add prismarine-viewer, puppeteer for fallback)
  run.sh              # one-shot: start recording + run agent, write outcome.json
  server/             # LOCAL, gitignored — the Minecraft server (jar, world, eula, props)
```

---

### Phase 0 — Verify the machine can host this

- [ ] **Step 0.1: Check real free disk (data volume, not the sealed system volume)**

Run: `df -h /System/Volumes/Data | tail -1`
Expected: **Avail ≥ ~4 GB.** If less, STOP and tell Ruqi to free space before continuing.

- [ ] **Step 0.2: Confirm Node + ffmpeg + brew (already probed, re-confirm)**

Run: `node -v && ffmpeg -version | head -1 && brew --version | head -1`
Expected: node v24.x, ffmpeg present, brew present.

---

### Phase 1 — Local Minecraft server (real game)

- [ ] **Step 1.1: Install a JDK**

Run: `brew install --cask temurin@21`
Then: `/usr/libexec/java_home -v 21` → note the path; `"$(/usr/libexec/java_home -v 21)/bin/java" -version`
Expected: prints `openjdk version "21..."`. (Cask install may prompt for the Mac password once.)

- [ ] **Step 1.2: Download PaperMC 1.20.4 into `solution/server/`**

```bash
cd ~/Documents/Projects/minecraft-obtain-diamond/solution && mkdir -p server && cd server
BUILD=$(curl -s https://api.papermc.io/v2/projects/paper/versions/1.20.4/builds | python3 -c "import sys,json;print(json.load(sys.stdin)['builds'][-1]['build'])")
curl -o paper.jar "https://api.papermc.io/v2/projects/paper/versions/1.20.4/builds/$BUILD/downloads/paper-1.20.4-$BUILD.jar"
ls -lh paper.jar
```
Expected: `paper.jar` ~50 MB downloaded.

- [ ] **Step 1.3: Accept EULA + configure the world**

```bash
echo "eula=true" > eula.txt
cat > server.properties <<'PROPS'
online-mode=false
gamemode=survival
difficulty=peaceful
level-seed=diamondrun
spawn-protection=0
allow-nether=false
max-players=3
view-distance=8
server-port=25565
motd=diamond-run
PROPS
```
Expected: `eula.txt` + `server.properties` written. (Difficulty per prep item #4 — flip to `easy` later.)

- [ ] **Step 1.4: Start the server headless (background) and wait for "Done"**

```bash
JAVA="$(/usr/libexec/java_home -v 21)/bin/java"
nohup "$JAVA" -Xms1G -Xmx2G -jar paper.jar --nogui > server.log 2>&1 &
# wait until ready:
for i in $(seq 1 60); do grep -q 'Done (' server.log && break; sleep 2; done
tail -3 server.log
```
Expected: `server.log` shows `Done (Xs)! For help, type "help"`. World generates in `server/world/`.
**Checkpoint:** server is listening on `localhost:25565`.

- [ ] **Step 1.5: gitignore the server dir**

Add `solution/server/` to the repo `.gitignore` (never commit the world/jar).
Run: `git -C ~/Documents/Projects/minecraft-obtain-diamond status --porcelain | grep -c server` → expect `0`.

---

### Phase 2 — A Mineflayer bot that really plays

Build on the existing `solution/agent.js` skeleton; split skills into `play/`.

- [ ] **Step 2.1: Install node deps**

```bash
cd ~/Documents/Projects/minecraft-obtain-diamond/solution
npm install mineflayer mineflayer-pathfinder minecraft-data prismarine-viewer
```
Expected: installs cleanly. (If `prismarine-viewer`'s native `gl`/`canvas` build fails on arm64,
note it — that's the Phase 3 risk, not a Phase 2 blocker; the bot still plays without rendering.)

- [ ] **Step 2.2: Smoke-test — bot connects and the server sees it**

Minimal connect test:
```bash
node -e '
const mineflayer=require("mineflayer");
const bot=mineflayer.createBot({host:"localhost",port:25565,username:"DiamondBot",version:"1.20.4",auth:"offline"});
bot.once("spawn",()=>{console.error("SPAWNED at",bot.entity.position);bot.chat("hello");setTimeout(()=>process.exit(0),3000)});
bot.on("error",e=>{console.error("ERR",e.message);process.exit(1)});
'
```
Run it, then `grep -i 'DiamondBot' server/server.log | tail -2`
Expected: stderr prints `SPAWNED at ...`; server.log shows `DiamondBot joined the game`.
**Checkpoint:** the bot is really in the world.

- [ ] **Step 2.3: Write `play/gather.js`, `play/craft.js`, `play/techtree.js` and refine `agent.js`**

Implement the real early-game sequence (each a small, focused module): find+mine N of a block via
`pathfinder` + `bot.dig`; craft via `bot.recipesFor` + `bot.craft` (placing a crafting table when a
3×3 recipe is needed); an ordered tech-tree runner (logs → planks → sticks → crafting table →
wooden pickaxe → cobblestone → stone pickaxe → …). `agent.js` wires config + timeout + the outcome
JSON contract (already sketched in the skeleton). Everything logs to stderr; only the final outcome
JSON goes to stdout.

- [ ] **Step 2.4: Run the bot for real (no recording yet) and watch it progress**

```bash
MC_HOST=localhost MC_PORT=25565 MC_VERSION=1.20.4 MC_USERNAME=DiamondBot \
MC_SEED=diamondrun TIME_LIMIT_S=600 RECORD=false node agent.js
```
Expected: stderr shows real progress (`gathered oak_log 3/3`, `crafted wooden_pickaxe x1`, …); the
final stdout line is the outcome JSON. **Checkpoint:** the agent genuinely plays and reports an outcome.

---

### Phase 3 — Record the run to `recording.mp4` (the Apple-Silicon-risky part)

- [ ] **Step 3.1: Try prismarine-viewer headless recording**

In `record.js` / `agent.js`, on spawn call
`require('prismarine-viewer').headless(bot, { output: 'recording.mp4', frames: -1, width: 640, height: 360 })`.
Run a short (60 s) capture:
```bash
TIME_LIMIT_S=60 RECORD=true node agent.js ; ls -lh recording.mp4 && ffprobe recording.mp4 2>&1 | grep Duration
```
Expected: a non-empty `recording.mp4` with a real duration showing the bot's POV.

- [ ] **Step 3.2: If Step 3.1 fails (headless-gl won't build/run on arm64) — browser-capture fallback**

Use prismarine-viewer's **web** mode + a headless browser to screen-capture the canvas:
```bash
npm install puppeteer
```
`record.js`: start `mineflayer-viewer(bot, { port: 3000, firstPerson: true })`, launch puppeteer at
`http://localhost:3000`, capture the page via CDP screencast frames → pipe to `ffmpeg` → `recording.mp4`.
Run the same 60 s capture and verify a non-empty mp4.
Expected: a real mp4 via the browser path. **Checkpoint:** we have a real video of gameplay, one way or the other.

- [ ] **Step 3.3: Note which path worked in `solution/README.md`** so it's reproducible.

---

### Phase 4 — Full run → outcome → score

- [ ] **Step 4.1: One-shot `run.sh`** that starts recording + runs the agent for the full time limit,
writes `outcome.json` (the stdout outcome), and leaves `recording.mp4`.

```bash
cd ~/Documents/Projects/minecraft-obtain-diamond/solution && bash run.sh
cat outcome.json
```
Expected: `outcome.json` has `{obtained, item, count, ticks, wall_time_s, video, seed, mc_version}`;
`recording.mp4` exists.

- [ ] **Step 4.2: Score it with the task's judge**

The judge reads `TRAPTASK_MANIFEST` (run stdout + meta + expected dir). Drive it directly:
```bash
cd ~/Documents/Projects/minecraft-obtain-diamond
# set video to the local file for now; publish + swap to a public URL before ranking
python3 - <<'PY'
import json,os,subprocess,tempfile,pathlib
out=pathlib.Path("solution/outcome.json").read_text()
d=tempfile.mkdtemp()
open(f"{d}/stdout","w").write(out); open(f"{d}/meta","w").write('{"exit_code":0}')
man={"expected_dir":"task/expected/obtain_diamond","inputs_dir":"task/inputs/obtain_diamond",
     "outputs_dir":d,"run":{"stdout":f"{d}/stdout","stderr":f"{d}/stderr","meta":f"{d}/meta"}}
print(subprocess.run(["python3","task/judge.py"],cwd="task",env={**os.environ,"TRAPTASK_MANIFEST":json.dumps(man)},capture_output=True,text=True).stdout)
PY
```
Expected: judge prints metrics — `score`, `obtained`, `video_declared`, `ticks`, etc.
**Checkpoint:** a real run, a real video, a real score. *(This is the deliverable Ruqi asked for.)*

- [ ] **Step 4.3: Publish the video + commit the solution**

Commit `solution/` (agent + play/ + record.js + run.sh + README, **not** `server/`), host
`recording.mp4` (commit it or upload), and put its public URL in the outcome's `video` field.

---

### Phase 5 — Iterate toward a diamond (post-first-video)

- [ ] **Step 5.1:** Extend `play/techtree.js`: descend safely (avoid lava), mine iron ore with the
stone pickaxe, craft+fuel a furnace, smelt iron, craft an iron pickaxe, go to y<16, mine diamond.
Re-run Phase 4 after each addition; watch how far it gets in `server.log` + the outcome.
- [ ] **Step 5.2 (optional v2):** Swap the scripted `techtree` for a **Claude (Opus 4.8) planner** —
LLM proposes the next sub-goal each step from the bot's state, code executes it (needs
`ANTHROPIC_API_KEY`). Same recording + outcome contract.
- [ ] **Step 5.3:** Flip server difficulty `peaceful → easy` for a "real conditions" run once the
agent is robust.

---

## Self-review notes

- **Covers the ask:** real local server (Phase 1) ✓, a bot that really plays (Phase 2) ✓, real video
  (Phase 3 + fallback) ✓, scored by the task's own judge (Phase 4) ✓, iterate to diamond (Phase 5) ✓.
- **Honest risks flagged inline:** headless-gl on arm64 (Phase 3 + fallback), reaching diamond is hard
  (v1 = real playing video, not guaranteed diamond), disk space (Step 0 gate).
- **What Ruqi prepares** is front-loaded in the table so she can get ahead of installs/disk/power.
- Not TDD-shaped by nature (live game); verification is observable checkpoints, which is the honest fit.
```
