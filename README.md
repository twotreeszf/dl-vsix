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
- Robust download with automatic retry mechanism
- File integrity verification

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

Analyzing dependencies...
Querying extension: platformio.platformio-ide
Found dependencies: ['ms-vscode.cpptools']
Querying extension: ms-vscode.cpptools

Found 2 extension(s) to download

Downloading [1/2]: ms-vscode.cpptools
Downloading 01-ms-vscode-cpptools-1.24.1.vsix: 100%|██████████| 77.9M/77.9M [00:19<00:00, 4.04MiB/s]
Successfully downloaded: downloads/01-ms-vscode-cpptools-1.24.1.vsix

Downloading [2/2]: platformio.platformio-ide
Downloading 02-platformio-platformio-ide-3.3.4.vsix: 100%|██████████| 3.23M/3.23M [00:01<00:00, 2.65MiB/s]
Successfully downloaded: downloads/02-platformio-platformio-ide-3.3.4.vsix
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
Downloaded files are stored in the `downloads` subdirectory with a consistent naming format:
```
{index}-{publisher}-{extension_id}-{version}.vsix
```
Example: 
- `01-ms-vscode-cpptools-1.24.1.vsix`
- `02-platformio-platformio-ide-3.3.4.vsix`

The numeric prefix indicates the installation order, ensuring dependencies are installed first.
