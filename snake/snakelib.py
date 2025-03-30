"""
Snake library management tool.
Handles creating, building, and installing Snake libraries.
"""

import os
import sys
import shutil
import argparse
import json
import re
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Default location for installed Snake libraries
DEFAULT_LIB_PATH = os.path.expanduser("~/snakelibs")


def parse_setup_file(setup_path: str) -> Dict[str, Any]:
    """
    Parse a setup.sk file to extract library configuration.
    
    Args:
        setup_path: Path to the setup.sk file
        
    Returns:
        Dictionary containing library configuration
    """
    try:
        with open(setup_path, 'r') as f:
            content = f.read()
        
        # Extract library name
        name_match = re.search(r'name\s*:\s*str\s*=\s*"([^"]+)"', content)
        if not name_match:
            raise ValueError("Library name not found in setup.sk")
        name = name_match.group(1)
        
        # Extract version
        version_match = re.search(r'version\s*:\s*str\s*=\s*"([^"]+)"', content)
        if not version_match:
            raise ValueError("Library version not found in setup.sk")
        version = version_match.group(1)
        
        # Extract dependencies
        dependencies = []
        deps_match = re.search(r'dependencies\s*:\s*(?:List\[str\]|list\[str\])\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if deps_match:
            deps_str = deps_match.group(1)
            # Parse comma-separated list of quoted strings
            for dep_match in re.finditer(r'"([^"]+)"', deps_str):
                dependencies.append(dep_match.group(1))
        
        # Extract Python dependencies
        python_dependencies = []
        py_deps_match = re.search(r'python_dependencies\s*:\s*(?:List\[str\]|list\[str\])\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if py_deps_match:
            py_deps_str = py_deps_match.group(1)
            # Parse comma-separated list of quoted strings
            for dep_match in re.finditer(r'"([^"]+)"', py_deps_str):
                python_dependencies.append(dep_match.group(1))
        
        # Extract to_cmd configuration
        to_cmd = []
        to_cmd_match = re.search(r'to_cmd\s*:\s*(?:List\[str\]|list\[str\])\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if to_cmd_match:
            to_cmd_str = to_cmd_match.group(1)
            # Parse comma-separated list of quoted strings
            for cmd_match in re.finditer(r'"([^"]+)"', to_cmd_str):
                to_cmd.append(cmd_match.group(1))
        
        return {
            "name": name,
            "version": version,
            "dependencies": dependencies,
            "python_dependencies": python_dependencies,
            "to_cmd": to_cmd
        }
    except Exception as e:
        raise ValueError(f"Error parsing setup.sk: {e}")


def build_library(source_dir: str, output_dir: Optional[str] = None) -> str:
    """
    Build a Snake library from source.
    
    Args:
        source_dir: Directory containing the library source
        output_dir: Directory to output the built library (defaults to ~/snakelibs)
        
    Returns:
        Path to the built library
    """
    # Validate source directory
    source_path = Path(source_dir).resolve()
    setup_path = source_path / "setup.sk"
    
    if not setup_path.exists():
        raise ValueError(f"setup.sk not found in {source_dir}")
    
    # Parse setup.sk
    config = parse_setup_file(str(setup_path))
    lib_name = config["name"]
    
    # Determine output directory
    if output_dir:
        lib_output_dir = Path(output_dir) / lib_name
    else:
        lib_output_dir = Path(DEFAULT_LIB_PATH) / lib_name
    
    # Create output directory if it doesn't exist
    os.makedirs(lib_output_dir, exist_ok=True)
    
    # Copy all .sk files to the output directory
    for sk_file in source_path.glob("**/*.sk"):
        if sk_file.name == "setup.sk":
            continue  # Skip setup.sk
        
        # Get relative path from source directory
        rel_path = sk_file.relative_to(source_path)
        target_path = lib_output_dir / rel_path
        
        # Create parent directories if they don't exist
        os.makedirs(target_path.parent, exist_ok=True)
        
        # Copy the file
        shutil.copy2(sk_file, target_path)
    
    # Create metadata file
    metadata = {
        "name": lib_name,
        "version": config["version"],
        "dependencies": config["dependencies"],
        "python_dependencies": config["python_dependencies"],
        "install_date": datetime.datetime.now().isoformat(),
        "to_cmd": config.get("to_cmd", [])
    }
    
    with open(lib_output_dir / "snake_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Create command scripts if to_cmd is specified
    if config.get("to_cmd"):
        create_command_scripts(lib_name, lib_output_dir, config["to_cmd"])
    
    print(f"Successfully built library {lib_name} v{config['version']} to {lib_output_dir}")
    return str(lib_output_dir)


def create_command_scripts(lib_name: str, lib_dir: Path, cmd_files: List[str]) -> None:
    """
    Create command scripts for the library that can be executed directly.
    
    Args:
        lib_name: Name of the library
        lib_dir: Directory where the library is installed
        cmd_files: List of files to create commands for
    """
    # Create bin directory if it doesn't exist
    bin_dir = Path(DEFAULT_LIB_PATH) / "bin"
    os.makedirs(bin_dir, exist_ok=True)
    
    # Get the system-specific script extension and shebang
    is_windows = sys.platform.startswith("win")
    
    for cmd_file in cmd_files:
        cmd_name = lib_name
        cmd_path = lib_dir / cmd_file
        
        if not cmd_path.exists():
            print(f"Warning: Command file {cmd_file} not found in library {lib_name}")
            continue
        
        # Create Windows batch file
        if is_windows:
            batch_path = bin_dir / f"{cmd_name}.bat"
            with open(batch_path, 'w') as f:
                f.write(f'@echo off\r\n')
                f.write(f'python -m snake.cli "{cmd_path}" %*\r\n')
            print(f"Created Windows command: {batch_path}")
        
        # Create Unix shell script
        else:
            # For macOS and Linux
            shell_path = bin_dir / cmd_name
            with open(shell_path, 'w') as f:
                f.write(f'#!/bin/sh\n')
                f.write(f'snake "{cmd_path}" "$@"\n')
            
            # Make the script executable
            os.chmod(shell_path, 0o755)
            print(f"Created Unix command: {shell_path}")
        
        # Add bin directory to PATH if not already there
        update_path_variable(bin_dir)


def update_path_variable(bin_dir: Path) -> None:
    """
    Update the PATH environment variable to include the bin directory.
    
    Args:
        bin_dir: Directory to add to PATH
    """
    bin_dir_str = str(bin_dir)
    
    # Check if already in PATH
    path_var = os.environ.get("PATH", "")
    if bin_dir_str in path_var.split(os.pathsep):
        return
    
    # Update PATH based on the platform
    if sys.platform.startswith("win"):
        # For Windows, update user PATH in registry
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                current_path = winreg.QueryValueEx(key, "PATH")[0]
                if bin_dir_str not in current_path.split(os.pathsep):
                    new_path = f"{current_path}{os.pathsep}{bin_dir_str}"
                    winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                    print(f"Added {bin_dir_str} to Windows PATH")
        except Exception as e:
            print(f"Warning: Could not update Windows PATH: {e}")
            print(f"Please manually add {bin_dir_str} to your PATH")
    else:
        # For Unix-like systems (Linux, macOS)
        shell = os.environ.get("SHELL", "").split("/")[-1]
        
        if shell == "bash":
            rc_file = os.path.expanduser("~/.bashrc")
        elif shell == "zsh":
            rc_file = os.path.expanduser("~/.zshrc")
        else:
            print(f"Warning: Unsupported shell {shell}")
            print(f"Please manually add {bin_dir_str} to your PATH")
            return
        
        # Check if already in rc file
        try:
            with open(rc_file, 'r') as f:
                content = f.read()
                if f"export PATH=\"{bin_dir_str}:$PATH\"" in content:
                    return
            
            # Append to rc file
            with open(rc_file, 'a') as f:
                f.write(f'\n# Added by Snake library manager\n')
                f.write(f'export PATH="{bin_dir_str}:$PATH"\n')
            
            print(f"Added {bin_dir_str} to PATH in {rc_file}")
            print(f"Please restart your terminal or run 'source {rc_file}' to apply changes")
        except Exception as e:
            print(f"Warning: Could not update PATH in {rc_file}: {e}")
            print(f"Please manually add {bin_dir_str} to your PATH")


def install_library(source_dir: str) -> str:
    """
    Install a Snake library to the user's library directory.
    
    Args:
        source_dir: Directory containing the library source
        
    Returns:
        Path to the installed library
    """
    return build_library(source_dir, DEFAULT_LIB_PATH)


def main():
    """Main entry point for the snakelib CLI."""
    parser = argparse.ArgumentParser(description="Snake library management tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build a Snake library")
    build_parser.add_argument("source_dir", help="Directory containing the library source")
    build_parser.add_argument("-o", "--output", help="Directory to output the built library")
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install a Snake library")
    install_parser.add_argument("source_dir", help="Directory containing the library source")
    
    args = parser.parse_args()
    
    try:
        if args.command == "build":
            build_library(args.source_dir, args.output)
        elif args.command == "install":
            install_library(args.source_dir)
        else:
            parser.print_help()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
