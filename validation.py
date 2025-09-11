import subprocess
import sys
from pathlib import Path

PUCCINI_CMD = "/usr/bin/puccini-tosca"
PUCCINI_FLAGS = ["-x", "data_types.string.permissive"]


def validate_template(file_path: Path) -> bool:
   # will run the puccini-tosca parse <with flag>
    try:
        result = subprocess.run(
            [PUCCINI_CMD, "parse", str(file_path)] + PUCCINI_FLAGS,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"Processed successfully: {file_path} \n")
            return True
        else:
            print(f"Failed to process: {file_path} \n")
            print("==== Error Output ====")
            print(result.stderr.strip() or result.stdout.strip())
            print("======================")
            return False
    
    except FileNotFoundError:
        print(f"Puccini not found at {PUCCINI_CMD}. Please install it first.")
        sys.exit(1)


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