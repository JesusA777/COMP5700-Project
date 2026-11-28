"""Task 1: Extractor. Owner: Person A.

Reads two CIS benchmark PDFs, asks Gemma-3-1B to find key data elements (KDEs)
with zero-shot, few-shot and chain-of-thought prompts, and saves one YAML file
per document plus a TEXT log of every LLM call.
"""

import difflib
import logging
import os
import re
import sys

import yaml
from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)  # the CIS PDFs trigger harmless xref warnings

logger = logging.getLogger(__name__)

MODEL_NAME = "google/gemma-3-1b-it"
PROMPT_TYPES = ["zero-shot", "few-shot", "chain-of-thought"]
MAX_CHUNK_CHARS = 2000  # chunk size for documents without CIS recommendation titles
MAX_CHUNK_TITLES = 8    # the 1B model skips titles or loops when it gets longer lists
MAX_NEW_TOKENS = 1024

OUTPUT_FORMAT = """element1:
  name: <short name of the key data element>
  requirements:
    - <requirement text>
    - <requirement text>
element2:
  name: <short name of the key data element>
  requirements:
    - <requirement text>"""

ZERO_SHOT_TEMPLATE = """You are a security analyst. Read the security requirements document below and identify its key data elements.
A key data element is a configuration item, component or setting that the requirements talk about (for example: container user, image, port, log file).
One key data element can map to several requirements.

Answer only with YAML in exactly this format and nothing else:
{output_format}

Document:
{document_text}"""

FEW_SHOT_TEMPLATE = """You are a security analyst. Identify the key data elements in a security requirements document.
A key data element is a configuration item, component or setting that the requirements talk about.
One key data element can map to several requirements.

Example document:
Ensure that a user for the container has been created
Ensure that HEALTHCHECK instructions have been added to container images
Ensure that COPY is used instead of ADD in Dockerfiles
Ensure that privileged containers are not used
Ensure that the container is restricted from acquiring additional privileges

Example answer:
element1:
  name: container user
  requirements:
    - Ensure that a user for the container has been created
element2:
  name: healthcheck instruction
  requirements:
    - Ensure that HEALTHCHECK instructions have been added to container images
element3:
  name: copy instruction
  requirements:
    - Ensure that COPY is used instead of ADD in Dockerfiles
element4:
  name: container privileges
  requirements:
    - Ensure that privileged containers are not used
    - Ensure that the container is restricted from acquiring additional privileges

Now do the same for the document below. Answer only with YAML in the same format and nothing else.

Document:
{document_text}"""

CHAIN_OF_THOUGHT_TEMPLATE = """You are a security analyst. Identify the key data elements in the security requirements document below.
A key data element is a configuration item, component or setting that the requirements talk about.
One key data element can map to several requirements.

Think step by step:
Step 1: List every requirement in the document (lines such as "Ensure that ...").
Step 2: For each requirement, decide which configuration item, component or setting it is about.
Step 3: Group requirements that are about the same item under one key data element.
Step 4: Write the result as YAML in exactly this format:
{output_format}

After your reasoning, write the final YAML after a line that says FINAL ANSWER:

Document:
{document_text}"""

# A CIS recommendation is "4.1 Ensure that a user for the container has been created (Manual)".
# It can wrap over several lines. CIS Controls ("16.7 Use Standard ...") have no (Manual)/(Automated).
NUMBERED_LINE = re.compile(r"^(\d+(?:\.\d+)+)\s+\S")
ASSESSMENT = re.compile(r"\s*\((?:Manual|Automated)\)")
MAX_TITLE_LINES = 5
# Used only for documents that have no (Manual)/(Automated) marks.
REQUIREMENT_LINE = re.compile(r"^\s*\d+(\.\d+)+\s+(Ensure|Do not|Avoid|Use|Enable|Restrict|Verify|Configure|Set|Run)\b", re.IGNORECASE)

_generator = None


# ---------------------------------------------------------------- function 1

def load_documents(pdf_path_1, pdf_path_2):
    """Validate both PDFs and return (text_1, text_2)."""
    return _read_pdf(pdf_path_1), _read_pdf(pdf_path_2)


def _read_pdf(pdf_path):
    if not isinstance(pdf_path, (str, os.PathLike)) or str(pdf_path).strip() == "":
        raise ValueError("PDF path must be a non-empty string")
    pdf_path = str(pdf_path)
    if not pdf_path.lower().endswith(".pdf"):
        raise ValueError(f"Not a .pdf file: {pdf_path}")
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if os.path.getsize(pdf_path) == 0:
        raise ValueError(f"File is empty: {pdf_path}")
    with open(pdf_path, "rb") as f:
        if f.read(5) != b"%PDF-":
            raise ValueError(f"File is not a valid PDF: {pdf_path}")
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:
        raise ValueError(f"Could not read PDF {pdf_path}: {error}") from error
    if text.strip() == "":
        raise ValueError(f"No text found in PDF: {pdf_path}")
    return text


# ------------------------------------------------------------ functions 2-4

def _check_text(document_text):
    if not isinstance(document_text, str) or document_text.strip() == "":
        raise ValueError("Document text must be a non-empty string")


def build_zero_shot_prompt(document_text):
    """Return a zero-shot prompt (str) asking for KDEs in the document."""
    _check_text(document_text)
    return ZERO_SHOT_TEMPLATE.format(output_format=OUTPUT_FORMAT, document_text=document_text)


def build_few_shot_prompt(document_text):
    """Return a few-shot prompt (str) asking for KDEs in the document."""
    _check_text(document_text)
    return FEW_SHOT_TEMPLATE.format(document_text=document_text)


def build_chain_of_thought_prompt(document_text):
    """Return a chain-of-thought prompt (str) asking for KDEs in the document."""
    _check_text(document_text)
    return CHAIN_OF_THOUGHT_TEMPLATE.format(output_format=OUTPUT_FORMAT, document_text=document_text)


PROMPT_BUILDERS = {
    "zero-shot": build_zero_shot_prompt,
    "few-shot": build_few_shot_prompt,
    "chain-of-thought": build_chain_of_thought_prompt,
}


# ---------------------------------------------------------------- function 5

def extract_kdes(document_text, document_name, output_dir="outputs", prompt_types=None, generator=None):
    """Run Gemma-3-1B with each prompt type, save <document_name>-kdes.yaml.

    Returns (kdes, records): the nested KDE dictionary and one record per LLM call
    (used by dump_llm_outputs). `generator` is a function prompt -> text; it
    defaults to Gemma-3-1B and can be replaced in tests.
    """
    _check_text(document_text)
    if not isinstance(document_name, str) or document_name.strip() == "":
        raise ValueError("Document name must be a non-empty string")
    prompt_types = prompt_types or PROMPT_TYPES
    for prompt_type in prompt_types:
        if prompt_type not in PROMPT_BUILDERS:
            raise ValueError(f"Unknown prompt type: {prompt_type}")
    generator = generator or _gemma_generate

    merged = {}  # lower-case name -> {"name": ..., "requirements": [...]}
    records = []
    chunks = _chunk_text(document_text)
    for prompt_type in prompt_types:
        for chunk, titles in chunks:
            _extract_chunk(chunk, titles, prompt_type, generator, merged, records)

    # Ask again, one title at a time, about the titles the model left out.
    retry_type = "few-shot" if "few-shot" in prompt_types else prompt_types[0]
    all_titles = list(dict.fromkeys(title for _, titles in chunks for title in titles))
    for title in _missing_titles(all_titles, merged):
        _extract_chunk(title, [title], retry_type, generator, merged, records)
    missing = _missing_titles(all_titles, merged)
    if missing:
        logger.warning("%s: no key data element found for %d of %d requirements: %s",
                       document_name, len(missing), len(all_titles), "; ".join(missing))

    kdes = {f"element{i}": entry for i, entry in enumerate(merged.values(), start=1)}
    os.makedirs(output_dir, exist_ok=True)
    yaml_path = os.path.join(output_dir, f"{document_name}-kdes.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(kdes, f, sort_keys=False, allow_unicode=True)
    return kdes, records


def _extract_chunk(chunk, titles, prompt_type, generator, merged, records):
    """Run one prompt, add its record to `records` and its KDEs to `merged`."""
    prompt = PROMPT_BUILDERS[prompt_type](chunk)
    output = generator(prompt)
    records.append({
        "llm_name": MODEL_NAME,
        "prompt": prompt,
        "prompt_type": prompt_type,
        "output": output,
    })
    for element in _parse_llm_output(output):
        requirements = element["requirements"]
        if titles:
            requirements = [_match_title(r, titles, element["name"]) for r in requirements]
        requirements = [r for r in requirements if r]
        if not requirements:
            continue
        key = element["name"].lower()
        entry = merged.setdefault(key, {"name": element["name"], "requirements": []})
        for requirement in requirements:
            if requirement not in entry["requirements"]:
                entry["requirements"].append(requirement)


def _missing_titles(titles, merged):
    found = {requirement for entry in merged.values() for requirement in entry["requirements"]}
    return [title for title in titles if title not in found]


def _clean_requirement_line(line):
    """Strip table-of-contents dots/page numbers, (Manual)/(Automated), checklist marks."""
    line = re.sub(r"[^\x20-\x7e]", " ", line)       # odd PDF symbols
    line = re.sub(r"\s*\.{2,}.*$", "", line)          # "....... 15"
    line = re.sub(r"(\s*\.)+\s*\d*\s*$", "", line)    # ". 120" (spaced dots + page number)
    line = ASSESSMENT.sub("", line)
    line = re.sub(r"(\s+o)+\s*$", "", line)           # checklist boxes "o o"
    return re.sub(r"\s+", " ", line).strip()


def _join_wrapped_title(lines, start):
    """Return the title starting at lines[start], up to (Manual)/(Automated), or None if it isn't a recommendation."""
    title = lines[start]
    for line in lines[start + 1:start + MAX_TITLE_LINES]:
        if ASSESSMENT.search(title) or NUMBERED_LINE.match(line):
            break
        # "containerd-shim-" + "runc-v1" is one word, "directories -" + "/etc/docker" is not
        title += ("" if re.search(r"\w-$", title) else " ") + line
    if not ASSESSMENT.search(title):
        return None
    return _clean_requirement_line(ASSESSMENT.split(title)[0])


def _find_titles(document_text):
    """Return {section number: title} for the CIS recommendations in the document, in document order."""
    lines = [line.strip() for line in document_text.splitlines() if line.strip()]
    found = {}
    for i, line in enumerate(lines):
        match = NUMBERED_LINE.match(line)
        title = _join_wrapped_title(lines, i) if match else None
        if title:
            found.setdefault(match.group(1), SECTION_NUMBER.sub("", title))
    if not found:  # no (Manual)/(Automated) marks: use single lines, keep the longest per section number
        for line in lines:
            if REQUIREMENT_LINE.match(line):
                line = _clean_requirement_line(line)
                number, title = line.split()[0], SECTION_NUMBER.sub("", line)
                if len(title) > len(found.get(number, "")):
                    found[number] = title
    return found


def _chunk_text(document_text):
    """Split the document into model-sized (chunk, titles) pairs.

    If there are CIS recommendations, a chunk is a list of titles from one top-level
    section, so a change in one section does not change the prompts of the others.
    Section numbers are left out: the model tends to answer with them instead of the titles.
    """
    found = _find_titles(document_text)
    if found:
        sections = {}
        for number, title in found.items():
            sections.setdefault(number.split(".")[0], []).append(title)
        chunks = []
        for titles in sections.values():
            for i in range(0, len(titles), MAX_CHUNK_TITLES):
                part = titles[i:i + MAX_CHUNK_TITLES]
                chunks.append(("\n".join(part) + "\n", part))
        return chunks

    chunks, current = [], ""
    for line in (line.strip() for line in document_text.splitlines() if line.strip()):
        if current and len(current) + len(line) + 1 > MAX_CHUNK_CHARS:
            chunks.append((current, []))
            current = ""
        current += line + "\n"
    if current:
        chunks.append((current, []))
    return chunks


SECTION_NUMBER = re.compile(r"^\s*\d+(\.\d+)*\.?\s*")
MATCH_CUTOFF = 0.8
SINGLE_TITLE_CUTOFF = 0.6  # looser when only one title was asked about, as it can't be mistaken for another
MATCH_MARGIN = 0.02  # how much better than the second-best title a fuzzy match must be


def _specifics(text):
    """Values in a requirement that must not differ, such as 644, root:root, /etc/docker or docker.sock."""
    words = (word.strip(".-") for word in re.findall(r"[\w./:=-]+", text.lower()))
    return {word for word in words if re.search(r"[\d/:=]|\w\.\w", word)}


def _match_title(requirement, titles, element_name=""):
    """Map a requirement from the LLM to the closest real title in the chunk, or None if it isn't one."""
    requirement = SECTION_NUMBER.sub("", requirement).strip().rstrip(".").lower()
    if not requirement:
        return None
    for title in titles:
        if title.lower() == requirement:
            return title

    # A shared beginning ("Ensure auditing is configured for Docker files and directories") fits
    # several titles: only the element name ("docker.sock") can tell which one is meant.
    same_start = [title for title in titles if title.lower().startswith(requirement)]
    if len(same_start) > 1:
        named = [title for title in same_start if title.lower().endswith(" " + element_name.lower())]
        return named[0] if len(named) == 1 else None

    scored = sorted(((difflib.SequenceMatcher(None, title.lower(), requirement).ratio(), title) for title in titles),
                    reverse=True)
    cutoff = SINGLE_TITLE_CUTOFF if len(titles) == 1 else MATCH_CUTOFF
    if not scored or scored[0][0] < cutoff:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < MATCH_MARGIN:
        return None  # several titles fit equally well
    if not _specifics(requirement) <= _specifics(scored[0][1]):
        return None  # a different value, such as 644 instead of 660
    return scored[0][1]


def _parse_llm_output(output):
    """Read `name:` / `- requirement` lines from the model output. Tolerates broken YAML."""
    if "FINAL ANSWER:" in output:
        output = output.split("FINAL ANSWER:")[-1]
    elements, current = [], None
    for raw_line in output.splitlines():
        line = raw_line.strip().strip("`")
        if line.lower().startswith("name:"):
            name = line[5:].strip().strip("\"'")
            current = {"name": name, "requirements": []} if name else None
            if current:
                elements.append(current)
        elif line.startswith("- ") and current is not None:
            requirement = line[2:].strip().strip("\"'")
            if requirement:
                current["requirements"].append(requirement)
    return [element for element in elements if element["requirements"]]


def _gemma_generate(prompt):
    global _generator
    if _generator is None:
        from transformers import pipeline  # imported here so tests don't need to load torch
        _generator = pipeline("text-generation", model=MODEL_NAME, device_map="auto")
    messages = [{"role": "user", "content": prompt}]
    result = _generator(messages, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    return result[0]["generated_text"][-1]["content"]


# ---------------------------------------------------------------- function 6

def dump_llm_outputs(records, output_path):
    """Write all LLM runs to a TEXT file in the required format."""
    if not isinstance(records, list):
        raise ValueError("Records must be a list")
    required = ("llm_name", "prompt", "prompt_type", "output")
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            if not all(key in record for key in required):
                raise ValueError(f"Record is missing one of {required}")
            f.write("*LLM Name*\n" + record["llm_name"] + "\n")
            f.write("*Prompt Used*\n" + record["prompt"] + "\n")
            f.write("*Prompt Type*\n" + record["prompt_type"] + "\n")
            f.write("*LLM Output*\n" + record["output"] + "\n")
            f.write("\n" + "=" * 80 + "\n\n")
    return output_path


# ------------------------------------------------------------------- runner

def run(pdf_path_1, pdf_path_2, output_dir="outputs"):
    """Run Task 1 on two PDFs. Returns the paths of the two YAML files."""
    texts = load_documents(pdf_path_1, pdf_path_2)
    names = [os.path.splitext(os.path.basename(p))[0] for p in (pdf_path_1, pdf_path_2)]
    yaml_paths, all_records = [], []
    for text, name in zip(texts, names):
        _, records = extract_kdes(text, name, output_dir)
        all_records.extend(records)
        yaml_paths.append(os.path.join(output_dir, f"{name}-kdes.yaml"))
    dump_llm_outputs(all_records, os.path.join(output_dir, f"{names[0]}-{names[1]}-llm-outputs.txt"))
    return yaml_paths


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extractor.py <first.pdf> <second.pdf>")
        sys.exit(1)
    print(run(sys.argv[1], sys.argv[2]))
