import argparse
import os
import sys
from dartfx.ddi.ddicdi_specification import DdiCdiModel

INDENT = " "*4

def escape_description(description):
    if description:
        # Handle the complex escaping needed for Python string literals
        # First, escape backslashes (this must come first!)
        description = description.replace('\\', '\\\\')
        # Then escape quotes
        description = description.replace('"', '\\"')
        # Handle triple quotes by escaping them
        if '"""' in description:
            description = description.replace('"""', '\\"\\"\\"')
        
        # Use triple quotes for multi-line descriptions or those with many quotes
        if '\n' in description or description.count('\\"') > 3:
            return f'"""{description}"""'
        else:
            return f'"{description}"'
    return '""'  # Return empty string in quotes instead of empty

def generate(model, output_dir):
    # create file
    output_file = os.path.join(output_dir, "ddicdi_sempyro.py")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_file, 'w') as file:
        print(f"Creating {output_file}...")
        print("Generating header...")
        file.write(generate_header(file))
        file.write("\n")
        print("Generating enumerations...")
        file.write("#\n# ENUMERATIONS\n#\n\n")
        file.write(generate_enumerations(model))
        file.write("\n")
        print("Generating datatypes...")
        file.write("#\n# DATA TYPES\n#\n\n")
        file.write(generate_datatypes(model))
        file.write("\n")
        print("Generating classes...")
        file.write("#\n# CLASSES\n#\n\n")
        file.write(generate_classes(model))
        file.write("\n")
    file.close()
    return

def generate_classes(model) -> str:
    code = ""
    resources = model.get_ucmis_classes()
    # Sort resources to ensure parent classes come before children
    subclass_of = model.get_subclassof()
    sorted_resources = topological_sort_resources(resources, subclass_of)
    
    for resource_uri in sorted_resources:  
        code += generate_resource(model, resource_uri)
    return code

def generate_datatypes(model) -> str:
    code = ""
    resources = model.get_ucmis_structureddatatypes()
    # Sort resources to ensure parent classes come before children
    subclass_of = model.get_subclassof()
    sorted_resources = topological_sort_resources(resources, subclass_of)
    
    for resource_uri in sorted_resources:  
        code += generate_resource(model, resource_uri)
    return code

def generate_field(resource, cardinality):
    # a resource is either an attribute or an association
    code  = ""
    code += f'# {resource.get("uri")} ({cardinality.get("display")}) | {resource.get("label")} | {resource.get("range")}\n'
    field_name = resource.get("label")
    # handle reserved Python/Pydantic keywords
    if field_name in ('for','from','construct'): # exception for reserved Python keyword (for, from) and Pydantic (construct)
        field_name = f'{field_name}_'
    code += f'{field_name}: '
    # convert range to python type
    range = resource.get("range")
    python_type = range_to_python_type(range)
    # check if list
    if cardinality.get('maxOccurs') == "unbounded" or int(cardinality.get('maxOccurs')) > 1:
        python_type = f'list[{python_type}]'
    # check if optional
    if cardinality.get('minOccurs') == "0":
        python_type += ' | None'        
    # create field
    code += f'{python_type} = Field(\n'
    # alias
    code += f'{INDENT}alias="{resource.get("label")}",\n'
    # default value
    if cardinality.get('minOccurs') == "0":
        code += f"{INDENT}default=None,\n"
    # description
    description = escape_description(resource.get("description"))
    code += f'{INDENT}description={description},\n'
    # json schema extra
    attribute_name = resource.get("uri").split(":")[-1]
    rdf_type = resource.get("range")
    if rdf_type.startswith("cdi:"):
        rdf_type = rdf_type.replace("cdi:", "CDI.") # CDI.Foo
    elif rdf_type.startswith("xsd:"):
        rdf_type = f'"{rdf_type}"' # "xsd:string" or "xsd:integer"
    else:
        raise ValueError(f"Unknown RDF type: {rdf_type}")
    code += f'{INDENT}json_schema_extra={{\n'
    code += f'{INDENT*2}"rdf_term": URIRef(CDI + "{attribute_name}"),\n'
    code += f'{INDENT*2}"rdf_type": {rdf_type}\n'
    code += f'{INDENT}}},\n'
    code += ')\n'
    code += '\n\n'
    return code

def generate_enumerations(model: DdiCdiModel) -> str:
    code = ""   
    resources = model.get_ucmis_enumerations()
    for resource_uri in resources:  
        print(resource_uri)
        enumeration = model.get_enumeration(resource_uri)
        class_name = enumeration.get('label')
        class_description = enumeration.get('description')
        # class 
        class_inheritance = "str, Enum"
        code += f"class {class_name}({class_inheritance}):\n"
        # header docs
        header = f'""" {class_name}.\n'
        header += f"\n{class_description}\n"
        header += '\n"""\n\n'
        code += indent_code(header, 1)
        # members
        for member in enumeration.get('members', []).values():
            member_uri = member.get('uri')
            member_uri = model.full_uri(member_uri)
            member_label = member.get('label')
            member_description = member.get('description')
            member_code = f'{member_label.upper()} = "{member_uri}"'
            if member_description:
                member_code += f'  # {member_description}'
            member_code += '\n\n'
            code += indent_code(member_code, 1)
        code += '\n\n'
    return code

def generate_header(file) -> str:
    code = ""
    code += (
        "from __future__ import annotations  # to allow forward references with Pydantic\n"
        "from abc import ABCMeta\n"
        "from datetime import date, datetime\n"
        "from enum import Enum\n"
        "from pydantic import ConfigDict, Field\n"
        "from rdflib import Namespace, URIRef, XSD\n"
        "from sempyro import LiteralField, RDFModel\n"
        
        "from typing import Union\n"
        "\n"
        "CDI = Namespace('http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/')"
    )
    code += '\n'
    return code

def generate_resource(model, resource_uri):
    print(resource_uri)
    properties = model.get_resource_properties(resource_uri)
    class_name = properties.get('rdfs:label')
    class_description = properties.get('rdfs:comment')

    # class 
    if 'rdfs:subClassOf' in properties:
        subclass_of = properties['rdfs:subClassOf']
        subclass_of = subclass_of.split('/')[-1]
        class_inheritance = subclass_of
        #class_inline_comment = '# type: ignore # noqa: F821'
    else:
        class_inheritance = "RDFModel, metaclass=ABCMeta"
        #class_inline_comment = ''
    code  = ""
    code += f"class {class_name}({class_inheritance}):\n"

    # header docs
    header = f'""" {class_name}.\n'
    header += f"\n{class_description}\n"
    header += '\n"""\n\n'
    code += indent_code(header, 1)

    # model config
    model_config = (
        'model_config = ConfigDict(\n'
        '    arbitrary_types_allowed=True,\n'
        '    use_enum_values=True,\n'
        '    json_schema_extra={\n'
        '        "$ontology": "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/",\n'
        '        "$namespace": str(CDI),\n'
        f'        "$IRI": CDI.{class_name},\n'
        '        "$prefix": "cdi",\n'
        '    },\n'
        ')\n'
    )
    code += indent_code(model_config, 1)
    code += '\n\n'

    # domain attributes
    domain_attributes = model.get_resource_domain_attributes(resource_uri, description=True)
    if domain_attributes:
        code += indent_code('#\n#  DOMAIN ATTRIBUTES\n#\n\n', 1)
        for attribute_uri, attribute in domain_attributes.items():
            cardinality = model.get_resource_attribute_cardinality(resource_uri, attribute_uri)
            code += indent_code(generate_field(attribute, cardinality), 1)
        code += '\n'

    # from associations
    from_associations = model.get_resource_associations_from(resource_uri, inherited=False, cardinalities=True)
    if from_associations:
        code += indent_code('#\n# FROM ASSOCIATIONS\n#\n\n', 1)
        for association_uri, association in from_associations.items():
            cardinality = association.get('from')
            code += indent_code(generate_field(association, cardinality), 1)
        code += '\n'

    # range attributes
    #range_attributes = model.get_resource_range_attributes(resource_uri, description=True)
    #if range_attributes:
    #    code += indent_code('#\n# RANGE ATTRIBUTES\n#\n\n', 1)
    #    for attribute_uri, attribute in range_attributes.items():
    #       cardinality = model.get_resource_attribute_cardinality(resource_uri, attribute_uri)
    #       code += indent_code(f"# {attribute_uri} ({cardinality.get('display')})\n\n", 1)
    #   code += '\n'

    # the end
    code += '\n\n'
    return code

def indent_code(code, level=0, indent=INDENT):
    indented_lines = []
    for line in code.splitlines():
        if line.strip():  # Only indent non-empty lines
            indented_lines.append(indent*level + line)
        else:
            indented_lines.append(line)  # Keep empty lines as is
    return "\n".join(indented_lines)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert DDI-CDI specification to SemPyro."
    )
    parser.add_argument(
        "ddi_cdi_dir",
        type=str,
        help="Path to the DDI-CDI specification directory."
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="Path to the output directory."
    )
    args = parser.parse_args()

    # Validate input directory
    if not os.path.isdir(args.ddi_cdi_dir):
        print(f"Error: DDI-CDI directory '{args.ddi_cdi_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    return args

def range_to_python_type(range):
    if isinstance(range, list):
        # if only one range, return that type directly
        if len(range) == 1:
            return range_to_python_type(range[0])
        # if multiple ranges, use Union
        python_type = "Union["
        ranges = []
        for r in range:
            ranges.append(range_to_python_type(r))
        python_type += ", ".join(ranges)
        python_type += "]"
        if len(ranges) == 1:
            python_type = ranges[0]
    else:
        # single range
        (prefix,rdf_type) = range.split(":")
        if prefix == "xsd":
            if rdf_type == "string":
                python_type = "Union[str, LiteralField]"
            elif rdf_type == "integer":
                python_type = "int"
            elif rdf_type == "boolean":
                python_type = "bool"
            elif rdf_type == "date":
                python_type = "Union[date, datetime]"
            elif rdf_type == "dateTime":
                python_type = "Union[date, datetime]"
            elif rdf_type == "decimal":
                python_type = "float"
            elif rdf_type == "double":
                python_type = "float"
            elif rdf_type == "language":
                python_type = "Union[str, LiteralField]"
            elif rdf_type == "anyURI":
                python_type = "Union[str, LiteralField]"
            else:
                python_type = None
                raise ValueError(f"{range}: Unknown XSD type: {rdf_type}")
        elif prefix == "cdi":
            python_type = rdf_type
        else:
            raise ValueError(f"{range}: Unknown prefix: {prefix}")
    return python_type

def topological_sort_resources(resources, subclass_of):
    """
    Sort resources in topological order so that parent classes come before their children.
    
    Args:
        resources: List of resource URIs
        subclass_of: Dictionary mapping child URI to parent URI
    
    Returns:
        List of resource URIs in topological order
    """
    # Create a set of all resources for quick lookup
    resource_set = set(resources)
    
    # Build adjacency list: parent -> [children] (within the resource set)
    children = {resource: [] for resource in resources}
    in_degree = {resource: 0 for resource in resources}
    
    for child, parent in subclass_of.items():
        # Only process if both child and parent are in our resource set
        if child in resource_set and parent in resource_set:
            children[parent].append(child)
            in_degree[child] += 1
    
    # Kahn's algorithm for topological sorting
    # Start with nodes that have no incoming edges (no parents in the set)
    queue = [resource for resource in resources if in_degree[resource] == 0]
    result = []
    
    while queue:
        # Remove a node with no incoming edges
        current = queue.pop(0)
        result.append(current)
        
        # For each child of current, remove the edge
        for child in children[current]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
    
    # Check for circular dependencies
    if len(result) != len(resources):
        print("Warning: Circular dependencies detected in inheritance hierarchy")
        # Add remaining resources to the end
        remaining = [r for r in resources if r not in result]
        result.extend(remaining)
    
    # Verification section
    print("\n--- Topological Sort Verification ---")
    
    # Check ordering correctness and find reordered items
    correct_orderings = 0
    total_relationships = 0
    reordered_items = []
    
    for child, parent in subclass_of.items():
        if child in resource_set and parent in resource_set:
            total_relationships += 1
            child_idx = result.index(child)
            parent_idx = result.index(parent)
            child_original_idx = resources.index(child)
            parent_original_idx = resources.index(parent)
            
            if parent_idx < child_idx:
                correct_orderings += 1
                # Check if order was changed from original
                if parent_original_idx > child_original_idx:
                    reordered_items.append(f"  ↻ {parent} → {child} (reordered to correct inheritance)")
            else:
                reordered_items.append(f"  ✗ {parent} → {child} (still incorrect order)")
    
    # Only show reordered items
    if reordered_items:
        print("Reordered relationships:")
        for item in reordered_items:
            print(item)
    else:
        print("No reordering was necessary.")
    
    if total_relationships > 0:
        success_rate = (correct_orderings / total_relationships) * 100
        print(f"\nOrdering success rate: {correct_orderings}/{total_relationships} ({success_rate:.1f}%)")
        if success_rate == 100.0:
            print("✓ All inheritance relationships are correctly ordered!")
        else:
            print("✗ Some inheritance relationships are incorrectly ordered.")
    else:
        print("No inheritance relationships found in this resource set.")
    
    print("--- End Verification ---\n")
    
    return result

if __name__ == "__main__":
    args = parse_args()
    print(f"DDI-CDI directory: {args.ddi_cdi_dir}")
    print(f"Output directory: {args.output_dir}")

    # Load DDI-CDI model
    ddi_cdi_model = DdiCdiModel(root_dir=args.ddi_cdi_dir)

    # check if the model is loaded correctly
    if not ddi_cdi_model or not hasattr(ddi_cdi_model, "_graph") or ddi_cdi_model._graph is None:
        print("Error: Failed to load DDI-CDI model.", file=sys.stderr)
        sys.exit(1)

    # Generate datatypes
    generate(ddi_cdi_model, args.output_dir)

