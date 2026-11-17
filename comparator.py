"""Task 2: Comparator. Owner: Person B."""

NO_NAME_DIFF = "NO DIFFERENCES IN REGARDS TO ELEMENT NAMES"
NO_REQ_DIFF = "NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS"


def load_yaml_files(yaml_path_1, yaml_path_2):
    """Validate and load both KDE YAML files, return (dict_1, dict_2)."""
    raise NotImplementedError


def compare_element_names(kdes_1, kdes_2, output_path):
    """Write element names that differ between the two files (or NO_NAME_DIFF)."""
    raise NotImplementedError


def compare_element_requirements(kdes_1, kdes_2, output_path):
    """Write NAME,REQU lines for requirements that differ (or NO_REQ_DIFF)."""
    raise NotImplementedError
