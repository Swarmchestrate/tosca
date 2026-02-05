import argparse
import sys
from pathlib import Path
from sardou import Sardou

def main():
    parser = argparse.ArgumentParser(
        description="Sardou - TOSCA template parser and processor"
    )
    parser.add_argument(
        "path",
        type=str,
        help="Path to the TOSCA template file"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print(f"Parsing TOSCA template: {target_path}")
    
    try:
        Sardou(str(target_path))
        
        if args.verbose:
            print("Successfully parsed TOSCA template")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"Error parsing TOSCA template: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()