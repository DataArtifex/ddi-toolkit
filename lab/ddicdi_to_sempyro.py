import argparse
import os
import sys
from dartfx.ddi.ddicdi_specification import DdiCdiModel

INDENT = " "*4

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

def generate_field(resource, cardinality):
    # a resource is either an attribute or an association
    code  = ""
    code += f'# {resource.get("uri")} ({cardinality.get("display")}) | {resource.get("label")} | {resource.get("range")}\n'
    field_name = resource.get("label")
    if field_name in ('for','from'): # exception for reserved keyword
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
    description = resource.get("description").replace('"', '\\"') if resource.get("description") else ""
    if description:
        if '\n' in description:
            code += f'{INDENT}description="""{description}""",\n'
        else:
            code += f'{INDENT}description="{description}",\n'
    # json schema extra
    attribute_name = resource.get("uri").split(":")[-1]
    rdf_type = resource.get("range")
    rdf_type = rdf_type.replace("cdi:", "CDI.") 
    rdf_type = rdf_type.replace("xsd:", "XSD.") 
    code += f'{INDENT}json_schema_extra={{\n'
    code += f'{INDENT*2}"rdf_term": URIRef(CDI + "{attribute_name}"),\n'
    code += f'{INDENT*2}"rdf_type": {rdf_type}\n'
    code += f'{INDENT}}},\n'
    code += ')\n'
    code += '\n\n'
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
        class_inline_comment = '# type: ignore # noqa: F821'
    else:
        class_inheritance = "RDFModel, metaclass=ABCMeta"
        class_inline_comment = ''
    code  = ""
    code += f"class {class_name}({class_inheritance}): {class_inline_comment}\n"

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
    range_attributes = model.get_resource_range_attributes(resource_uri, description=True)
    if range_attributes:
        code += indent_code('#\n# RANGE ATTRIBUTES\n#\n\n', 1)
        for attribute_uri, attribute in range_attributes.items():
            cardinality = model.get_resource_attribute_cardinality(resource_uri, attribute_uri)
            code += indent_code(f"# {attribute_uri} ({cardinality.get('display')})\n\n", 1)
        code += '\n'

    # the end
    code += '\n\n'
    return code

def generate_datatypes(model) -> str:
    code = ""
    resources = model.get_ucmis_structureddatatypes()
    for resource_uri in resources:  
        code += generate_resource(model, resource_uri)
    return code

def generate_classes(model) -> str:
    resource_uri = model.get_ucmis_classes()
    code = ""
    for resource_uri in resource_uri:  
        code += generate_resource(model, resource_uri)
    return code

def generate_enumerations(model) -> str:
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
            member_label = member.get('label')
            member_description = member.get('description')
            member_code = f'{member_label.upper()} = "{member_uri}"'
            if member_description:
                member_code += f'  # {member_description}'
            member_code += '\n'
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

