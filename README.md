# Custom Shell with Autocompletion and Modern UI

Welcome to the Custom Shell project! This project implements a custom shell with autocompletion and a modern user interface using PyQt5. The shell supports both built-in commands and external executables, along with many advanced features to enhance user productivity.

## Features

- **Built-in Commands**: Supports common shell commands like `cd`, `pwd`, `echo`, `type`, and `clear`.
- **External Command Execution**: Automatically detects and executes external executables from the user's PATH.
- **Autocompletion**: Offers command and path autocompletion using a Trie-based algorithm.
- **Environment Variable Support**: Set and export environment variables using the `set` and `export` commands.
- **Command History and Search**: 
  - Maintains command history across sessions.
  - Navigate previous commands using the Up/Down arrow keys.
  - Search through history with Ctrl+R.
- **File Redirection**: Supports output and error redirection using operators such as `>`, `1>`, `2>`, `>>`, and `2>>`.
- **Relative Path Handling**: Seamlessly manages relative paths (e.g., `./`, `../`, `~`, `~/`).
- **Syntax Highlighting**: Provides syntax highlighting for commands, paths, strings, and error messages.
- **Directory Preview on Autocomplete**: When a directory is uniquely completed, displays a preview of its contents.
- **Modern UI & Customization**: 
  - Built with PyQt5 for a sleek, modern look.
  - Customize the interface by changing the font and text color.
  - Switch between Dark and Light themes for optimal viewing.

## Getting Started

### Prerequisites

- Python 3.x
- Pipenv
- PyQt5

### Installation

1. **Clone the repository**:
   ```sh
   git clone https://github.com/Emir2099/ShellPy.git
   cd ShellPy


2. **Install dependencies**:
   ```sh
   pipenv install

3. **Running the Shell**:
   To run the shell locally, use the following command:
   ```sh
   python main.py

4. **Usage**:
   Once the shell is running, you can use it like a regular shell. Here are some examples of supported commands:

   Change Directory:
   ```sh
   $ cd /path/to/directory
   ```
   Print Working Directory:
   ```sh
   $ pwd
   ```
   Echo Text:
   ```sh 
   $ echo "Hello, World!"
   ```
   Clear Screen:
   ```sh
   $ clear
   ```
   Type Command:
   ```sh
   $ type echo
   ```
   Set and Export Environment Variables:
   ```sh
   $ set VAR value
   $ export VAR
   ```
   Command Redirection:
   ```
   $ echo "Hello, World!" > output.txt
   ```
   History Search
   ```
   Ctrl + R
   ```

5. **Customization**:
You can customize the shell's appearance through the settings menu:

Change Font: Select "Settings" > "Change Font" to choose a different font.
Change Color: Select "Settings" > "Change Color" to choose a different text color.
Themes: Switch between Dark and Light themes from the "Themes" menu.