import logging
import os
from typing import Any

import pyshacl
from rdflib import Graph

from .assistants import CdiAssistant


def ddi_cdi_resources_to_graph(resources: dict[str, CdiAssistant]) -> Graph:
    """
    Helper to convert a stack of DdiCdiResources to a RDF Graph
    """
    g = Graph()
    g.bind("cdi", "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/")
    g.bind("skos", "http://www.w3.org/2004/02/skos/core#")

    for r in resources.values():
        if hasattr(r, "add_to_rdf_graph"):
            r.add_to_rdf_graph(g)
        elif hasattr(r, "to_rdf_graph"):
            r.to_rdf_graph(graph=g)
        else:
            logging.warning(f"Resource {r} has no serialization method")

    return g


def shacl_validate_ddi_cdi(data: Graph | str | Any) -> tuple[bool, Graph, str]:
    """
    Validates a DDI-CDI graph or Assistant resources using the model_1_0_0.shacl.ttl file.

    Args:
        data: The DDI-CDI graph to validate (rdflib.Graph, path to file, or dictionary of CdiAssistant resources).

    Returns:
        A tuple containing:
        - conforms (bool): True if the graph is valid, False otherwise.
        - results_graph (rdflib.Graph): The validation report graph.
        - results_text (str): The validation report as text.
    """
    shacl_path = os.path.join(os.path.dirname(__file__), "model_1_0_0.shacl.ttl")

    if isinstance(data, str):
        g = Graph()
        g.parse(data)
    elif isinstance(data, Graph):
        g = data
    elif isinstance(data, dict):
        g = ddi_cdi_resources_to_graph(data)
    else:
        raise ValueError("Unsupported data type for validation. Expected Graph, file path, or resources dict.")

    logging.info(f"Validating DDI-CDI graph against {shacl_path}")

    conforms, results_graph, results_text = pyshacl.validate(
        data_graph=g, shacl_graph=shacl_path, inference=None, serialize_report_graph=False
    )

    return conforms, results_graph, results_text
