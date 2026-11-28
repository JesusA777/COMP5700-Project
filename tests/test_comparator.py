"""Task 2 tests: one test per comparator function."""

import os

import pytest

import comparator

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_A = os.path.join(FIXTURES, "sample-a-kdes.yaml")
SAMPLE_B = os.path.join(FIXTURES, "sample-b-kdes.yaml")


def read_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


def make_kdes(*elements):
    """Build a KDE dictionary from (name, [requirements]) pairs."""
    return {f"element{i}": {"name": name, "requirements": requirements}
            for i, (name, requirements) in enumerate(elements, start=1)}


def test_load_yaml_files(tmp_path):
    kdes_1, kdes_2 = comparator.load_yaml_files(SAMPLE_A, SAMPLE_B)
    assert kdes_1["element2"] == {"name": "add instruction",
                                  "requirements": ["Ensure that COPY is used instead of ADD in Dockerfiles"]}
    assert len(kdes_2["element1"]["requirements"]) == 2

    with pytest.raises(FileNotFoundError):
        comparator.load_yaml_files(SAMPLE_A, str(tmp_path / "missing.yaml"))
    with pytest.raises(ValueError):
        comparator.load_yaml_files("", SAMPLE_B)
    not_yaml = tmp_path / "notes.txt"
    not_yaml.write_text("element1: {name: a, requirements: [b]}")
    with pytest.raises(ValueError):
        comparator.load_yaml_files(str(not_yaml), SAMPLE_B)

    bad_contents = [
        "",                                            # empty file
        "element1: [unclosed",                         # broken YAML
        "- a\n- b\n",                                  # not a dictionary
        "element1: text\n",                            # element is not a dictionary
        "element1: {requirements: [b]}\n",             # no name
        "element1: {name: a}\n",                       # no requirements
        "element1: {name: a, requirements: b}\n",      # requirements is not a list
        "element1: {name: a, requirements: [4.1]}\n",  # requirement is not a string
    ]
    bad_yaml = tmp_path / "bad.yaml"
    for content in bad_contents:
        bad_yaml.write_text(content)
        with pytest.raises(ValueError):
            comparator.load_yaml_files(SAMPLE_A, str(bad_yaml))


def test_compare_element_names(tmp_path):
    out_path = tmp_path / "new-folder" / "names.txt"
    kdes_1, kdes_2 = comparator.load_yaml_files(SAMPLE_A, SAMPLE_B)

    assert comparator.compare_element_names(kdes_1, kdes_2, str(out_path)) == str(out_path)
    assert out_path.read_text() == read_fixture("element_name_differences.txt")

    # The same document, and names that differ only in order, case or spacing, are not differences.
    comparator.compare_element_names(kdes_1, kdes_1, str(out_path))
    assert out_path.read_text() == comparator.NO_NAME_DIFF + "\n"
    comparator.compare_element_names(make_kdes(("Docker Socket", ["r1"]), ("image sprawl", ["r2"])),
                                     make_kdes(("image  sprawl", ["r2"]), ("docker socket", ["r1"])), str(out_path))
    assert out_path.read_text() == comparator.NO_NAME_DIFF + "\n"

    with pytest.raises(ValueError):
        comparator.compare_element_names(None, kdes_2, str(out_path))


def test_compare_element_requirements(tmp_path):
    out_path = tmp_path / "new-folder" / "requirements.txt"
    kdes_1, kdes_2 = comparator.load_yaml_files(SAMPLE_A, SAMPLE_B)

    assert comparator.compare_element_requirements(kdes_1, kdes_2, str(out_path)) == str(out_path)
    assert out_path.read_text() == read_fixture("element_requirement_differences.txt")

    # The same document, and requirements that differ only in order, case or spacing, are not differences.
    comparator.compare_element_requirements(kdes_1, kdes_1, str(out_path))
    assert out_path.read_text() == comparator.NO_REQ_DIFF + "\n"
    comparator.compare_element_requirements(make_kdes(("Docker Socket", ["Ensure A", "Ensure B"])),
                                            make_kdes(("docker socket", ["ensure b", "Ensure  A"])), str(out_path))
    assert out_path.read_text() == comparator.NO_REQ_DIFF + "\n"

    # A changed requirement is listed once for each document; a moved one is listed under both names.
    comparator.compare_element_requirements(make_kdes(("socket", ["old text"]), ("image", ["moved"])),
                                            make_kdes(("socket", ["new text", "moved"])), str(out_path))
    assert out_path.read_text().splitlines() == ["socket,old text", "socket,new text", "socket,moved", "image,moved"]

    with pytest.raises(ValueError):
        comparator.compare_element_requirements(kdes_1, ["not", "kdes"], str(out_path))
