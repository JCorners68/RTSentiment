"""
Dependency health check system for the Kanban CLI.

This module provides tools to verify and repair Python and Node.js
dependencies, ensuring that all required packages are installed correctly.
"""
import os
import sys
import platform
import subprocess
import importlib
import logging
import pkg_resources
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import shutil

from ..config.settings import get_project_root, load_config

# Configure module logger
logger = logging.getLogger(__name__)

class DependencyCheckResult:
    """Result of a dependency health check."""
    
    def __init__(self):
        """Initialize a new dependency check result."""
        self.python_version = sys.version
        self.platform = platform.platform()
        self.python_path = sys.executable
        self.timestamp = None
        
        # Python packages
        self.python_packages_required = []
        self.python_packages_missing = []
        self.python_packages_outdated = []
        self.python_packages_ok = []
        
        # Node.js
        self.node_installed = False
        self.node_version = None
        self.npm_version = None
        self.node_packages_required = []
        self.node_packages_missing = []
        self.node_packages_outdated = []
        self.node_packages_ok = []
        
        # Optional dependencies
        self.optional_packages_missing = []
        
        # Overall status
        self.status = "unknown"
        self.errors = []
        self.warnings = []
        self.repair_actions = []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary for serialization.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            "python_version": self.python_version,
            "platform": self.platform,
            "python_path": self.python_path,
            "timestamp": self.timestamp,
            "python_packages": {
                "required": self.python_packages_required,
                "missing": self.python_packages_missing,
                "outdated": self.python_packages_outdated,
                "ok": self.python_packages_ok
            },
            "node": {
                "installed": self.node_installed,
                "version": self.node_version,
                "npm_version": self.npm_version,
                "packages": {
                    "required": self.node_packages_required,
                    "missing": self.node_packages_missing,
                    "outdated": self.node_packages_outdated,
                    "ok": self.node_packages_ok
                }
            },
            "optional_packages_missing": self.optional_packages_missing,
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "repair_actions": self.repair_actions
        }

def check_python_dependencies(requirements_file: Optional[Path] = None) -> Tuple[List[str], List[Dict], List[str]]:
    """
    Check Python dependencies against requirements file.
    
    Args:
        requirements_file: Path to requirements.txt file. If None, looks in project root.
        
    Returns:
        Tuple containing:
            - List of missing packages
            - List of outdated packages with current and required versions
            - List of successfully installed packages
    """
    # Get project root
    project_root = get_project_root()
    
    # Find requirements file if not provided
    if requirements_file is None:
        requirements_file = project_root / "requirements.txt"
    
    # Check if requirements file exists
    if not requirements_file.exists():
        logger.warning(f"Requirements file not found at {requirements_file}")
        return [], [], []
    
    # Read requirements file
    with open(requirements_file, 'r') as f:
        requirements_content = f.read()
    
    # Parse requirements
    requirements = {}
    for line in requirements_content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Handle options like -e or -r
        if line.startswith('-'):
            continue
        
        # Split package name and version specification
        if '>=' in line:
            name, version = line.split('>=', 1)
            requirements[name.strip()] = {'min_version': version.strip(), 'operator': '>='}
        elif '==' in line:
            name, version = line.split('==', 1)
            requirements[name.strip()] = {'exact_version': version.strip(), 'operator': '=='}
        elif '<=' in line:
            name, version = line.split('<=', 1)
            requirements[name.strip()] = {'max_version': version.strip(), 'operator': '<='}
        elif '>' in line:
            name, version = line.split('>', 1)
            requirements[name.strip()] = {'min_version': version.strip(), 'operator': '>'}
        elif '<' in line:
            name, version = line.split('<', 1)
            requirements[name.strip()] = {'max_version': version.strip(), 'operator': '<'}
        else:
            # No version specified
            requirements[line.strip()] = {'operator': None}
    
    # Check installed packages
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    
    missing_packages = []
    outdated_packages = []
    ok_packages = []
    
    for package, req in requirements.items():
        # Normalize package name
        package_key = package.lower().replace('-', '_')
        
        # Check if package is installed
        if package_key not in installed_packages:
            missing_packages.append(package)
            continue
        
        installed_version = installed_packages[package_key]
        
        # Check version requirements
        if req['operator'] == '==':
            if installed_version != req['exact_version']:
                outdated_packages.append({
                    'name': package,
                    'installed_version': installed_version,
                    'required_version': req['exact_version'],
                    'operator': '=='
                })
            else:
                ok_packages.append(package)
        elif req['operator'] == '>=':
            if pkg_resources.parse_version(installed_version) < pkg_resources.parse_version(req['min_version']):
                outdated_packages.append({
                    'name': package,
                    'installed_version': installed_version,
                    'required_version': f">={req['min_version']}",
                    'operator': '>='
                })
            else:
                ok_packages.append(package)
        elif req['operator'] == '<=':
            if pkg_resources.parse_version(installed_version) > pkg_resources.parse_version(req['max_version']):
                outdated_packages.append({
                    'name': package,
                    'installed_version': installed_version,
                    'required_version': f"<={req['max_version']}",
                    'operator': '<='
                })
            else:
                ok_packages.append(package)
        elif req['operator'] == '>':
            if pkg_resources.parse_version(installed_version) <= pkg_resources.parse_version(req['min_version']):
                outdated_packages.append({
                    'name': package,
                    'installed_version': installed_version,
                    'required_version': f">{req['min_version']}",
                    'operator': '>'
                })
            else:
                ok_packages.append(package)
        elif req['operator'] == '<':
            if pkg_resources.parse_version(installed_version) >= pkg_resources.parse_version(req['max_version']):
                outdated_packages.append({
                    'name': package,
                    'installed_version': installed_version,
                    'required_version': f"<{req['max_version']}",
                    'operator': '<'
                })
            else:
                ok_packages.append(package)
        else:
            # No version requirement
            ok_packages.append(package)
    
    return missing_packages, outdated_packages, ok_packages

def check_optional_dependencies() -> List[Dict[str, str]]:
    """
    Check for optional dependencies that enhance functionality but aren't required.
    
    Returns:
        List of missing optional packages with package name and description
    """
    optional_packages = [
        {"name": "python-magic", "description": "Better MIME type detection for attachments"},
        {"name": "rich", "description": "Enhanced terminal output formatting"},
        {"name": "pygments", "description": "Syntax highlighting for code previews"},
        {"name": "colorama", "description": "Cross-platform colored terminal output"},
        {"name": "tqdm", "description": "Progress bars for long-running operations"}
    ]
    
    missing_optional = []
    
    for package in optional_packages:
        try:
            importlib.import_module(package["name"].replace('-', '_'))
        except ImportError:
            missing_optional.append(package)
    
    return missing_optional

def check_node_environment() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if Node.js is installed and get its version.
    
    Returns:
        Tuple containing:
            - Boolean indicating if Node.js is installed
            - Node.js version string or None
            - npm version string or None
    """
    # Check Node.js
    try:
        node_version_output = subprocess.check_output(["node", "--version"], universal_newlines=True).strip()
        node_installed = True
        node_version = node_version_output
    except (subprocess.SubprocessError, FileNotFoundError):
        node_installed = False
        node_version = None
    
    # Check npm
    npm_version = None
    if node_installed:
        try:
            npm_version_output = subprocess.check_output(["npm", "--version"], universal_newlines=True).strip()
            npm_version = npm_version_output
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    return node_installed, node_version, npm_version

def check_node_dependencies(package_json_path: Optional[Path] = None) -> Tuple[List[str], List[Dict], List[str]]:
    """
    Check Node.js dependencies against package.json file.
    
    Args:
        package_json_path: Path to package.json file. If None, looks in node server dir.
        
    Returns:
        Tuple containing:
            - List of missing packages
            - List of outdated packages with current and required versions
            - List of successfully installed packages
    """
    # Get project root
    project_root = get_project_root()
    
    # Find package.json file if not provided
    if package_json_path is None:
        package_json_path = project_root / "ui" / "kanban" / "server" / "package.json"
    
    # Check if Node.js is installed
    node_installed, _, _ = check_node_environment()
    if not node_installed:
        logger.warning("Node.js is not installed")
        return [], [], []
    
    # Check if package.json exists
    if not package_json_path.exists():
        logger.warning(f"package.json not found at {package_json_path}")
        return [], [], []
    
    # Read package.json
    with open(package_json_path, 'r') as f:
        package_json = json.load(f)
    
    # Get dependencies
    dependencies = {}
    dependencies.update(package_json.get("dependencies", {}))
    dependencies.update(package_json.get("devDependencies", {}))
    
    # Get node_modules directory
    node_modules_dir = package_json_path.parent / "node_modules"
    
    # Check if node_modules exists
    if not node_modules_dir.exists():
        # All dependencies are missing
        return list(dependencies.keys()), [], []
    
    # Check installed packages
    missing_packages = []
    outdated_packages = []
    ok_packages = []
    
    for package, version_req in dependencies.items():
        # Check if package is installed
        package_dir = node_modules_dir / package
        if not package_dir.exists():
            missing_packages.append(package)
            continue
        
        # Check package version
        package_json_path = package_dir / "package.json"
        if not package_json_path.exists():
            missing_packages.append(package)
            continue
        
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            installed_version = package_data.get("version")
            if not installed_version:
                missing_packages.append(package)
                continue
            
            # Parse version requirement
            version_req = version_req.strip()
            if version_req.startswith('^'):
                # Caret range (^) means compatible with the specified version
                required_version = version_req[1:]
                major_version = required_version.split('.')[0]
                installed_major = installed_version.split('.')[0]
                
                if installed_major != major_version:
                    outdated_packages.append({
                        'name': package,
                        'installed_version': installed_version,
                        'required_version': version_req,
                        'operator': '^'
                    })
                else:
                    ok_packages.append(package)
                
            elif version_req.startswith('~'):
                # Tilde range (~) means compatible with the specified minor version
                required_version = version_req[1:]
                major_minor = '.'.join(required_version.split('.')[:2])
                installed_major_minor = '.'.join(installed_version.split('.')[:2])
                
                if installed_major_minor != major_minor:
                    outdated_packages.append({
                        'name': package,
                        'installed_version': installed_version,
                        'required_version': version_req,
                        'operator': '~'
                    })
                else:
                    ok_packages.append(package)
                
            elif version_req.startswith('>='):
                # Greater than or equal
                required_version = version_req[2:].strip()
                
                if pkg_resources.parse_version(installed_version) < pkg_resources.parse_version(required_version):
                    outdated_packages.append({
                        'name': package,
                        'installed_version': installed_version,
                        'required_version': version_req,
                        'operator': '>='
                    })
                else:
                    ok_packages.append(package)
                
            elif version_req.startswith('>'):
                # Greater than
                required_version = version_req[1:].strip()
                
                if pkg_resources.parse_version(installed_version) <= pkg_resources.parse_version(required_version):
                    outdated_packages.append({
                        'name': package,
                        'installed_version': installed_version,
                        'required_version': version_req,
                        'operator': '>'
                    })
                else:
                    ok_packages.append(package)
                
            elif version_req.startswith('<='):
                # Less than or equal
                required_version = version_req[2:].strip()
                
                if pkg_resources.parse_version(installed_version) > pkg_resources.parse_version(required_version):
                    outdated_packages.append({
                        'name': package,
                        'installed_version': installed_version,
                        'required_version': version_req,
                        'operator': '<='
                    })
                else:
                    ok_packages.append(package)
                
            elif version_req.startswith('<'):
                # Less than
                required_version = version_req[1:].strip()
                
                if pkg_resources.parse_version(installed_version) >= pkg_resources.parse_version(required_version):
                    outdated_packages.append({
                        'name': package,
                        'installed_version': installed_version,
                        'required_version': version_req,
                        'operator': '<'
                    })
                else:
                    ok_packages.append(package)
                
            else:
                # Exact version or other format
                if version_req != installed_version:
                    outdated_packages.append({
                        'name': package,
                        'installed_version': installed_version,
                        'required_version': version_req,
                        'operator': '=='
                    })
                else:
                    ok_packages.append(package)
            
        except Exception as e:
            logger.warning(f"Error checking package {package}: {str(e)}")
            missing_packages.append(package)
    
    return missing_packages, outdated_packages, ok_packages

def repair_python_dependencies(missing_packages: List[str], outdated_packages: List[Dict]) -> Tuple[bool, List[str], List[str]]:
    """
    Attempt to repair Python dependencies by installing missing and outdated packages.
    
    Args:
        missing_packages: List of missing package names
        outdated_packages: List of outdated package dictionaries
        
    Returns:
        Tuple containing:
            - Boolean indicating overall success
            - List of successful repairs
            - List of failed repairs with error messages
    """
    successes = []
    failures = []
    
    # Install pip if not already installed
    try:
        import pip
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip"], stdout=subprocess.PIPE)
            successes.append("Installed pip")
        except subprocess.SubprocessError:
            failures.append("Failed to install pip")
            return False, successes, failures
    
    # Upgrade pip
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.PIPE)
        successes.append("Upgraded pip to latest version")
    except subprocess.SubprocessError:
        failures.append("Failed to upgrade pip")
    
    # Install missing packages
    for package in missing_packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package], stdout=subprocess.PIPE)
            successes.append(f"Installed missing package: {package}")
        except subprocess.SubprocessError as e:
            failures.append(f"Failed to install missing package: {package} - {str(e)}")
    
    # Upgrade outdated packages
    for package_info in outdated_packages:
        package_name = package_info['name']
        required_version = package_info['required_version']
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package_name}{required_version}"], stdout=subprocess.PIPE)
            successes.append(f"Upgraded package: {package_name} to {required_version}")
        except subprocess.SubprocessError as e:
            failures.append(f"Failed to upgrade package: {package_name} to {required_version} - {str(e)}")
    
    return len(failures) == 0, successes, failures

def repair_node_dependencies(package_json_path: Optional[Path] = None) -> Tuple[bool, List[str], List[str]]:
    """
    Attempt to repair Node.js dependencies by running npm install.
    
    Args:
        package_json_path: Path to package.json file. If None, looks in node server dir.
        
    Returns:
        Tuple containing:
            - Boolean indicating overall success
            - List of successful repairs
            - List of failed repairs with error messages
    """
    successes = []
    failures = []
    
    # Get project root
    project_root = get_project_root()
    
    # Find package.json file if not provided
    if package_json_path is None:
        package_json_path = project_root / "ui" / "kanban" / "server" / "package.json"
    
    # Check if Node.js is installed
    node_installed, _, _ = check_node_environment()
    if not node_installed:
        failures.append("Node.js is not installed. Please install Node.js manually.")
        return False, successes, failures
    
    # Check if package.json exists
    if not package_json_path.exists():
        failures.append(f"package.json not found at {package_json_path}")
        return False, successes, failures
    
    # Run npm install
    try:
        subprocess.check_call(["npm", "install"], cwd=package_json_path.parent, stdout=subprocess.PIPE)
        successes.append("Successfully ran npm install")
        return True, successes, failures
    except subprocess.SubprocessError as e:
        failures.append(f"Failed to run npm install: {str(e)}")
        return False, successes, failures

def run_dependency_check() -> DependencyCheckResult:
    """
    Run a comprehensive dependency health check.
    
    Returns:
        DependencyCheckResult object with check results
    """
    result = DependencyCheckResult()
    import datetime
    result.timestamp = datetime.datetime.now().isoformat()
    
    # Check Python dependencies
    python_missing, python_outdated, python_ok = check_python_dependencies()
    result.python_packages_required = python_missing + python_ok + [p['name'] for p in python_outdated]
    result.python_packages_missing = python_missing
    result.python_packages_outdated = python_outdated
    result.python_packages_ok = python_ok
    
    # Check optional dependencies
    result.optional_packages_missing = check_optional_dependencies()
    
    # Check Node.js environment
    result.node_installed, result.node_version, result.npm_version = check_node_environment()
    
    # Check Node.js dependencies if Node.js is installed
    if result.node_installed:
        node_missing, node_outdated, node_ok = check_node_dependencies()
        result.node_packages_required = node_missing + node_ok + [p['name'] for p in node_outdated]
        result.node_packages_missing = node_missing
        result.node_packages_outdated = node_outdated
        result.node_packages_ok = node_ok
    
    # Determine overall status
    if python_missing or python_outdated:
        result.status = "unhealthy"
        if python_missing:
            result.errors.append(f"Missing {len(python_missing)} required Python packages")
        if python_outdated:
            result.errors.append(f"Found {len(python_outdated)} outdated Python packages")
        
        # Add repair actions
        if python_missing:
            packages_str = ", ".join(python_missing)
            result.repair_actions.append(f"Install missing Python packages: pip install {packages_str}")
        
        if python_outdated:
            for pkg in python_outdated:
                result.repair_actions.append(f"Upgrade {pkg['name']}: pip install {pkg['name']}{pkg['required_version']}")
    
    if result.node_installed and (result.node_packages_missing or result.node_packages_outdated):
        result.status = "unhealthy"
        if result.node_packages_missing:
            result.errors.append(f"Missing {len(result.node_packages_missing)} required Node.js packages")
        if result.node_packages_outdated:
            result.errors.append(f"Found {len(result.node_packages_outdated)} outdated Node.js packages")
        
        # Add repair actions
        result.repair_actions.append("Run 'npm install' in the server directory to install Node.js dependencies")
    
    if result.optional_packages_missing:
        result.warnings.append(f"Missing {len(result.optional_packages_missing)} optional packages that may enhance functionality")
        # Add repair actions
        packages_str = " ".join([pkg["name"] for pkg in result.optional_packages_missing])
        result.repair_actions.append(f"Install optional packages: pip install {packages_str}")
    
    # If no errors, status is healthy
    if not result.errors:
        result.status = "healthy"
    
    return result

def fix_dependencies(auto_approve: bool = False) -> Tuple[bool, List[str], List[str]]:
    """
    Attempt to fix all dependency issues.
    
    Args:
        auto_approve: If True, proceed without asking for confirmation
        
    Returns:
        Tuple containing:
            - Boolean indicating overall success
            - List of successful repairs
            - List of failed repairs with error messages
    """
    # Run dependency check
    check_result = run_dependency_check()
    
    # If everything is healthy, return success
    if check_result.status == "healthy" and not check_result.warnings:
        return True, ["All dependencies are healthy. No repair needed."], []
    
    # If repair actions needed, ask for confirmation
    if not auto_approve and check_result.repair_actions:
        print("The following repairs are recommended:")
        for action in check_result.repair_actions:
            print(f"  - {action}")
        
        response = input("Do you want to proceed with repairs? [y/N] ")
        if response.lower() != 'y':
            return False, [], ["Repair cancelled by user"]
    
    successes = []
    failures = []
    
    # Fix Python dependencies
    if check_result.python_packages_missing or check_result.python_packages_outdated:
        python_success, python_successes, python_failures = repair_python_dependencies(
            check_result.python_packages_missing,
            check_result.python_packages_outdated
        )
        successes.extend(python_successes)
        failures.extend(python_failures)
    
    # Fix Node.js dependencies
    if check_result.node_installed and (check_result.node_packages_missing or check_result.node_packages_outdated):
        node_success, node_successes, node_failures = repair_node_dependencies()
        successes.extend(node_successes)
        failures.extend(node_failures)
    
    # Fix optional packages
    if check_result.optional_packages_missing:
        optional_packages = [pkg["name"] for pkg in check_result.optional_packages_missing]
        for package in optional_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package], stdout=subprocess.PIPE)
                successes.append(f"Installed optional package: {package}")
            except subprocess.SubprocessError as e:
                failures.append(f"Failed to install optional package: {package} - {str(e)}")
    
    return len(failures) == 0, successes, failures