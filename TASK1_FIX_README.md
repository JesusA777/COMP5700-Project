# Why Task 1 was changed

Task 1 (`extractor.py`) ran and produced valid YAML, and Task 2 worked with it. Testing Task 2 on that
YAML showed that many of the reported differences were not real: some requirements were cut off and
others never reached the YAML. The fix makes the Task 1 output complete, so that Tasks 2 and 3 compare
what the PDFs actually say.

The output formats in `README.md` and the functions' names and parameters did not change.
Task 2's code did not need to change either.

## Problems found

| # | Problem | Cause | Example |
|---|---|---|---|
| 1 | Requirements were cut off | The PDF text was read one line at a time, so the rest of a wrapped title was lost | v0 3.16 ended at `...permissions are set to 660`, without `or more restrictively` |
| 2 | Requirements were missing from the YAML | With around 30 titles per prompt, Gemma often answered with section numbers (`4.1`) or repeated itself, and those answers were discarded | `Ensure secrets are not stored in Dockerfiles` was in the v0 and v2 YAML but not in v1's, although it is in all three PDFs |
| 3 | Recommendation 2.1 was skipped | Titles had to start with certain words, and `Run` was not one of them | `Run the Docker daemon as a non-root user, if possible` |
| 4 | Text that is not a requirement was included | CIS Controls references and page numbers were treated as part of the titles | `16.7 Use Standard Hardening Configuration Templates for`, `/var/lib/docker 23` |
| 5 | Some answers could match the wrong title | The closest title was always accepted, even if several were about as close | A generic `Ensure auditing is configured for Docker files and directories` could match any of the auditing titles |

## Why it matters

- **Task 2:** a requirement that is cut off in one YAML file but not in the other is reported as a difference.
- **Task 3:** a requirement that is missing from one YAML file looks like a change, so it could be mapped
  to a Hadolint rule although nothing changed.

## What was changed

| # | Fix in `extractor.py` |
|---|---|
| 1, 3, 4 | A title is now read up to `(Manual)` or `(Automated)`, over several lines if needed. Only real recommendations have these marks. |
| 2 | Gemma gets at most 8 titles at a time, without section numbers. Titles it leaves out are asked about again, one at a time. If it still leaves one out, a warning is logged. |
| 2 | Titles are grouped by section, so sections that did not change get the same prompts for every document. |
| 5 | An answer is only matched if it is clear which title it means and its values (`660`, `root:root`, `/etc/docker`) agree. |

Also changed: the section numbers were removed from the few-shot example (`extractor.py` and `PROMPT.md`),
`test_extract_kdes` covers the cases above, and the YAML files and LLM logs in `outputs/` were regenerated
with Gemma-3-1B.

## Results

| | v0 | v1 | v2 |
|---|---|---|---|
| Recommendations in the PDF | 117 | 117 | 118 |
| Distinct requirements in the YAML, before | 53 | 75 | 87 |
| Distinct requirements in the YAML, after | 117 | 117 | 118 |

| Task 2 comparison | Name differences | Requirement differences |
|---|---|---|
| v0 and v1 | 89 → 9 | 165 → 46 |
| v0 and v2 | 95 → 26 | 184 → 113 |
| v1 and v2 | 96 → 17 | 155 → 67 |
| Same document twice (v1, v2) | no differences | no differences |

The titles in the PDFs differ only as follows:

- v0 to v1: 1.1.9 changes from `docker.socket` to `docker.sock`
- v1 to v2: `Ensure devicemapper storage driver is not used` is added

## Known limits

- **Extra differences remain.** When one title changes, Gemma may rename and regroup the other titles in the
  same prompt. Its names and groups are kept as they are, and some of them are questionable.
- **Task 1 is slower.** It makes at least 54 Gemma calls per document (before: 12 to 15). On a laptop CPU, v0
  took about 63 minutes.
- **Saved answers were reused.** When the outputs were generated, a prompt that occurs in more than one document
  was run once and its answer reused. One prompt of each type was run again to check this, and the answers were
  identical.
- **Library versions.** The outputs were generated with PyTorch 2.14.0 (CPU) and PyYAML 6.0.3, not the versions
  in `requirements.txt` (2.13.0 and 6.0.2).
