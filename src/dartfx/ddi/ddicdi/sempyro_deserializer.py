"""SemPyRO Deserialization Utility for SemPyRO Model Classes.

This module provides utilities to deserialize RDF graphs into sempyro_model Pydantic classes.
It supports the inverse operation of the to_graph() serialization provided by SemPyRO.

Usage:
    >>> from rdflib import Graph
    >>> from dartfx.ddi.ddicdi.sempyro_deserializer import SemPyRODeserializer
    >>> from dartfx.ddi.ddicdi import sempyro_model
    >>> 
    >>> # Load an RDF graph
    >>> graph = Graph()
    >>> graph.parse("data.ttl", format="turtle")
    >>> 
    >>> # Deserialize to Python objects
    >>> deserializer = SemPyRODeserializer(sempyro_model)
    >>> instances = deserializer.deserialize(graph)
    >>> 
    >>> # Or deserialize a specific subject
    >>> from rdflib import URIRef
    >>> subject_uri = URIRef("http://example.org/instance1")
    >>> instance = deserializer.deserialize_subject(graph, subject_uri)
"""

from typing import Any, Dict, List, Optional, Type, Union, get_args, get_origin
import inspect

from rdflib import Graph, URIRef, Literal, RDF, BNode
from rdflib.term import Node
from pydantic import BaseModel
from pydantic.fields import FieldInfo


class SemPyRODeserializationError(Exception):
    """Exception raised when SemPyRO deserialization fails."""
    pass


class SemPyRODeserializer:
    """Deserializes RDF graphs into SemPyRO Pydantic model instances.
    
    This class provides functionality to parse RDF graphs and instantiate
    the corresponding Pydantic models from sempyro_model.py. It handles:
    - Type mapping from RDF class URIs to Python classes
    - Field mapping using rdf_term annotations
    - Inheritance hierarchies
    - Relationships between instances
    - Collections (lists) of values
    
    Attributes:
        module: The module containing the Pydantic model classes (typically sempyro_model)
        class_registry: A mapping from RDF type URIs to Python classes
        instances: A cache of already deserialized instances by their URI
    """
    
    def __init__(self, model_module: Any):
        """Initialize the deserializer with a model module.
        
        Args:
            model_module: The module containing Pydantic models (e.g., sempyro_model)
        """
        self.module = model_module
        self.class_registry: Dict[str, Type[BaseModel]] = {}
        self.instances: Dict[str, BaseModel] = {}
        self._build_class_registry()
    
    def _build_class_registry(self) -> None:
        """Build a registry mapping RDF type URIs to Python classes.
        
        Scans the model module for all classes that have model_config with $IRI,
        and creates a mapping from their RDF type URIs to the Python class objects.
        """
        for name, obj in inspect.getmembers(self.module):
            if inspect.isclass(obj) and issubclass(obj, BaseModel):
                # Check if class has model_config with $IRI
                if hasattr(obj, 'model_config'):
                    config = obj.model_config
                    iri = None
                    
                    # Try different ways to access $IRI
                    if isinstance(config, dict):
                        # Direct access
                        if '$IRI' in config:
                            iri = config['$IRI']
                        # Check in json_schema_extra
                        elif 'json_schema_extra' in config:
                            extra = config['json_schema_extra']
                            if isinstance(extra, dict) and '$IRI' in extra:
                                iri = extra['$IRI']
                    elif hasattr(config, 'get'):
                        # ConfigDict object
                        iri = config.get('$IRI')
                        if not iri:
                            extra = config.get('json_schema_extra')
                            if isinstance(extra, dict) and '$IRI' in extra:
                                iri = extra['$IRI']
                    
                    if iri:
                        self.class_registry[str(iri)] = obj
    
    def get_class_for_type(self, rdf_type: Union[str, URIRef]) -> Optional[Type[BaseModel]]:
        """Get the Python class corresponding to an RDF type URI.
        
        Args:
            rdf_type: The RDF type URI (from rdf:type predicate)
            
        Returns:
            The corresponding Python class, or None if not found
        """
        return self.class_registry.get(str(rdf_type))
    
    def deserialize(self, graph: Graph, root_types: Optional[List[str]] = None) -> List[BaseModel]:
        """Deserialize all subjects in an RDF graph to Pydantic instances.
        
        Args:
            graph: The RDF graph to deserialize
            root_types: Optional list of RDF type URIs to filter subjects by.
                       If provided, only subjects with these types will be deserialized.
                       
        Returns:
            List of deserialized Pydantic model instances
            
        Example:
            >>> graph = Graph()
            >>> graph.parse("data.ttl", format="turtle")
            >>> deserializer = RDFDeserializer(sempyro_model)
            >>> # Deserialize all InstanceVariable objects
            >>> variables = deserializer.deserialize(
            ...     graph, 
            ...     root_types=["http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"]
            ... )
        """
        self.instances.clear()  # Clear cache for new deserialization
        results = []
        
        # Find all subjects with rdf:type
        subjects = set()
        for s, p, o in graph.triples((None, RDF.type, None)):
            if root_types is None or str(o) in root_types:
                subjects.add(s)
        
        # Deserialize each subject
        for subject in subjects:
            try:
                instance = self.deserialize_subject(graph, subject)
                if instance:
                    results.append(instance)
            except SemPyRODeserializationError as e:
                # Log warning but continue with other subjects
                print(f"Warning: Failed to deserialize {subject}: {e}")
                continue
        
        return results
    
    def deserialize_subject(self, graph: Graph, subject: Union[str, URIRef, BNode]) -> Optional[BaseModel]:
        """Deserialize a specific RDF subject to a Pydantic instance.
        
        Args:
            graph: The RDF graph containing the subject
            subject: The URI or blank node of the subject to deserialize
            
        Returns:
            A Pydantic model instance, or None if the subject cannot be deserialized
            
        Raises:
            RDFDeserializationError: If deserialization fails
            
        Example:
            >>> from rdflib import URIRef
            >>> subject_uri = URIRef("http://example.org/var1")
            >>> instance = deserializer.deserialize_subject(graph, subject_uri)
        """
        if not isinstance(subject, (URIRef, BNode)):
            subject = URIRef(subject)
        
        # Check if already deserialized
        subject_str = str(subject)
        if subject_str in self.instances:
            return self.instances[subject_str]
        
        # Get the rdf:type of the subject
        rdf_types = list(graph.objects(subject, RDF.type))
        if not rdf_types:
            return None
        
        # Try each type until we find a matching class
        python_class = None
        for rdf_type in rdf_types:
            if isinstance(rdf_type, (URIRef, str)):
                python_class = self.get_class_for_type(rdf_type)
                if python_class:
                    break
        
        if not python_class:
            raise SemPyRODeserializationError(
                f"No Python class found for RDF types: {[str(t) for t in rdf_types]}"
            )
        
        # Extract field values from the graph
        field_values = self._extract_field_values(graph, subject, python_class)
        
        # Create the instance
        try:
            instance = python_class(**field_values)
            self.instances[subject_str] = instance
            return instance
        except Exception as e:
            raise SemPyRODeserializationError(
                f"Failed to instantiate {python_class.__name__}: {e}"
            ) from e
    
    def _extract_field_values(self, graph: Graph, subject: Node, python_class: Type[BaseModel]) -> Dict[str, Any]:
        """Extract field values for a Pydantic class from RDF triples.
        
        Args:
            graph: The RDF graph
            subject: The subject node
            python_class: The Pydantic class to instantiate
            
        Returns:
            Dictionary of field names to values
        """
        field_values = {}
        
        # Get all model fields (includes inherited fields)
        for field_name, field_info in python_class.model_fields.items():
            # Get RDF metadata from json_schema_extra
            rdf_term = self._get_rdf_term(field_info)
            if not rdf_term:
                continue
            
            # Get all values for this predicate
            values = list(graph.objects(subject, URIRef(rdf_term)))
            if not values:
                continue
            
            # Determine if field is a list
            is_list = self._is_list_field(field_info)
            
            # Process values based on field type
            if is_list:
                converted_values = []
                for v in values:
                    converted = self._convert_value(graph, v, field_info)
                    if converted is not None:  # Skip None values
                        converted_values.append(converted)
                if converted_values:  # Only add if we have values
                    field_values[field_name] = converted_values
            else:
                # Take the first value if multiple exist
                converted = self._convert_value(graph, values[0], field_info)
                if converted is not None:
                    field_values[field_name] = converted
        
        return field_values
    
    def _get_rdf_term(self, field_info: FieldInfo) -> Optional[str]:
        """Extract the rdf_term from a field's json_schema_extra.
        
        Args:
            field_info: The Pydantic field info
            
        Returns:
            The RDF term URI as a string, or None if not found
        """
        if not field_info.json_schema_extra:
            return None
        
        if isinstance(field_info.json_schema_extra, dict):
            rdf_term = field_info.json_schema_extra.get('rdf_term')
            if isinstance(rdf_term, URIRef):
                return str(rdf_term)
            elif isinstance(rdf_term, str):
                return rdf_term
        
        return None
    
    def _is_list_field(self, field_info: FieldInfo) -> bool:
        """Check if a field is a list type.
        
        Args:
            field_info: The Pydantic field info
            
        Returns:
            True if the field is a list, False otherwise
        """
        annotation = field_info.annotation
        origin = get_origin(annotation)
        
        # Check for List, list
        if origin is list or origin is List:
            return True
        
        # Check for Union (e.g., list[...] | None or Optional[list[...]])
        if origin is Union:
            args = get_args(annotation)
            for arg in args:
                # Skip None type
                if arg is type(None):
                    continue
                arg_origin = get_origin(arg)
                if arg_origin in (list, List):
                    return True
        
        # Fallback: check string representation for list[
        # This handles cases where Union with list doesn't properly detect via get_origin
        annotation_str = str(annotation)
        if 'list[' in annotation_str.lower():
            return True
        
        return False
    
    def _get_inner_type(self, field_info: FieldInfo) -> Optional[Type]:
        """Get the inner type of a field (e.g., the T in List[T]).
        
        Args:
            field_info: The Pydantic field info
            
        Returns:
            The inner type, or None if it cannot be determined
        """
        annotation = field_info.annotation
        origin = get_origin(annotation)
        
        # Handle List[T] or list[T]
        if origin in (list, List):
            args = get_args(annotation)
            return args[0] if args else None
        
        # Handle Optional[List[T]]
        if origin is Union:
            args = get_args(annotation)
            for arg in args:
                if get_origin(arg) in (list, List):
                    inner_args = get_args(arg)
                    return inner_args[0] if inner_args else None
        
        # Not a list, return the type itself
        return annotation
    
    def _convert_value(self, graph: Graph, value: Node, field_info: FieldInfo) -> Any:
        """Convert an RDF value to a Python value based on the field type.
        
        Args:
            graph: The RDF graph (needed for nested objects)
            value: The RDF node value
            field_info: The Pydantic field info
            
        Returns:
            The converted Python value, or None if conversion fails
        """
        # Get the expected type
        inner_type = self._get_inner_type(field_info)
        
        # Handle Literal values (strings, numbers, dates, etc.)
        if isinstance(value, Literal):
            # Direct literal conversion
            python_value = value.toPython()
            
            # Handle enum types
            if inner_type and inspect.isclass(inner_type) and hasattr(inner_type, '__members__'):
                # It's an enum, convert the URI to enum value
                try:
                    return inner_type(str(value))
                except (ValueError, KeyError):
                    return python_value
            
            return python_value
        
        # Handle URIRef and BNode values (potential references to other objects or enum values)
        elif isinstance(value, (URIRef, BNode)):
            value_str = str(value)
            
            # Check if it's an enum value
            if inner_type and inspect.isclass(inner_type) and hasattr(inner_type, '__members__'):
                try:
                    return inner_type(value_str)
                except (ValueError, KeyError):
                    pass
            
            # Check if it's a reference to another object (has rdf:type in graph)
            has_type = False
            for _ in graph.objects(value, RDF.type):
                has_type = True
                break
            
            if has_type:
                # It's a reference to another object, deserialize it
                if inner_type and inspect.isclass(inner_type) and issubclass(inner_type, BaseModel):
                    try:
                        return self.deserialize_subject(graph, value)
                    except SemPyRODeserializationError:
                        # If deserialization fails, return None
                        return None
                else:
                    # We don't know the type, try to deserialize anyway
                    try:
                        return self.deserialize_subject(graph, value)
                    except SemPyRODeserializationError:
                        return None
            
            # Otherwise, return as string (might be a simple URI reference)
            return value_str
        
        return value


# Convenience function for simple deserialization
def from_graph(graph: Graph, model_module: Any, 
               subject: Optional[Union[str, URIRef, BNode]] = None,
               root_types: Optional[List[str]] = None) -> Union[BaseModel, List[BaseModel], None]:
    """Convenience function to deserialize RDF graph to Pydantic instances.
    
    Args:
        graph: The RDF graph to deserialize
        model_module: The module containing Pydantic models (e.g., sempyro_model)
        subject: Optional specific subject to deserialize. If provided, only this subject
                is deserialized. Otherwise, all subjects are deserialized.
        root_types: Optional list of RDF type URIs to filter subjects by (only used if
                   subject is None)
                   
    Returns:
        - If subject is provided: A single Pydantic instance or None
        - If subject is None: A list of Pydantic instances
        
    Examples:
        >>> # Deserialize a specific subject
        >>> instance = from_graph(graph, sempyro_model, 
        ...                      subject="http://example.org/var1")
        >>> 
        >>> # Deserialize all InstanceVariable objects
        >>> variables = from_graph(graph, sempyro_model,
        ...     root_types=["http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/InstanceVariable"]
        ... )
        >>> 
        >>> # Deserialize everything
        >>> all_instances = from_graph(graph, sempyro_model)
    """
    deserializer = SemPyRODeserializer(model_module)
    
    if subject is not None:
        return deserializer.deserialize_subject(graph, subject)
    else:
        return deserializer.deserialize(graph, root_types=root_types)


# Mixin class that can be used to add deserialization to existing classes
class SemPyRODeserializableMixin:
    """Mixin to add from_graph class method to Pydantic models.
    
    This mixin can be added to any Pydantic model class to provide a convenient
    from_graph() class method for deserialization.
    
    Example:
        >>> from dartfx.ddi.ddicdi.sempyro_model import InstanceVariable
        >>> from dartfx.ddi.ddicdi.sempyro_deserializer import SemPyRODeserializableMixin
        >>> 
        >>> class DeserializableInstanceVariable(SemPyRODeserializableMixin, InstanceVariable):
        ...     pass
        >>> 
        >>> # Now you can deserialize directly
        >>> var = DeserializableInstanceVariable.from_graph(graph, subject_uri)
    """
    
    @classmethod
    def from_graph(cls, graph: Graph, subject: Union[str, URIRef, BNode]) -> Optional[BaseModel]:
        """Deserialize an RDF subject to an instance of this class.
        
        Args:
            graph: The RDF graph containing the subject
            subject: The URI or blank node of the subject
            
        Returns:
            An instance of the base class, or None if deserialization fails
            
        Note:
            The returned instance will be of the base model type (e.g., InstanceVariable)
            not the mixin class type (e.g., DeserializableInstanceVariable).
        """
        # Need to import here to avoid circular imports
        import sys
        
        # Get the module containing this class
        module = sys.modules[cls.__module__]
        
        deserializer = SemPyRODeserializer(module)
        instance = deserializer.deserialize_subject(graph, subject)
        
        # The deserialized instance will be of the base model type (e.g., InstanceVariable)
        # not the custom mixin type (e.g., DeserializableInstanceVariable)
        # So we just need to verify it's compatible, not an exact type match
        if instance:
            # Check if the instance is compatible with the base class
            # Get the base classes excluding the mixin
            base_classes = [b for b in cls.__bases__ if b != SemPyRODeserializableMixin]
            if base_classes and isinstance(instance, base_classes[0]):
                return instance
        
        return None
