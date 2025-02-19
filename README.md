# VS Code Extension Downloader

A command-line tool to download VS Code extensions from the Visual Studio Marketplace.

## Features

- Automatically detects system platform (Windows/macOS/Linux)
- Supports both ARM and x64 architectures
- Downloads platform-specific extension versions when available
- Shows download progress with a progress bar
- Optional recursive dependency downloading
- Avoids duplicate downloads
- Generates organized filenames with publisher, extension ID and version

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script and follow the prompts:

```bash
python vsix_downloader.py
```

The script will ask for:
1. A VS Code Marketplace URL
2. Whether to download dependencies

Example marketplace URLs:
- https://marketplace.visualstudio.com/items?itemName=ms-vscode.cpptools
- https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide

### Example Output

```
Enter VS Marketplace URL: https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide
Download dependencies? (y/N): y
Detected platform: darwin-arm64

Querying extension: platformio.platformio-ide
Downloading platformio-platformio-ide-3.3.4.vsix...
Extension downloaded successfully

Found dependencies: ['ms-vscode.cpptools']

Querying extension: ms-vscode.cpptools
Downloading ms-vscode-cpptools-1.24.1.vsix...
Extension downloaded successfully
```

### Features

#### Platform Detection
Automatically detects your system platform and architecture to download the correct version:
- Windows: win32-x64, win32-arm64
- macOS: darwin-x64, darwin-arm64
- Linux: linux-x64, linux-arm64, linux-armhf

#### Dependency Resolution
When enabled, automatically:
- Reads the extension manifest
- Identifies required dependencies
- Downloads all dependencies recursively
- Prevents duplicate downloads

#### Organized Output
Downloaded files are named in a consistent format:
```
{publisher}-{extension_id}-{version}.vsix
```
Example: `ms-python-python-2024.0.1.vsix`
