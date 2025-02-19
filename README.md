# VS Code Extension Downloader

A simple tool to download VS Code extensions from the Visual Studio Marketplace.

## Features

- Automatically detects system platform (Windows/macOS/Linux)
- Supports both ARM and x64 architectures
- Downloads platform-specific extension versions when available
- Shows download progress with a progress bar
- Handles marketplace URL

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script and enter a VS Code Marketplace URL when prompted:

```bash
python vsix_downloader.py
```

Example marketplace URLs:
- https://marketplace.visualstudio.com/items?itemName=ms-vscode.cpptools
- https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide

The extension will be downloaded to the current directory.
