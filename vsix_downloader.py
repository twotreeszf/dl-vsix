#!/usr/bin/env python3

import requests
import json
import platform
import sys
import os
import time
import subprocess
from tqdm import tqdm
import re

# Constants
API_ENDPOINT = 'https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery'
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json;api-version=7.0-preview.1'
}

def get_target_platform():
    """Detect the current system's platform for downloading the correct extension version."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == 'darwin':
        if 'arm' in machine:
            return 'darwin-arm64'
        return 'darwin-x64'
    elif system == 'windows':
        if 'arm' in machine:
            return 'win32-arm64'
        return 'win32-x64'
    elif system == 'linux':
        if 'aarch64' in machine:
            return 'linux-arm64'
        elif 'armv7' in machine:
            return 'linux-armhf'
        return 'linux-x64'
    return 'web'

def parse_extension_url(url):
    """Parse publisher and extension ID from marketplace URL."""
    pattern = r'marketplace\.visualstudio\.com/items\?itemName=([^.]+)\.([^&]+)'
    match = re.search(pattern, url)
    if not match:
        raise ValueError('Invalid marketplace URL format')
    return match.group(1), match.group(2)

def get_extension_info(publisher, extension_id):
    """Query extension information from marketplace."""
    payload = {
        'assetTypes': None,
        'filters': [{
            'criteria': [{
                'filterType': 7,
                'value': f'{publisher}.{extension_id}'
            }],
            'direction': 2,
            'pageSize': 100,
            'pageNumber': 1,
            'sortBy': 0,
            'sortOrder': 0,
            'pagingToken': None
        }],
        'flags': 2151
    }
    
    response = requests.post(API_ENDPOINT, json=payload, headers=HEADERS)
    response.raise_for_status()
    return response.json()

class Extension:
    """Represents a VS Code extension with its dependencies."""
    def __init__(self, publisher, extension_id, version=None, download_url=None, dependencies=None):
        self.publisher = publisher
        self.extension_id = extension_id
        self.version = version
        self.download_url = download_url
        self.dependencies = dependencies or []
        self.key = f'{publisher}.{extension_id}'
    
    def __str__(self):
        return self.key

def get_extension_manifest(version):
    """Get the manifest content from extension version."""
    try:
        for file in version['files']:
            if file['assetType'] == 'Microsoft.VisualStudio.Code.Manifest':
                response = requests.get(file['source'])
                response.raise_for_status()
                return response.json()
        return None
    except Exception:
        return None

def get_extension_dependencies(manifest):
    """Extract extension dependencies from manifest."""
    if not manifest:
        return []
    return manifest.get('extensionDependencies', [])

def get_download_info(extension_info, target_platform):
    """Extract download URL, version and dependencies for specific platform from extension info."""
    try:
        result = extension_info['results'][0]
        extension = result['extensions'][0]
        versions = extension['versions']
        
        # Find version matching our platform
        for version in versions:
            target = version.get('targetPlatform', '')
            if target.lower() == target_platform.lower():
                version_str = version.get('version')
                download_url = None
                
                # Get manifest and VSIX package
                manifest = get_extension_manifest(version)
                dependencies = get_extension_dependencies(manifest)
                
                for file in version['files']:
                    if file['assetType'] == 'Microsoft.VisualStudio.Services.VSIXPackage':
                        download_url = file['source']
                        break
                
                if download_url:
                    return download_url, version_str, dependencies
                
        raise ValueError(f'No package found for platform: {target_platform}')
    except (KeyError, IndexError) as e:
        raise ValueError(f'Failed to parse extension info: {str(e)}')

def build_dependency_tree(extension, target_platform, visited=None):
    """Build a dependency tree for the extension."""
    if visited is None:
        visited = set()
    
    if extension.key in visited:
        return extension
    
    visited.add(extension.key)
    print(f'Querying extension: {extension.key}')
    
    # Get extension info
    extension_info = get_extension_info(extension.publisher, extension.extension_id)
    download_url, version, dependencies = get_download_info(extension_info, target_platform)
    
    # Update extension info
    extension.version = version
    extension.download_url = download_url
    
    # Process dependencies
    if dependencies:
        print(f'Found dependencies: {dependencies}')
        for dep in dependencies:
            try:
                dep_publisher, dep_id = dep.split('.')
                dep_extension = Extension(dep_publisher, dep_id)
                extension.dependencies.append(build_dependency_tree(dep_extension, target_platform, visited))
            except Exception as e:
                print(f'Warning: Failed to process dependency {dep}: {str(e)}')
    
    return extension

def get_download_order(extension, order=None, visited=None):
    """Get the download order for extensions (dependencies first)."""
    if order is None:
        order = []
    if visited is None:
        visited = set()
    
    if extension.key in visited:
        return
    
    # Process dependencies first
    for dep in extension.dependencies:
        get_download_order(dep, order, visited)
    
    # Add current extension
    if extension.key not in visited:
        order.append(extension)
        visited.add(extension.key)
    
    return order

def download_with_retry(url, output_path, filename, max_retries=3):
    """Download file with retry mechanism."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            temp_path = output_path + '.tmp'
            
            with open(temp_path, 'wb') as f, tqdm(
                desc=f'Downloading {filename}',
                total=total_size,
                unit='iB',
                unit_scale=True
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    size = f.write(chunk)
                    pbar.update(size)
            
            # Verify file size
            if os.path.getsize(temp_path) == total_size:
                os.rename(temp_path, output_path)
                return True
            else:
                print(f'Download incomplete, retrying ({attempt + 1}/{max_retries})')
                continue
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f'Download failed: {str(e)}')
                print(f'Retrying ({attempt + 1}/{max_retries})...')
                time.sleep(1)  # Wait before retry
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise
    
    return False

def download_extension(extension, index, total, output_dir='downloads'):
    """Download extension with progress bar and retry mechanism."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with order prefix
    filename = f'{index:02d}-{extension.publisher}-{extension.extension_id}-{extension.version}.vsix'
    output_path = os.path.join(output_dir, filename)
    
    # Skip if already downloaded and size is correct
    if os.path.exists(output_path):
        print(f'Skipping {filename} (already exists)')
        return output_path
    
    print(f'\nDownloading [{index}/{total}]: {extension.key}')
    
    # Download file with retry
    if download_with_retry(extension.download_url, output_path, filename):
        return output_path
    else:
        raise Exception('Download failed after all retries')

def install_extensions(downloaded_files):
    """Install downloaded extensions in Windsurf."""
    windsurf_cli = '/Applications/Windsurf.app/Contents/Resources/app/bin/windsurf'
    
    if not os.path.exists(windsurf_cli):
        print('Windsurf not found. Please make sure it is installed in /Applications')
        return False
    
    print('\nInstalling extensions in Windsurf...')
    for file in downloaded_files:
        print(f'Installing {os.path.basename(file)}...')
        try:
            result = subprocess.run(
                [windsurf_cli, '--install-extension', file],
                capture_output=True,
                text=True,
                check=True
            )
            print('Successfully installed')
        except subprocess.CalledProcessError as e:
            print(f'Failed to install: {e.stderr}')
            return False
    
    print('\nAll extensions installed successfully!')
    return True

def main():
    try:
        # Get marketplace URL
        url = input('Enter VS Marketplace URL: ').strip()
        
        # Ask about dependencies
        download_deps = input('Download dependencies? (y/N): ').strip().lower() == 'y'
        
        # Parse extension info
        publisher, extension_id = parse_extension_url(url)
        extension = Extension(publisher, extension_id)
        
        # Get target platform
        target_platform = get_target_platform()
        print(f'Detected platform: {target_platform}')
        
        # Build dependency tree
        print('\nAnalyzing dependencies...')
        root = build_dependency_tree(extension, target_platform)
        
        downloaded_files = []
        if download_deps:
            # Get download order (dependencies first)
            download_list = get_download_order(root)
            total = len(download_list)
            print(f'\nFound {total} extension(s) to download')
            
            # Download all extensions in order
            for i, ext in enumerate(download_list, 1):
                try:
                    output_path = download_extension(ext, i, total)
                    downloaded_files.append(output_path)
                    print(f'Successfully downloaded: {output_path}')
                except Exception as e:
                    print(f'Error downloading {ext.key}: {str(e)}')
        else:
            # Download single extension
            output_path = download_extension(root, 1, 1)
            downloaded_files.append(output_path)
            print(f'Successfully downloaded: {output_path}')
        
        # Ask to install in Windsurf
        if downloaded_files:
            install = input('\nInstall extensions in Windsurf? (y/N): ').strip().lower() == 'y'
            if install:
                install_extensions(downloaded_files)
        
    except Exception as e:
        print(f'Error: {str(e)}')
        sys.exit(1)

if __name__ == '__main__':
    main()