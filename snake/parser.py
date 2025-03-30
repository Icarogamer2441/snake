"""
Parser module for the Snake language.
Handles parsing Snake code and extracting type annotations.
"""

import ast
import re
import os
import json
from typing import Dict, Any, Tuple, List, Optional


class SnakeNode:
    """Base class for all Snake AST nodes"""
    pass


class SnakeSyntaxError(Exception):
    """Exception raised for errors in the Snake syntax."""
    def __init__(self, message, line=None, column=None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{message} at line {line}, column {column}" if line else message)


def parse_snake(source_code: str, file_path: str = None) -> Tuple[ast.Module, Dict[str, Any]]:
    """
    Parse Snake code into a Python AST and extract type information.
    
    Args:
        source_code: The Snake source code as a string
        file_path: Path to the source file (for resolving imports)
        
    Returns:
        Tuple containing:
        - Python AST module
        - Dictionary of type annotations
    """
    # Process imports
    source_code = process_imports(source_code, file_path)
    
    # Process enum definitions
    source_code, enum_defs = process_enums(source_code)
    
    # Process struct definitions
    source_code, struct_defs = process_structs(source_code)
    
    # Process constant definitions
    source_code, const_defs = process_constants(source_code)
    
    # Process logical operators
    source_code = process_logical_operators(source_code)
    
    # Add argc and argv to the source code
    source_code = add_argc_argv(source_code)
    
    # Remove semicolons at the end of lines
    source_code = re.sub(r';(\s*\n|\s*$)', r'\1', source_code)
    
    # Extract type annotations
    type_annotations = extract_type_annotations(source_code)
    
    # Add struct definitions to type annotations
    for struct_name, struct_def in struct_defs.items():
        type_annotations[struct_name] = struct_def
    
    # Add enum definitions to type annotations
    for enum_name, enum_def in enum_defs.items():
        type_annotations[enum_name] = enum_def
    
    # Add constant definitions to type annotations
    for const_name, const_def in const_defs.items():
        type_annotations[const_name] = const_def
    
    # Parse the modified source code as Python
    try:
        python_ast = ast.parse(source_code)
    except SyntaxError as e:
        raise SnakeSyntaxError(f"Invalid syntax: {e}", getattr(e, 'lineno', None), getattr(e, 'offset', None))
    
    return python_ast, type_annotations


def find_library_path(lib_name: str) -> Optional[str]:
    """
    Find the path to a Snake library.
    
    Args:
        lib_name: Name of the library
        
    Returns:
        Path to the library, or None if not found
    """
    # Check in the user's library directory
    user_lib_path = os.path.expanduser(f"~/snakelibs/{lib_name}")
    if os.path.isdir(user_lib_path):
        return user_lib_path
    
    # Check in the system library directory (if it exists)
    system_lib_path = f"/usr/local/lib/snakelibs/{lib_name}"
    if os.path.isdir(system_lib_path):
        return system_lib_path
    
    return None


def process_imports(source_code: str, file_path: str = None) -> str:
    """
    Process import statements in the source code.
    
    Args:
        source_code: The Snake source code
        file_path: Path to the source file (for resolving relative imports)
        
    Returns:
        Modified source code with imports processed
    """
    # Pattern to match Snake file imports: import "file.sk";
    snake_file_import_pattern = r'import\s+"([^"]+\.sk)"\s*;'
    
    # Pattern to match Snake library imports: import "library";
    snake_lib_import_pattern = r'import\s+"([^"]+)"\s*;'
    
    # Pattern to match Python imports: from python import module;
    python_import_pattern = r'from\s+python\s+import\s+([a-zA-Z0-9_.,\s]+)\s*;'
    
    # Process Snake file imports
    for match in re.finditer(snake_file_import_pattern, source_code):
        import_stmt = match.group(0)
        import_file = match.group(1)
        
        # Resolve the import path
        if file_path and not os.path.isabs(import_file):
            base_dir = os.path.dirname(file_path)
            import_path = os.path.join(base_dir, import_file)
        else:
            import_path = import_file
        
        # Read the imported file
        try:
            with open(import_path, 'r') as f:
                imported_code = f.read()
            
            # Process the imported code recursively
            imported_code = process_imports(imported_code, import_path)
            
            # Replace the import statement with the processed code
            source_code = source_code.replace(import_stmt, imported_code)
        except FileNotFoundError:
            raise SnakeSyntaxError(f"Could not find imported file: {import_file}")
    
    # Process Snake library imports (after file imports to avoid conflicts)
    for match in re.finditer(snake_lib_import_pattern, source_code):
        import_stmt = match.group(0)
        lib_name = match.group(1)
        
        # Skip if this is a file import (already processed)
        if lib_name.endswith('.sk'):
            continue
        
        # Find the library
        lib_path = find_library_path(lib_name)
        if not lib_path:
            raise SnakeSyntaxError(f"Could not find Snake library: {lib_name}")
        
        # Check for main file
        main_file = os.path.join(lib_path, "__main__.sk")
        if not os.path.isfile(main_file):
            raise SnakeSyntaxError(f"Invalid Snake library: {lib_name} (missing __main__.sk)")
        
        # Read the library's main file
        try:
            with open(main_file, 'r') as f:
                lib_code = f.read()
            
            # Process the library code recursively
            lib_code = process_imports(lib_code, main_file)
            
            # Replace the import statement with the processed code
            source_code = source_code.replace(import_stmt, lib_code)
            
            # Check for Python dependencies
            metadata_file = os.path.join(lib_path, "snake_metadata.json")
            if os.path.isfile(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Add Python imports for dependencies
                    if "python_dependencies" in metadata and metadata["python_dependencies"]:
                        py_imports = []
                        for dep in metadata["python_dependencies"]:
                            py_imports.append(f"import {dep}")
                        
                        # Add imports at the beginning of the code
                        source_code = "\n".join(py_imports) + "\n" + source_code
                except Exception as e:
                    print(f"Warning: Could not process library metadata: {e}")
        except FileNotFoundError:
            raise SnakeSyntaxError(f"Could not read library main file: {lib_name}")
    
    # Process Python imports
    for match in re.finditer(python_import_pattern, source_code):
        import_stmt = match.group(0)
        modules = match.group(1).split(',')
        
        # Generate Python import statements
        python_imports = []
        for module in modules:
            module = module.strip()
            if module:
                python_imports.append(f"import {module}")
        
        # Replace the Snake import statement with Python imports
        python_import_code = '\n'.join(python_imports)
        source_code = source_code.replace(import_stmt, python_import_code)
    
    return source_code


def process_enums(source_code: str) -> Tuple[str, Dict[str, Any]]:
    """
    Process enum definitions in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Tuple containing:
        - Modified source code with enums converted to Enum classes
        - Dictionary of enum definitions
    """
    enum_defs = {}
    
    # Regular expression to match enum definitions
    # This pattern captures the enum name and the entire body
    enum_pattern = r'enum\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:((?:\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\s*:\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?\s*=\s*[^,\n]+)?)+)'
    
    # Find all enum definitions
    for match in re.finditer(enum_pattern, source_code):
        enum_name = match.group(1)
        enum_body = match.group(2)
        
        # Extract enum members
        members = []
        member_values = {}
        member_types = {}
        
        # Pattern for members with values (NAME: TYPE = VALUE)
        valued_member_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?)\s*=\s*([^,\n]+)'
        
        # Pattern for simple members (NAME)
        simple_member_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(?!\s*:)'
        
        # Find members with values
        for member_match in re.finditer(valued_member_pattern, enum_body):
            member_name = member_match.group(1)
            member_type = member_match.group(2)
            member_value = member_match.group(3).strip()
            
            members.append(member_name)
            member_values[member_name] = member_value
            member_types[member_name] = member_type
        
        # Find simple members
        for member_match in re.finditer(simple_member_pattern, enum_body):
            member_name = member_match.group(1)
            if member_name not in members:  # Avoid duplicates from the valued pattern
                members.append(member_name)
        
        # Store enum definition
        enum_defs[enum_name] = {
            'kind': 'enum',
            'members': members,
            'values': member_values,
            'types': member_types
        }
        
        # Generate Enum class definition
        class_def = ["from enum import Enum", ""]
        class_def.append(f"class {enum_name}(Enum):")
        
        # Add enum members
        for member in members:
            if member in member_values:
                class_def.append(f"    {member} = {member_values[member]}")
            else:
                # Auto-assign values for simple members
                class_def.append(f"    {member} = {members.index(member) + 1}")
        
        # Add a blank line after the enum
        class_def.append("")
        
        # Replace enum definition with Enum class
        enum_code = match.group(0)
        enum_class_code = "\n".join(class_def)
        source_code = source_code.replace(enum_code, enum_class_code)
    
    return source_code, enum_defs


def process_structs(source_code: str) -> Tuple[str, Dict[str, Any]]:
    """
    Process struct definitions in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Tuple containing:
        - Modified source code with structs converted to classes
        - Dictionary of struct definitions
    """
    struct_defs = {}
    
    # Regular expression to match struct definitions
    struct_pattern = r'struct\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:((?:\s*[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?\s*;)*)'
    
    # Find all struct definitions
    for match in re.finditer(struct_pattern, source_code):
        struct_name = match.group(1)
        struct_body = match.group(2)
        
        # Extract field definitions
        fields = {}
        field_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?)\s*;'
        for field_match in re.finditer(field_pattern, struct_body):
            field_name = field_match.group(1)
            field_type = field_match.group(2)
            fields[field_name] = field_type
        
        # Store struct definition
        struct_defs[struct_name] = {
            'kind': 'struct',
            'fields': fields
        }
        
        # Generate class definition to replace struct
        class_def = [f"class {struct_name}:"]
        
        # Add __init__ method
        init_params = ", ".join([f"{field}: {field_type}" for field, field_type in fields.items()])
        class_def.append(f"    def __init__(self, {init_params}) -> None:")
        
        # Add field assignments
        for field in fields:
            class_def.append(f"        self.{field} = {field}")
        
        # Add __repr__ method for better string representation
        class_def.append("    def __repr__(self) -> str:")
        repr_fields = ", ".join([f"{field}={{self.{field}}}" for field in fields])
        class_def.append(f"        return f\"{struct_name}({repr_fields})\"")
        
        # Replace struct definition with class definition
        struct_code = match.group(0)
        class_code = "\n".join(class_def)
        source_code = source_code.replace(struct_code, class_code)
    
    return source_code, struct_defs


def process_constants(source_code: str) -> Tuple[str, Dict[str, Dict[str, Any]]]:
    """
    Process constant definitions in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Tuple containing:
        - Modified source code with constants converted to regular variables
        - Dictionary of constant definitions
    """
    const_pattern = r'const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_\.]*)\s*=\s*(.+?)(?:;|$)'
    const_defs = {}
    
    # Find all constant definitions
    matches = re.finditer(const_pattern, source_code, re.MULTILINE)
    
    # Replace each constant definition with a regular variable definition
    modified_code = source_code
    for match in matches:
        const_name = match.group(1)
        const_type = match.group(2)
        const_value = match.group(3)
        
        # Store constant definition
        const_defs[const_name] = {
            'type': const_type,
            'value': const_value,
            'is_constant': True
        }
        
        # Replace 'const' with an empty string to make it a regular variable
        const_def = match.group(0)
        var_def = const_def.replace('const ', '')
        modified_code = modified_code.replace(const_def, var_def)
    
    return modified_code, const_defs


def extract_type_annotations(source_code: str) -> Dict[str, Any]:
    """
    Extract type annotations from Snake code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Dictionary mapping function/variable names to their type annotations
    """
    type_info = {}
    
    # Regular expression to match function definitions with type annotations
    func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)\s*->\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?)\s*:'
    
    # Find all function definitions with return type annotations
    for match in re.finditer(func_pattern, source_code):
        func_name = match.group(1)
        params_str = match.group(2)
        return_type = match.group(3)
        
        # Parse parameter types
        param_types = {}
        if params_str.strip():
            params = params_str.split(',')
            for param in params:
                param = param.strip()
                if ':' in param:
                    param_parts = param.split(':', 1)
                    param_name = param_parts[0].strip()
                    param_type = param_parts[1].strip()
                    param_types[param_name] = param_type
        
        type_info[func_name] = {
            'params': param_types,
            'return': return_type.strip()
        }
    
    # Extract variable type annotations
    var_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?)\s*='
    for match in re.finditer(var_pattern, source_code):
        var_name = match.group(1)
        var_type = match.group(2)
        type_info[var_name] = {'type': var_type.strip()}
    
    return type_info


def validate_types(ast_node: ast.Module, type_annotations: Dict[str, Any]) -> List[str]:
    """
    Validate that the code adheres to the type annotations.
    
    Args:
        ast_node: Python AST module
        type_annotations: Dictionary of type annotations
        
    Returns:
        List of type error messages, if any
    """
    errors = []
    # This is a simplified type checker
    # A real implementation would traverse the AST and validate types
    
    # For now, we'll just return an empty list
    return errors


def add_argc_argv(source_code: str) -> str:
    """
    Add argc and argv variables to the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with argc and argv variables added
    """
    # Add import for sys if not already present
    sys_import_present = False
    if "import sys" in source_code:
        sys_import_present = True
    elif "from python import sys" in source_code:
        sys_import_present = True
    
    # Add argc and argv definitions at the beginning of the code
    if sys_import_present:
        argc_argv_code = """
# Define command-line arguments
argv = sys.argv
argc = len(argv)

"""
    else:
        argc_argv_code = """
import sys

# Define command-line arguments
argv = sys.argv
argc = len(argv)

"""
    
    return argc_argv_code + source_code


def process_logical_operators(source_code: str) -> str:
    """
    Process logical operators in the source code.
    Converts C-style operators (&&, ||, !) to Python-style operators (and, or, not).
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with logical operators processed
    """
    # Replace logical operators with their Python equivalents
    # We need to be careful with the replacements to avoid affecting strings and comments
    
    # Function to process a single line
    def process_line(line):
        # Skip processing if the line is a comment or a string
        if line.strip().startswith('#'):
            return line
        
        # We'll use a state machine to track strings
        in_single_quote = False
        in_double_quote = False
        in_triple_single_quote = False
        in_triple_double_quote = False
        i = 0
        result = []
        
        while i < len(line):
            # Check for string boundaries
            if i + 2 < len(line) and line[i:i+3] == '"""' and not in_single_quote and not in_triple_single_quote:
                in_triple_double_quote = not in_triple_double_quote
                result.append(line[i:i+3])
                i += 3
                continue
            elif i + 2 < len(line) and line[i:i+3] == "'''" and not in_double_quote and not in_triple_double_quote:
                in_triple_single_quote = not in_triple_single_quote
                result.append(line[i:i+3])
                i += 3
                continue
            elif line[i] == '"' and not in_single_quote and not in_triple_single_quote and not in_triple_double_quote:
                # Check if it's not escaped
                if i == 0 or line[i-1] != '\\':
                    in_double_quote = not in_double_quote
                result.append(line[i])
                i += 1
                continue
            elif line[i] == "'" and not in_double_quote and not in_triple_double_quote and not in_triple_single_quote:
                # Check if it's not escaped
                if i == 0 or line[i-1] != '\\':
                    in_single_quote = not in_single_quote
                result.append(line[i])
                i += 1
                continue
            
            # If we're in a string, don't process operators
            if in_single_quote or in_double_quote or in_triple_single_quote or in_triple_double_quote:
                result.append(line[i])
                i += 1
                continue
            
            # Process logical operators
            if i + 1 < len(line) and line[i:i+2] == '&&':
                result.append(' and ')
                i += 2
            elif i + 1 < len(line) and line[i:i+2] == '||':
                result.append(' or ')
                i += 2
            elif line[i] == '!' and (i == 0 or not line[i-1].isalnum()):
                # Make sure we're not in the middle of a word or number
                # And not part of a not-equal operator (!=)
                if i + 1 < len(line) and line[i+1] != '=':
                    result.append('not ')
                    i += 1
                else:
                    result.append(line[i])
                    i += 1
            else:
                result.append(line[i])
                i += 1
        
        return ''.join(result)
    
    # Process each line
    lines = source_code.split('\n')
    processed_lines = [process_line(line) for line in lines]
    
    return '\n'.join(processed_lines)
