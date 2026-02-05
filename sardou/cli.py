import argparse
import sys
import glob
from pathlib import Path
from sardou import Sardou

def main():
    parser = argparse.ArgumentParser(
        description="Sardou - TOSCA template parser and processor"
    )
    parser.add_argument(
        "path",
        type=str,
        nargs="+",
        help="Path(s) to TOSCA template file(s), supports glob patterns"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Expand glob patterns and collect all files
    files = []
    for path_pattern in args.path:
        expanded = glob.glob(path_pattern)
        if expanded:
            files.extend(expanded)
        else:
            # If glob returns nothing, treat as literal path
            files.append(path_pattern)
    
    if not files:
        print("Error: No files found matching the given path(s)", file=sys.stderr)
        sys.exit(1)
    
    # Process each file
    for file_path in files:
        target_path = Path(file_path).resolve()
        if not target_path.exists():
            print(f"Error: Path does not exist: {file_path}", file=sys.stderr)
            sys.exit(1)
        
        if args.verbose:
            print(f"Parsing TOSCA template: {target_path}")
        
        try:
            tpl = Sardou(str(target_path))
            
            if args.verbose:
                print("Successfully parsed TOSCA template")
        except Exception as e:
            print(f"Error parsing TOSCA template: {e}", file=sys.stderr)
            sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()