import os
import shutil
import json
import glob

from lxml import etree
import xmlschema

from parse_errors import summarize_errors
from utils import sort_element, remove_dupes, fix_namespaces, BUILDINGSYNC_URI, NAMESPACES


def fix_timestamp(file, directory):
    """Turn TimeStamp into Timestamp"""
    filepath = os.path.join(directory, file)
    with open(filepath, 'r') as f:
        filedata = f.read()

    # Replace the target string
    filedata = filedata.replace('TimeStamp', 'Timestamp')

    # Write the file out again
    with open(filepath, 'w') as f:
        f.write(filedata)


package_of_measures_xpath = '/'.join([
    'auc:Facilities',
    'auc:Facility',
    'auc:Reports',
    'auc:Report',
    'auc:Scenarios',
    'auc:Scenario',
    'auc:ScenarioType',
    'auc:PackageOfMeasures'
])

scenarios_xpath = '/'.join([
    'auc:Facilities',
    'auc:Facility',
    'auc:Reports',
    'auc:Report',
    'auc:Scenarios',
    'auc:Scenario',
])
schema_2_0_instance = xmlschema.XMLSchema('./schema_2_0.xsd')


def fix_calculationmethod(file, directory):
    """Does a couple of fixes
    - sort elements at PackageOfMeasures
    - remove duplicated elements in PackageOfMeasures
    - sort elements at Scenario
    - remove duplicated elements in Scenario
    """

    filepath = os.path.join(directory, file)
    # get the calculation method parent, PackageOfMeasures, and sort its children
    tree = etree.parse(filepath)
    elements = tree.xpath(package_of_measures_xpath, namespaces=NAMESPACES)
    for element in elements:
        sort_element(schema_2_0_instance, tree, element)

        # remove duplicate children in PackageOfMeasures
        remove_dupes(element)

    # sort the scenario children (ResourceUses in wrong position)
    elements = tree.xpath(scenarios_xpath, namespaces=NAMESPACES)
    for element in elements:
        sort_element(schema_2_0_instance, tree, element)

        # remove duplicates
        remove_dupes(element)

    filedata = etree.tostring(tree).decode()

    # Write the file out again
    with open(filepath, 'w') as f:
        f.write(filedata)


def fix_subsections(file, directory):
    """Replaces Subsection(s) with Section(s)"""
    filepath = os.path.join(directory, file)
    with open(filepath, 'r') as f:
        filedata = f.read()

    # Replace the target string
    filedata = filedata.replace('auc:Subsection', 'auc:Section')

    # Write the file out again
    with open(filepath, 'w') as f:
        f.write(filedata)


report_xpath = 'auc:Facilities/auc:Facility/auc:Report'


def fix_report(file, directory):
    """nest Report in Reports"""
    filepath = os.path.join(directory, file)
    tree = etree.parse(filepath)

    report = tree.xpath(report_xpath, namespaces=NAMESPACES)
    assert len(report) == 1
    report = report[0]

    facility = report.getparent()
    facility.remove(report)
    reports = etree.SubElement(facility, f'{{{BUILDINGSYNC_URI}}}Reports')
    reports.append(report)

    filedata = etree.tostring(tree).decode()

    # Write the file out again
    with open(filepath, 'w') as f:
        f.write(filedata)


light_xpath = 'auc:Facilities/auc:Facility/auc:Systems/auc:LightingSystems/auc:LightingSystem/auc:PrimaryLightingSystemType'


def fix_primarylightingsystemtype(file, directory):
    """turns PrimaryLightingSystemType into a user defined field"""
    filepath = os.path.join(directory, file)

    tree = etree.parse(filepath)
    elements = tree.xpath(light_xpath, namespaces=NAMESPACES)
    assert len(elements) > 0
    for element in elements:
        lighting_type = element.text

        parent_element = element.getparent()
        parent_element.remove(element)

        udfs = etree.SubElement(parent_element, f'{{{BUILDINGSYNC_URI}}}UserDefinedFields')
        udf = etree.SubElement(udfs, f'{{{BUILDINGSYNC_URI}}}UserDefinedField')
        etree.SubElement(udf, f'{{{BUILDINGSYNC_URI}}}FieldName').text = 'PrimaryLightingSystemType'
        etree.SubElement(udf, f'{{{BUILDINGSYNC_URI}}}FieldValue').text = lighting_type

    filedata = etree.tostring(tree).decode()

    # Write the file out again
    with open(filepath, 'w') as f:
        f.write(filedata)


def fix_occupancyclassification(file, directory):
    """Replace Hotel with Lodging"""
    filepath = os.path.join(directory, file)
    with open(filepath, 'r') as f:
        filedata = f.read()

    # Replace the target string
    filedata = filedata.replace('Hotel', 'Lodging')

    # Write the file out again
    with open(filepath, 'w') as f:
        f.write(filedata)


def fix_schemalocation(file, directory):
    """Makes sure that the schemaLocation is properly set"""
    filepath = os.path.join(directory, file)
    tree = etree.parse(filepath)

    # fix the namespaces of the tree if necessary
    root_nsmap = tree.getroot().nsmap
    if root_nsmap.get('auc') is None or root_nsmap.get('xsi') is None:
        tree = fix_namespaces(tree)
    
    # make sure schemalocation is set
    root = tree.getroot()
    root.set('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', 'http://buildingsync.net/schemas/bedes-auc/2019 https://raw.githubusercontent.com/BuildingSync/schema/v2.0/BuildingSync.xsd')

    # save the finished tree
    filedata = etree.tostring(tree).decode()

    # Write the file out again
    with open(filepath, 'w') as f:
        f.write(filedata)

error_fixes_map = {
    'starttimestamp': fix_timestamp,
    'calculationmethod': fix_calculationmethod,
    'subsections': fix_subsections,
    'report': fix_report,
    'primarylightingsystemtype': fix_primarylightingsystemtype,
    'occupancyclassification': fix_occupancyclassification
}

data_dir = os.sys.argv[1]

# copy over the source files
fixed_data_dir = os.path.join(
    os.path.dirname(data_dir),
    os.path.basename(data_dir) + '_fixed')
print(f'Copying source files into {fixed_data_dir}')
if not os.path.isdir(fixed_data_dir):
    shutil.copytree(data_dir, fixed_data_dir)
else:
    raise Exception(f'Remove the _fixed data directory before running this script to fix files: {fixed_data_dir}')

# get the summary of validation errors
validation_errors_dir = os.sys.argv[2]
print(f'Summarizing validation errors from {validation_errors_dir}')
parsed_errors = summarize_errors(validation_errors_dir)

# only care about the schema validity errors
# we are just going to delete the file which has a parsing error
element_errors = parsed_errors['Schemas validity error ']

# elements we won't try to fix (either fixed manually or deleted) - see README
skipped_elements = [
    'Address',
    'Audits',
    'ResourceUses'  # handled by fixes to CalculationMethod (same files)
]

# iterate through the errors and fix the files
for element, specific_errors in element_errors.items():
    print(f'\nFixing {element}')
    # get the fixer function
    element_tag = element.split(' ')[1]
    fixer = error_fixes_map.get(element_tag.lower())
    if not fixer:
        if element_tag not in skipped_elements:
            raise Exception(f'Failed to find fixer for {element_tag}, which is not supposed to be skipped')
        # skipping this element
        continue

    # collect all files that had errors with this element (fixes are grouped by elements, not specific errors)
    files_to_fix = []
    for error_description, error_data in specific_errors.items():
        # get _only_ the basename after removing the ':<linenumber>' part of the filename
        files_to_fix += [os.path.basename(filename.split(':')[0]) for filename in error_data['files']]

    # only grab unique files
    files_to_fix = list(set(files_to_fix))

    # fix to the file
    for source_file in files_to_fix:
        fixer(source_file, fixed_data_dir)
        print('.', end='', flush=True)

# lastly fix the namespaces and schemaLocation for ALL files
print('\nFixing namespaces and schemalocation')
for file_path in glob.glob(os.path.join(fixed_data_dir, '*.xml')):
    try:
        fix_schemalocation(os.path.basename(file_path), fixed_data_dir)
    except Exception as e:
        print(f'\nSkipping file {file_path} due to exception: {str(e)}')
    print('.', end='', flush=True)

print('\n\n========  DONE  ========')
print('Fixed files saved to ', fixed_data_dir)
