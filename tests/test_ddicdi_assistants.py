from dartfx.ddi.ddicdi import model_1_0_0 as model
from dartfx.ddi.ddicdi import model_1_1_0 as model_latest
from dartfx.ddi.ddicdi.assistants import (
    CdiAssistant,
    CdiClassAssistant,
    CdiResourceAssistant,
)


def test_create_instance_variable():
    name = "GENDER"
    # Using generic CdiClassAssistant instead of VariableAssistant
    assistant = CdiClassAssistant.create(model.InstanceVariable, name=name)

    # Check type: it should be the assistant wrapping the resource
    assert isinstance(assistant, CdiClassAssistant)
    assert isinstance(assistant.resource, model.InstanceVariable)

    # Proxy check: Assistant should expose resource properties
    assert assistant.name is not None
    assert len(assistant.name) == 1
    assert assistant.name[0].name == name

    # Check identifiers
    assert assistant.identifier is not None
    assert assistant.identifier.ddiIdentifier is not None

    # Method proxy check: get_ddi_identifier_value should be available on assistant
    ddi_id = assistant.get_ddi_identifier_value()  # type: ignore
    assert ddi_id is not None
    assert "_InstanceVariable" in ddi_id

    # Check URI via proxy
    uri = assistant.get_uri()  # type: ignore
    assert uri is not None
    assert uri.startswith("urn:ddi-cdi:")


def test_factory_with_custom_ids():
    id_prefix = "prefix"
    id_suffix = "suffix"
    assistant = CdiClassAssistant.factory(model.InstanceVariable, id_prefix=id_prefix, id_suffix=id_suffix)

    assert isinstance(assistant, CdiClassAssistant)
    ddi_id = assistant.get_ddi_identifier_value()  # type: ignore
    assert ddi_id == f"{id_prefix}_InstanceVariable_{id_suffix}"

    uri = assistant.get_uri()  # type: ignore
    assert str(uri) == f"urn:ddi-cdi:{ddi_id}"


def test_create_instance_variable_with_kwargs():
    assistant = CdiClassAssistant.create(
        model.InstanceVariable, name="VAR1", id_prefix="p", id_suffix="s", non_ddi_id="sid"
    )

    assert assistant.name[0].name == "VAR1"
    ddi_id = assistant.get_ddi_identifier_value()  # type: ignore
    assert ddi_id == "p_InstanceVariable_s"

    # Check non-ddi identifier proxy
    assert assistant.identifier.nonDdiIdentifier is not None
    assert assistant.identifier.nonDdiIdentifier[0].value == "sid"


def test_automated_instance_binding():
    # Test that we can call ResourceAssistant methods directly on the assistant instance
    assistant = CdiClassAssistant.create(model.InstanceVariable, name="TEST_VAR")

    # This calls ResourceAssistant.set_ddi_identifier(assistant.resource, "NEW_ID")
    assistant.set_ddi_identifier("NEW_ID")  # type: ignore

    assert assistant.get_ddi_identifier_value() == "NEW_ID"  # type: ignore
    assert assistant.resource.get_ddi_identifier_value() == "NEW_ID"  # type: ignore

    assistant.set_simple_name("UPDATED_NAME")  # type: ignore
    assert assistant.name[0].name == "UPDATED_NAME"


def test_automated_instance_binding_isolation():
    # We add a dummy instance method to CdiClassAssistant
    def assistant_only_method(_self):
        return "I am private to the assistant"

    CdiClassAssistant.assistant_only_method = assistant_only_method  # type: ignore[attr-defined]

    # Check that the assistant instance DOES have it
    assistant = CdiClassAssistant.create(model.InstanceVariable, name="isolation_test")
    assert assistant.assistant_only_method() == "I am private to the assistant"

    # Check that the underlying CDIResource does NOT have it
    assert not hasattr(assistant.resource, "assistant_only_method")


def test_classmethod_selective_exposure():
    from dartfx.ddi.ddicdi import model_1_0_0 as model
    from dartfx.ddi.ddicdi.assistants import (
        CdiResourceAssistant,
        automate_instance_methods,
    )

    class OtherAssistant(CdiResourceAssistant):
        @classmethod
        def resource_helper(cls, _resource: model.CDIResource):
            return "bound"

    @automate_instance_methods(model.CDIResource)
    class SelectiveAssistant(CdiAssistant):
        @classmethod
        def plain_utility(cls, data: str):
            return f"data: {data}"

    res = model.InstanceVariable()
    assistant = SelectiveAssistant(resource=res)

    # OtherAssistant bound 'resource_helper' to CDIResource
    resource_helper = getattr(res, "resource_helper", None)
    assert callable(resource_helper)
    assert resource_helper() == "bound"

    # SelectiveAssistant proxies to res, which has the method!
    # This works because SelectiveAssistant doesn't have its own 'resource_helper'.
    assert assistant.resource_helper() == "bound"

    # Should NOT be bound to resource
    assert not hasattr(res, "plain_utility")

    # Should work on the class
    assert SelectiveAssistant.plain_utility("test") == "data: test"


def test_subclass_automatic_binding():
    class SubAssistant(CdiResourceAssistant):
        @classmethod
        def subclass_helper(cls, _resource: model.CDIResource):
            return "from subclass"

    assistant = CdiClassAssistant.create(model.InstanceVariable, name="subclass_test")

    # The method should be bound to the underlying resource
    assert hasattr(assistant.resource, "subclass_helper")

    # And accessible via the assistant proxy
    assert assistant.subclass_helper() == "from subclass"


def test_generic_create():
    # Test that we can create any CDI class using the generic create method.
    # We use Category because it has a 'name' attribute.
    name = "Category1"
    assistant = CdiClassAssistant.create(model.Category, name=name)

    assert isinstance(assistant.resource, model.Category)
    assert assistant.name[0].name == name
    assert assistant.get_ddi_identifier_value() is not None  # type: ignore


def test_create_instance_variable_latest_model():
    assistant = CdiClassAssistant.create(model_latest.InstanceVariable, name="LATEST_VAR")

    assert isinstance(assistant.resource, model_latest.InstanceVariable)
    assert assistant.name[0].name == "LATEST_VAR"
    assert assistant.get_ddi_identifier_value() is not None  # type: ignore
    get_ddi_identifier_value = getattr(assistant.resource, "get_ddi_identifier_value", None)
    assert callable(get_ddi_identifier_value)
    assert get_ddi_identifier_value() is not None
