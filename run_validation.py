import sys
from pathlib import Path

from floria.validation import validate_template

def main():
    templates_dir = Path("templates")
    yaml_files = list(templates_dir.rglob("*.yaml")) # finds all YAML files inside subfolders

    if not yaml_files:
        print("No YAML files found under templates/")
        sys.exit(0)

    success, fail = 0, 0
    for file in yaml_files:
        print(f"\nProcessing {file}...\n")
        if validate_template(file):
            success += 1
        else:
            fail += 1

    print("============================")
    print(f"{success} Successful")
    print(f"{fail} Failed")
    print("============================")

    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()