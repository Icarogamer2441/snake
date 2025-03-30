# Snake Language

Snake is a statically typed superset of Python that enforces type annotations and adds some syntactic sugar.

## Features

- Required static typing
- Semicolons at the end of statements (optional in Python, required in Snake)
- Struct support for defining simple data structures
- Enum support for defining enumerated types
- Import support for both Snake files and Python libraries
- Library system for creating and sharing reusable code
- Constants support for defining immutable values
- Command-line arguments support with built-in argc/argv
- C-style logical operators (&&, ||, !) alongside Python-style operators
- Python compatibility (compiles to valid Python)

## Installation

Install the Snake language interpreter:

```bash
pip install -e .
```

## Usage

Create a Snake file with the `.sk` extension:

```snake
# example.sk
def greet(name: str) -> str:
    return "Hello, " + name;

print(greet("World"));
```

Run your Snake file:

```bash
snake example.sk
```

You can also save the generated Python code to a file:

```bash
snake example.sk -o example.py
```

You can pass command-line arguments to your Snake script:

```bash
snake example.sk arg1 arg2 arg3
```

## Type System

Snake enforces static typing. All functions must have return type annotations and parameter type annotations:

```snake
# Valid Snake code
def add(a: int, b: int) -> int:
    return a + b;

# Variables can also have type annotations
x: int = 10;
```

## Struct Support

Snake supports structs for defining simple data structures:

```snake
# Define a struct
struct Point:
    x: int;
    y: int;

# Create a struct instance
p: Point = Point(1, 2);

# Access struct fields
print(p.x);  # Outputs: 1
print(p.y);  # Outputs: 2

# Modify struct fields
p.x = 3;
print(p.x);  # Outputs: 3
```

Structs can also be nested:

```snake
struct Vector3:
    x: float;
    y: float;
    z: float;

struct Particle:
    position: Vector3;
    velocity: Vector3;
    lifetime: float;

# Create a particle
particle: Particle = Particle(
    Vector3(1.0, 2.0, 3.0),
    Vector3(0.1, 0.2, 0.3),
    5.0
);
```

## Enum Support

Snake supports enums for defining enumerated types:

```snake
# Simple enum with auto-assigned values
enum Color:
    RED
    GREEN
    BLUE

# Enum with explicit values
enum Status:
    OK: str = "OK"
    ERROR: str = "ERROR"
    WARNING: str = "WARNING"

# Using enums
color: Color = Color.RED;
status: Status = Status.OK;

print(color);  # Outputs: Color.RED
print(status);  # Outputs: Status.OK

# Enums can be used as function parameters
def process_status(s: Status) -> None:
    if s == Status.ERROR:
        print("Error occurred");
    elif s == Status.WARNING:
        print("Warning occurred");
    else:
        print("Everything is OK");
```

## Constants Support

Snake supports constants for defining immutable values:

```snake
# Define constants
const PI: float = 3.14159265358979323846;
const MAX_USERS: int = 1000;
const APP_NAME: str = "Snake App";
const DEBUG_MODE: bool = True;

# Use constants in expressions
const CIRCLE_AREA: float = PI * 10 * 10;  # Area of circle with radius 10

# Use constants in functions
def calculate_circle_area(radius: float) -> float:
    return PI * radius * radius;

# Constants cannot be reassigned
# PI = 3.14;  # This would cause a runtime error

# Constants are evaluated at compile time when possible
const COMPUTED: int = 10 * 20 + 5;  # This becomes 205 at compile time
```

Constants provide several benefits:
- They clearly communicate that a value should not be changed
- They help prevent bugs by ensuring values remain constant
- They can be optimized by the compiler
- They improve code readability by giving meaningful names to literal values

## Logical Operators

Snake supports both Python-style and C-style logical operators:

```snake
# Python-style operators
result1: bool = a and b or c;
result2: bool = not a;

# C-style operators
result3: bool = a && b || c;
result4: bool = !a;

# Mixed operators (perfectly valid)
result5: bool = a && b or !c;
```

The C-style operators are converted to their Python equivalents during parsing:
- `&&` becomes `and`
- `||` becomes `or`
- `!` becomes `not`

This allows you to use the syntax you're most comfortable with, whether you're coming from Python or from languages like C, Java, or JavaScript.

Example of complex conditions:

```snake
# Check if a value is within a range
if value >= min_val && value <= max_val:
    print("Value is in range");

# Check if all conditions are met
if condition1 && condition2 && !condition3:
    print("All conditions met");

# Check if any condition is met
if condition1 || condition2 || condition3:
    print("At least one condition is met");
```

## Command-line Arguments Support

Snake provides built-in support for command-line arguments through the automatically defined `argc` and `argv` variables:

```snake
# Display the number of arguments
print("Number of arguments:", argc);

# Display all arguments
print("Arguments:", argv);

# Access individual arguments
if argc > 1:
    print("First argument:", argv[1]);
    
# Process arguments
if argc > 1:
    if argv[1] == "help":
        print("Help information");
    elif argv[1] == "version":
        print("Version 1.0.0");
```

When running a Snake script with arguments:

```bash
snake myscript.sk arg1 arg2 arg3
```

The variables will be set as follows:
- `argc` = 4 (the script name plus three arguments)
- `argv` = ["myscript.sk", "arg1", "arg2", "arg3"]

This makes it easy to create command-line utilities and scripts that process user input.

## Import Support

Snake supports importing both Snake files and Python libraries:

```snake
# Import another Snake file
import "utils.sk";

# Import Python libraries
from python import math, random;

# Use functions from the imported Snake file
result: int = add(10, 5);

# Use imported Python libraries
print(math.sqrt(16));  # Outputs: 4.0
print(random.randint(1, 100));  # Outputs: a random number between 1 and 100
```

When importing Snake files:
- The path can be relative to the current file
- The imported file's code is included in the current file
- All functions, structs, and enums from the imported file are available

When importing Python libraries:
- Use the `from python import` syntax
- Multiple libraries can be imported with a comma-separated list
- Standard Python import rules apply

## Library System

Snake includes a library system for creating and sharing reusable code:

### Creating a Library

1. Create a directory for your library with the following structure:
```
mylib/
  ├── setup.sk       # Library configuration
  ├── __main__.sk    # Main library code
  └── other_files.sk # Additional modules
```

2. Define your library configuration in `setup.sk`:
```snake
# Library metadata
name: str = "mylib";
version: str = "0.1.0";
description: str = "My awesome library";
author: str = "Your Name";

# Dependencies
dependencies: List[str] = [];  # Other Snake libraries
python_dependencies: List[str] = ["numpy", "pandas"];  # Python libraries
```

3. Create your library code in `__main__.sk` and other files.

### Installing a Library

Install a library using the `snakelib` command:

```bash
# Navigate to the library directory
cd mylib

# Install the library
snakelib install .
```

This will install the library to `~/snakelibs/mylib/`.

### Using a Library

Once installed, you can import the library in your Snake code:

```snake
# Import the library
import "mylib";

# Use functions from the library
result = mylib.some_function();
```

## Development

To install development dependencies:

```bash
pip install -e ".[dev]"
```

## License

MIT
