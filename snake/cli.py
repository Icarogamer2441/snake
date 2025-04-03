"""
Command-line interface for the Snake language.
"""

import sys
import os
import argparse
import shutil
from pathlib import Path
from typing import List, Optional

from .parser import parse_snake, SnakeSyntaxError, validate_types
from .transformer import transform_to_python


def run_snake_file(file_path: str, check_only: bool = False, output_file: Optional[str] = None, verbose: bool = False) -> int:
    """
    Run a Snake file by parsing it, transforming it to Python, and executing it.
    
    Args:
        file_path: Path to the Snake file
        check_only: If True, only check for syntax and type errors without running
        output_file: If provided, save the generated Python code to this file
        verbose: If True, show the compiled Python code with line numbers
        
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
        
        # If verbose mode is enabled, display the compiled Python code with line numbers
        if verbose:
            print("\nCompiled Python code:")
            print("-------------------")
            lines = python_code.split('\n')
            for i, line in enumerate(lines, 1):
                print(f"{i:4d} | {line}")
            print("-------------------\n")
        
        # Execute the Python code
        code_obj = compile(python_code, file_path, 'exec')
        
        # Create a new namespace for execution
        namespace = {'__name__': '__main__'}
        
        # Execute the code
        exec(code_obj, namespace)
        
        return 0
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def create_project(project_path):
    """Create a new Snake project structure."""
    project_dir = Path(project_path)
    
    # Create directories
    os.makedirs(project_dir / "src", exist_ok=True)
    os.makedirs(project_dir / "out", exist_ok=True)
    
    # Create main.sk
    with open(project_dir / "src" / "main.sk", "w") as f:
        f.write('print("Hello, world!");\n')
    
    # Create config.sk
    with open(project_dir / "config.sk", "w") as f:
        f.write(f'name: str = "{project_dir.name}";\n')
        f.write('description: str = "README.md";\n')
        f.write('version: str = "0.1.0";\n')
    
    # Create README.md
    with open(project_dir / "README.md", "w") as f:
        f.write(f"# {project_dir.name}\n\nA Snake language project.\n")
    
    print(f"Created new Snake project at {project_path}")

def read_config(config_path):
    """Read the config.sk file and extract settings."""
    config = {'name': 'snakeproj', 'description': 'README.md', 'version': '0.1.0'}
    
    with open(config_path, 'r') as f:
        for line in f:
            if ':' in line and '=' in line:
                key, value = line.split('=', 1)
                key = key.split(':', 1)[0].strip()
                value = value.strip().strip(';').strip('"\'')
                config[key] = value
    
    return config

def build_project(project_dir='.'):
    """Build the Snake project."""
    project_path = Path(project_dir)
    config_path = project_path / "config.sk"
    
    if not config_path.exists():
        print("Error: config.sk not found. Are you in a Snake project directory?")
        return False
    
    config = read_config(config_path)
    output_name = config['name']
    
    # Check if src directory exists
    src_dir = project_path / "src"
    if not src_dir.exists() or not (src_dir / "main.sk").exists():
        print("Error: src/main.sk not found")
        return False
    
    # Ensure out directory exists
    out_dir = project_path / "out"
    os.makedirs(out_dir, exist_ok=True)
    
    # Build main.sk to out/{output_name}.py
    output_file = out_dir / f"{output_name}.py"
    
    try:
        source_file = src_dir / "main.sk"
        output_path = str(output_file)
        
        # Use the existing run_snake_file function with check_only=True and output_file set
        result = run_snake_file(str(source_file), check_only=True, output_file=output_path)
        
        if result == 0:
            print(f"Built project to {output_file}")
            return True
        else:
            return False
    except Exception as e:
        print(f"Build failed: {e}")
        return False

def run_project(project_dir='.'):
    """Build and run the Snake project."""
    # First build the project
    if not build_project(project_dir):
        return False
    
    project_path = Path(project_dir)
    config = read_config(project_path / "config.sk")
    output_name = config['name']
    
    # Run the compiled Python file
    output_file = project_path / "out" / f"{output_name}.py"
    
    try:
        print(f"Running {output_name}...")
        # Use Python's exec to run the file
        with open(output_file, 'r') as f:
            code = f.read()
        exec(code, {'__file__': str(output_file)})
        return True
    except Exception as e:
        print(f"Run failed: {e}")
        return False

def snakeproj_command():
    parser = argparse.ArgumentParser(description="Snake project management")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new Snake project")
    create_parser.add_argument("path", help="Path to the new project directory")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build the Snake project")
    build_parser.add_argument("--dir", default=".", help="Project directory (default: current directory)")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Build and run the Snake project")
    run_parser.add_argument("--dir", default=".", help="Project directory (default: current directory)")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_project(args.path)
    elif args.command == "build":
        build_project(args.dir)
    elif args.command == "run":
        run_project(args.dir)
    else:
        parser.print_help()

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
    
    # Check if snakeproj command is called
    if len(args) > 0 and args[0] == "snakeproj":
        # Remove "snakeproj" from args and call snakeproj_command
        new_args = [sys.argv[0]] + args[1:]
        sys.argv = new_args
        snakeproj_command()
        return 0
    
    # Create a parser with version and verbose as standalone arguments
    parser = argparse.ArgumentParser(description="Snake programming language")
    parser.add_argument("--version", action="store_true", help="Show version information")
    parser.add_argument("--verbose", action="store_true", help="Show compiled Python code with line numbers")
    
    # First check if --version is in the arguments
    parsed_args, remaining_args = parser.parse_known_args(args)
    
    # Show version and exit if --version flag is present
    if parsed_args.version:
        from . import __version__
        print(f"Snake version {__version__}")
        return 0
    
    # Store the verbose flag
    verbose = parsed_args.verbose
    
    # If we're still here, create a new parser for the rest of the arguments
    file_parser = argparse.ArgumentParser(description="Snake programming language")
    file_parser.add_argument("file", help="Snake source file to run")
    file_parser.add_argument("--check", action="store_true", help="Check for errors without running")
    file_parser.add_argument("-o", "--output", help="Save the generated Python code to the specified file")
    file_parser.add_argument("--verbose", action="store_true", help="Show compiled Python code with line numbers")
    file_parser.add_argument("--version", action="store_true", help="Show version information")
    
    # Parse known arguments, leaving the rest for the Snake script
    parsed_args, script_args = file_parser.parse_known_args(remaining_args)
    
    # Update verbose flag if it was specified in the second parser
    verbose = verbose or parsed_args.verbose
    
    # Save the original sys.argv
    original_argv = sys.argv.copy()
    
    try:
        # Set sys.argv to the script name and its arguments
        sys.argv = [parsed_args.file] + script_args
        
        # Run the file
        return run_snake_file(parsed_args.file, parsed_args.check, parsed_args.output, verbose)
    finally:
        # Restore the original sys.argv
        sys.argv = original_argv


if __name__ == "__main__":
    sys.exit(main())
