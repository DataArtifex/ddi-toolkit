"""
DDI-CDI Assistant Module

This module provides a suite of 'Assistants' designed to simplify the creation,
manipulation, and management of DDI-CDI model resources.

Key Architecture Features:
1.  **Automatic Instance Binding**: Any @classmethod defined in an assistant that
    takes a `resource` (or CDIResource) as its first parameter after `cls` is
    automatically attached as an instance method to the `model.CDIResource` class.
2.  **Transparent Proxying**: Assistants like `CdiResourceAssistant` can wrap
    a specific model instance. They proxy all attribute and method access to
    the underlying resource, allowing them to be used as smart wrappers.
3.  **Opt-in Complexity**: Use generic factories for simple classes, and
    specialized assistants (like `VariableAssistant`) only when complex
    domain logic is required.

Creation Methods:
- **`create()`**: The high-level "User API". A one-liner convenience method that
  calls the factory and sets common attributes like 'name' in a single step.
- **`factory()`**: The internal "Engine API". Handles the heavy lifting of
  instantiation, DDI Identifier generation, and URI creation.

Basic Usage:
    # Generic creation of any CDI class
    record = CdiClassAssistant.create(model.Category, name="MainCategory")

    # Specific creation using specialized assistants
    var = VariableAssistant.create_instance_variable(name="INCOME")

    # Both return 'Assistant' instances that proxy to the underlying CDI model objects.
"""

import functools
import inspect
import uuid
from collections.abc import Callable
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel
from rdflib import Graph, URIRef

from . import model_1_0_0 as model


class AssistantMethodDescriptor:
    """
    A descriptor that handles dual-use of assistant methods.
    1. When accessed via Class: returns a method bound to the class (normal classmethod).
    2. When accessed via Instance: returns a method bound to the class AND the instance's resource.
    """

    def __init__(self, cls: type, func: Callable[..., Any]):
        self.cls = cls
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __get__(self, instance: Any, owner: type) -> Callable[..., Any]:
        if instance is None:
            # Bound to class: (cls, ...)
            return functools.partial(self.func, owner)
        # Bound to class and instance.resource: (cls, resource, ...)
        # Bound to class and instance.resource: (cls, resource, ...)
        return functools.partial(self.func, self.cls, instance.resource)


def _bind_assistant_methods(assistant_cls: type, target_class: type) -> None:
    """
    Internal helper to attach classmethods from an assistant class to a target model class.

    A method is attached ONLY if it is a @classmethod and its first parameter after 'cls'
    is either named 'resource' or type-hinted as 'target_class' (CDIResource).
    """

    def make_instance_wrapper(f: Callable[..., Any], c: type) -> Callable[..., Any]:
        @functools.wraps(f)
        def instance_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            return f(c, self, *args, **kwargs)

        return instance_wrapper

    for name, attr in list(assistant_cls.__dict__.items()):
        if isinstance(attr, (classmethod, AssistantMethodDescriptor)):
            func = attr.__func__ if isinstance(attr, classmethod) else attr.func
            try:
                sig = inspect.signature(func)
                params = list(sig.parameters.values())

                # Check for (cls, resource, ...) pattern
                if len(params) >= 2:
                    p_name = params[1].name
                    p_type = params[1].annotation
                    # Robust check: name is 'resource' OR is type-hinted as CDIResource (or subclass)
                    is_resource_param = (
                        p_name == "resource"
                        or p_type is model.CDIResource
                        or (isinstance(p_type, type) and issubclass(p_type, model.CDIResource))
                        or "CDIResource" in str(p_type)
                    )

                    if is_resource_param:
                        # Bind to the model class (e.g. model.CDIResource)
                        if not hasattr(target_class, name):
                            setattr(target_class, name, make_instance_wrapper(func, assistant_cls))

                        # Bind to the assistant class using our descriptor
                        if isinstance(attr, classmethod):
                            setattr(assistant_cls, name, AssistantMethodDescriptor(assistant_cls, func))
            except (ValueError, TypeError):
                # Skip methods that can't be inspected (e.g. some built-ins)
                continue


def automate_instance_methods(target_class: type) -> Callable[[type], type]:
    """
    Decorator for manual assistant method binding.
    """

    def decorator(cls: type) -> type:
        _bind_assistant_methods(cls, target_class)
        return cls

    return decorator


class CdiAssistant(BaseModel):
    """
    Base class for all DDI-CDI Assistants.
    """

    resource: Any | None = None

    model_config = {"extra": "allow"}

    @classmethod
    def _bind_to_model(cls, target_class: type) -> None:
        """Helper to bind assistant methods to a specific model class."""
        _bind_assistant_methods(cls, target_class)

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute and method access to the wrapped resource."""
        if name == "resource":
            raise AttributeError(name)

        # Use object.__getattribute__ to avoid recursion during init
        try:
            res = object.__getattribute__(self, "resource")
            if res is not None:
                return getattr(res, name)
        except AttributeError:
            pass

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Proxy attribute assignment to the wrapped resource."""
        if name == "resource":
            super().__setattr__(name, value)
        elif self.resource is not None and hasattr(self.resource, name):
            setattr(self.resource, name, value)
        else:
            super().__setattr__(name, value)


@automate_instance_methods(model.CDIResource)
class CdiResourceAssistant(CdiAssistant):
    """
    Base assistant for all CDI Resources (both Classes and DataTypes).
    Methods defined here are available on all objects inheriting from CDIResource.
    """

    resource: model.CDIResource | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Automatically bind methods of the new subclass to CDIResource
        cls._bind_to_model(model.CDIResource)

    @classmethod
    def get_uri(cls, resource: model.CDIResource) -> str | None:
        identifier = getattr(resource, "identifier", None)
        if identifier is not None:
            uri = getattr(identifier, "uri", None)
            if uri is not None:
                return str(uri)
        elif getattr(resource, "id", None) is not None:
            return str(resource.id)
        return None

    @classmethod
    def set_uri(cls, resource: model.CDIResource, value: str) -> str:
        if hasattr(resource, "identifier"):
            identifier = getattr(resource, "identifier", None)
            if identifier is None:
                identifier = model.Identifier()
                resource.identifier = identifier
            identifier.uri = value

        # Crucial: Sync with resource.id field.
        # In RdfBaseModel, the 'id' field determines the RDF subject URI.
        # CDI resources set rdf_uri_generator with auto_uuid=False, so failing to set this
        # would result in the resource being serialized as a blank node [].
        resource.id = value
        return value

    @classmethod
    def add_resources(
        cls,
        resource: model.CDIResource,
        target_resources: Any,
        property_name: str,
        clear: bool = False,
        exact_match: bool = True,
    ) -> bool:
        """
        Attaches one or more resources to a specified property of the CDI resource.

        This method is the primary engine for building relationships between CDI objects.
        It handles URI resolution from various input types (Assistant wrappers, raw
        model objects, or strings/URIRefs) and ensures correct assignment based on
        the target property's type (list vs. singular).
        """
        target_property = property_name
        if not hasattr(resource, target_property):
            if not exact_match:
                # Dir(resource) might be expensive, but needed for prefix search
                # (e.g. 'isDefinedBy' matching 'isDefinedBy_RepresentedVariable')
                matches = [p for p in dir(resource) if p.startswith(property_name)]
                if matches:
                    target_property = matches[0]
                else:
                    return False
            else:
                return False

        if not isinstance(target_resources, list):
            target_resources = [target_resources]

        uris = []
        for r in target_resources:
            uri = None
            if hasattr(r, "get_uri") and callable(r.get_uri):
                uri = r.get_uri()
            elif hasattr(r, "resource") and hasattr(r.resource, "identifier") and r.resource.identifier:
                uri = r.resource.identifier.uri
            elif hasattr(r, "identifier") and r.identifier:
                uri = r.identifier.uri
            elif hasattr(r, "id") and r.id:
                uri = str(r.id)
            elif isinstance(r, (str, URIRef)):
                uri = str(r)

            if uri:
                uris.append(URIRef(uri))

        field = resource.model_fields.get(target_property)
        is_list = False
        if field:
            annotation = field.annotation
            # Unwrap Annotated if present
            if get_origin(annotation) is Annotated:
                annotation = get_args(annotation)[0]

            import types

            origin = get_origin(annotation)
            if origin is list:
                is_list = True
            elif origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType):
                args = get_args(annotation)
                for arg in args:
                    if get_origin(arg) is list:
                        is_list = True
                        break

        if target_property == "has_InstanceVariable":
            # Force list for debug if detection fails
            # is_list = True
            pass

        current = getattr(resource, target_property)
        if is_list:
            if current is None:
                current = []
                setattr(resource, target_property, current)
            if clear:
                current.clear()
            current.extend(uris)
        else:
            if uris:
                setattr(resource, target_property, uris[0])
        return True

    @classmethod
    def add_to_rdf_graph(cls, resource: model.CDIResource, graph: Graph) -> Any:
        """Helper to add the resource to an RDF graph."""
        return resource.to_rdf_graph(graph=graph)


@automate_instance_methods(model.CDIClass)
class CdiClassAssistant(CdiResourceAssistant):
    """
    General assistant for CDI Classes.
    Methods defined here are available on all objects inheriting from CDIClass.
    """

    resource: model.CDIClass | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Automatically bind methods of the new subclass to CDIClass
        cls._bind_to_model(model.CDIClass)

    @classmethod
    def get_ddi_identifier_value(cls, resource: model.CDIClass) -> str | None:
        identifier = getattr(resource, "identifier", None)
        if identifier is not None:
            ddi_id = getattr(identifier, "ddiIdentifier", None)
            if ddi_id is not None:
                return str(getattr(ddi_id, "dataIdentifier", ""))
        return None

    @classmethod
    def set_identifiers(
        cls,
        resource: model.CDIClass,
        ddi: str | None = None,
        nonddi: str | None = None,
        uri: str | None = None,
    ) -> Any:
        identifier = getattr(resource, "identifier", None)
        if identifier is None:
            identifier = model.Identifier()
            if hasattr(resource, "identifier"):
                resource.identifier = identifier

        if ddi:
            ddi_id = getattr(identifier, "ddiIdentifier", None)
            if ddi_id is None:
                ddi_id = model.InternationalRegistrationDataIdentifier(
                    dataIdentifier=ddi, registrationAuthorityIdentifier="int.dataartifex", versionIdentifier="1"
                )
                identifier.ddiIdentifier = ddi_id
            else:
                ddi_id.dataIdentifier = ddi

        if nonddi:
            nonddi_list = getattr(identifier, "nonDdiIdentifier", None)
            if nonddi_list is None:
                nonddi_list = []
                identifier.nonDdiIdentifier = nonddi_list
            nonddi_list.append(model.NonDdiIdentifier(value=nonddi, type="generic"))

        if uri:
            cls.set_uri(resource, uri)

        return identifier

    @classmethod
    def set_ddi_identifier(
        cls,
        resource: model.CDIClass,
        value: str,
        authority: str | None = None,
        version: str | None = None,
    ) -> Any:
        identifier = cls.set_identifiers(resource, ddi=value)
        if identifier:
            ddi_id = getattr(identifier, "ddiIdentifier", None)
            if ddi_id:
                if authority:
                    ddi_id.registrationAuthorityIdentifier = authority
                if version:
                    ddi_id.versionIdentifier = version
                return ddi_id
        return None

    @classmethod
    def add_nonddi_identifier(
        cls, resource: model.CDIClass, value: str, type: str | None = None, clear: bool = False
    ) -> Any:
        identifier = getattr(resource, "identifier", None)
        if clear and identifier:
            identifier.nonDdiIdentifier = None

        identifier = cls.set_identifiers(resource, nonddi=value)
        if identifier:
            nonddi_list = getattr(identifier, "nonDdiIdentifier", [])
            if nonddi_list and type:
                nonddi_list[-1].type = type
            return nonddi_list[-1] if nonddi_list else None
        return None

    @classmethod
    def set_simple_name(cls, resource: model.CDIClass, value: str) -> Any:
        if hasattr(resource, "name"):
            instance = model.ObjectName(name=value)
            resource.name = [instance]
            return instance
        return None

    @classmethod
    def set_simple_display_label(cls, resource: model.CDIClass, value: str, language: str = "en") -> Any:
        if hasattr(resource, "displayLabel") and value:
            lang_string = model.LanguageString(content=value, language=language)
            display_label = model.LabelForDisplay(languageSpecificString=[lang_string])
            resource.displayLabel = [display_label]
            return display_label
        return None

    @classmethod
    def add_data_structure(cls, resource: model.CDIClass, data_structure: Any) -> Any:
        return cls.add_resources(resource, data_structure, "has_DataStructure", exact_match=False)

    @classmethod
    def add_categories(cls, resource: model.CDIClass, category: Any) -> Any:
        return cls.add_resources(resource, category, "has_Category", exact_match=False)

    @classmethod
    def set_category(cls, resource: model.CDIClass, category: Any) -> Any:
        return cls.add_resources(resource, category, "denotes", exact_match=False)

    @classmethod
    def set_category_set(cls, resource: model.CDIClass, category_set: Any) -> Any:
        return cls.add_resources(resource, category_set, "has_CategorySet", exact_match=False)

    @classmethod
    def add_code(cls, resource: model.CDIClass, code: Any) -> Any:
        return cls.add_resources(resource, code, "has_Code", exact_match=False)

    @classmethod
    def add_dataset(cls, resource: model.CDIClass, dataset: Any) -> Any:
        return cls.add_resources(resource, dataset, "has_DataSet", exact_match=False)

    @classmethod
    def add_variable(cls, resource: model.CDIClass, variable: Any) -> Any:
        return cls.add_resources(resource, variable, "has_InstanceVariable", exact_match=False)

    @classmethod
    def factory(
        cls,
        target_cls: type[model.CDIClass],
        id_prefix: str | None = None,
        id_suffix: str | None = None,
        base_uri: str = "urn:ddi-cdi:",
        non_ddi_id: str | None = None,
        non_ddi_id_type: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> "CdiClassAssistant":
        if id_prefix is None:
            id_prefix = str(uuid.uuid4())

        cdi_resource = target_cls(*args, **kwargs)

        cdi_resource_uid = f"{id_prefix}_{cdi_resource.__class__.__name__}"
        if id_suffix:
            cdi_resource_uid += f"_{id_suffix}"

        cls.set_ddi_identifier(cdi_resource, cdi_resource_uid)

        cdi_resource_uri = f"{base_uri}{cdi_resource_uid}"
        cls.set_uri(cdi_resource, cdi_resource_uri)

        if non_ddi_id:
            cls.add_nonddi_identifier(cdi_resource, non_ddi_id, type=non_ddi_id_type)

        return cls(resource=cdi_resource)

    @classmethod
    def create(cls, target_cls: type[model.CDIClass], name: str | None = None, **kwargs: Any) -> "CdiClassAssistant":
        assistant = cls.factory(target_cls, **kwargs)
        if name and assistant.resource:
            cls.set_simple_name(assistant.resource, name)
        return assistant


@automate_instance_methods(model.CDIDataType)
class CdiDataTypeAssistant(CdiResourceAssistant):
    """
    General assistant for CDI Data Types.
    Methods defined here are available on all objects inheriting from CDIDataType.
    """

    resource: model.CDIDataType | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Automatically bind methods of the new subclass to CDIDataType
        cls._bind_to_model(model.CDIDataType)

    @classmethod
    def factory(
        cls,
        target_cls: type[model.CDIDataType],
        id_prefix: str | None = None,
        id_suffix: str | None = None,
        base_uri: str = "urn:ddi-cdi:",
        *args: Any,
        **kwargs: Any,
    ) -> "CdiDataTypeAssistant":
        """Factory for creating data types. Unlike classes, they don't have DDI identifiers."""
        cdi_datatype = target_cls(*args, **kwargs)

        if id_prefix:
            uid = f"{id_prefix}_{cdi_datatype.__class__.__name__}"
            if id_suffix:
                uid += f"_{id_suffix}"
            cls.set_uri(cdi_datatype, f"{base_uri}{uid}")

        return cls(resource=cdi_datatype)

    @classmethod
    def create(cls, target_cls: type[model.CDIDataType], **kwargs: Any) -> "CdiDataTypeAssistant":
        return cls.factory(target_cls, **kwargs)


# For backward compatibility
CdiResourceAssistantAlias = CdiClassAssistant  # If needed for extremely old code
# Note: CdiResourceAssistant is now a real class for CDIResource-level methods.
