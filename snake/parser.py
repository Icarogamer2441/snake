"""
Parser module for the Snake language.
Handles parsing Snake code and extracting type annotations.
"""

import ast
import re
import os
import json
import random
import functools # Import functools for total_ordering
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


# --- Modified Code: Definitions for Maybe and Half ---
MAYBE_HALF_DEFINITIONS = """
import random
import functools # Import functools for total_ordering

# Helper classes and instances for Maybe/Half types
class __SnakeMaybeType:
    # No fixed value, behavior is randomized
    def __bool__(self):
        # Randomly True or False when used in boolean context
        return random.choice([True, False])

    @property # <-- Make value a property
    def value(self):
        # Randomly True or False when .value is accessed
        # Note: This is now a property, accessed in Snake as Maybe.value,
        # which correctly calls this method in the generated Python.
        return random.choice([True, False])

    def __repr__(self):
        return "Maybe"

@functools.total_ordering # Automatically generates missing comparison methods
class __SnakeHalfType:
    value = 0.5 # Fixed float value

    def __bool__(self):
        # Always True in boolean context (represents uncertainty, not False)
        return True

    def __repr__(self):
        return "Half"

    # --- Comparison Methods ---
    def __eq__(self, other):
        # Compare other value to Half's fixed value (0.5)
        try:
            # Handles Half == number and number == Half
            return self.value == float(other)
        except (ValueError, TypeError):
            # Cannot compare with non-numeric types
            return NotImplemented 

    def __lt__(self, other):
        # Compare other value to Half's fixed value (0.5)
        try:
            # Handles Half < number and number > Half
            return self.value < float(other)
        except (ValueError, TypeError):
             # Cannot compare with non-numeric types
            return NotImplemented

    # Properties for direct comparison access if needed (though Half == 0.5 etc. now works)
    # Example: Can be used like `if Half.is_greater(x):`
    def is_equal(self, other):
        try: return float(other) == self.value
        except: return False
        
    def is_less(self, other):
        try: return float(other) < self.value
        except: return False

    def is_greater(self, other):
        try: return float(other) > self.value
        except: return False

# Singleton instances
Maybe = __SnakeMaybeType()
Half = __SnakeHalfType()
"""
# --- End Modified Code ---


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
    # --- Added Code: Prepend Maybe/Half definitions ---
    # Inject Maybe/Half definitions early
    source_code = MAYBE_HALF_DEFINITIONS + source_code
    # --- End Added Code ---
    
    # Process imports
    source_code, imports = process_imports(source_code, file_path)
    
    # Process enum definitions
    source_code, enum_defs = process_enums(source_code)
    
    # Process struct definitions
    source_code, struct_defs = process_structs(source_code)
    
    # Process constant definitions
    source_code, const_defs = process_constants(source_code)
    
    # Process export declarations
    source_code, exports = process_exports(source_code)
    
    # Process type casts
    source_code = process_type_casts(source_code)
    
    # Process logical operators
    source_code = process_logical_operators(source_code)
    
    # Process orelse expressions
    source_code = process_orelse(source_code)
    
    # Process for method syntax
    source_code = process_for_method(source_code)
    
    # Process increment/decrement operators
    source_code = process_increment_decrement(source_code)
    
    # Process static methods and property decorators
    source_code = process_static_and_property(source_code)
    
    # Process custom string methods
    source_code = process_string_methods(source_code)
    
    # Process string format method
    source_code = process_string_format(source_code)
    
    # Process custom list methods
    source_code = process_list_methods(source_code)
    
    # Process 'this' keyword in class methods
    source_code = process_this_keyword(source_code)
    
    # Add command-line arguments
    source_code = add_command_line_args(source_code)
    
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
    
    # Add exported function information to type annotations
    for func_name, func_info in exports.items():
        if func_name in type_annotations:
            type_annotations[func_name].update(func_info)
        else:
            type_annotations[func_name] = func_info
    
    # Parse the modified source code as Python
    try:
        python_ast = ast.parse(source_code)
    except SyntaxError as e:
        line = e.lineno
        col = e.offset
        raise SnakeSyntaxError(str(e), line, col)
    
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


def process_imports(source_code: str, file_path: str = None) -> Tuple[str, Dict[str, Any]]:
    """
    Process import statements in the source code.
    
    Args:
        source_code: The Snake source code
        file_path: Path to the source file (for resolving relative imports)
        
    Returns:
        Tuple containing:
        - Modified source code with imports processed
        - Dictionary of imported modules
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
            imported_code, _ = process_imports(imported_code, import_path)
            
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
            lib_code, _ = process_imports(lib_code, main_file)
            
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
    
    return source_code, {}


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
    enum_pattern = r'enum\s+([a-zA-Z_][a-zA-z0-9_]*)\s*:((?:\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\s*:\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?\s*=\s*[^,\n]+)?)+)'
    
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
    struct_pattern = r'struct\s+([a-zA-Z_][a-zA-z0-9_]*)\s*:((?:\s*[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?\s*;)*)'
    
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


def process_constants(source_code: str) -> Tuple[str, Dict[str, Any]]:
    """
    Process constant definitions in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Tuple containing:
        - Modified source code with constants converted to regular variables
        - Dictionary of constant definitions
    """
    const_defs = {}
    modified_code = source_code
    
    # Regular expression to match constant definitions
    const_pattern = r'const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?)\s*=\s*([^;]+);'
    
    # Find all constant definitions
    for match in re.finditer(const_pattern, source_code):
        const_name = match.group(1)
        const_type = match.group(2)
        const_value = match.group(3)
        
        # Store constant information
        const_defs[const_name] = {
            'type': const_type,
            'value': const_value,
            'is_constant': True  # Mark as constant for type checking
        }
        
        # Replace 'const' with regular variable declaration
        const_def = match.group(0)
        var_def = f"{const_name}: {const_type} = {const_value};"
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
    type_checker = TypeChecker(type_annotations)
    type_checker.visit(ast_node)
    return type_checker.errors


class TypeChecker(ast.NodeVisitor):
    """AST visitor that checks type consistency."""
    
    def __init__(self, type_annotations: Dict[str, Any]):
        self.type_annotations = type_annotations
        self.errors = []
        self.current_function = None
        self.variables = {}  # Track variable types in current scope
        self.return_seen = False
        self.scopes = [{}]  # Stack of variable scopes for tracking variables in different contexts
        self.current_scope = self.scopes[0]  # Current active scope
        self.function_scopes = {}  # Store function scopes for reuse
        self.inferred_types = {}  # Track inferred types from expressions
        self.in_loop = False  # Track if we're in a loop
        self.in_condition = False  # Track if we're in a conditional
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definition for type consistency."""
        old_function = self.current_function
        old_variables = self.variables.copy()
        old_scope = self.current_scope
        
        # Create a new scope for this function
        self.current_function = node.name
        self.variables = {}
        self.scopes.append({})
        self.current_scope = self.scopes[-1]
        self.return_seen = False
        
        # Get function type information
        func_type_info = self.type_annotations.get(node.name, {})
        return_type = func_type_info.get('return')
        param_types = func_type_info.get('params', {})
        
        # Check parameter types
        for arg in node.args.args:
            if hasattr(arg, 'arg') and arg.arg in param_types:
                param_type = param_types[arg.arg]
                self.variables[arg.arg] = param_type
                self.current_scope[arg.arg] = param_type
        
        # Visit function body
        for stmt in node.body:
            self.visit(stmt)
        
        # Check if function with non-None return type has a return statement
        if return_type and return_type != 'None' and not self.return_seen:
            self.errors.append(f"Function '{node.name}' is missing a return statement")
        
        # Store this function's scope for future reference
        self.function_scopes[node.name] = self.current_scope.copy()
        
        # Restore previous state
        self.current_function = old_function
        self.variables = old_variables
        self.current_scope = old_scope
        self.scopes.pop()
    
    def visit_Return(self, node: ast.Return) -> None:
        """Check return statement for type consistency."""
        self.return_seen = True
        
        if not self.current_function:
            self.errors.append("Return statement outside of function")
            return
        
        # Get expected return type
        func_type_info = self.type_annotations.get(self.current_function, {})
        expected_type = func_type_info.get('return')
        
        if not expected_type:
            return
        
        # Check if return value matches expected type
        if node.value:
            actual_type = self.get_expr_type(node.value)
            if actual_type and not self.is_compatible_type(actual_type, expected_type, node.value):
                self.errors.append(
                    f"Function '{self.current_function}' returns {actual_type}, "
                    f"but its return type is {expected_type}"
                )
        elif expected_type != 'None':
            self.errors.append(
                f"Function '{self.current_function}' has no return value, "
                f"but its return type is {expected_type}"
            )
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Check assignment for type consistency."""
        # Visit the value first
        self.visit(node.value)
        
        # Get the value type
        value_type = self.get_expr_type(node.value)
        
        # Check each target
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                
                # If this is the first assignment, record the type
                if var_name not in self.current_scope:
                    # Check if we have type annotation
                    if var_name in self.type_annotations and 'type' in self.type_annotations[var_name]:
                        expected_type = self.type_annotations[var_name]['type']
                        self.variables[var_name] = expected_type
                        self.current_scope[var_name] = expected_type
                        
                        # Check if the assigned value matches the type annotation
                        if value_type and not self.is_compatible_type(value_type, expected_type, node.value):
                            self.errors.append(
                                f"Variable '{var_name}' has type {expected_type}, "
                                f"but is assigned a value of type {value_type}"
                            )
                            
                            # Check list element types if this is a list assignment
                            if expected_type.startswith('list[') and isinstance(node.value, ast.List):
                                self.check_list_elements(node.value, expected_type, var_name)
                                
                            # Check dict element types if this is a dict assignment
                            if expected_type.startswith('dict[') and isinstance(node.value, ast.Dict):
                                self.check_dict_elements(node.value, expected_type, var_name)
                    else:
                        # No type annotation, infer from value
                        if value_type:
                            self.variables[var_name] = value_type
                            self.current_scope[var_name] = value_type
                            # Store the inferred type for future reference
                            self.inferred_types[var_name] = value_type
                else:
                    # This is a reassignment, check type compatibility
                    expected_type = self.current_scope[var_name]
                    if value_type and not self.is_compatible_type(value_type, expected_type, node.value):
                        self.errors.append(
                            f"Variable '{var_name}' has type {expected_type}, "
                            f"but is assigned a value of type {value_type}"
                        )
                        
                        # Check list element types if this is a list assignment
                        if expected_type.startswith('list[') and isinstance(node.value, ast.List):
                            self.check_list_elements(node.value, expected_type, var_name)
                            
                        # Check dict element types if this is a dict assignment
                        if expected_type.startswith('dict[') and isinstance(node.value, ast.Dict):
                            self.check_dict_elements(node.value, expected_type, var_name)
                    
                    # Check if we're trying to reassign a constant
                    if var_name in self.type_annotations and self.type_annotations[var_name].get('is_constant'):
                        self.errors.append(f"Cannot reassign constant '{var_name}'")
            
            elif isinstance(target, ast.Subscript):
                # Handle dictionary or list updates
                if isinstance(target.value, ast.Name):
                    container_name = target.value.id
                    
                    # Check if this is a dictionary update
                    if container_name in self.current_scope:
                        container_type = self.current_scope[container_name]
                        
                        # Handle dictionary updates
                        if container_type.startswith('dict['):
                            # Extract key and value types from the container type
                            key_value_types = container_type[5:-1].split(',')
                            if len(key_value_types) == 2:
                                expected_key_type = key_value_types[0].strip()
                                expected_value_type = key_value_types[1].strip()
                                
                                # Check key type
                                key_type = self.get_expr_type(target.slice)
                                if key_type and not self.is_compatible_type(key_type, expected_key_type):
                                    self.errors.append(
                                        f"Dictionary '{container_name}' has key type {expected_key_type}, "
                                        f"but is accessed with a key of type {key_type}"
                                    )
                                
                                # Check value type
                                if value_type and not self.is_compatible_type(value_type, expected_value_type):
                                    self.errors.append(
                                        f"Dictionary '{container_name}' has value type {expected_value_type}, "
                                        f"but is assigned a value of type {value_type}"
                                    )
                        
                        # Handle list updates
                        elif container_type.startswith('list['):
                            expected_elem_type = container_type[5:-1]
                            
                            # Check if index is an integer
                            index_type = self.get_expr_type(target.slice)
                            if index_type and index_type != 'int':
                                self.errors.append(
                                    f"List '{container_name}' index must be an integer, got {index_type}"
                                )
                            
                            # Check element type
                            if value_type and not self.is_compatible_type(value_type, expected_elem_type):
                                self.errors.append(
                                    f"List '{container_name}' has element type {expected_elem_type}, "
                                    f"but is assigned a value of type {value_type}"
                                )
    
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Check annotated assignment for type consistency."""
        # Visit the value first if it exists
        if node.value:
            self.visit(node.value)
            
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            
            # Get the annotation type
            if isinstance(node.annotation, ast.Name):
                ann_type = node.annotation.id
            else:
                # Complex type annotation, use string representation
                ann_type = ast.unparse(node.annotation)
            
            # Record the variable type
            self.variables[var_name] = ann_type
            self.current_scope[var_name] = ann_type
            
            # If there's a value, check its type
            if node.value:
                value_type = self.get_expr_type(node.value)
                if value_type and not self.is_compatible_type(value_type, ann_type, node.value):
                    self.errors.append(
                        f"Variable '{var_name}' has type {ann_type}, "
                        f"but is assigned a value of type {value_type}"
                    )
                
                # Check list element types if this is a list assignment
                if ann_type.startswith('list[') and isinstance(node.value, ast.List):
                    self.check_list_elements(node.value, ann_type, var_name)
                    
                # Check dict element types if this is a dict assignment
                if ann_type.startswith('dict[') and isinstance(node.value, ast.Dict):
                    self.check_dict_elements(node.value, ann_type, var_name)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Check function call for type consistency."""
        # Visit arguments first
        for arg in node.args:
            self.visit(arg)
        
        # Visit keyword arguments
        for keyword in node.keywords:
            self.visit(keyword.value)
        
        # Check if this is a method call on a list
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            obj_name = node.func.value.id
            method_name = node.func.attr
            
            # Get the object type
            obj_type = self.get_expr_type(node.func.value)
            
            # Check list methods that modify the list
            if obj_type and obj_type.startswith('list['):
                elem_type = obj_type[5:-1].strip()  # Extract element type
                
                # Check append method
                if method_name == 'append' and len(node.args) == 1:
                    arg_type = self.get_expr_type(node.args[0])
                    if arg_type and not self.is_compatible_type(arg_type, elem_type):
                        self.errors.append(
                            f"List '{obj_name}' has element type {elem_type}, "
                            f"but append() was called with a value of type {arg_type}"
                        )
                
                # Check insert method
                elif method_name == 'insert' and len(node.args) >= 2:
                    # First arg should be an index (int)
                    index_type = self.get_expr_type(node.args[0])
                    if index_type and index_type != 'int':
                        self.errors.append(
                            f"List '{obj_name}' insert() method requires an integer index, "
                            f"but was called with an index of type {index_type}"
                        )
                    
                    # Second arg should match the element type
                    if len(node.args) > 1:
                        arg_type = self.get_expr_type(node.args[1])
                        if arg_type and not self.is_compatible_type(arg_type, elem_type):
                            self.errors.append(
                                f"List '{obj_name}' has element type {elem_type}, "
                                f"but insert() was called with a value of type {arg_type}"
                            )
                
                # Check extend method
                elif method_name == 'extend' and len(node.args) == 1:
                    arg_type = self.get_expr_type(node.args[0])
                    if arg_type:
                        if not arg_type.startswith('list['):
                            self.errors.append(
                                f"List '{obj_name}' extend() method requires a list argument, "
                                f"but was called with an argument of type {arg_type}"
                            )
                        else:
                            # Check if the element types are compatible
                            arg_elem_type = arg_type[5:-1].strip()
                            if not self.is_compatible_type(arg_elem_type, elem_type):
                                self.errors.append(
                                    f"List '{obj_name}' has element type {elem_type}, "
                                    f"but extend() was called with a list of element type {arg_elem_type}"
                                )
                
                # Check pop method
                elif method_name == 'pop':
                    return elem_type  # pop() returns an element of the list
                
                # Check printall method
                elif method_name == 'printall' and len(node.args) == 0:
                    # This is valid, no additional checks needed
                    pass
            
            # Check if printall() is called on a non-list object
            elif method_name == 'printall' and len(node.args) == 0:
                if not obj_type or not obj_type.startswith('list['):
                    self.errors.append(
                        f"Object '{obj_name}' of type {obj_type or 'unknown'} has no method 'printall()'. "
                        f"The printall() method can only be used on list objects."
                    )
            
            # Continue with the original implementation for other function calls
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                
                # Check if we have type information for this function
                if func_name in self.type_annotations and 'params' in self.type_annotations[func_name]:
                    param_types = self.type_annotations[func_name]['params']
                    
                    # Check if the number of arguments matches (allowing for default parameters)
                    if len(node.args) > len(param_types):
                        self.errors.append(
                            f"Function '{func_name}' takes {len(param_types)} arguments, "
                            f"but {len(node.args)} were given"
                        )
                        return
                    
                    # Check each argument type
                    for i, (param_name, param_type) in enumerate(param_types.items()):
                        if i < len(node.args):
                            arg_type = self.get_expr_type(node.args[i])
                            
                            # Extract the base type without default value
                            base_param_type = param_type
                            if '=' in param_type:
                                base_param_type = param_type.split('=')[0].strip()
                            
                            if arg_type and not self.is_compatible_type(arg_type, base_param_type):
                                self.errors.append(
                                    f"Argument {i+1} to function '{func_name}' has type {arg_type}, "
                                    f"but parameter '{param_name}' has type {base_param_type}"
                                )
                    
                    # Check keyword arguments
                    for keyword in node.keywords:
                        if keyword.arg in param_types:
                            param_type = param_types[keyword.arg]
                            arg_type = self.get_expr_type(keyword.value)
                            
                            # Extract the base type without default value
                            base_param_type = param_type
                            if '=' in param_type:
                                base_param_type = param_type.split('=')[0].strip()
                            
                            if arg_type and not self.is_compatible_type(arg_type, base_param_type):
                                self.errors.append(
                                    f"Keyword argument '{keyword.arg}' to function '{func_name}' has type {arg_type}, "
                                    f"but parameter '{keyword.arg}' has type {base_param_type}"
                                )
                        else:
                            self.errors.append(f"Function '{func_name}' has no parameter named '{keyword.arg}'")
            
            # Check if this is a method call
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
                method_name = node.func.attr
                
                # Get the object type
                obj_type = self.get_expr_type(node.func.value)
                
                # Check if this is a method call on a struct
                if obj_type in self.type_annotations:
                    struct_info = self.type_annotations.get(obj_type, {})
                    if isinstance(struct_info, dict) and struct_info.get('kind') == 'struct':
                        # This is a struct, check if the method exists
                        # For now, we don't have method type information for structs
                        pass
    
    def visit_Dict(self, node: ast.Dict) -> None:
        """Check dictionary elements for type consistency."""
        # Visit all keys and values
        for key in node.keys:
            self.visit(key)
        for value in node.values:
            self.visit(value)
    
    def visit_List(self, node: ast.List) -> None:
        """Check list elements for type consistency."""
        # Visit all elements
        for elem in node.elts:
            self.visit(elem)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check attribute access for type consistency."""
        # Visit the value first
        self.visit(node.value)
        
        # Get the type of the object being accessed
        obj_type = self.get_expr_type(node.value)
        
        # Check if this is a struct field access
        if obj_type in self.type_annotations:
            struct_info = self.type_annotations.get(obj_type, {})
            if isinstance(struct_info, dict) and struct_info.get('kind') == 'struct':
                # This is a struct, check if the attribute is a valid field
                fields = struct_info.get('fields', {})
                if node.attr not in fields:
                    self.errors.append(f"Struct '{obj_type}' has no field '{node.attr}'")
        # --- Added Code: Check for Maybe/Half .value access ---
        elif isinstance(node.value, ast.Name) and node.value.id in ['Maybe', 'Half']:
            if node.attr != 'value':
                self.errors.append(f"Type '{node.value.id}' has no attribute '{node.attr}'")
        # --- End Added Code ---
    
    def get_expr_type(self, node: ast.expr) -> Optional[str]:
        """Determine the type of an expression."""
        if isinstance(node, ast.Constant):
            # Handle literals
            if node.value is None:
                return 'None'
            return type(node.value).__name__
        
        elif isinstance(node, ast.Name):
            # Variable reference
            var_name = node.id
            
            # Check if it's a known variable in the current scope
            if var_name in self.current_scope:
                return self.current_scope[var_name]
            
            # Check if it's a variable with type annotation
            if var_name in self.type_annotations and 'type' in self.type_annotations[var_name]:
                return self.type_annotations[var_name]['type']
            
            # --- Added Code: Handle Maybe/Half types ---
            # Check if it's Maybe or Half
            if var_name == 'Maybe' or var_name == 'Half':
                return 'bool' # Treat Maybe/Half as compatible with bool
            # --- End Added Code ---
            
            # Check if it's an inferred type
            if var_name in self.inferred_types:
                return self.inferred_types[var_name]
            
            return None
        
        elif isinstance(node, ast.Call):
            # Function call
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                
                # Check if this is a struct constructor
                if func_name in self.type_annotations:
                    struct_info = self.type_annotations.get(func_name, {})
                    if isinstance(struct_info, dict) and struct_info.get('kind') == 'struct':
                        # Check struct constructor arguments
                        self.check_struct_fields(node, func_name, func_name)
                        return func_name
                
                # Regular function call
                func_info = self.type_annotations.get(func_name, {})
                return func_info.get('return')
            
            # Method call
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
                method_name = node.func.attr
                
                # Get the object type
                obj_type = self.get_expr_type(node.func.value)
                
                # Check if this is a method call on a struct
                if obj_type in self.type_annotations:
                    struct_info = self.type_annotations.get(obj_type, {})
                    if isinstance(struct_info, dict) and struct_info.get('kind') == 'struct':
                        # For now, we don't have method type information for structs
                        # In the future, we could add method type information to struct definitions
                        pass
                
                # Handle built-in methods for known types
                if obj_type == 'str':
                    if method_name in ['strip', 'lstrip', 'rstrip', 'upper', 'lower', 'title', 'capitalize']:
                        return 'str'
                    elif method_name in ['split', 'splitlines']:
                        return 'list[str]'
                    elif method_name in ['isdigit', 'isalpha', 'isalnum', 'startswith', 'endswith']:
                        return 'bool'
                    elif method_name == 'format':
                        return 'str'
                    elif method_name == 'add':  # Custom Snake method
                        return 'str'
                    elif method_name == 'remove':  # Custom Snake method
                        return 'str'
                    elif method_name == 'f':  # Custom Snake method
                        return 'str'
                
                elif obj_type and obj_type.startswith('list['):
                    if method_name in ['append', 'insert', 'remove', 'clear', 'sort', 'reverse', 'printall']:
                        return 'None'
                    elif method_name == 'count':
                        return 'int'
                    elif method_name == 'index':
                        return 'int'
                    elif method_name == 'copy':
                        return obj_type
                    elif method_name == 'pop':
                        elem_type = obj_type[5:-1].strip()  # Extract element type
                        return elem_type
            
                elif obj_type and obj_type.startswith('dict['):
                    if method_name in ['clear', 'pop', 'popitem', 'update']:
                        return 'None'
                    elif method_name == 'get':
                        # Return the value type from dict[key_type, value_type]
                        value_type = obj_type.split(',')[1].strip()[:-1]  # Remove trailing ']'
                        return value_type
                    elif method_name == 'keys':
                        key_type = obj_type.split('[')[1].split(',')[0].strip()
                        return f'list[{key_type}]'
                    elif method_name == 'values':
                        value_type = obj_type.split(',')[1].strip()[:-1]  # Remove trailing ']'
                        return f'list[{value_type}]'
                    elif method_name == 'items':
                        key_type = obj_type.split('[')[1].split(',')[0].strip()
                        value_type = obj_type.split(',')[1].strip()[:-1]  # Remove trailing ']'
                        return f'list[tuple[{key_type}, {value_type}]]'
                    elif method_name == 'copy':
                        return obj_type
            
            return None
        
        elif isinstance(node, ast.BinOp):
            # Binary operation
            left_type = self.get_expr_type(node.left)
            right_type = self.get_expr_type(node.right)
            
            # Handle numeric operations
            if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)):
                if left_type in ('int', 'float') and right_type in ('int', 'float'):
                    # Promote to float if either operand is float
                    if 'float' in (left_type, right_type):
                        return 'float'
                    return 'int'
                
                # String concatenation
                if isinstance(node.op, ast.Add) and left_type == 'str' and right_type == 'str':
                    return 'str'
                
                # String repetition
                if isinstance(node.op, ast.Mult) and (
                    (left_type == 'str' and right_type == 'int') or
                    (left_type == 'int' and right_type == 'str')
                ):
                    return 'str'
                
                # List concatenation
                if isinstance(node.op, ast.Add) and left_type and right_type and (
                    left_type.startswith('list[') and right_type.startswith('list[')
                ):
                    # If element types match, preserve them
                    left_elem_type = left_type[5:-1]
                    right_elem_type = right_type[5:-1]
                    if left_elem_type == right_elem_type:
                        return f'list[{left_elem_type}]'
                    return 'list'
                
                # List repetition
                if isinstance(node.op, ast.Mult) and (
                    (left_type and left_type.startswith('list[') and right_type == 'int') or
                    (left_type == 'int' and right_type and right_type.startswith('list['))
                ):
                    list_type = left_type if left_type.startswith('list[') else right_type
                    return list_type
            
            # Comparison operations
            elif isinstance(node.op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                return 'bool'
            
            # Bitwise operations
            elif isinstance(node.op, (ast.BitOr, ast.BitAnd, ast.BitXor)):
                if left_type == 'int' and right_type == 'int':
                    return 'int'
            
            # Shift operations
            elif isinstance(node.op, (ast.LShift, ast.RShift)):
                if left_type == 'int' and right_type == 'int':
                    return 'int'
            
            return None
        
        elif isinstance(node, ast.BoolOp):
            # Boolean operation (and, or)
            return 'bool'
        
        elif isinstance(node, ast.UnaryOp):
            # Unary operation
            if isinstance(node.op, ast.Not):
                return 'bool'
            
            operand_type = self.get_expr_type(node.operand)
            if isinstance(node.op, (ast.UAdd, ast.USub)) and operand_type in ('int', 'float'):
                return operand_type
            
            if isinstance(node.op, ast.Invert) and operand_type == 'int':
                return 'int'
            
            return None
        
        elif isinstance(node, ast.Compare):
            # Comparison
            return 'bool'
        
        elif isinstance(node, ast.List):
            # List literal
            if node.elts:
                # Try to determine element type from the first element
                elem_type = self.get_expr_type(node.elts[0])
                
                # Check if all elements have the same type
                all_same_type = True
                for elem in node.elts[1:]:
                    if self.get_expr_type(elem) != elem_type:
                        all_same_type = False
                        break
                
                if all_same_type and elem_type:
                    return f'list[{elem_type}]'
            
            return 'list'
        
        elif isinstance(node, ast.Dict):
            # Dict literal
            if node.keys and node.values:
                # Try to determine key and value types from the first pair
                key_type = self.get_expr_type(node.keys[0])
                value_type = self.get_expr_type(node.values[0])
                
                # Check if all keys have the same type
                all_keys_same_type = True
                for key in node.keys[1:]:
                    if self.get_expr_type(key) != key_type:
                        all_keys_same_type = False
                        break
                
                # Check if all values have the same type
                all_values_same_type = True
                for value in node.values[1:]:
                    if self.get_expr_type(value) != value_type:
                        all_values_same_type = False
                        break
                
                if all_keys_same_type and all_values_same_type and key_type and value_type:
                    return f'dict[{key_type}, {value_type}]'
            
            return 'dict'
        
        elif isinstance(node, ast.Tuple):
            # Tuple literal
            if node.elts:
                elem_types = []
                for elem in node.elts:
                    elem_type = self.get_expr_type(elem)
                    if elem_type:
                        elem_types.append(elem_type)
                    else:
                        elem_types.append('Any')
                
                if elem_types:
                    return f'tuple[{", ".join(elem_types)}]'
            
            return 'tuple'
        
        elif isinstance(node, ast.Subscript):
            # Subscript access (e.g., list[index] or dict[key])
            value_type = self.get_expr_type(node.value)
            
            if value_type and value_type.startswith('list['):
                # List access returns the element type
                elem_type = value_type[5:-1]  # Remove 'list[' and ']'
                return elem_type
            
            elif value_type and value_type.startswith('dict['):
                # Dict access returns the value type
                key_value_types = value_type[5:-1].split(',')
                if len(key_value_types) == 2:
                    return key_value_types[1].strip()
            
            elif value_type and value_type.startswith('tuple['):
                # Tuple access with a constant index
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                    index = node.slice.value
                    tuple_types = value_type[6:-1].split(',')  # Remove 'tuple[' and ']'
                    if 0 <= index < len(tuple_types):
                        return tuple_types[index].strip()
            
            return None
        
        elif isinstance(node, ast.Attribute):
            # Attribute access (e.g., obj.attr)
            value_type = self.get_expr_type(node.value)
            
            # Check if this is a struct field access
            if value_type in self.type_annotations:
                struct_info = self.type_annotations.get(value_type, {})
                if isinstance(struct_info, dict) and struct_info.get('kind') == 'struct':
                    fields = struct_info.get('fields', {})
                    if node.attr in fields:
                        return fields[node.attr]
            # --- Added Code: Handle Maybe/Half .value access type ---
            # Check if it's Maybe.value or Half.value
            elif isinstance(node.value, ast.Name) and node.value.id == 'Maybe' and node.attr == 'value':
                # Maybe.value returns a random bool
                return 'bool' 
            elif isinstance(node.value, ast.Name) and node.value.id == 'Half' and node.attr == 'value':
                 # Half.value is the fixed float 0.5
                return 'float'
            # --- End Added Code ---
            
            return None
        
        # Add more cases as needed
        
        return None
    
    def is_compatible_type(self, actual_type: str, expected_type: str, node: Optional[ast.AST] = None) -> bool:
        """Check if actual_type is compatible with expected_type."""
        # All type is compatible with everything
        if expected_type == 'All' or expected_type == 'Any':
            return True
            
        # Any type can be assigned to All or Any
        if actual_type == 'All' or actual_type == 'Any':
            return True
            
        # Exact match
        if actual_type == expected_type:
            return True
        
        # None can be assigned to any optional type
        if actual_type == 'None' and expected_type.startswith('Optional['):
            return True
        
        # int can be assigned to float
        if actual_type == 'int' and expected_type == 'float':
            return True
        
        # Check for generic types (e.g., list[int] is compatible with list)
        # --- Modified Code: Adjusted generic type check logic ---
        # Check if actual_type is a specific version of expected_type (e.g., list[int] compatible with list)
        if '[' in actual_type and actual_type.split('[')[0] == expected_type:
             return True

        # Check if expected_type is a specific version of actual_type (e.g. list compatible with list[int] - less common, maybe disallow?)
        # Let's keep the original logic for now, which checks compatibility more broadly.
        # If we need stricter checks later, we can refine this.
        if '[' in expected_type and expected_type.split('[')[0] == actual_type.split('[')[0]:
            # Check detailed compatibility for known generics
            if actual_type.startswith('list[') and expected_type.startswith('list['):
                 actual_elem_type = actual_type[5:-1].strip()
                 expected_elem_type = expected_type[5:-1].strip()
                 # Allow assignment if expected is 'All' or types are compatible
                 return expected_elem_type == 'All' or self.is_compatible_type(actual_elem_type, expected_elem_type)

            if actual_type.startswith('dict[') and expected_type.startswith('dict['):
                # Simplified check, relies on recursive calls for key/value compatibility
                # Extract types safely
                try:
                    actual_key_type, actual_value_type = self._extract_dict_types(actual_type)
                    expected_key_type, expected_value_type = self._extract_dict_types(expected_type)
                    
                    key_compatible = expected_key_type == 'All' or self.is_compatible_type(actual_key_type, expected_key_type)
                    value_compatible = expected_value_type == 'All' or self.is_compatible_type(actual_value_type, expected_value_type)
                    
                    return key_compatible and value_compatible
                except ValueError:
                    return False # Malformed dict type string

            # Fallback for other potential generics or if parsing fails
            return True # Assume compatible if base types match
        # --- End Modified Code ---

        # Check for tuple compatibility
        if actual_type.startswith('tuple[') and expected_type.startswith('tuple['):
            actual_types = actual_type[6:-1].split(',')
            expected_types = expected_type[6:-1].split(',')
            
            # Check if the tuple has the same number of elements
            if len(actual_types) != len(expected_types):
                return False
            
            # Check if each element is compatible
            for i in range(len(actual_types)):
                if not self.is_compatible_type(actual_types[i].strip(), expected_types[i].strip()):
                    return False
            
            return True
        
        # Check for list compatibility with element types
        if actual_type.startswith('list[') and expected_type.startswith('list['):
            actual_elem_type = actual_type[5:-1].strip()
            expected_elem_type = expected_type[5:-1].strip()
            
            return self.is_compatible_type(actual_elem_type, expected_elem_type)
        
        # Check for dict compatibility with key and value types
        if actual_type.startswith('dict[') and expected_type.startswith('dict['):
            actual_types = actual_type[5:-1].split(',')
            expected_types = expected_type[5:-1].split(',')
            
            if len(actual_types) != 2 or len(expected_types) != 2:
                return False
            
            actual_key_type = actual_types[0].strip()
            actual_value_type = actual_types[1].strip()
            expected_key_type = expected_types[0].strip()
            expected_value_type = expected_types[1].strip()
            
            return (self.is_compatible_type(actual_key_type, expected_key_type) and
                    self.is_compatible_type(actual_value_type, expected_value_type))
        
        # Check for struct types
        for struct_name, struct_info in self.type_annotations.items():
            if isinstance(struct_info, dict) and struct_info.get('kind') == 'struct':
                if actual_type == struct_name and expected_type == struct_name:
                    return True
        
        # Check for enum types
        for enum_name, enum_info in self.type_annotations.items():
            if isinstance(enum_info, dict) and enum_info.get('kind') == 'enum':
                if actual_type == enum_name and expected_type == enum_name:
                    return True
        
        # --- Added Code: Allow Maybe/Half assignment to bool ---
        if expected_type == 'bool' and actual_type in ['Maybe', 'Half', 'bool']:
             # We already handle actual_type == 'bool' above.
             # Since get_expr_type returns 'bool' for Maybe/Half, this check might be redundant
             # but let's keep it explicit for clarity if get_expr_type changes.
             # The core logic is that get_expr_type maps Maybe/Half to 'bool',
             # making them compatible via the exact match rule.
             pass # This case is implicitly handled by get_expr_type returning 'bool'
        # --- End Added Code ---

        return False
    
    def check_list_elements(self, node: ast.List, expected_type: str, var_name: str) -> None:
        """Check that all elements in a list match the expected element type."""
        if not expected_type.startswith('list[') or not expected_type.endswith(']'):
            return
            
        # Extract the expected element type
        expected_elem_type = expected_type[5:-1]  # Remove 'list[' and ']'
        
        # If the expected element type is All, all elements are valid
        if expected_elem_type == 'All':
            return
            
        # Check each element
        for i, elem in enumerate(node.elts):
            elem_type = self.get_expr_type(elem)
            if elem_type and not self.is_compatible_type(elem_type, expected_elem_type):
                self.errors.append(
                    f"List element at index {i} in '{var_name}' has type {elem_type}, "
                    f"but expected {expected_elem_type}"
                )
    
    def check_dict_elements(self, node: ast.Dict, expected_type: str, var_name: str) -> None:
        """Check that all keys and values in a dict match the expected types."""
        if not expected_type.startswith('dict[') or not expected_type.endswith(']'):
            return
            
        # Extract the expected key and value types
        type_params = expected_type[5:-1]  # Remove 'dict[' and ']'
        
        # Split by comma, but handle nested types with commas
        bracket_count = 0
        split_index = -1
        
        for i, char in enumerate(type_params):
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
            elif char == ',' and bracket_count == 0:
                split_index = i
                break
        
        if split_index == -1:
            # Malformed dict type
            self.errors.append(f"Invalid dictionary type annotation: {expected_type}")
            return
            
        expected_key_type = type_params[:split_index].strip()
        expected_value_type = type_params[split_index+1:].strip()
        
        # If either expected type is All, skip checking for that part
        check_keys = expected_key_type != 'All'
        check_values = expected_value_type != 'All'
        
        # Check each key-value pair
        for i, (key, value) in enumerate(zip(node.keys, node.values)):
            key_type = self.get_expr_type(key)
            value_type = self.get_expr_type(value)
            
            if check_keys and key_type and not self.is_compatible_type(key_type, expected_key_type):
                self.errors.append(
                    f"Dictionary key at index {i} in '{var_name}' has type {key_type}, "
                    f"but expected {expected_key_type}"
                )
                
            if check_values and value_type and not self.is_compatible_type(value_type, expected_value_type):
                self.errors.append(
                    f"Dictionary value at index {i} in '{var_name}' has type {value_type}, "
                    f"but expected {expected_value_type}"
                )
    
    def check_struct_fields(self, node: ast.Call, struct_name: str, var_name: str) -> None:
        """Check that struct constructor arguments match the expected field types."""
        # Get struct definition
        struct_info = self.type_annotations.get(struct_name, {})
        if not isinstance(struct_info, dict) or struct_info.get('kind') != 'struct':
            return
            
        fields = struct_info.get('fields', {})
        
        # Check if the number of arguments matches the number of fields
        if len(node.args) != len(fields):
            self.errors.append(
                f"Struct '{struct_name}' constructor expects {len(fields)} arguments, "
                f"but got {len(node.args)}"
            )
            return
            
        # Check each argument type
        field_names = list(fields.keys())
        for i, (field_name, arg) in enumerate(zip(field_names, node.args)):
            expected_type = fields[field_name]
            
            # Skip type checking for fields with All type
            if expected_type == 'All':
                continue
                
            arg_type = self.get_expr_type(arg)
            
            if arg_type and not self.is_compatible_type(arg_type, expected_type):
                self.errors.append(
                    f"Field '{field_name}' in struct '{struct_name}' has type {expected_type}, "
                    f"but is assigned a value of type {arg_type}"
                )

    # --- Added Code: Helper to extract dict types ---
    def _extract_dict_types(self, dict_type_str: str) -> Tuple[str, str]:
         """Extracts key and value types from a dict type string like 'dict[key, value]'."""
         if not dict_type_str.startswith('dict[') or not dict_type_str.endswith(']'):
             raise ValueError("Invalid dict type format")

         type_params = dict_type_str[5:-1]
         bracket_count = 0
         split_index = -1

         for i, char in enumerate(type_params):
             if char == '[': bracket_count += 1
             elif char == ']': bracket_count -= 1
             elif char == ',' and bracket_count == 0:
                 split_index = i
                 break

         if split_index == -1:
             raise ValueError("Could not find comma separator for dict types")

         key_type = type_params[:split_index].strip()
         value_type = type_params[split_index+1:].strip()
         return key_type, value_type
    # --- End Added Code ---


def add_command_line_args(source_code: str) -> str:
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
    Process logical operators (&&, ||, !) in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with logical operators replaced
    """
    # Replace && with and
    source_code = re.sub(r'(\s)&&(\s)', r'\1and\2', source_code)
    
    # Replace || with or
    source_code = re.sub(r'(\s)\|\|(\s)', r'\1or\2', source_code)
    
    # Replace ! with not (but not !=)
    source_code = re.sub(r'(\s)!([^=])', r'\1not \2', source_code)
    
    return source_code


def process_type_casts(source_code: str) -> str:
    """
    Process type cast expressions in the source code.
    Converts C-style type casts (e.g., (int)a) to Python function calls.
    Also handles dictionary-to-struct conversions (e.g., (Point){"x": 1, "y": 2}).
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with type casts processed
    """
    # Add helper functions at the beginning of the code
    helper_functions = """
# Helper functions for type casting
def __snake_cast(value, target_type):
    if target_type == int:
        return int(value)
    elif target_type == float:
        return float(value)
    elif target_type == str:
        return str(value)
    elif target_type == bool:
        return bool(value)
    else:
        return target_type(value)

def __snake_cast_dict_to_struct(struct_type, dict_value):
    # Create an instance of the struct with default values
    instance = struct_type.__new__(struct_type)
    
    # Set the fields from the dictionary
    for key, value in dict_value.items():
        setattr(instance, key, value)
    
    return instance

# Define the All type (equivalent to Python's Any type)
class All:
    pass

"""
    
    # Regular expression to match type casts: (Type)expr
    # This regex captures the type name and the expression being cast
    type_cast_pattern = r'\(([A-Za-z_][A-Za-z0-9_]*)\)([A-Za-z_][A-Za-z0-9_]*)'
    
    # Replace type casts with function calls
    processed_code = re.sub(type_cast_pattern, r'__snake_cast(\2, \1)', source_code)
    
    # Regular expression to match dictionary-to-struct conversions: (Type){...}
    # This is more complex because we need to capture the type and the dictionary literal
    struct_cast_pattern = r'\(([A-Za-z_][A-Za-z0-9_]*)\)(\{[^}]*\})'
    
    # Replace struct casts with function calls
    processed_code = re.sub(struct_cast_pattern, r'__snake_cast_dict_to_struct(\1, \2)', processed_code)
    
    return helper_functions + processed_code


def process_string_methods(source_code: str) -> str:
    """
    Process custom string methods (.add() and .remove()) in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with custom string methods processed
    """
    # Add string helper functions
    helper_functions = """
# String helper functions
def __snake_string_add(string, value):
    return string + value

def __snake_string_remove(string, value):
    return string.replace(value, "")

"""
    
    # Process each line to handle string methods
    lines = source_code.split('\n')
    processed_lines = []
    
    for line in lines:
        # Skip processing if the line is a comment
        if line.strip().startswith('#'):
            processed_lines.append(line)
            continue
        
        # Process standalone variable.add() statements first
        standalone_add_match = re.search(r'^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*add\s*\(\s*(.*?)\s*\)\s*;', line)
        if standalone_add_match:
            indent = standalone_add_match.group(1)
            var_name = standalone_add_match.group(2)
            value = standalone_add_match.group(3)
            processed_lines.append(f"{indent}{var_name} = {var_name} + {value};")
            continue
        
        # Process standalone variable.remove() statements
        standalone_remove_match = re.search(r'^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*remove\s*\(\s*(.*?)\s*\)\s*;', line)
        if standalone_remove_match:
            indent = standalone_remove_match.group(1)
            var_name = standalone_remove_match.group(2)
            value = standalone_remove_match.group(3)
            processed_lines.append(f"{indent}{var_name} = {var_name}.replace({value}, \"\");")
            continue
        
        # Process .add() method in expressions
        processed_line = line
        add_expr_matches = list(re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*add\s*\(\s*(.*?)\s*\)', processed_line))
        for match in reversed(add_expr_matches):  # Process in reverse to avoid messing up positions
            expr = match.group(1)
            value = match.group(2)
            start, end = match.span()
            processed_line = processed_line[:start] + f"__snake_string_add({expr}, {value})" + processed_line[end:]
        
        # Process .remove() method in expressions
        remove_expr_matches = list(re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*remove\s*\(\s*(.*?)\s*\)', processed_line))
        for match in reversed(remove_expr_matches):  # Process in reverse to avoid messing up positions
            expr = match.group(1)
            value = match.group(2)
            start, end = match.span()
            processed_line = processed_line[:start] + f"__snake_string_remove({expr}, {value})" + processed_line[end:]
        
        processed_lines.append(processed_line)
    
    return helper_functions + '\n'.join(processed_lines)


def process_string_format(source_code: str) -> str:
    """
    Process string format method (.f()) in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with .f() method replaced with .format()
    """
    # Add string format helper function
    helper_function = """
# String format helper function
def __snake_format(string, *args, **kwargs):
    return string.format(*args, **kwargs)

"""
    
    # Replace .f() with .format()
    format_pattern = r'\.f\('
    source_code = re.sub(format_pattern, '.format(', source_code)
    
    return helper_function + source_code


def process_list_methods(source_code: str) -> str:
    """
    Process custom list methods (printall()) in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with custom list methods processed
    """
    # Function to process a single line
    def process_line(line):
        # Skip processing if the line is a comment or a string literal
        if line.strip().startswith('#'):
            return line
        
        # Process printall() method
        printall_pattern = r'([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*printall\s*\(\s*\)'
        printall_matches = list(re.finditer(printall_pattern, line))
        
        for match in reversed(printall_matches):  # Process in reverse to avoid messing up positions
            list_var = match.group(1)
            start, end = match.span()
            
            # Replace with a for loop that prints each element with its index
            replacement = f"for __i, __val in enumerate({list_var}): print(f\"Index {{__i}}: {{__val}}\")"
            line = line[:start] + replacement + line[end:]
        
        return line
    
    # Process each line
    lines = source_code.split('\n')
    processed_lines = [process_line(line) for line in lines]
    
    return '\n'.join(processed_lines)


def optimize_python_code(python_code: str) -> str:
    """
    Optimize the generated Python code to make it smaller and more efficient.
    
    Args:
        python_code: The generated Python code
        
    Returns:
        Optimized Python code
    """
    # Remove unnecessary whitespace
    lines = python_code.split('\n')
    optimized_lines = []
    
    # Track imports to consolidate them
    imports = {}
    import_pattern = re.compile(r'^import\s+(\w+)$')
    from_import_pattern = re.compile(r'^from\s+(\w+)\s+import\s+(.+)$')
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Consolidate imports
        import_match = import_pattern.match(line.strip())
        if import_match:
            module = import_match.group(1)
            if module not in imports:
                imports[module] = {'type': 'import', 'items': []}
            continue
            
        from_import_match = from_import_pattern.match(line.strip())
        if from_import_match:
            module = from_import_match.group(1)
            items = [item.strip() for item in from_import_match.group(2).split(',')]
            
            if module not in imports:
                imports[module] = {'type': 'from_import', 'items': []}
            
            for item in items:
                if item not in imports[module]['items']:
                    imports[module]['items'].append(item)
            continue
        
        # Add non-import lines to the optimized code
        optimized_lines.append(line)
    
    # Reconstruct the optimized code with consolidated imports
    consolidated_imports = []
    for module, info in imports.items():
        if info['type'] == 'import':
            consolidated_imports.append(f"import {module}")
        else:  # from_import
            items = ', '.join(sorted(info['items']))
            consolidated_imports.append(f"from {module} import {items}")
    
    # Add the consolidated imports at the beginning of the file
    optimized_code = '\n'.join(consolidated_imports + [''] + optimized_lines)
    
    # Remove redundant parentheses
    optimized_code = re.sub(r'\(\(([^()]*)\)\)', r'(\1)', optimized_code)
    
    # Simplify boolean expressions
    optimized_code = re.sub(r'True\s+==\s+True', 'True', optimized_code)
    optimized_code = re.sub(r'False\s+==\s+False', 'True', optimized_code)
    optimized_code = re.sub(r'True\s+==\s+False', 'False', optimized_code)
    optimized_code = re.sub(r'False\s+==\s+True', 'False', optimized_code)
    
    # Simplify not expressions
    optimized_code = re.sub(r'not\s+False', 'True', optimized_code)
    optimized_code = re.sub(r'not\s+True', 'False', optimized_code)
    
    # Simplify if conditions
    optimized_code = re.sub(r'if\s+True\s*:', 'if True:', optimized_code)
    optimized_code = re.sub(r'if\s+False\s*:', 'if False:', optimized_code)
    
    # Remove unnecessary pass statements in non-empty blocks
    lines = optimized_code.split('\n')
    i = 0
    while i < len(lines) - 1:
        if lines[i].strip().endswith(':') and 'pass' in lines[i+1] and i+2 < len(lines) and lines[i+2].strip():
            lines.pop(i+1)  # Remove the pass line
        else:
            i += 1
    
    # Join the lines back together
    optimized_code = '\n'.join(lines)
    
    # Optimize multiple consecutive blank lines into a single blank line
    optimized_code = re.sub(r'\n\s*\n\s*\n+', '\n\n', optimized_code)
    
    # Remove trailing whitespace
    optimized_code = re.sub(r'[ \t]+$', '', optimized_code, flags=re.MULTILINE)
    
    return optimized_code


def parse_snake_code(source_code: str) -> str:
    """
    Parse Snake code and convert it to Python.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        The equivalent Python code
    """
    # Process imports
    source_code, imports = process_imports(source_code)
    
    # Process enum definitions
    source_code, enum_defs = process_enums(source_code)
    
    # Process struct definitions
    source_code, struct_defs = process_structs(source_code)
    
    # Process constant definitions
    source_code, const_defs = process_constants(source_code)
    
    # Process type casts
    source_code = process_type_casts(source_code)
    
    # Process logical operators
    source_code = process_logical_operators(source_code)
    
    # Process orelse expressions
    source_code = process_orelse(source_code)
    
    # Process for method syntax
    source_code = process_for_method(source_code)
    
    # Process increment/decrement operators
    source_code = process_increment_decrement(source_code)
    
    # Process static methods and property decorators
    source_code = process_static_and_property(source_code)
    
    # Process custom string methods
    source_code = process_string_methods(source_code)
    
    # Process string format method
    source_code = process_string_format(source_code)
    
    # Process custom list methods
    source_code = process_list_methods(source_code)
    
    # Process 'this' keyword in class methods
    source_code = process_this_keyword(source_code)
    
    # Add command-line arguments
    if '__name__' in source_code and '__main__' in source_code:
        source_code = add_command_line_args(source_code)
    
    # Generate the Python code
    python_code = generate_python_code(source_code, imports, enum_defs, struct_defs, const_defs)
    
    # Optimize the generated Python code
    optimized_code = optimize_python_code(python_code)
    
    return optimized_code


def process_increment_decrement(source_code: str) -> str:
    """
    Process increment (++) and decrement (--) operators in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with increment/decrement operators replaced
    """
    # Function to process a single line
    def process_line(line):
        # Skip processing if the line is a comment or a string literal
        if line.strip().startswith('#'):
            return line
            
        # Process increment operators (i++)
        increment_pattern = r'([A-Za-z_][A-Za-z0-9_]*)\+\+\s*;'
        line = re.sub(increment_pattern, r'\1 = \1 + 1;', line)
        
        # Process decrement operators (i--)
        decrement_pattern = r'([A-Za-z_][A-Za-z0-9_]*)\-\-\s*;'
        line = re.sub(decrement_pattern, r'\1 = \1 - 1;', line)
        
        return line
    
    # Process each line
    lines = source_code.split('\n')
    processed_lines = [process_line(line) for line in lines]
    
    return '\n'.join(processed_lines)


def process_exports(source_code: str) -> Tuple[str, Dict[str, Any]]:
    """
    Process export declarations in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Tuple containing:
        - Modified source code with export keywords removed
        - Dictionary of exported function information
    """
    exports = {}
    
    # Regular expression to match export declarations
    export_pattern = r'export\s+def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    
    # Find all export declarations
    for match in re.finditer(export_pattern, source_code):
        func_name = match.group(1)
        exports[func_name] = {'is_exported': True}
        
        # Check if this is the main function
        if func_name == 'main':
            exports[func_name]['is_main'] = True
    
    # Remove the export keyword from the source code
    modified_code = re.sub(r'export\s+def', 'def', source_code)
    
    return modified_code, exports


def process_this_keyword(source_code: str) -> str:
    """
    Process 'this' keyword in class methods, replacing it with 'self'.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with 'this' replaced with 'self'
    """
    # Replace 'this' parameter in method definitions
    # Pattern matches: def method_name(this, ...) or def method_name(this):
    method_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*this\s*([,\)])'
    source_code = re.sub(method_pattern, r'def \1(self\2', source_code)
    
    # Replace 'this.' with 'self.' in method bodies
    this_attr_pattern = r'this\.'
    source_code = re.sub(this_attr_pattern, 'self.', source_code)
    
    return source_code


def process_static_and_property(source_code: str) -> str:
    """
    Process static methods and property decorators in the source code.
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with static methods and property decorators converted to Python
    """
    # Process each line to handle indentation correctly
    lines = source_code.split('\n')
    processed_lines = []
    
    for i, line in enumerate(lines):
        # Skip processing if the line is a comment or empty
        if line.strip().startswith('#') or not line.strip():
            processed_lines.append(line)
            continue
        
        # Process static method declarations
        if 'static def ' in line:
            # Get the indentation level
            indent = line[:line.index('static')]
            # Replace 'static def' with 'def', but keep the method name and parameters
            method_line = line.replace('static def ', 'def ')
            # Add the @staticmethod decorator on the previous line with the same indentation
            processed_lines.append(f"{indent}@staticmethod")
            processed_lines.append(method_line)
        # Process property decorators
        elif 'property def ' in line:
            # Get the indentation level
            indent = line[:line.index('property')]
            # Replace 'property def' with 'def', but keep the method name and parameters
            property_line = line.replace('property def ', 'def ')
            # Add the @property decorator on the previous line with the same indentation
            processed_lines.append(f"{indent}@property")
            processed_lines.append(property_line)
        else:
            processed_lines.append(line)
    
    return '\n'.join(processed_lines)


def process_for_method(source_code: str) -> str:
    """
    Process .for() method syntax for creating for loops.
    Supports two patterns:
    1. variable.for(iterable): - Variable is both the iterator and loop variable
    2. iterable.for(variable): - Iterable is on the left, variable is in parentheses
    3. iterable.for(var1, var2, ...): - Support for multiple variables (tuple unpacking)
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with .for() method converted to standard for loops
    """
    # Pattern to match variable.for(iterable): syntax (original)
    var_for_pattern = r'^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*\.for\s*\((.*?)\):'
    
    # Pattern to match iterable.for(variable): syntax with single or multiple variables
    # This pattern captures: indentation, iterable, and variable(s)
    iterable_for_pattern = r'^(\s*)([^.]+?)\.for\s*\((.*?)\):'
    
    lines = source_code.split('\n')
    processed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check for iterable.for(variable): pattern first (new syntax)
        match_iterable = re.match(iterable_for_pattern, line)
        if match_iterable:
            indent, iterable, variables = match_iterable.groups()
            # Replace with standard for loop syntax
            # The variables part can be a single variable or multiple comma-separated variables
            processed_lines.append(f"{indent}for {variables} in {iterable}:")
        else:
            # Check for variable.for(iterable): pattern (original syntax)
            match_var = re.match(var_for_pattern, line)
            if match_var:
                indent, var_name, iterable = match_var.groups()
                # Replace with standard for loop syntax
                processed_lines.append(f"{indent}for {var_name} in {iterable}:")
            else:
                processed_lines.append(line)
        
        i += 1
    
    return '\n'.join(processed_lines)


def process_orelse(source_code: str) -> str:
    """
    Process 'orelse' expressions in the source code.
    The 'orelse' keyword provides a fallback value when an expression raises an exception.
    
    Example:
        a = expr orelse fallback;
        
    Compiles to:
        try:
            a = expr
        except:
            a = fallback
    
    Args:
        source_code: The Snake source code
        
    Returns:
        Modified source code with 'orelse' expressions converted to try-except blocks
    """
    # Pattern to match variable assignments with orelse
    # Captures: indentation, variable, expression, fallback value
    orelse_pattern = r'^(\s*)([A-Za-z_][A-Za-z0-9_]*(?:\s*:\s*[A-Za-z_][A-Za-z0-9_\[\],\s]*)?)\s*=\s*(.*?)\s+orelse\s+(.*?);'
    
    lines = source_code.split('\n')
    processed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        match = re.match(orelse_pattern, line)
        
        if match:
            indent, var_decl, expr, fallback = match.groups()
            # Replace with try-except block
            processed_lines.append(f"{indent}try:")
            processed_lines.append(f"{indent}    {var_decl} = {expr}")
            processed_lines.append(f"{indent}except:")
            processed_lines.append(f"{indent}    {var_decl} = {fallback}")
        else:
            processed_lines.append(line)
        
        i += 1
    
    return '\n'.join(processed_lines)
