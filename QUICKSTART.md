# Quickstart — from zero to a CR workbook

Windows / PowerShell commands, since that is where the team works. macOS and
Linux are the same apart from the venv activate line.

---

## The one thing to understand first

**This repository *is* your CR working folder.** You clone it once, open that
folder in VS Code, and every CR you ever estimate lives inside it under
`workspaces/`.

You do **not** copy the tool into other projects, and you do **not** open your
CR documents in some other folder.

The reason is not arbitrary. GitHub Copilot only reads
`.github/copilot-instructions.md` and `.github/prompts/*.prompt.md` **from the
folder you currently have open in VS Code**. Open a different folder and Copilot
has never heard of the estimation rules, the weights, or `/generate-cr` — you
get generic answers and a wrong spreadsheet. Open *this* folder and it knows all
of it automatically.

```
CR/                                  ← clone here, open THIS in VS Code
├── .github/                         ← Copilot reads these. Do not move them.
│   ├── copilot-instructions.md
│   └── prompts/generate-cr.prompt.md
├── src/, templates/, docs/          ← the engine. You never edit these.
└── workspaces/                      ← YOUR CRs live here (git-ignored)
    ├── SLADCYBQSK-42132/
    │   ├── inputs/
    │   │   ├── figma/       your-screen.png, flows.pdf
    │   │   ├── stories/     SLADCYBQSK-42132.md
    │   │   ├── hld/         hld.md
    │   │   └── lld/         lld.md          (optional)
    │   └── output/
    │       ├── SLADCYBQSK-42132_cr_spec.json      ← Copilot writes this
    │       └── SLADCYBQSK-42132-CR-Estimation.xlsx ← the deliverable
    └── SLADCYBQSK-42528/ ...
```

`workspaces/` is git-ignored, so your CR documents and generated workbooks never
get committed. Each CR is just a new folder next to the last one.

---

## One-time setup (about 5 minutes)

### 1. Clone and open in VS Code

```powershell
git clone https://github.com/VSaikiranOwn/CR.git
cd CR
git checkout claude/cr-generation-utility-s8sfrz
code .
```

That last line opens this folder as the VS Code workspace. **This is the step
that makes Copilot aware of the tool.**

### 2. Install the tool

Needs Python 3.10 or newer (`python --version` to check).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

macOS / Linux: `source .venv/bin/activate` instead of the Activate.ps1 line.

If PowerShell refuses to run the activate script, allow it once for your user:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Optional, only if your Figma exports arrive as PDF rather than PNG:

```powershell
pip install -e ".[pdf]"
```

Check it worked:

```powershell
cr-tool rules
```

You should see the weights table. If `cr-tool` is not found, the venv is not
active — re-run the Activate line.

### 3. Turn on Copilot prompt files in VS Code

Open Settings (`Ctrl+,`) and confirm these two:

| Setting | Value | What it does |
|---|---|---|
| `chat.promptFiles` | on | lets you run `/generate-cr` in Copilot Chat |
| `github.copilot.chat.codeGeneration.useInstructionFiles` | on | loads `copilot-instructions.md` automatically |

Both are on by default in recent VS Code. If you cannot find `chat.promptFiles`,
your VS Code is older than prompt-file support — update it, or use the
[manual fallback](#if-prompt-files-are-not-available) below.

Make sure Copilot Chat is in **Agent** mode (the dropdown at the bottom of the
chat box). Ask mode cannot run commands or write files.

---

## Estimating a CR (every time, about 2 minutes of your effort)

### Step 1 — make a folder for this CR

```powershell
cr-tool init workspaces\SLADCYBQSK-42132 --key SLADCYBQSK-42132
```

Use the Jira key as the name. This creates the `inputs/` and `output/` folders.

### Step 2 — drop your files in

| Put this | Here |
|---|---|
| Figma screen exports (`.png`, `.jpg`, `.pdf`) | `inputs\figma\` |
| Jira user story exported as Markdown | `inputs\stories\` |
| HLD as Markdown | `inputs\hld\` |
| LLD as Markdown, if you have one | `inputs\lld\` |

Drag and drop in the VS Code explorer is fine. Filenames do not matter much —
the folder decides how each file is treated.

> No LLD? Normal. The tool says so and carries on with less endpoint detail.

### Step 3 — ask Copilot

In Copilot Chat (Agent mode), type:

```
/generate-cr
```

then tell it which folder, e.g. *"workspaces/SLADCYBQSK-42132"*.

It will inventory the pack, read your screens and documents, show you its
plan — the TSP rows with the counts behind each size, and the Details rows with
the complexity flags — then write the spec JSON and run `cr-tool build`.

**Attach the Figma images to the chat** when it asks, or drag them into the chat
box. Copilot has to actually look at a screen to count interactions on it.

### Step 4 — read what it reports back

You get the MD breakdown, the TSP per story, and two lists worth your attention:

- **Placeholders** — cells it marked `[TBD: ...]` because the input pack did not
  say. Each one comes with a cell coordinate. Fill them in.
- **Warnings** — a row over 10 MD, a row with too many flags, or a story that
  appears on one sheet but not the other.

### Step 5 — adjust and rebuild

If a number looks wrong, **edit the spec JSON, not the spreadsheet**:

```powershell
cr-tool build workspaces\SLADCYBQSK-42132\output\SLADCYBQSK-42132_cr_spec.json
```

Rebuild takes under a second. Or just tell Copilot *"make row 3 MS Medium
instead of Complex and rebuild"*.

Editing the `.xlsx` by hand works, but the next rebuild overwrites it, and the
spec stops being the record of what you decided. Keep the spec as the truth.

### Step 6 — send it

`workspaces\SLADCYBQSK-42132\output\SLADCYBQSK-42132-CR-Estimation.xlsx`

Open it in Excel once before sending. Excel recalculates every formula on open.

---

## A second CR

Just step 1 again with a new key. Nothing else to set up:

```powershell
cr-tool init workspaces\SLADCYBQSK-42528 --key SLADCYBQSK-42528
```

---

## If prompt files are not available

The prompt files are ordinary Markdown. Open
`.github/prompts/generate-cr.prompt.md`, copy everything below the `---` header,
paste it into Copilot Chat, and add *"The workspace is
workspaces/SLADCYBQSK-42132"*. Same result, one extra paste.

## If you are not using VS Code

The tool is a plain CLI and does not need Copilot at all. Write the spec JSON
yourself against `schema/cr_spec.schema.json` (start from
`examples/starter_cr_spec.json`, and read `docs/estimation-rules.md` for how to
choose the values), then run `cr-tool build`. Copilot only automates the
analysis and the typing.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `cr-tool: command not found` | venv not active | `.\.venv\Scripts\Activate.ps1` |
| `/generate-cr` does not appear in chat | wrong folder open, or `chat.promptFiles` off | open the `CR` folder itself as the workspace root; check the setting |
| Copilot ignores the weights and invents its own | you opened a subfolder, not the repo root | `.github/` must sit directly in the open folder |
| Copilot edits the `.xlsx` directly | it drifted from the prompt | tell it to go through `cr-tool build`; the spec JSON is the input |
| `SPEC ERROR: ... is not a valid option` | a scope size or reusability level was mistyped | the message lists the valid values |
| Figma PDF pages are not being read | PDFs are not images | `cr-tool inventory <dir> --split-pdf` to turn pages into PNGs |
| Numbers differ from a colleague's sheet | they used the older Complex=4 weight | ver. 2 uses Complex=5; `cr-tool rules` prints the current set |
