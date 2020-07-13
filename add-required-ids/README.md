Used to add an ID for all elements in the BuildingSync/schema repository `examples` directory for which an ID is not present.

Assume the following directory structure:
```
|-schema/
|--BuildingSync.xsd
|-transformations/
```

Workflow:
1. Make sure the schema directory is checked out on the branch / commit you want to use for the BuildingSync.xsd file.
1. run `python main.py path/to/dir/with/bsync/xml/files`
