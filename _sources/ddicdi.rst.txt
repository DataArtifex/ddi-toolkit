DDI Cross Domain Integration
============================

DDI Cross Domain Integration (CDI) is in early stage and current development work is exploratory.

Very little is documented at this time....

The current objective is to create base classes and methods to create and manipulate DDI-CDI resources.
The focus is on supporting the profile being advocated by the CODATA [Cross Domain Interoperability Framework](https://cdif.codata.org/).

The :py:class:`dartfx.ddicdi.DdiCdiResource` class is at the heart of the implementation. It holds nuemrous helper methods, as well as the RDF serilizer.

All other classes derive from it and are implemente as `@dataclass`. 

The classes and their attributes' match the names of the DDI-CDI resources and properties. This therefore does not follow common Python naming conventions (snake case).
The attribute's field() is used to provide extra information as needed. The `metatata` value for example is used to document valid classes for references.

Class generator prompt
----------------------

The dataclasses were generated with meta.ai using the promt below. The XML Schema representation of a class or datatype were used as a reference. 
This can be found in the 

Note that this is not perfect and 

Prompt::

    Convert the XSD resources described below the ===== line, strictly adhering to the following rules and instructions:
    - make sure to take cardinality into account
    - use the resource documentation as class documentation
    - use the field-level documentation as an inline comment for the class attributes
    - only generate the dataclass definition. No imports or examples.
    - Double quote parent class names in Python as they may defined later in the code
    - Double quote the attribute classes' names in Python as they may defined later in the code
    - use lower case typing (eg. list instead of List), as specified in PEP 585
    - If applicable, drop the XsdType suffix for the Python class name
    - Make sure to render and format as Python code
    - Make sure to include the @dataclass annotation on the class
    - Preserver original property name for class attributes (use camelCase)
    - use field(...) to initialize attributes
    - Drop the XsdType from the class names
    - For AssociationReference, do not use subclasses. Do not include a target class prefix on such property.

    <copy/paste XML Schema representation here>


* .. automodule:: dartfx.ddi.ddicdi
    :members:
    :undoc-members:
    :show-inheritance: