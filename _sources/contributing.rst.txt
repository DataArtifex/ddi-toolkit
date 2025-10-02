Contributing
============

We welcome contributions to the DDI Toolkit! This document outlines how to contribute to the project.

Getting Started
---------------

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature or bug fix
4. Make your changes
5. Run tests to ensure everything works
6. Submit a pull request

Development Setup
-----------------

.. code-block:: bash

   # Fork and clone the repository
   git clone https://github.com/yourusername/ddi-toolkit.git
   cd ddi-toolkit
   
   # Create a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install development dependencies
   pip install -e .
   
   # Verify installation
   pytest

Running Tests
-------------

.. code-block:: bash

   # Run all tests
   pytest
   
   # Run tests with verbose output
   pytest -v
   
   # Run specific test file
   pytest tests/test_ddicodebook.py
   
   # Run tests for specific module
   pytest tests/test_ddicdi_specification.py

Code Style
----------

Follow PEP 8 guidelines and use meaningful names:

.. code-block:: python

   # Good
   def load_ddi_codebook(file_path: str) -> codeBookType:
       """Load a DDI-Codebook from XML file."""
       return ddicodebook.loadxml(file_path)
   
   # Use type hints
   from typing import Optional, List, Dict
   
   def extract_variables(codebook: codeBookType, 
                        var_type: Optional[str] = None) -> List[Dict]:
       """Extract variable information from codebook."""
       # Implementation here
       pass

Documentation
-------------

Documentation is built with Sphinx:

.. code-block:: bash

   # Build documentation
   cd docs
   make html
   
   # View documentation
   open build/html/index.html

Submitting Changes
------------------

1. Ensure all tests pass
2. Update documentation if needed
3. Add or update tests for new features
4. Follow the existing code style
5. Write clear commit messages
6. Submit a pull request with a clear description

Types of Contributions
----------------------

**High Priority:**

- DDI-CDI specification coverage improvements
- Test coverage enhancements  
- Documentation updates and examples
- Bug fixes in DDI-Codebook processing

**Medium Priority:**

- Performance optimizations
- Additional utility functions
- Integration improvements
- Error handling enhancements

**Experimental:**

- DDI-Codebook to DDI-CDI conversion
- Advanced RDF serialization features
- Integration with external tools

Guidelines
----------

**Code Quality:**

- Keep changes focused and atomic
- Include tests for new functionality
- Update documentation for user-facing changes
- Follow Python naming conventions (except DDI-CDI classes)
- Add comprehensive type hints
- Write clear docstrings with examples

**Testing:**

- Write unit tests for all new functions
- Test edge cases and error conditions
- Ensure existing tests continue to pass
- Use meaningful test names and assertions

**Documentation:**

- Update API documentation for new features
- Add examples to demonstrate usage
- Update changelog for significant changes
- Keep README current with new capabilities

**DDI-Specific Guidelines:**

- Maintain compatibility with DDI specifications
- Handle malformed XML gracefully in DDI-Codebook
- Follow DDI-CDI naming conventions for model classes
- Test with real-world DDI documents when possible
