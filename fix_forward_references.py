#!/usr/bin/env python3
"""
Script to fix forward reference issues in the ddicdi_sempyro.py file.
This script replaces all forward reference inheritance with direct RDFModel inheritance.
"""

import re
import sys
from pathlib import Path

def fix_forward_references(file_path):
    """Fix forward reference inheritance issues in the generated sempyro file."""
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match class definitions with forward reference inheritance
    # Matches: class ClassName(SomeClass): # type: ignore # noqa: F821
    pattern = r'class (\w+)\((\w+)\):\s*# type: ignore # noqa: F821'
    
    # Find all matches
    matches = re.findall(pattern, content)
    
    print(f"Found {len(matches)} forward reference inheritance issues:")
    for class_name, parent_class in matches:
        print(f"  {class_name} inherits from {parent_class}")
    
    # Replace all forward reference inheritance with RDFModel inheritance
    def replace_inheritance(match):
        class_name = match.group(1)
        parent_class = match.group(2)
        return f'class {class_name}(RDFModel, metaclass=ABCMeta): # type: ignore # noqa: F821'
    
    # Apply the replacement
    new_content = re.sub(pattern, replace_inheritance, content)
    
    # Write the fixed file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"\nFixed {len(matches)} forward reference issues in {file_path}")
    return len(matches)

if __name__ == "__main__":
    # Path to the sempyro file
    sempyro_file = Path("src/dartfx/ddi/ddicdi_sempyro.py")
    
    if not sempyro_file.exists():
        print(f"Error: {sempyro_file} not found!")
        sys.exit(1)
    
    # Fix forward references
    num_fixes = fix_forward_references(sempyro_file)
    
    if num_fixes > 0:
        print(f"\nSuccess! Fixed {num_fixes} forward reference issues.")
        print("You may want to review the changes and test the import.")
    else:
        print("No forward reference issues found.")
