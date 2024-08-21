# DDI Toolkit
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md)

**This project is in its early development stages, so stability is not guaranteed, and documentation is limited. We welcome your feedback and contributions as we refine and expand this project together!**

## Overview

This package provides utilities for using, processing, or converting metadata based on the [Data Documentation Initiative (DDI)](https://ddialliance.org/), an international standard for describing the data produced by surveys and other observational methods in the social, behavioral, economic, and health sciences.

There are three major flavors of DDI: DDI-Codebbok, DDI-Lifecycle, and the upcoming DDI Cross Domain Integration (CDI). This initial version of th epackage focuses on [DDI-Codebook](https://ddialliance.org/Specification/DDI-Codebook/2.5/), the light-weight version of the standard, intended primarily to document simple survey data. This specification has been widely adopted around the globe by statistical agencies, data producers, archives, research centers, and international organizations. Thousands of datasets have been documented with DDI-C.


## Installation### PyPI ReleaseOnce stable, this package will be officially released and distributed through [PyPI](https://pypi.org/). Stay tuned for updates!### Local InstallationIn the meantime, you can install the package locally by following these steps:1. **Clone the Repository:**   First, clone the repository to your local machine:   ```bash   git clone <repository-url>   cd <repository-directory>   ```2. **Install the Package:**   From the project's home directory, run the following command to install the package:   ```bash   pip install -e .   ```### Installing DependenciesTo install the required dependencies, execute the following command:```bashpip install -r requirements.txt```Make sure you are in the project's root directory when running these commands.Feel free to replace `<repository-url>` and `<repository-directory>` with the actual URL and directory name of your project. This enhanced version provides clear instructions and formatting to guide users through the installation process effectively.
 
## Usage

### Load and process a DDI-Codebook XML document

```
from dartfx.ddi import codebook
my_codebook = codebook.loadXml('mycodebook.xml')
# do something useful...
```

### Convert a DDI-Codebook to DDI-CDIF

This core package is used by other [Data Artifex](http://www.dataartifex.org) components leveraging DDI.

## Roadmap

- Add additional helper methods (as needed arise)
- SQL schema generators
- DCAT generator
- Explore how this can potentially be used with LLMs
 
## Contributing
 
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D
 
## License
 
The MIT License (MIT)

Copyright (c) 2024 Pascal L.G.A. Heus

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.