#
# sort_includes.py
#
# Organizes and alphabetically sorts include directives in C source files as follows:
#   Group of standard library includes (e.g. <stdlib.h>)
#   Group of custom library includes (e.g. <include.h>)
#   For source files (.c), include local associated header file (e.g. "file.h" for file.c)
#   Group of local includes (e.g. "include.h")
# A whiteline is added between these groups as well as at the end of the file if missing.
# Removes duplicates from include lists
#
# Usage: python(.exe) sort_includes.py [-h] path
# Example: py Tools\sort_includes Application\src
#
# Requires Python version 3.4 or higher
# Incompatible with Python 2.x
#
# TODO: sort includes inside #if-blocks
#

from io import StringIO
from pathlib import Path
from argparse import ArgumentParser

files_refactored = 0
excluded_dirs = [ '.git', '.vscode', 'ASF', 'config', 'lib']
excluded_files = [ 'asf.h', 'git_version.h', 'aes.c', 'aes.h' ]
stdlib_includes = [ '<assert.h>', '<complex.h>', '<ctype.h>', '<errno.h>', '<float.h>', '<inttypes.h>', 
                    '<limits.h>', '<locale.h>', '<math.h>', '<signal.h>', '<stdarg.h>', '<stdbool.h>', 
                    '<stddef.h>', '<stdint.h>', '<stdio.h>', '<stdlib.h>', '<string.h>', '<time.h>' ]

def dir_excluded(path):
    for part in path.parts:
        if part in excluded_dirs:
            return True
    return False

def file_excluded(path):
    if (path.suffix == '.c' or path.suffix == '.h'):
        return path.name in excluded_files
    return False

# Recursively get all source files (and headers) inside of the specified folder
source_file_paths = []
def collect_source_files(folder_path):
    for path in Path.iterdir(folder_path):
        if path.is_file() and not file_excluded(path):
            source_file_paths.append(path.absolute())
        if path.is_dir() and not dir_excluded(path):
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
    lib_includes_stdlib = []
    lib_includes_other = []

    for directive in sorted(lib_includes):
        if any([x in directive for x in stdlib_includes]):
            lib_includes_stdlib.append(directive)
        else:
            lib_includes_other.append(directive)
    
    # Add whiteline between stdlib and other library include directives
    if len(lib_includes_stdlib) > 0 and len(lib_includes_other) > 0:
        lib_includes_stdlib.append('')

    return lib_includes_stdlib + lib_includes_other

def sort_src_includes(file_path, src_includes):
    # Place source header at top
    if file_path.suffix == '.c':
        for directive in src_includes:
            if file_path.stem in directive: # associated header file
                src_includes.remove(directive)
                directive = '#include "{}.h"'.format(file_path.stem)  # only use basename
                if len(src_includes) > 0:
                     # put directive first and return rest of includes sorted
                    return [directive, ''] + sorted(src_includes)
                else:
                    return [directive]
    return sorted(src_includes)
            
def sort_include_lines(file_path, include_lines):
    # Get includes in the form #include <...>
    lib_includes = [x for x in include_lines if str(x).endswith('>')]

    # Get includes in the form #include "..."
    src_includes = [x for x in include_lines if str(x).endswith('\"')] 

    # Custom sorting, remove duplicates
    lib_includes = list(dict.fromkeys(sort_lib_includes(file_path, lib_includes)))
    src_includes = list(dict.fromkeys(sort_src_includes(file_path, src_includes)))

    # Buffer to write new file contents to
    out_buffer = StringIO()

    # Open file for reading and write to buffer
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
                    first_line_after_include_block = True
                    
                    # Dump all the sorted include directives here
                    for include_line in lib_includes:
                        out_buffer.write(include_line + '\n')
                    if len(lib_includes) > 0:
                        out_buffer.write('\n')
                    for include_line in src_includes:
                        out_buffer.write(include_line + '\n')
                    if len(src_includes) > 0:
                        out_buffer.write('\n')
                elif in_if_block: # Write line as-is; #include directives between #if/#endif directives are untouched
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

    # Get last line and append newline if necessary
    out_buffer.seek(out_buffer.tell() - 1)
    last_line = out_buffer.readline()
    if '\n' not in last_line:
        out_buffer.write('\n')
    out_buffer.truncate()

    with file_path.open('r+') as overwritten_file:
        overwritten_file.seek(0)
        print(out_buffer.getvalue(), file=overwritten_file, end='')
        overwritten_file.truncate()

def sort_includes(path):
    if path.is_file():
        includes = collect_include_lines(path)
        if len(includes) > 0:
            print(path)
            sort_include_lines(path, includes)
            global files_refactored
            files_refactored += 1
    elif path.is_dir():
        for file in collect_source_files(path):
            sort_includes(file)

def main():
    parser = ArgumentParser(description='Sort #include directives of a source file or source files in a directory')
    parser.add_argument('path', type=str, help='path to source file or source directory')
    args = parser.parse_args()

    if len(args.path) > 0:
        p = Path(args.path)
        if not p.exists():
            raise FileNotFoundError(p)
        else:
            sort_includes(p)
            print('Refactored', files_refactored, 'files.')

if __name__ == "__main__":
    main()
