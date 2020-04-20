from io import StringIO

from lxml import etree

BUILDINGSYNC_URI = 'http://buildingsync.net/schemas/bedes-auc/2019'
NAMESPACES = {
    'auc': BUILDINGSYNC_URI
}

def children_sorter_factory(schema, tree, element):
    """returns a function for getting a key value for sorting elements

    Used to sort an elements children after inserting a new element to ensure
    it meets the schema sequence specification

    :param schema: xmlschema.XmlSchema, the schema to follow
    :param tree: ElementTree, the tree from which the element came from
    :param element: Element, the element whose children are to be sorted
    """
    # get the element from the schema
    element_path = tree.getpath(element)
    schema_element = schema.find(element_path)
    if schema_element is None:
        raise Exception(f'Unable to find path in schema: "{element_path}"')

    ordered_children = [child.name for child in schema_element.iterchildren()]

    # construct a function for sorting an element's children by returning the index of the
    # child according to the ordering of the schema
    def _getkey(element):
        if isinstance(element, etree._Comment):
            # put comments at the end
            return 100
        elif not isinstance(element, etree._Element):
            raise Exception(f'Unknown type while sorting: "{type(element)}"')

        if element.tag not in ordered_children:
            # a more helpful exception that the one raised by .index()
            raise Exception(f'Failed to find "{element.tag}" in {ordered_children}')

        return ordered_children.index(element.tag)

    return _getkey


def sort_element(schema, tree, element):
    """Sorts an element's children in place"""
    getter = children_sorter_factory(schema, tree, element)
    element[:] = sorted(element, key=getter)


def remove_dupes(element):
    """Removes duplicate children
    !! assumes that element's children are already in sorted order
    be careful which elements this is run on as it might find false positives that it removes
    """
    prev_child_text = ''
    prev_child_tag = ''
    prev_child = None
    for child in element:
        if child.text == prev_child_text and child.tag == prev_child_tag:
            element.remove(child)
        elif child.tag == prev_child_tag and 'AnnualSavingsSourceEnergy' in child.tag:
            # keep the one with a smaller value (being conservative)
            if float(prev_child_text) < float(child.text):
                element.remove(child)
            else:
                element.remove(prev_child)

        prev_child_text = child.text
        prev_child_tag = child.tag
        prev_child = child


def fix_namespaces(tree):
    """This method should be called when then namespace map is not correct.
    It will clone the tree, ensuring all nodes have the proper namespace prefixes
    """
    original_tree = tree

    etree.register_namespace('auc', BUILDINGSYNC_URI)
    etree.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

    new_tree = etree.parse(StringIO('''<?xml version="1.0"?>
        <auc:BuildingSync xmlns:auc="http://buildingsync.net/schemas/bedes-auc/2019" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://buildingsync.net/schemas/bedes-auc/2019 https://raw.githubusercontent.com/BuildingSync/schema/v2.0/BuildingSync.xsd">
        </auc:BuildingSync>'''))

    new_root = new_tree.getroot()
    original_root = original_tree.getroot()

    def clone_subtree(original, new):
        for child in original.iterchildren():
            new_child = etree.Element(child.tag)
            # update text
            new_child.text = child.text
            # update attributes
            for attr, val in child.items():
                new_child.set(attr, val)
            new.append(new_child)
            clone_subtree(child, new_child)

    clone_subtree(original_root, new_root)

    return new_tree


def add_child_to_element(element, child, tree, schema):
    element.append(child)
    sort_element(schema, tree, element)


def add_udfs(element, udfs):
    # get or create the udf container
    udf_container = element.xpath('auc:UserDefinedFields', namespaces=NAMESPACES)
    if udf_container:
        udf_container = udf_container[0]
    else:
        udf_container = etree.SubElement(element, f'{{{BUILDINGSYNC_URI}}}UserDefinedFields')
    # add the fields
    for udf_raw in udfs:
        udf_elem = etree.SubElement(udf_container, f'{{{BUILDINGSYNC_URI}}}UserDefinedField')
        etree.SubElement(udf_elem, f'{{{BUILDINGSYNC_URI}}}FieldName').text = udf_raw[0]
        etree.SubElement(udf_elem, f'{{{BUILDINGSYNC_URI}}}FieldValue').text = udf_raw[1]
