def process_errors(source_code: str):
    import re
    error_defs = {}

    # Support optional parameter list (with or without parentheses)
    error_pattern = r'error\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*?)\))?\s*->\s*(f?\".*?\");'

    matches = list(re.finditer(error_pattern, source_code, re.DOTALL))
    for match in matches:
        err_name = match.group(1)
        params_str = match.group(2)
        msg_expr = match.group(3).strip()

        params = []
        if params_str:
            params_str = params_str.strip()
            if params_str:
                # Parse parameters
                for param in params_str.split(','):
                    pname, ptype = param.strip().split(':')
                    pname = pname.strip()
                    ptype = ptype.strip()
                    params.append((pname, ptype))

        # Save param metadata
        error_defs[err_name] = {
            'kind': 'error',
            'params': {p: t for p, t in params}
        }

        # Before generating class code, rewrite message placeholders to use self.<param>
        if params:
            for pname, _ in params:
                # Replace {param} with {self.param} inside the message string (string stays f-prefixed)
                msg_expr = re.sub(rf'\{{\s*{pname}\s*\}}', r'{self.' + pname + '}', msg_expr)

        # Generate replacement class code
        lines = [f"class {err_name}(Exception):"]

        if params:
            init_signature = ", ".join(f"{p}: {t}" for p, t in params)
            lines.append(f"    def __init__(self, {init_signature}):")
            for pname, _ in params:
                lines.append(f"        self.{pname} = {pname}")
        else:
            lines.append("    def __init__(self):")
            lines.append("        pass")

        lines.append("    def __str__(self):")
        lines.append(f"        return {msg_expr}")
        lines.append("")

        class_code = "\n".join(lines)

        # Replace the entire error definition with the generated class
        source_code = source_code.replace(match.group(0), class_code)

    return source_code, error_defs