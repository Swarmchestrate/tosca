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
