"""Task 2: Comparator. Owner: Person B.

Compares the two KDE YAML files written by Task 1 and saves the differences in
element names and in element requirements as two TEXT files.
"""

import os
import sys

import yaml

NO_NAME_DIFF = "NO DIFFERENCES IN REGARDS TO ELEMENT NAMES"
NO_REQ_DIFF = "NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS"

NAMES_FILE = "element_name_differences.txt"
REQS_FILE = "element_requirement_differences.txt"


# ---------------------------------------------------------------- function 1

def load_yaml_files(yaml_path_1, yaml_path_2):
    """Validate and load both KDE YAML files, return (dict_1, dict_2)."""
    return _read_yaml(yaml_path_1), _read_yaml(yaml_path_2)


def _read_yaml(yaml_path):
    if not isinstance(yaml_path, (str, os.PathLike)) or str(yaml_path).strip() == "":
        raise ValueError("YAML path must be a non-empty string")
    yaml_path = str(yaml_path)
    if not yaml_path.lower().endswith((".yaml", ".yml")):
        raise ValueError(f"Not a .yaml file: {yaml_path}")
    if not os.path.isfile(yaml_path):
        raise FileNotFoundError(f"File not found: {yaml_path}")
    if os.path.getsize(yaml_path) == 0:
        raise ValueError(f"File is empty: {yaml_path}")
    try:
        with open(yaml_path, encoding="utf-8") as f:
            kdes = yaml.safe_load(f)
    except (yaml.YAMLError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read YAML {yaml_path}: {error}") from error
    try:
        _check_kdes(kdes)
    except ValueError as error:
        raise ValueError(f"{yaml_path}: {error}") from error
    return kdes


def _check_kdes(kdes):
    """Raise ValueError unless kdes is {element: {"name": str, "requirements": [str, ...]}}."""
    if not isinstance(kdes, dict):
        raise ValueError("KDEs must be a dictionary of elements")
    for key, element in kdes.items():
        if not isinstance(element, dict):
            raise ValueError(f"{key} must have a name and requirements")
        name, requirements = element.get("name"), element.get("requirements")
        if not isinstance(name, str) or name.strip() == "":
            raise ValueError(f"{key} must have a non-empty name")
        if not isinstance(requirements, list):
            raise ValueError(f"{key} must have a list of requirements")
        if not all(isinstance(r, str) and r.strip() for r in requirements):
            raise ValueError(f"{key} has a requirement that is not a non-empty string")


# ------------------------------------------------------------ functions 2-3

def compare_element_names(kdes_1, kdes_2, output_path):
    """Write element names that differ between the two files (or NO_NAME_DIFF)."""
    index_1, index_2 = _index_kdes(kdes_1), _index_kdes(kdes_2)
    differences = [name for key, (name, _) in index_1.items() if key not in index_2]
    differences += [name for key, (name, _) in index_2.items() if key not in index_1]
    return _write_lines(differences or [NO_NAME_DIFF], output_path)


def compare_element_requirements(kdes_1, kdes_2, output_path):
    """Write NAME,REQU lines for requirements that differ (or NO_REQ_DIFF).

    A requirement differs if its element has it in only one of the two files, so
    every requirement of an element that is missing from one file is listed.
    """
    index_1, index_2 = _index_kdes(kdes_1), _index_kdes(kdes_2)
    differences = []
    for key in {**index_1, **index_2}:  # elements of file 1, then the new ones in file 2
        name_1, reqs_1 = index_1.get(key, (None, {}))
        name_2, reqs_2 = index_2.get(key, (None, {}))
        name = name_1 or name_2
        differences += [f"{name},{text}" for req, text in reqs_1.items() if req not in reqs_2]
        differences += [f"{name},{text}" for req, text in reqs_2.items() if req not in reqs_1]
    return _write_lines(differences or [NO_REQ_DIFF], output_path)


def _index_kdes(kdes):
    """Return {name key: (name, {requirement key: requirement})}.

    Keys ignore case and spacing, like the extractor does when it merges names.
    """
    _check_kdes(kdes)
    index = {}
    for element in kdes.values():
        name = _one_line(element["name"])
        _, requirements = index.setdefault(name.lower(), (name, {}))
        for requirement in map(_one_line, element["requirements"]):
            requirements.setdefault(requirement.lower(), requirement)
    return index


def _one_line(text):
    return " ".join(text.split())


def _write_lines(lines, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return output_path


# ------------------------------------------------------------------- runner

def run(yaml_path_1, yaml_path_2, output_dir="outputs"):
    """Run Task 2 on two YAML files. Returns the paths of the two TEXT files."""
    kdes_1, kdes_2 = load_yaml_files(yaml_path_1, yaml_path_2)
    return [
        compare_element_names(kdes_1, kdes_2, os.path.join(output_dir, NAMES_FILE)),
        compare_element_requirements(kdes_1, kdes_2, os.path.join(output_dir, REQS_FILE)),
    ]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python comparator.py <first-kdes.yaml> <second-kdes.yaml>")
        sys.exit(1)
    print(run(sys.argv[1], sys.argv[2]))
