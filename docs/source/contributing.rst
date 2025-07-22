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

   # Clone the repository
   git clone https://github.com/DataArtifex/ddi-toolkit.git
   cd ddi-toolkit
   
   # Create a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install development dependencies
   pip install -e .[dev]

Running Tests
-------------

.. code-block:: bash

   # Run all tests
   pytest
   
   # Run tests with coverage
   pytest --cov=dartfx.ddi
   
   # Run specific test file
   pytest tests/test_ddicdi_model.py

Code Style
----------

We use Black for code formatting:

.. code-block:: bash

   # Format code
   black src/ tests/
   
   # Check formatting
   black --check src/ tests/

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

- Bug fixes
- New features
- Documentation improvements
- Test coverage improvements
- Performance optimizations

Guidelines
----------

- Keep changes focused and atomic
- Include tests for new functionality
- Update documentation for user-facing changes
- Follow Python naming conventions
- Add type hints where appropriate
