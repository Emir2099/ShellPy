# Custom Shell with Autocompletion and Modern UI

Welcome to the Custom Shell project! This project implements a custom shell with autocompletion and a modern user interface using PyQt5. The shell supports built-in commands, external executables, and provides a customizable UI.

## Features

- **Built-in Commands**: Supports common shell commands like `cd`, `pwd`, `echo`, `type`, and `clear`.
- **Autocompletion**: Provides autocompletion for built-in commands and external executables in the user's PATH.
- **Modern UI**: A sleek and modern user interface built with PyQt5.
- **Customization**: Allows users to change the font and text color through a settings menu.

## Getting Started

### Prerequisites

- Python 3.x
- Pipenv
- PyQt5

### Installation

1. **Clone the repository**:
   ```sh
   git clone https://github.com/yourusername/custom-shell.git
   cd custom-shell

2. **Install dependencies**:
   ```sh
   pipenv install

3. **Running the Shell**:
   To run the shell locally, use the following command:
   ```sh
   main.py

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

5. **Customization**:
You can customize the shell's appearance through the settings menu:

Change Font: Select "Settings" > "Change Font" to choose a different font.
Change Color: Select "Settings" > "Change Color" to choose a different text color.