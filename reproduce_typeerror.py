import uuid

from dartfx.ddi.ddicdi import model_1_0_0 as model
from dartfx.ddi.ddicdi.assistants import CdiResourceAssistant


def reproduce():
    base_uuid = str(uuid.uuid4())
    # Create an InstanceVariable assistant
    cdi_instance_var = CdiResourceAssistant.factory(
        model.InstanceVariable,
        id_prefix=base_uuid,
        id_suffix="test",
        non_ddi_id="test",
        non_ddi_id_type="ddi-codebook",
    )

    # Try calling set_simple_name
    print("Calling set_simple_name...")
    cdi_instance_var.set_simple_name("TEST_NAME")
    print("Success!")


if __name__ == "__main__":
    reproduce()
