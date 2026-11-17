"""Task 3: Executor. Owner: Person C."""

NO_DIFFERENCES = "NO DIFFERENCES FOUND"
NO_MAPPING = "NO MAPPING FOUND"
CSV_HEADERS = ["FilePath", "DefaultSeverity", "RULEID", "COUNT"]


def load_text_files(names_txt_path, reqs_txt_path):
    """Validate and read both Task 2 TEXT files, return (names_text, reqs_text)."""
    raise NotImplementedError


def map_differences_to_rules(names_text, reqs_text, output_path):
    """Write NO_DIFFERENCES, NO_MAPPING, or matching Hadolint rule IDs (one per line)."""
    raise NotImplementedError


def run_hadolint(rules_txt_path, dockerfiles_dir):
    """Run Hadolint on the Dockerfiles based on the rules file, return a pandas DataFrame."""
    raise NotImplementedError


def write_csv(results_df, output_path):
    """Write a CSV with CSV_HEADERS from the Hadolint results."""
    raise NotImplementedError
