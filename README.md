# COMP 5700 Project – Security Requirements Change Detector

## Team

| Name | BannerID | Auburn email |
|---|---|---|
| TODO | TODO | TODO@auburn.edu |
| TODO | TODO | TODO@auburn.edu |
| TODO | TODO | TODO@auburn.edu |

## LLM used

**Gemma-3-1B** (`google/gemma-3-1b-it`), via Hugging Face `transformers`.

## Project overview

The tool takes two Docker CIS benchmark PDFs, finds what changed between them, and runs Hadolint on a set of Dockerfiles based on those changes.

```
two PDFs ──► Task 1: Extractor ──► two KDE YAML files
                                         │
                                         ▼
                 Task 2: Comparator ──► two TEXT files (name / requirement differences)
                                         │
                                         ▼
                 Task 3: Executor ───► Hadolint rules TEXT file ──► Hadolint scan ──► CSV
```

| File | Task | What it does |
|---|---|---|
| `extractor.py` | Task 1 | Validates the PDFs, builds zero-shot / few-shot / chain-of-thought prompts, runs Gemma-3-1B to extract key data elements (KDEs), saves `<doc>-kdes.yaml` and an LLM output log |
| `comparator.py` | Task 2 | Compares the two YAML files by element name and by requirements, writes two TEXT files |
| `executor.py` | Task 3 | Maps the differences to Hadolint rules, runs Hadolint on the Dockerfiles, writes `hadolint_results.csv` |
| `main.py` | – | Runs Tasks 1 → 2 → 3 for two PDFs (entry point for the PyInstaller binary) |
| `PROMPT.md` | Task 1 | The zero-shot, few-shot and chain-of-thought prompts |
| `tests/` | – | One test per function (13 total), run by GitHub Actions |
| `outputs/` | – | Generated YAML, TEXT and CSV files |

### Output formats

- **KDE YAML** (`outputs/<doc>-kdes.yaml`, e.g. `docker-cis-v0-kdes.yaml`):
  ```yaml
  element1:
    name: container user
    requirements:
      - Ensure that a user for the container has been created
  ```
- **Task 2:** `element_name_differences.txt` (one name per line, or `NO DIFFERENCES IN REGARDS TO ELEMENT NAMES`) and `element_requirement_differences.txt` (`NAME,REQU` per line, or `NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS`).
- **Task 3:** `hadolint_rules.txt` (`NO DIFFERENCES FOUND`, `NO MAPPING FOUND`, or one rule ID per line such as `DL3002`) and `hadolint_results.csv` with headers `FilePath,DefaultSeverity,RULEID,COUNT`.

## Getting started on a new machine

### 1. Prerequisites

- Python 3.10 or newer
- Git
- [Hadolint](https://github.com/hadolint/hadolint/releases) on your `PATH` (check with `hadolint --version`)
  - Windows: download `hadolint-Windows-x86_64.exe`, rename it to `hadolint.exe`, and put it in a folder on your `PATH`
  - macOS: `brew install hadolint`
  - Linux: download `hadolint-Linux-x86_64`, rename it to `hadolint`, `chmod +x` it, and move it to `/usr/local/bin`
- A Hugging Face account with access to Gemma-3: open https://huggingface.co/google/gemma-3-1b-it and accept the license

### 2. Clone and create a virtual environment

```bash
git clone <repo-url>
cd comp5700-project
python3 -m venv comp5700-venv
```

Activate it:

```bash
source comp5700-venv/bin/activate        # macOS / Linux / Git Bash
comp5700-venv\Scripts\activate           # Windows cmd / PowerShell
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Log in to Hugging Face (needed once, to download Gemma)

```bash
hf auth login
```

Paste an access token from https://huggingface.co/settings/tokens (read access is enough). The model downloads on the first run.

### 5. Get the input files

- Put `docker-cis-v0.pdf`, `docker-cis-v1.pdf`, `docker-cis-v2.pdf` in the project folder (they are not stored in the repo).
- Unzip the Dockerfile dataset (`dockerfiles.zip`) into a `dockerfiles/` folder in the project (not stored in the repo).

### 6. Run the tests

```bash
pytest
```

The tests do not download Gemma or need the Dockerfiles; they use small sample files in `tests/fixtures/`.

### 7. Run the project

```bash
python main.py docker-cis-v0.pdf docker-cis-v1.pdf
```

Results are written to `outputs/`.

## Building and running the binary

```bash
pyinstaller --onefile main.py
./dist/main docker-cis-v0.pdf docker-cis-v1.pdf          # macOS / Linux
dist\main.exe docker-cis-v0.pdf docker-cis-v1.pdf        # Windows
```

Input pairs used for grading:

| Input | Documents |
|---|---|
| Input-1 | docker-cis-v0.pdf, docker-cis-v1.pdf |
| Input-2 | docker-cis-v0.pdf, docker-cis-v2.pdf |
| Input-3 | docker-cis-v1.pdf, docker-cis-v2.pdf |
| Input-4 | docker-cis-v1.pdf, docker-cis-v1.pdf |
| Input-5 | docker-cis-v2.pdf, docker-cis-v2.pdf |

## GitHub Actions

`.github/workflows/tests.yml` runs `pytest` on every push and pull request. GitHub Actions cannot detect a local `git pull`, so it runs on push and pull request instead: whatever a contributor pulls has already been tested.

## Team workflow

- Work on a feature branch (`feature/extractor`, `feature/comparator`, `feature/executor`) and open a pull request into `main`.
- Do not change the output formats above without telling the team: the other tasks depend on them.
