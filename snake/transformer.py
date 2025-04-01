"""
Transformer module for the Snake language.
Handles transforming Snake AST to valid Python code.
"""

import ast
import astor
from typing import Dict, Any, Optional, Set


class SnakeTransformer(ast.NodeTransformer):
    """
    AST transformer that converts Snake AST to Python AST.
    Handles type annotations and other Snake-specific features.
    """
    
    def __init__(self, type_annotations: Dict[str, Any]):
        self.type_annotations = type_annotations
        self.structs = {name: info for name, info in type_annotations.items() 
                       if isinstance(info, dict) and info.get('kind') == 'struct'}
        self.enums = {name: info for name, info in type_annotations.items() 
                     if isinstance(info, dict) and info.get('kind') == 'enum'}
        self.constants = {name for name, info in type_annotations.items() 
                        if isinstance(info, dict) and info.get('is_constant')}
        self.exports = {name for name, info in type_annotations.items()
                      if isinstance(info, dict) and info.get('is_exported')}
        self.has_main = any(info.get('is_main', False) for info in type_annotations.values() 
                          if isinstance(info, dict))
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """
        Process function definitions, adding type annotations as needed.
        """
        # Apply transformations to the function body
        node.body = [self.visit(stmt) for stmt in node.body]
        
        # Add type annotations if available
        if node.name in self.type_annotations:
            func_types = self.type_annotations[node.name]
            
            # Add return type annotation if not already present
            if 'return' in func_types and not node.returns:
                return_type = func_types['return']
                node.returns = ast.Name(id=return_type, ctx=ast.Load())
            
            # Add parameter type annotations if not already present
            if 'params' in func_types:
                for arg in node.args.args:
                    if hasattr(arg, 'arg') and arg.arg in func_types['params'] and not arg.annotation:
                        param_type = func_types['params'][arg.arg]
                        arg.annotation = ast.Name(id=param_type, ctx=ast.Load())
        
        return node
    
    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """
        Process assignments, adding type annotations as needed.
        Also prevent reassignment of constants.
        """
        # Check if we're trying to reassign a constant
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            if var_name in self.constants:
                # Replace with a runtime error that will be raised if this code is executed
                return ast.Raise(
                    exc=ast.Call(
                        func=ast.Name(id='RuntimeError', ctx=ast.Load()),
                        args=[ast.Constant(value=f"Cannot reassign constant '{var_name}'")],
                        keywords=[]
                    ),
                    cause=None
                )
        
        # Only handle simple assignments with a single target for now
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            
            # If we have type information for this variable
            if var_name in self.type_annotations and 'type' in self.type_annotations[var_name]:
                var_type = self.type_annotations[var_name]['type']
                
                # Create an AnnAssign node instead of Assign
                return ast.AnnAssign(
                    target=node.targets[0],
                    annotation=ast.Name(id=var_type, ctx=ast.Load()),
                    value=self.visit(node.value),
                    simple=1
                )
        
        # Default: just visit the value
        node.value = self.visit(node.value)
        return node
    
    def visit_Call(self, node: ast.Call) -> ast.Call:
        """
        Process function/constructor calls, handling struct instantiation.
        """
        # Check if this is a struct constructor call
        if isinstance(node.func, ast.Name) and node.func.id in self.structs:
            struct_name = node.func.id
            struct_info = self.structs[struct_name]
            
            # Make sure the constructor arguments match the struct fields
            if len(node.args) == len(struct_info['fields']):
                # This is a valid struct constructor call, no changes needed
                pass
        
        # Visit all arguments
        node.args = [self.visit(arg) for arg in node.args]
        if node.keywords:
            node.keywords = [self.visit(kw) for kw in node.keywords]
        
        return node
    
    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        """
        Process attribute access, handling enum members.
        """
        # Check if this is an enum member access (e.g., Color.RED)
        if isinstance(node.value, ast.Name) and node.value.id in self.enums:
            enum_name = node.value.id
            enum_info = self.enums[enum_name]
            
            # Check if the attribute is a valid enum member
            if node.attr in enum_info['members']:
                # This is a valid enum member access, no changes needed
                pass
        
        return node


def transform_to_python(python_ast: ast.Module, type_annotations: Dict[str, Any]) -> str:
    """
    Transform Snake AST to valid Python code.
    
    Args:
        python_ast: Python AST module
        type_annotations: Dictionary of type annotations
        
    Returns:
        Valid Python code as a string
    """
    # Apply transformations
    transformer = SnakeTransformer(type_annotations)
    transformed_ast = transformer.visit(python_ast)
    
    # Add main function call if it exists and is exported
    if transformer.has_main:
        # Create an if __name__ == "__main__" block to call the main function
        main_call_ast = ast.parse("""
if __name__ == "__main__":
    main()
""").body
        transformed_ast.body.extend(main_call_ast)
    
    ast.fix_missing_locations(transformed_ast)
    
    # Convert the AST back to source code
    python_code = astor.to_source(transformed_ast)
    
    return python_code
