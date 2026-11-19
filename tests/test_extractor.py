"""Task 1 tests: one test per extractor function. Gemma is replaced by a fake generator."""

import os

import pytest
import yaml

import extractor


def make_pdf(path, text):
    """Write a minimal one-page PDF containing `text`."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(path, "wb") as f:
        f.write(out)


SAMPLE_TEXT = "4.1 Ensure that a user for the container has been created"


def test_load_documents(tmp_path):
    pdf_1 = tmp_path / "doc-a.pdf"
    pdf_2 = tmp_path / "doc-b.pdf"
    make_pdf(pdf_1, SAMPLE_TEXT)
    make_pdf(pdf_2, "4.9 Ensure that COPY is used instead of ADD in Dockerfiles")
    text_1, text_2 = extractor.load_documents(str(pdf_1), str(pdf_2))
    assert "user for the container" in text_1
    assert "COPY is used instead of ADD" in text_2

    not_pdf = tmp_path / "notes.txt"
    not_pdf.write_text("hello")
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_text("this is not a pdf")
    with pytest.raises(FileNotFoundError):
        extractor.load_documents(str(tmp_path / "missing.pdf"), str(pdf_2))
    with pytest.raises(ValueError):
        extractor.load_documents(str(not_pdf), str(pdf_2))
    with pytest.raises(ValueError):
        extractor.load_documents(str(pdf_1), str(fake_pdf))


def test_build_zero_shot_prompt():
    prompt = extractor.build_zero_shot_prompt(SAMPLE_TEXT)
    assert isinstance(prompt, str)
    assert SAMPLE_TEXT in prompt
    assert "requirements:" in prompt
    with pytest.raises(ValueError):
        extractor.build_zero_shot_prompt("")


def test_build_few_shot_prompt():
    prompt = extractor.build_few_shot_prompt(SAMPLE_TEXT)
    assert isinstance(prompt, str)
    assert SAMPLE_TEXT in prompt
    assert "Example answer:" in prompt
    with pytest.raises(ValueError):
        extractor.build_few_shot_prompt("   ")


def test_build_chain_of_thought_prompt():
    prompt = extractor.build_chain_of_thought_prompt(SAMPLE_TEXT)
    assert isinstance(prompt, str)
    assert SAMPLE_TEXT in prompt
    assert "step by step" in prompt
    assert "FINAL ANSWER:" in prompt
    with pytest.raises(ValueError):
        extractor.build_chain_of_thought_prompt(None)


def test_extract_kdes(tmp_path):
    def fake_gemma(prompt):
        return (
            "Step 1: ...\nFINAL ANSWER:\n```yaml\n"
            "element1:\n  name: container user\n  requirements:\n"
            "    - Ensure that a user for the container has been created\n"
            "    - 4.1\n"                                      # junk: only a section number
            "    - Ensure that the moon is made of cheese\n```"  # made up: not in the document
        )

    kdes, records = extractor.extract_kdes(SAMPLE_TEXT, "docker-cis-test", str(tmp_path), generator=fake_gemma)

    assert kdes == {"element1": {"name": "container user",
                                 "requirements": ["Ensure that a user for the container has been created"]}}
    assert [r["prompt_type"] for r in records] == ["zero-shot", "few-shot", "chain-of-thought"]
    yaml_path = tmp_path / "docker-cis-test-kdes.yaml"
    assert yaml_path.exists()
    assert yaml.safe_load(yaml_path.read_text()) == kdes


def test_dump_llm_outputs(tmp_path):
    records = [{"llm_name": extractor.MODEL_NAME, "prompt": "PROMPT TEXT",
                "prompt_type": "zero-shot", "output": "OUTPUT TEXT"}]
    out_path = tmp_path / "llm-outputs.txt"
    extractor.dump_llm_outputs(records, str(out_path))
    content = out_path.read_text()
    for expected in ["*LLM Name*\ngoogle/gemma-3-1b-it", "*Prompt Used*\nPROMPT TEXT",
                     "*Prompt Type*\nzero-shot", "*LLM Output*\nOUTPUT TEXT"]:
        assert expected in content
    assert content.index("*LLM Name*") < content.index("*Prompt Used*") < content.index("*Prompt Type*") < content.index("*LLM Output*")
