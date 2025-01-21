import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QMenuBar, QAction, QColorDialog, QFontDialog
from PyQt5.QtGui import QTextCursor, QFont
from PyQt5.QtCore import Qt

if os.name == 'nt':
    import msvcrt
else:
    import tty
    import termios

from autocomplete_trie import compile_trie, autocomplete, longest_common_prefix

def populate_path_map():
    path_env = os.environ.get("PATH")
    if not path_env:
        return {}
    file_map = {}
    paths = path_env.split(":") if os.name != 'nt' else path_env.split(";")
    paths.append(".")
    for path in paths:
        if not os.path.exists(path):
            continue
        files = os.listdir(path)
        for file in files:
            if os.path.isfile(os.path.join(path, file)) and os.access(os.path.join(path, file), os.X_OK):
                file_map[file] = os.path.join(path, file)
    return file_map

def get_relative_path(working_directory, relative_path):
    current_path = []
    folders = relative_path.split("/")
    for idx, folder in enumerate(folders):
        if folder == ".":
            if idx > 0:
                return None
            current_path.append(working_directory)
        elif folder == "..":
            if idx == 0:
                current_path = working_directory.split("/")
            current_path.pop()
        elif folder:
            current_path.append(folder)
    return "/".join(current_path)

def parse_arguments(command_input):
    command = []
    curr_command = ""
    single_quoted = False
    double_quoted = False
    backslashed = False
    for ch in command_input:
        if backslashed:
            if backslashed and double_quoted:
                if ch == "n":
                    curr_command += "\\n"
                elif ch in ["\\", "$", '"']:
                    curr_command += ch
                else:
                    curr_command += "\\"
                    curr_command += ch
                backslashed = False
            else:
                curr_command += ch
                backslashed = False
        elif ch == "\\":
            if single_quoted:
                curr_command += ch
            else:
                backslashed = True
        elif ch == '"':
            if single_quoted:
                curr_command += ch
            elif not double_quoted:
                double_quoted = True
            else:
                double_quoted = False
        elif ch == "'":
            if double_quoted:
                curr_command += ch
            elif not single_quoted:
                single_quoted = True
            else:
                single_quoted = False
        elif ch == " ":
            if not single_quoted and not double_quoted:
                if curr_command:
                    command.append(curr_command)
                    curr_command = ""
            else:
                curr_command += ch
        else:
            curr_command += ch
    if curr_command:
        command.append(curr_command)
    return command

class FileDescriptor:
    def __init__(self, filepath, write_strategy):
        self.filepath = filepath
        self.write_strategy = write_strategy

def parse_pipes(commands):
    idx = 0
    executions = []
    output_file = None
    err_file = None
    while idx < len(commands):
        if commands[idx] in [">", "1>"]:
            output_file = FileDescriptor(commands[idx + 1], "w")
            idx += 2
        elif commands[idx] == "2>":
            err_file = FileDescriptor(commands[idx + 1], "w")
            idx += 2
        elif commands[idx] in [">>", "1>>"]:
            output_file = FileDescriptor(commands[idx + 1], "a")
            idx += 2
        elif commands[idx] in ["2>>"]:
            err_file = FileDescriptor(commands[idx + 1], "a")
            idx += 2
        else:
            executions.append(commands[idx])
            idx += 1
    return executions, output_file, err_file

def output_result(result, output_file):
    if output_file is None:
        print(result)
        return
    with open(output_file.filepath, output_file.write_strategy) as f:
        f.write(result)
        f.write("\n")

def output_err(result, error_file):
    if error_file is None:
        print(result)
        return
    with open(error_file.filepath, error_file.write_strategy) as f:
        f.write(result)
        f.write("\n")

def execute_command(command, output_text):
    args = parse_arguments(command)
    if not args:
        output_text.append("Error: No command entered\n")
        return
    args, output_file, err_file = parse_pipes(args)
    if err_file is not None and not os.path.exists(err_file.filepath):
        folder_path = "/".join(err_file.filepath.split("/")[:-1])
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        with open(err_file.filepath, "a"):
            pass
    if args[0] == "exit":
        if len(args) == 1:
            sys.exit(0)
        try:
            sys.exit(int(args[1]))
        except ValueError:
            output_text.append("Error: Invalid exit code\n")
    elif args[0] == "echo":
        output_result(" ".join(args[1:]), output_file)
        output_text.append(" ".join(args[1:]) + "\n")
    elif args[0] == "pwd":
        output_result(os.getcwd(), output_file)
        output_text.append(os.getcwd() + "\n")
    elif args[0] == "cd":
        if len(args) < 2:
            output_text.append("Error: Missing argument for cd\n")
            return
        full_path = None
        if args[1][0] == "/":
            if os.path.exists(args[1]):
                full_path = args[1]
            else:
                output_err(f"cd: {args[1]}: No such file or directory", err_file)
                output_text.append(f"cd: {args[1]}: No such file or directory\n")
                return
        elif os.name == 'nt' and ":" in args[1]:
            if os.path.exists(args[1]):
                full_path = args[1]
            else:
                output_err(f"cd: {args[1]}: No such file or directory", err_file)
                output_text.append(f"cd: {args[1]}: No such file or directory\n")
                return
        elif "./" in args[1]:
            relative_path = get_relative_path(os.getcwd(), args[1])
            if relative_path:
                full_path = relative_path
            else:
                output_err(f"cd: {args[1]}: No such file or directory", err_file)
                output_text.append(f"cd: {args[1]}: No such file or directory\n")
                return
        elif args[1] == "~":
            full_path = os.path.expanduser("~")
        elif args[1][0:2] == "~/":
            relative_path = get_relative_path(os.path.expanduser("~"), args[1][2:])
            if relative_path:
                full_path = relative_path
            else:
                output_err(f"cd: {args[1]}: No such file or directory", err_file)
                output_text.append(f"cd: {args[1]}: No such file or directory\n")
                return
        if full_path:
            os.chdir(full_path)
    elif args[0] == "type":
        if len(args) < 2:
            output_text.append("Error: Missing argument for type\n")
            return
        if args[1] in builtins:
            output_result(f"{args[1]} is a shell builtin", output_file)
            output_text.append(f"{args[1]} is a shell builtin\n")
        elif args[1] in path_map:
            output_result(f"{args[1]} is {path_map[args[1]]}", output_file)
            output_text.append(f"{args[1]} is {path_map[args[1]]}\n")
        else:
            output_err(f"{args[1]}: not found", err_file)
            output_text.append(f"{args[1]}: not found\n")
    elif args[0] == "clear":
        output_text.clear()
        output_text.append("$ ")
    elif args[0] in path_map:
        saved_dir = os.getcwd()
        stdoutfile = (
            open(output_file.filepath, output_file.write_strategy)
            if output_file
            else None
        )
        stderrfile = (
            open(err_file.filepath, err_file.write_strategy) if err_file else None
        )
        os.chdir("/".join(path_map[args[0]].split("/")[:-1]))
        sub_args = args[1:]
        result = subprocess.run(
            [path_map[args[0]].split("/")[-1]] + sub_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        os.chdir(saved_dir)
        output_text.append(result.stdout.decode() + "\n")
        if result.stderr:
            output_text.append(result.stderr.decode() + "\n")
    else:
        output_result(f"{command}: command not found", output_file)
        output_text.append(f"{command}: command not found\n")

class ShellUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Shell UI")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.output_text = QTextEdit(self)
        self.output_text.setReadOnly(False)
        self.output_text.setFont(QFont("Courier", 10))
        self.output_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        self.layout.addWidget(self.output_text)

        self.output_text.append("$ ")
        self.output_text.moveCursor(QTextCursor.End)

        self.output_text.installEventFilter(self)

        self.create_menu()

    def create_menu(self):
        menubar = self.menuBar()
        settings_menu = menubar.addMenu('Settings')

        change_font_action = QAction('Change Font', self)
        change_font_action.triggered.connect(self.change_font)
        settings_menu.addAction(change_font_action)

        change_color_action = QAction('Change Color', self)
        change_color_action.triggered.connect(self.change_color)
        settings_menu.addAction(change_color_action)

    def change_font(self):
        font, ok = QFontDialog.getFont()
        if ok:
            self.output_text.setFont(font)

    def change_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.output_text.setStyleSheet(f"background-color: #1e1e1e; color: {color.name()};")

    def eventFilter(self, obj, event):
        if obj == self.output_text and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                cursor = self.output_text.textCursor()
                cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
                self.output_text.setTextCursor(cursor)
                command = self.output_text.toPlainText().split("\n")[-1][2:]
                self.output_text.append("")
                execute_command(command, self.output_text)
                self.output_text.append("$ ")
                self.output_text.moveCursor(QTextCursor.End)
                return True
            elif event.key() == Qt.Key_Tab:
                cursor = self.output_text.textCursor()
                cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
                self.output_text.setTextCursor(cursor)
                current_line = self.output_text.toPlainText().split("\n")[-1][2:]
                buf_words = current_line.split()
                if buf_words:
                    res = autocomplete(buf_words[-1], trie)
                    if res:
                        if len(res) == 1:
                            buf_words[-1] += res[0].word
                        else:
                            common_prefix = longest_common_prefix([buf_words[-1] + suffix.word for suffix in res])
                            if common_prefix:
                                buf_words[-1] = common_prefix
                        new_line = " ".join(buf_words)
                        self.output_text.textCursor().insertText(new_line[len(current_line):])
                return True
            elif event.key() == Qt.Key_Backspace:
                cursor = self.output_text.textCursor()
                cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
                if cursor.selectedText().startswith("$ "):
                    cursor.clearSelection()
                else:
                    cursor.deletePreviousChar()
                return True
        return super().eventFilter(obj, event)

def main():
    global builtins, path_map, trie
    builtins = ["exit", "echo", "type", "pwd", "clear"]
    path_map = populate_path_map()
    trie = compile_trie(list(path_map.keys()) + builtins)

    app = QApplication(sys.argv)
    shell_ui = ShellUI()
    shell_ui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()