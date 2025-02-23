import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QMenuBar, QAction, QColorDialog, QFontDialog, QListWidget, QInputDialog
from PyQt5.QtGui import QTextCursor, QFont, QTextCharFormat, QSyntaxHighlighter, QColor
from PyQt5.QtCore import Qt, QRegExp, QEvent
import json

if os.name == 'nt':
    import msvcrt
else:
    import tty
    import termios

from autocomplete_trie import compile_trie, autocomplete, longest_common_prefix

env_vars = {}

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
    for var in env_vars:
        command_input = command_input.replace(f"${var}", env_vars[var])
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
    if args[0] == "set":
        if len(args) >= 3:
            env_vars[args[1]] = " ".join(args[2:])
    elif args[0] == "export":
        os.environ[args[1]] = env_vars.get(args[1], "")
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
        target_dir = args[1]
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

class ShellHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Commands (builtins)
        command_format = QTextCharFormat()
        command_format.setForeground(QColor("#569cd6"))  # Blue
        keywords = ["exit", "echo", "pwd", "cd", "type", "clear"]
        self.highlighting_rules.append((r'\b(' + '|'.join(keywords) + r')\b', command_format))

        # Paths
        path_format = QTextCharFormat()
        path_format.setForeground(QColor("#ce9178"))  # Orange
        self.highlighting_rules.append((r'[\'"]?([\/\.~][^\s\'"]*)[\'"]?', path_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))  # Orange
        self.highlighting_rules.append((r'"[^"]*"|\'[^\']*\'', string_format))

        # Errors
        error_format = QTextCharFormat()
        error_format.setForeground(QColor("#ff5555"))  # Red
        self.highlighting_rules.append((r'Error:.*', error_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

class ShellUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.history = []
        self.history_index = -1
        self.draft = ""
        self.current_theme = "dark"  # Add theme tracking
        self.suggestion_list = QListWidget()  # Create widget
        self.suggestion_list.hide()  # But don't add to layout yet
        self.initUI()

    def closeEvent(self, event):
        with open(os.path.expanduser("~/.shell_history"), "w") as f:
            json.dump({
                "history": self.history[-100:],
                "theme": self.current_theme
            }, f)

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
        self.layout.addWidget(self.suggestion_list) 

        self.highlighter = ShellHighlighter(self.output_text.document())

        self.output_text.append("$ ")
        self.output_text.moveCursor(QTextCursor.End)

        self.output_text.installEventFilter(self)

        self.create_menu()
        
        if os.path.exists(os.path.expanduser("~/.shell_history")):
            with open(os.path.expanduser("~/.shell_history"), "r") as f:
                data = json.load(f)
                self.history = data.get("history", [])
                self.apply_theme(data.get("theme", "dark"))

    def create_menu(self):
        menubar = self.menuBar()
        settings_menu = menubar.addMenu('Settings')

        change_font_action = QAction('Change Font', self)
        change_font_action.triggered.connect(self.change_font)
        settings_menu.addAction(change_font_action)

        change_color_action = QAction('Change Color', self)
        change_color_action.triggered.connect(self.change_color)
        settings_menu.addAction(change_color_action)

        theme_menu = menubar.addMenu('Themes')
        dark_action = QAction('Dark', self)
        dark_action.triggered.connect(lambda: self.apply_theme('dark'))
        light_action = QAction('Light', self)
        light_action.triggered.connect(lambda: self.apply_theme('light'))
        theme_menu.addAction(dark_action)
        theme_menu.addAction(light_action)
        
    def apply_theme(self, theme):
        themes = {
            'dark': {"bg": "#1e1e1e", "fg": "#d4d4d4"},
            'light': {"bg": "white", "fg": "black"}
        }
        self.output_text.setStyleSheet(
            f"background-color: {themes[theme]['bg']}; color: {themes[theme]['fg']};")
        
    def change_font(self):
        font, ok = QFontDialog.getFont()
        if ok:
            self.output_text.setFont(font)

    def change_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.output_text.setStyleSheet(f"background-color: #1e1e1e; color: {color.name()};")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key_event = event  
            if key_event.modifiers() == Qt.ControlModifier and key_event.key() == Qt.Key_R:
                self.show_history_search()
                return True

            if obj == self.output_text:
                key = key_event.key()
                cursor = self.output_text.textCursor()

                if key not in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Enter]:
                    self.show_suggestions()

                # Handle Up/Down arrows only on last line
                if key in [Qt.Key_Up, Qt.Key_Down]:
                    if cursor.hasSelection():
                        return False
                    if cursor.blockNumber() < self.output_text.document().blockCount() - 1:
                        return False
                    self.handle_history_navigation(key_event)
                    return True

                # Enter key - execute command
                elif key in [Qt.Key_Return, Qt.Key_Enter]:
                    cursor.movePosition(QTextCursor.End)
                    self.output_text.setTextCursor(cursor)
                    command_line = self.output_text.document().lastBlock().text()[2:]  # Get text after "$ "
                    self.history.append(command_line)
                    self.history_index = -1
                    execute_command(command_line, self.output_text)
                    self.output_text.append("$ ")
                    self.output_text.moveCursor(QTextCursor.End)
                    return True

                # Tab key - autocomplete
                elif key == Qt.Key_Tab:
                    self.handle_tab_completion()
                    return True

                # Backspace - prevent deletion of prompt
                elif key == Qt.Key_Backspace:
                    if cursor.positionInBlock() > 2:  # Allow deletion only after "$ "
                        return False  # Let default backspace handle it
                    else:
                        return True  # Block deletion of prompt


        return super().eventFilter(obj, event)

    def show_history_search(self):
        search, ok = QInputDialog.getText(self, "Search History", "Command:")
        if ok:
            matches = [cmd for cmd in self.history if search in cmd]
            self.suggestion_list.clear()
            self.suggestion_list.addItems(matches)
            
            
    def show_suggestions(self):
        """Show command suggestions under cursor"""
        current_text = self.get_current_line()
        suggestions = autocomplete(current_text.split()[-1] if current_text else "", trie)
        self.suggestion_list.clear()
        for sug in suggestions:
            self.suggestion_list.addItem(sug.word)
        if suggestions:
            cursor_rect = self.output_text.cursorRect()
            self.suggestion_list.move(
                self.output_text.mapToGlobal(cursor_rect.bottomLeft()))
            self.suggestion_list.show()


    def handle_history_navigation(self, event):
        if not self.history:
            return

        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        if event.key() == Qt.Key_Up:
            if self.history_index == -1:
                self.draft = self.get_current_line()
                self.history_index = len(self.history) - 1
            elif self.history_index > 0:
                self.history_index -= 1
        elif event.key() == Qt.Key_Down:
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
            else:
                self.history_index = -1

        if self.history_index >= 0:
            new_text = self.history[self.history_index]
        else:
            new_text = self.draft

        self.replace_current_line(new_text)

    def get_current_line(self):
        return self.output_text.document().lastBlock().text()[2:]

    def replace_current_line(self, text):
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText("$ " + text)
        self.output_text.setTextCursor(cursor)

    def handle_tab_completion(self):
        current_line = self.get_current_line()
        buf_words = current_line.split()
        if not buf_words:
            return

        current_word = buf_words[-1]
        if any(current_word.startswith(prefix) for prefix in ('/', './', '../', '~/', '~')):
            self.handle_path_completion(current_word, buf_words, current_line)
        else:
            self.handle_command_completion(current_word, buf_words, current_line)

    def handle_path_completion(self, current_word, buf_words, current_line):
        expanded_word = os.path.expanduser(current_word)
        dirname, partial = os.path.split(expanded_word)
        dirname = dirname or '.'
        if not os.path.exists(dirname):
            return

        try:
            files = os.listdir(dirname)
        except:
            return

        matches = [f for f in files if f.startswith(partial)]
        if not matches:
            return

        if len(matches) == 1:
            completion = matches[0][len(partial):]
            full_path = os.path.join(dirname, matches[0])
            if os.path.isdir(full_path):
                completion += '/'
            try:
                preview_items = os.listdir(full_path)[:3]
                preview = ", ".join(preview_items)
                if len(os.listdir(full_path)) > 3:
                    preview += "..."
                self.output_text.append(f"  Contents: {preview}")
            except Exception as e:
                self.output_text.append(f"  Preview error: {str(e)}")
                
            buf_words[-1] = current_word + completion
            new_line = ' '.join(buf_words)
            self.output_text.textCursor().insertText(new_line[len(current_line):])
        else:
            common_prefix = longest_common_prefix(matches)
            if common_prefix:
                common_prefix = common_prefix[len(partial):]
                buf_words[-1] = current_word + common_prefix
            else:
                self.show_completion_options(matches)

        new_line = ' '.join(buf_words)
        self.output_text.textCursor().insertText(new_line[len(current_line):])

    def handle_command_completion(self, current_word, buf_words, current_line):
        res = autocomplete(current_word, trie)
        if res:
            if len(res) == 1:
                buf_words[-1] += res[0].word
            else:
                common_prefix = longest_common_prefix([buf_words[-1] + suffix.word for suffix in res])
                if common_prefix:
                    buf_words[-1] = common_prefix
            new_line = " ".join(buf_words)
            self.output_text.textCursor().insertText(new_line[len(current_line):])

    def show_completion_options(self, matches):
        self.output_text.append("\n" + " ".join(matches))
        self.output_text.moveCursor(QTextCursor.End)

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