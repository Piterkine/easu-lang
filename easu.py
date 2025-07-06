import sys
import re

variables = {}
functions = {}
break_loop = False
continue_loop = False
return_value = None
should_return = False

def evaluate(expression):
    if expression.startswith('[') and expression.endswith(']'):
        return [get_value(x.strip()) for x in expression[1:-1].split(',') if x.strip()]

    array_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\[(\d+)\]', expression)
    if array_match:
        name, index = array_match.groups()
        index = int(index)
        if name in variables and isinstance(variables[name], list):
            return variables[name][index]
        else:
            raise Exception(f"'{name}' is not a valid array.")

    dot_call = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)(\.(push|pop|length|map|filter|forEach))\s*(.*)', expression)
    if dot_call:
        name, _, method, rest = dot_call.groups()
        if name not in variables or not isinstance(variables[name], list):
            raise Exception(f"'{name}' is not an array.")
        arr = variables[name]

        if method == 'push':
            val = get_value(rest.strip())
            arr.append(val)
        elif method == 'pop':
            arr.pop()
        elif method == 'length':
            return len(arr)
        elif method in ['map', 'filter', 'forEach']:
            func_name = rest.strip()
            if func_name not in functions:
                raise Exception(f"Function '{func_name}' not defined.")
            params, body = functions[func_name]
            results = []
            for item in arr:
                saved = variables.copy()
                variables[params[0]] = item
                global return_value, should_return
                return_value = None
                should_return = False
                run_lines(body)
                if method == 'map' and return_value is not None:
                    results.append(return_value)
                elif method == 'filter' and return_value:
                    results.append(item)
                elif method == 'forEach':
                    pass
                variables = saved
            if method in ['map', 'filter']:
                variables[name] = results
        return None

    tokens = expression.split()
    if len(tokens) == 1:
        return get_value(tokens[0])
    elif len(tokens) == 3:
        left = get_value(tokens[0])
        op = tokens[1]
        right = get_value(tokens[2])
        if op == '+': return str(left) + str(right) if isinstance(left, str) or isinstance(right, str) else left + right
        elif op == '-': return left - right
        elif op == '*': return left * right
        elif op == '/': return left / right
        elif op == '%': return left % right
        elif op == '**': return left ** right
        elif op == '//': return left // right
        elif op == '==': return left == right
        elif op == '!=': return left != right
        elif op == '<': return left < right
        elif op == '<=': return left <= right
        elif op == '>': return left > right
        elif op == '>=': return left >= right
        else: raise SyntaxError(f"Unsupported operator: {op}")
    else:
        raise SyntaxError("Invalid expression")

def get_value(token):
    if token.isdigit(): return int(token)
    elif token.replace('.', '', 1).isdigit(): return float(token)
    elif token in variables: return variables[token]
    elif token.startswith('"') and token.endswith('"'): return token[1:-1]
    else: raise NameError(f"Undefined variable '{token}'")

def run_block(lines, start_index):
    block = []
    i = start_index + 1
    brace_count = 1
    while i < len(lines):
        line = lines[i].strip()
        if '{' in line: brace_count += 1
        if '}' in line: brace_count -= 1
        if brace_count == 0: break
        block.append(line)
        i += 1
    return block, i

def run_lines(lines):
    global break_loop, continue_loop, return_value, should_return
    i = 0
    while i < len(lines):
        line = lines[i].strip().rstrip(';')
        if not line or line.startswith('//'):
            i += 1
            continue

        if line.startswith("let "):
            rest = line[4:].strip()
            if '[' in rest and '=' in rest:
                array_name = rest[:rest.index('[')].strip()
                index = int(rest[rest.index('[')+1:rest.index(']')])
                expr = rest[rest.index('=') + 1:].strip()
                val = evaluate(expr)
                if array_name in variables and isinstance(variables[array_name], list):
                    variables[array_name][index] = val
                else:
                    raise Exception(f"'{array_name}' is not a valid array.")
            else:
                name, expr = rest.split('=', 1)
                name = name.strip()
                expr = expr.strip()
                value = evaluate(expr)
                variables[name] = value

        elif line.startswith("print "):
            expr = line[6:]
            print(evaluate(expr))

        elif line == "break":
            break_loop = True
            return

        elif line == "continue":
            continue_loop = True
            return

        elif line.startswith("return "):
            expr = line[7:]
            return_value = evaluate(expr)
            should_return = True
            return

        elif line.startswith("if "):
            condition = line[3:].strip()
            if condition.endswith('{'): condition = condition[:-1].strip()
            if_true, block_end = run_block(lines, i)
            result = evaluate(condition)
            if result:
                run_lines(if_true)
            else:
                if block_end + 1 < len(lines) and lines[block_end + 1].strip().startswith("else"):
                    else_block, else_end = run_block(lines, block_end + 1)
                    run_lines(else_block)
                    i = else_end
                else:
                    i = block_end
            if should_return: return
            i = block_end

        elif line.startswith("while "):
            condition = line[6:].strip()
            if condition.endswith('{'): condition = condition[:-1].strip()
            loop_body, block_end = run_block(lines, i)
            while evaluate(condition):
                break_loop = False
                continue_loop = False
                run_lines(loop_body)
                if break_loop: break
                if should_return: return
            i = block_end

        elif line.startswith("for "):
            tokens = line[4:].split()
            var = tokens[0]
            start = get_value(tokens[2])
            end = get_value(tokens[4])
            loop_body, block_end = run_block(lines, i)
            for j in range(start, end + 1):
                variables[var] = j
                break_loop = False
                continue_loop = False
                run_lines(loop_body)
                if break_loop: break
                if continue_loop: continue
                if should_return: return
            i = block_end

        elif line.startswith("switch "):
            value = evaluate(line[7:].strip().rstrip('{').strip())
            switch_block, block_end = run_block(lines, i)
            executing = False
            default_block = []
            j = 0
            while j < len(switch_block):
                subline = switch_block[j].strip()
                if subline.startswith("case "):
                    case_val = evaluate(subline[5:].strip().rstrip(':'))
                    if value == case_val:
                        executing = True
                        j += 1
                        while j < len(switch_block) and not switch_block[j].strip().startswith(("case", "default")):
                            run_lines([switch_block[j]])
                            if break_loop or should_return: break
                            j += 1
                        break
                elif subline.startswith("default"):
                    j += 1
                    while j < len(switch_block) and not switch_block[j].strip().startswith("case"):
                        default_block.append(switch_block[j])
                        j += 1
                else:
                    j += 1
            if not executing and default_block:
                run_lines(default_block)
            i = block_end

        elif line.startswith("function "):
            parts = line.split()
            name = parts[1]
            params = parts[2:] if len(parts) > 2 else []
            if name in functions:
                raise Exception(f"Function '{name}' already defined.")
            block, block_end = run_block(lines, i)
            functions[name] = (params, block)
            i = block_end

        elif line.split()[0] in functions:
            parts = line.split()
            name = parts[0]
            args = parts[1:]
            params, body = functions[name]
            if len(params) != len(args):
                raise Exception(f"Function '{name}' expected {len(params)} args, got {len(args)}")
            saved_vars = variables.copy()
            for p, a in zip(params, args):
                variables[p] = get_value(a)
            global return_value, should_return
            return_value = None
            should_return = False
            run_lines(body)
            variables.update(saved_vars)
            if return_value is not None:
                variables[name] = return_value

        i += 1

def run_program_from_file(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
        run_lines(lines)

def run_demo_program():
    program = """
    let nums = [1, 2, 3];
    nums.push 4;
    nums.pop;
    print nums.length;

    function double x {
      return x * 2;
    }
    nums.map double;
    nums.forEach double;
    """
    run_lines(program.strip().splitlines())

if __name__ == "__main__":
    if len(sys.argv) == 2:
        run_program_from_file(sys.argv[1])
    else:
        print("Running Easu demo program...\n")
        run_demo_program()
        print("\nYou can also run a .easu file like this: python easu.py program.easu")
