"""Task 1: Extractor. Owner: Person A."""

MODEL_NAME = "google/gemma-3-1b-it"


def load_documents(pdf_path_1, pdf_path_2):
    """Validate both PDFs and return (text_1, text_2)."""
    raise NotImplementedError


def build_zero_shot_prompt(document_text):
    """Return a zero-shot prompt (str) asking for KDEs in the document."""
    raise NotImplementedError


def build_few_shot_prompt(document_text):
    """Return a few-shot prompt (str) asking for KDEs in the document."""
    raise NotImplementedError


def build_chain_of_thought_prompt(document_text):
    """Return a chain-of-thought prompt (str) asking for KDEs in the document."""
    raise NotImplementedError


def extract_kdes(document_text, prompt_type, document_name, output_dir="outputs"):
    """Run Gemma-3-1B with the chosen prompt, save <document_name>-kdes.yaml, return the dict."""
    raise NotImplementedError


def dump_llm_outputs(records, output_path):
    """Write all LLM runs to a TEXT file in the required format."""
    raise NotImplementedError
