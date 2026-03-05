"""Generic DDI utilities and experimental data models.

Note:
    The simplified models in this module (Variable, Code, CodeList, DataDictionary)
    are currently **experimental** and subject to change in future versions.
"""

from decimal import Decimal

from pydantic import BaseModel, Field

__all__ = [
    "Variable",
    "Code",
    "CodeList",
    "DataDictionary",
]


#
# EXPERIMENTAL SIMPLIFIED MODEL
#


class Variable(BaseModel):
    """
    Experimental simplified representation of a variable.

    .. admonition:: Experimental
        This class is part of an experimental simplified model and may change.

    :meta private:
    """

    name: str
    data_type: str | None = Field(default="str")


class Code(BaseModel):
    """
    Experimental simplified representation of a code.

    .. admonition:: Experimental
        This class is part of an experimental simplified model and may change.

    :meta private:
    """

    value: str | int | Decimal
    label: str | None = Field(default=None)
    is_missing: bool | None = Field(default=None)


class CodeList(BaseModel):
    """
    Experimental simplified representation of a code list.

    .. admonition:: Experimental
        This class is part of an experimental simplified model and may change.

    :meta private:
    """

    codes: list[Code] = Field(default_factory=list)


class DataDictionary(BaseModel):
    """
    Experimental simplified representation of a data dictionary.

    .. admonition:: Experimental
        This class is part of an experimental simplified model and may change.

    :meta private:
    """

    variables: list[Variable] = Field(default_factory=list)
    codes: list[Code] = Field(default_factory=list)
