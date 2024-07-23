
collection: collection.yaml
	# validate
	linkml-lint collection.yaml --ignore-warnings --validate || exit 1;
	# generate python
	gen-python collection.yaml > collection.py
	# generate JSON schema
	gen-python collection.yaml > collection.py
	gen-json-schema collection.yaml > collection.json

