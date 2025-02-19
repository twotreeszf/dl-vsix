#!/usr/bin/env python3

import requests
import json
import platform
import sys
import os
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

def download_with_dependencies(url, publisher, extension_id, target_platform, downloaded=None):
    """Download extension and its dependencies recursively."""
    if downloaded is None:
        downloaded = set()
    
    # Skip if already downloaded
    extension_key = f'{publisher}.{extension_id}'
    if extension_key in downloaded:
        print(f'Skipping {extension_key} (already downloaded)')
        return
    
    # Get extension info
    print(f'\nQuerying extension: {extension_key}')
    extension_info = get_extension_info(publisher, extension_id)
    download_url, version, dependencies = get_download_info(extension_info, target_platform)
    
    # Download current extension
    output_path = download_extension(download_url, publisher, extension_id, version)
    print(f'Extension downloaded successfully: {output_path}')
    downloaded.add(extension_key)
    
    # Download dependencies
    if dependencies:
        print(f'\nFound dependencies: {dependencies}')
        for dep in dependencies:
            try:
                dep_publisher, dep_id = dep.split('.')
                download_with_dependencies(download_url, dep_publisher, dep_id, target_platform, downloaded)
            except Exception as e:
                print(f'Warning: Failed to download dependency {dep}: {str(e)}')

def download_extension(url, publisher, extension_id, version, output_dir='.'):
    """Download extension with progress bar."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    # Generate filename using extension info
    filename = f'{publisher}-{extension_id}-{version}.vsix'
    output_path = os.path.join(output_dir, filename)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(output_path, 'wb') as f, tqdm(
        desc=f'Downloading {filename}',
        total=total_size,
        unit='iB',
        unit_scale=True
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            size = f.write(chunk)
            pbar.update(size)
    
    return output_path

def main():
    try:
        # Get marketplace URL
        url = input('Enter VS Marketplace URL: ').strip()
        
        # Ask about dependencies
        download_deps = input('Download dependencies? (y/N): ').strip().lower() == 'y'
        
        # Parse extension info
        publisher, extension_id = parse_extension_url(url)
        
        # Get target platform
        target_platform = get_target_platform()
        print(f'Detected platform: {target_platform}')
        
        if download_deps:
            # Download extension and its dependencies
            download_with_dependencies(url, publisher, extension_id, target_platform)
        else:
            # Download single extension
            print(f'\nQuerying extension: {publisher}.{extension_id}')
            extension_info = get_extension_info(publisher, extension_id)
            download_url, version, _ = get_download_info(extension_info, target_platform)
            output_path = download_extension(download_url, publisher, extension_id, version)
            print(f'\nExtension downloaded successfully: {output_path}')
        
    except Exception as e:
        print(f'Error: {str(e)}')
        sys.exit(1)

if __name__ == '__main__':
    main()