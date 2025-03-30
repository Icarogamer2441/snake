"""
Command-line interface for the Snake language.
"""

import sys
import os
import argparse
from typing import List, Optional

from .parser import parse_snake, SnakeSyntaxError, validate_types
from .transformer import transform_to_python


def run_snake_file(file_path: str, check_only: bool = False, output_file: Optional[str] = None) -> int:
    """
    Run a Snake file by parsing it, transforming it to Python, and executing it.
    
    Args:
        file_path: Path to the Snake file
        check_only: If True, only check for syntax and type errors without running
        output_file: If provided, save the generated Python code to this file
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Read the file
        with open(file_path, 'r') as f:
            source_code = f.read()
        
        # Parse the Snake code - pass the file path for import resolution
        try:
            python_ast, type_annotations = parse_snake(source_code, file_path)
        except SnakeSyntaxError as e:
            print(f"Compilation error: {e}", file=sys.stderr)
            return 1
        
        # Validate types
        type_errors = validate_types(python_ast, type_annotations)
        if type_errors:
            for error in type_errors:
                print(f"Type error: {error}", file=sys.stderr)
            return 1
        
        # Transform to Python
        python_code = transform_to_python(python_ast, type_annotations)
        
        # Save the Python code to the output file if specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(python_code)
            print(f"Generated Python code saved to {output_file}")
            if check_only:
                return 0
        
        if check_only:
            print(f"No errors found in {file_path}")
            return 0
        
        # Execute the Python code
        code_obj = compile(python_code, file_path, 'exec')
        
        # Create a new namespace for execution
        namespace = {}
        
        # Execute the code
        exec(code_obj, namespace)
        
        return 0
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the Snake CLI.
    
    Args:
        args: Command-line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code
    """
    if args is None:
        args = sys.argv[1:]
    
    # Create a parser that captures only the known arguments
    parser = argparse.ArgumentParser(description="Snake programming language")
    parser.add_argument("file", help="Snake source file to run")
    parser.add_argument("--check", action="store_true", help="Check for errors without running")
    parser.add_argument("--version", action="store_true", help="Show version information")
    parser.add_argument("-o", "--output", help="Save the generated Python code to the specified file")
    
    # Parse known arguments, leaving the rest for the Snake script
    parsed_args, script_args = parser.parse_known_args(args)
    
    # Show version and exit
    if parsed_args.version:
        from . import __version__
        print(f"Snake version {__version__}")
        return 0
    
    # Save the original sys.argv
    original_argv = sys.argv.copy()
    
    try:
        # Set sys.argv to the script name and its arguments
        sys.argv = [parsed_args.file] + script_args
        
        # Run the file
        return run_snake_file(parsed_args.file, parsed_args.check, parsed_args.output)
    finally:
        # Restore the original sys.argv
        sys.argv = original_argv


if __name__ == "__main__":
    sys.exit(main())
