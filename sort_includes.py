import argparse
from io import StringIO
from pathlib import Path

excluded_dirs = [ Path('.'), Path('.vscode'), Path('ASF'), Path('config'), Path('lib')]
excluded_files = [ Path('asf.h'), Path('git_version.h'), Path('voicecard/win32/aes.c'), Path('voicecard/win32/aes.h') ]
source_file_paths = []

# TODO: sort includes inside #if-blocks

# Recursively get all source files (and headers) inside of the specified folder
def collect_source_files(folder_path):
    for path in Path.iterdir(folder_path):
        if path.is_file() and path not in excluded_files and (path.suffix == '.c' or path.suffix == '.h'):
            source_file_paths.append(path.absolute())
        if path.is_dir() and str(path) not in excluded_dirs:
            collect_source_files(path)
    return source_file_paths

# Get all lines with an #include directive (excluding those inside of #if directives)
def collect_include_lines(file_path):
    lines = []
    in_if_block = False
    for line in file_path.open('r'):
        line = str(line).rstrip()
        if line.startswith('#include') and not in_if_block:
            lines.append(line)
        elif line.startswith('#if'):
            in_if_block = True
        elif line.startswith('#endif') and in_if_block:
            in_if_block = False
    return lines

def sort_lib_includes(file_path, lib_includes):
    stdlib_includes = ['<assert.h>', '<complex.h>', '<ctype.h>', '<errno.h>', '<float.h>', '<inttypes.h>', '<limits.h>', '<locale.h>', '<math.h>', '<signal.h>', 
                       '<stdalign.h>',  '<stdarg.h>',  '<stdbool.h>', '<stddef.h>', '<stdint.h>', '<stdio.h>', '<stdlib.h>', '<string.h>', '<time.h>']
    
    lib_includes_stdlib = []
    lib_includes_other = []

    for directive in sorted(lib_includes):
        if any([x in directive for x in stdlib_includes]):
            lib_includes_stdlib.append(directive)
        else:
            lib_includes_other.append(directive)
    
    if len(lib_includes_other) > 0:
        lib_includes_other = [''] + lib_includes_other
    return lib_includes_stdlib + lib_includes_other

def sort_src_includes(file_path, src_includes):
    if file_path.suffix == '.c':
        for directive in src_includes:
            if file_path.stem in directive: # associated header file
                src_includes.remove(directive)
                return [directive, ''] + sorted(src_includes) # put directive first and return rest of includes sorted
    return sorted(src_includes)
            
def sort_include_lines(file_path, include_lines):
    # Get includes in the form #include <...>
    lib_includes = [x for x in include_lines if str(x).endswith('>')]

    # Get includes in the form #include "..."
    src_includes = [x for x in include_lines if str(x).endswith('\"')] 

    # Custom sorting
    lib_includes = sort_lib_includes(file_path, lib_includes)
    src_includes = sort_src_includes(file_path, src_includes)

    new_includes = []
    if len(lib_includes) > 0:
        new_includes = lib_includes + ['']
    if len(src_includes) > 0:
        new_includes = new_includes + src_includes

    out_buffer = StringIO()
    last_line_is_newline = False

    # Open file for reading and writing
    with file_path.open('r+') as src_file:
        file_lines = src_file.readlines()
        in_if_block = False
        first_include_line = True
        first_line_after_include_block = False

        for line in file_lines:
            line = str(line)
            if line.startswith('#include'):
                if first_include_line:
                    first_include_line = False
                    # Dump all the sorted include directives here
                    for new_include_line in new_includes:
                        out_buffer.write(new_include_line + '\n')
                        first_line_after_include_block = True
                elif in_if_block: #print line as-is, because #include directives between #if/#endif directives are untouched
                    out_buffer.write(line)
            elif not first_include_line and line.startswith('#if'):
                out_buffer.write(line)
                in_if_block = True
                first_line_after_include_block = False
            elif not first_include_line and line.startswith('#end'):
                out_buffer.write(line)
                in_if_block = False
                first_line_after_include_block = False
            elif first_line_after_include_block and not line.strip(): # whitespace after #include blocks
                continue
            else:
                out_buffer.write(line)
                first_line_after_include_block = False
        out_buffer.truncate()

        # Add new line to output buffer if the file's last line is not a newline
        if not file_lines[-1].strip():
            last_line_is_newline = True
    
    with file_path.open('r+') as overwritten_file:
        overwritten_file.seek(0)
        end_char = '' if last_line_is_newline else '\n'
        print(out_buffer.getvalue(), file=overwritten_file, end=end_char)
        overwritten_file.truncate()

def sort_includes(path):
    if type(path) is str:
        path = Path(path)
    if path.is_file():
        includes = collect_include_lines(path)
        if len(includes) > 0:
            sort_include_lines(path, includes)
    elif path.is_dir():
        for file in collect_source_files(path):
            sort_includes(file)

def main():
    parser = argparse.ArgumentParser(description='Sort #include directives of a source file or source files in a directory')
    parser.add_argument('path', type=str, help='path to source file or source directory')
    args = parser.parse_args()

    if len(args.path) > 0:
        sort_includes(args.path)

if __name__ == "__main__":
    main()
