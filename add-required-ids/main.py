import os
import sys

import urllib
from uuid import uuid4

from lxml import etree
from xmlschema import XMLSchema


BUILDINGSYNC_URI = 'http://buildingsync.net/schemas/bedes-auc/2019'
NAMESPACES = {
    'auc': BUILDINGSYNC_URI
}

def add_ids(file_name, elements_requiring_ids):
    """
    Parse file and add unique ID attributes to all elements not containing one

    :param file_name: Path of BSync XML file to read in
    :param elements_requiring_ids: [xmlschema.validators.elements.XsdElement] Schema elements that have ID attributes
    :return:
    """
    tree = etree.parse(file_name)
    for el in elements_requiring_ids:
        # A nice method to return the full path to an element, so as to avoid
        # finding elements such as auc:LinkedPremises/auc:Building
        xp = "//" + el.get_path().replace(f"{{{BUILDINGSYNC_URI}}}", 'auc:')
        elements_in_file = tree.xpath(xp, namespaces=NAMESPACES)
        for el2 in elements_in_file:
            if not 'ID' in el2.attrib.keys():
                el2.set('ID', f"{el.local_name}-{uuid4()}")

    with open(file_name, 'w') as f:
        f.write(etree.tostring(tree.getroot(), pretty_print=True, xml_declaration=True, encoding="UTF-8").decode())


if __name__ == "__main__":
    assert len(sys.argv) == 2, "Specify path to directory with XML files to update as argument, like so: python main.py ../path/to/files"
    source = sys.argv[1]
    files = [source]
    if os.path.isdir(source):
        files = [os.path.join(source, f) for f in os.listdir(source) if f.endswith('.xml')]

    # Load in schema and get location to example files
    schema_path = os.path.realpath("../../schema")
    schema = XMLSchema(os.path.join(schema_path, "BuildingSync.xsd"))

    # very nice function - XPath in Schema file
    elements_requiring_ids = schema.findall("//*[@ID]")

    # Setup parse
    parser = etree.XMLParser(remove_blank_text=True)
    etree.set_default_parser(parser)
    etree.register_namespace('auc', BUILDINGSYNC_URI)

    for file_name in files:
        print(f"Processing: {os.path.realpath(file_name)}")
        add_ids(file_name, elements_requiring_ids)
