"""A simplified and generic model for cross-DDI operations, casual users, and generic helpers.

**experimental** and subject to change in future versions.
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "Variable",
    "Code",
    "CodeList",
    "DataDictionary",
]


#
# SIMPLIFIED MODEL
#


class SimpleResource(BaseModel):
    """
    Experimental simplified representation of a base resource.

    .. admonition:: Experimental
        This class is part of an experimental simplified model and may change.

    :meta private:
    """

    id: str | None = Field(default=None)
    attributes: dict[str, Any] | None = Field(default=None)


class Variable(SimpleResource):
    """
    Experimental simplified representation of a variable.

    .. admonition:: Experimental
        This class is part of an experimental simplified model and may change.

    :meta private:
    """

    name: str
    data_type: str | None = Field(default="str")


class Code(SimpleResource):
    """
    Experimental simplified representation of a code.

    .. admonition:: Experimental
        This class is part of an experimental simplified model and may change.

    :meta private:
    """

    value: str | int | Decimal
    label: str | None = Field(default=None)
    is_missing: bool | None = Field(default=None)


class CodeList(SimpleResource):
    """
    Experimental simplified representation of a code list.

    .. admonition:: Experimental
        This class is part of an experimental simplified model and may change.

    :meta private:
    """

    codes: list[Code] = Field(default_factory=list)


class DataDictionary(SimpleResource):
    """
    Experimental simplified representation of a data dictionary.

    .. admonition:: Experimental
        This class is part of an experimental simplified model and may change.

    :meta private:
    """

    variables: list[Variable] = Field(default_factory=list)
    codes: list[Code] = Field(default_factory=list)
