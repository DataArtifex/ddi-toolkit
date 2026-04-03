import uuid

from dartfx.ddi.ddicdi import model_1_0_0 as model
from dartfx.ddi.ddicdi.assistants import CdiClassAssistant


def reproduce():
    base_uuid = str(uuid.uuid4())
    # Create an InstanceVariable assistant
    cdi_instance_var = CdiClassAssistant.factory(
        model.InstanceVariable,
        id_prefix=base_uuid,
        id_suffix="test",
        non_ddi_id="test",
        non_ddi_id_type="ddi-codebook",
    )

    # Try calling set_simple_name
    print("Calling set_simple_name...")
    assert cdi_instance_var.resource is not None
    CdiClassAssistant.set_simple_name(cdi_instance_var.resource, "TEST_NAME")
    print("Success!")


if __name__ == "__main__":
    reproduce()
