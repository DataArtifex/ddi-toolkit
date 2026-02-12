import os
import logging
from typing import Tuple, Union, Any

from rdflib import Graph
import pyshacl

def validate_ddi_cdi(data: Union[Graph, str, Any]) -> Tuple[bool, Graph, str]:
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
        # Assume it's a dictionary of CdiAssistant resources
        # We import here to avoid circular dependency
        from ..utils import ddi_cdi_resources_to_graph
        g = ddi_cdi_resources_to_graph(data)
    else:
        raise ValueError("Unsupported data type for validation. Expected Graph, file path, or resources dict.")
        
    logging.info(f"Validating DDI-CDI graph against {shacl_path}")
    
    conforms, results_graph, results_text = pyshacl.validate(
        data_graph=g,
        shacl_graph=shacl_path,
        inference='rdfs',
        serialize_report_graph=True
    )
    
    return conforms, results_graph, results_text
