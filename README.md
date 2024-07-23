# DDI Toolkit

This package provides various utilities for using, processing, or converting metadata based on the [Data Documentation Initiative (DDI)](https://ddialliance.org/), an international standard for describing the data produced by surveys and other observational methods in the social, behavioral, economic, and health sciences.

There are three major flavors of DDI: DDI-Codebbok, DDI-Lifecycle, and the upcoming DDI Cross Domain Integration (CDI). This initial version of th epackage focuses on [DDI-Codebook](https://ddialliance.org/Specification/DDI-Codebook/2.5/), the light-weight version of the standard, intended primarily to document simple survey data. This specification has been widely adopted around the globe by statistical agencies, data producers, archives, research centers, and international organizations. Thousands of datasets have been documented with DDI-C.


## Installation
 
```
pip install dartfx-ddi
```
 
## Usage

```
from dartfx.ddi import codebook
my_codebook = codebook.loadXml('mycodebook.xml')
# do something useful...
```

This core package is used by other [Data Artifex](http://www.dataartifex.org) components leveraging DDI.

## Roadmap

- Add additional helper methods (as needed arise)
- Conversion to DDI-CDI
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