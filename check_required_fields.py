import os
import sys

# Setup path
sys.path.append(os.path.join(os.getcwd(), "src"))

from dartfx.ddi.ddicdi import model_1_0_0 as model

classes_to_check = [
    model.InstanceVariable,
    model.SubstantiveValueDomain,
    model.CodeList,
    model.CategorySet,
    model.DataSet,
    model.LogicalRecord,
    model.DataStructure,
    model.DataStructureComponent,
    model.ComponentPosition,
    model.Category,
    model.Code,
    model.Notation,
]

for cls in classes_to_check:
    required = [name for name, field in cls.model_fields.items() if field.is_required()]
    print(f"{cls.__name__} required fields: {required}")
