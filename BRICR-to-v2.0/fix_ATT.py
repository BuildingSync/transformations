import os
from io import StringIO
import glob
import traceback

from lxml import etree
from xmlschema import XMLSchema

from utils import (
    BUILDINGSYNC_URI,
    NAMESPACES,
    add_child_to_element,
    add_udfs
)

schema = XMLSchema('schema_2_0.xsd')

parser = etree.XMLParser(remove_blank_text=True)
etree.set_default_parser(parser)


def fix_file(source, save_dir):
    tree = etree.parse(source)

    # Add UDFs to end of report
    udfs_raw = [
        ["Audit Date For Level 1: Walk-through Is Not Applicable", "false"],
        ["Audit Date For Level 2: Energy Survey and Analysis Is Not Applicable", "false"],
        ["Audit Date For Level 3: Detailed Survey and Analysis Is Not Applicable", "false"],
        ["Audit Filing Status", "Initial Filing"],
        ["Audit Filing Status Is Not Applicable", "false"],
        ["Audit Notes For Not Applicable", ""],
        ["Audit Notes Is Not Applicable", "false"],
        ["Audit Team Notes Is Not Applicable", "false"],
        ["Audit Template Report Type", "BRICR Phase 0/1"],
        ["Early Compliance", "false"],
        ["Early Compliance Is Not Applicable", "false"],
        ["Required Audit Year Is Not Applicable", "false"]
    ]

    report_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report'
    report_element = tree.xpath(report_xpath, namespaces=NAMESPACES)[0]
    add_udfs(report_element, udfs_raw)

    # add Liked premises or system if it doesn't exist
    lps_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:LinkedPremisesOrSystem'
    if not tree.xpath(lps_xpath, namespaces=NAMESPACES):
        building_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Buildings/auc:Building'
        building_id = tree.xpath(building_xpath, namespaces=NAMESPACES)[0].get('ID')
        lps_elem = etree.Element(f'{{{BUILDINGSYNC_URI}}}LinkedPremisesOrSystem')
        etree.SubElement(
            etree.SubElement(lps_elem, f'{{{BUILDINGSYNC_URI}}}Building'),
            f'{{{BUILDINGSYNC_URI}}}LinkedBuildingID',
            IDref=building_id
        )
        report_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report'
        report_element = tree.xpath(report_xpath, namespaces=NAMESPACES)[0]
        add_child_to_element(report_element, lps_elem, tree, schema)

    # make sure address is in Buildings/Building
    building_address_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Buildings/auc:Building/auc:Address'
    building_address_elem = tree.xpath(building_address_xpath, namespaces=NAMESPACES)
    if not building_address_elem:
        site_address_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Address'
        site_address_elem = tree.xpath(site_address_xpath, namespaces=NAMESPACES)[0]
        site_address_elem.getparent().remove(site_address_elem)
        building_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Buildings/auc:Building'
        building_elem = tree.xpath(building_xpath, namespaces=NAMESPACES)[0]
        add_child_to_element(building_elem, site_address_elem, tree, schema)

    # move FloorsAboveGrade and FloorsBelowGrade to ConditionedFloorsAboveGrade and ConditionedFloorsBelowGrade
    above_grade_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Buildings/auc:Building/auc:FloorsAboveGrade'
    above_grade_elem = tree.xpath(above_grade_xpath, namespaces=NAMESPACES)
    if above_grade_elem:
        above_grade_elem = above_grade_elem[0]
        n_floors = above_grade_elem.text
        building_elem = above_grade_elem.getparent()
        building_elem.remove(above_grade_elem)
        conditioned_above_grade_elem = etree.Element(f'{{{BUILDINGSYNC_URI}}}ConditionedFloorsAboveGrade')
        conditioned_above_grade_elem.text = n_floors
        add_child_to_element(building_elem, conditioned_above_grade_elem, tree, schema)

    below_grade_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Buildings/auc:Building/auc:FloorsBelowGrade'
    below_grade_elem = tree.xpath(below_grade_xpath, namespaces=NAMESPACES)
    if below_grade_elem:
        below_grade_elem = below_grade_elem[0]
        n_floors = below_grade_elem.text
        building_elem = below_grade_elem.getparent()
        building_elem.remove(below_grade_elem)
        conditioned_below_grade_elem = etree.Element(f'{{{BUILDINGSYNC_URI}}}ConditionedFloorsBelowGrade')
        conditioned_below_grade_elem.text = n_floors
        add_child_to_element(building_elem, conditioned_below_grade_elem, tree, schema)


    # -- Edit Measures
    # add measuresavingsanalysis and some udfs
    measure_udf_raw = [["Rebate Available", "false"]]
    measure_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Measures/auc:Measure'
    measures = tree.xpath(measure_xpath, namespaces=NAMESPACES)
    for measure_element in measures:
        # add savings analysis
        msa_elem = etree.Element(f'{{{BUILDINGSYNC_URI}}}MeasureSavingsAnalysis')
        etree.SubElement(msa_elem, f'{{{BUILDINGSYNC_URI}}}FundingFromIncentives').text = '0'
        add_child_to_element(measure_element, msa_elem, tree, schema)

        # add udfs
        add_udfs(measure_element, measure_udf_raw)


    # -- Edit Scenarios
    # check that ResourceUnits are in kBtu
    resource_units_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:Scenarios/auc:Scenario/auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualSavingsByFuels/auc:AnnualSavingsByFuel/auc:ResourceUnits'
    resource_units_elems = tree.xpath(resource_units_xpath, namespaces=NAMESPACES)
    for ru_elem in resource_units_elems:
        if ru_elem.text != 'kBtu':
            raise Exception(f'Expected all ResourceUses to be kBtu, but found one with "{ru_elem.text}"')

    # change electricity units to kWh, gas to therms
    electricity_savings_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:Scenarios/auc:Scenario/auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualSavingsByFuels/auc:AnnualSavingsByFuel[auc:EnergyResource="Electricity"]/auc:ResourceUnits[text()="kBtu"]'
    gas_savings_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:Scenarios/auc:Scenario/auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualSavingsByFuels/auc:AnnualSavingsByFuel[auc:EnergyResource="Natural gas"]/auc:ResourceUnits[text()="kBtu"]'

    for electricity_units in tree.xpath(electricity_savings_xpath, namespaces=NAMESPACES):
        electricity_units.text = 'kWh'
        electricity_value = electricity_units.getparent().xpath('auc:AnnualSavingsNativeUnits', namespaces=NAMESPACES)[0]
        electricity_value.text = str(float(electricity_value.text) * 3.412)

    for gas_units in tree.xpath(gas_savings_xpath, namespaces=NAMESPACES):
        gas_units.text = 'therms'
        gas_value = gas_units.getparent().xpath('auc:AnnualSavingsNativeUnits', namespaces=NAMESPACES)[0]
        gas_value.text = str(float(gas_value.text) * 0.01)

    # add temporal status, annual peak electricity reduction, and some udfs
    scenario_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:Scenarios/auc:Scenario'
    scenarios = tree.xpath(scenario_xpath, namespaces=NAMESPACES)
    for scenario_element in scenarios:
        ts_elem = etree.Element(f'{{{BUILDINGSYNC_URI}}}TemporalStatus')
        ts_elem.text = 'Current'
        add_child_to_element(scenario_element, ts_elem, tree, schema)

        aper_elem = etree.Element(f'{{{BUILDINGSYNC_URI}}}AnnualPeakElectricityReduction')
        aper_elem.text = '0'
        pom_elem = scenario_element.xpath('auc:ScenarioType/auc:PackageOfMeasures', namespaces=NAMESPACES)[0]
        add_child_to_element(pom_elem, aper_elem, tree, schema)

        udfs = [
            ["Application Scale", "Entire facility"],
            ["Recommended Resource Savings Category", "Potential Capital Recommendations"]
        ]
        add_udfs(scenario_element, udfs)

    # add a special scenario so we don't loose all of our scenario information
    building_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Buildings/auc:Building'
    building_id = tree.xpath(building_xpath, namespaces=NAMESPACES)[0].get('ID')
    new_scenario_text = """<auc:Scenario ID="ScenarioType-69870486597440" xmlns:auc="http://buildingsync.net/schemas/bedes-auc/2019">
  <auc:TemporalStatus>Current</auc:TemporalStatus>
  <auc:ScenarioType>
    <auc:Other></auc:Other>
  </auc:ScenarioType>
  <auc:ResourceUses>
    <auc:ResourceUse ID="ResourceUseType-69870486534900">
      <auc:EnergyResource>Electricity</auc:EnergyResource>
      <auc:ResourceBoundary>Site</auc:ResourceBoundary>
      <auc:ResourceUnits>kWh</auc:ResourceUnits>
      <auc:EndUse>All end uses</auc:EndUse>
    </auc:ResourceUse>
    <auc:ResourceUse ID="ResourceUseType-69870486438520">
      <auc:EnergyResource>Natural gas</auc:EnergyResource>
      <auc:ResourceBoundary>Site</auc:ResourceBoundary>
      <auc:ResourceUnits>therms</auc:ResourceUnits>
      <auc:EndUse>All end uses</auc:EndUse>
    </auc:ResourceUse>
  </auc:ResourceUses>
  <auc:LinkedPremises>
    <auc:Building>
      <auc:LinkedBuildingID IDref="{building_id}"></auc:LinkedBuildingID>
    </auc:Building>
  </auc:LinkedPremises>
  <auc:UserDefinedFields>
    <auc:UserDefinedField>
      <auc:FieldName>Other Scenario Type</auc:FieldName>
      <auc:FieldValue>Audit Template Available Energy</auc:FieldValue>
    </auc:UserDefinedField>
  </auc:UserDefinedFields>
</auc:Scenario>""".format(building_id=building_id)
    new_scenario_tree = etree.fromstring(new_scenario_text)
    scenarios_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:Scenarios'
    scenarios_elem = tree.xpath(scenarios_xpath, namespaces=NAMESPACES)[0]
    add_child_to_element(scenarios_elem, new_scenario_tree, tree, schema)

    # -- NY Use Case Changes
    # add ID to Facility and Site
    facility_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility'
    tree.xpath(facility_xpath, namespaces=NAMESPACES)[0].set('ID', 'FacilityID')

    site_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site'
    tree.xpath(site_xpath, namespaces=NAMESPACES)[0].set('ID', 'SiteID')

    # IdentifierLabel for Assessor parcel number must be changed to Custom ID 2
    premise_id_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Buildings/auc:Building/auc:PremisesIdentifiers/auc:PremisesIdentifier[auc:IdentifierLabel="Assessor parcel number"]'
    premise_id_elem = tree.xpath(premise_id_xpath, namespaces=NAMESPACES)
    if premise_id_elem:
        premise_id_elem = premise_id_elem[0]
        id_name = etree.Element(f'{{{BUILDINGSYNC_URI}}}IdentifierCustomName')
        id_name.text = 'Custom ID 2'
        add_child_to_element(premise_id_elem, id_name, tree, schema)
        # change IdentifierLabel to custom
        id_label = premise_id_elem.xpath('auc:IdentifierLabel', namespaces=NAMESPACES)
        id_label[0].text = 'Custom'

    # add ID to package of measures (required)
    pom_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:Scenarios/auc:Scenario/auc:ScenarioType/auc:PackageOfMeasures'
    id_number = 0
    for pom_elem in tree.xpath(pom_xpath, namespaces=NAMESPACES):
        pom_elem.set('ID', f'PackageOfMeasures_ID_{id_number}')
        id_number += 1

    # add ID to scenario
    scenario_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:Scenarios/auc:Scenario'
    id_number = 0
    for scenario_elem in tree.xpath(scenario_xpath, namespaces=NAMESPACES):
        if not scenario_elem.get('ID'):
            scenario_elem.set('ID', f'Scenario_ID_{id_number}')
            id_number += 1

    # make all AnnualSavingsCost >= 0
    asc_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report/auc:Scenarios/auc:Scenario/auc:ScenarioType/auc:PackageOfMeasures/auc:AnnualSavingsCost'
    for asc_elem in tree.xpath(asc_xpath, namespaces=NAMESPACES):
        if int(asc_elem.text) < 0:
            asc_elem.text = '0'


    # add id to Report
    report_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Reports/auc:Report'
    report_element = tree.xpath(report_xpath, namespaces=NAMESPACES)[0]
    report_element.set('ID', 'Report_ID_0')

    # add premises identifiers to auc:Site
    site_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site'
    site_elem = tree.xpath(site_xpath, namespaces=NAMESPACES)[0]
    pids_elem = etree.Element(f'{{{BUILDINGSYNC_URI}}}PremisesIdentifiers')
    pid_elem = etree.SubElement(pids_elem, f'{{{BUILDINGSYNC_URI}}}PremisesIdentifier')
    etree.SubElement(pid_elem, f'{{{BUILDINGSYNC_URI}}}IdentifierLabel').text = 'Custom'
    etree.SubElement(pid_elem, f'{{{BUILDINGSYNC_URI}}}IdentifierCustomName').text = 'Borough'
    etree.SubElement(pid_elem, f'{{{BUILDINGSYNC_URI}}}IdentifierValue').text = '18749'
    add_child_to_element(site_elem, pids_elem, tree, schema)

    # fix the Section type so the type is Space function
    section_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Buildings/auc:Building/auc:Sections/auc:Section'
    section_elem = tree.xpath(section_xpath, namespaces=NAMESPACES)[0]
    type_xpath = 'auc:SectionType'
    type_elem = section_elem.xpath(type_xpath, namespaces=NAMESPACES)
    if type_elem:
        type_elem[0].text = 'Space function'
    else:
        type_elem = etree.Element(f'{{{BUILDINGSYNC_URI}}}SectionType')
        type_elem.text = 'Space function'
        add_child_to_element(section_elem, type_elem, tree, schema)

    # -- SAVE THE RESULT!
    result = etree.tostring(tree, pretty_print=True).decode()
    with open(os.path.join(save_dir, os.path.basename(source)), 'w') as f:
        f.write(result)

if __name__ == '__main__':
    source_dir = os.sys.argv[1]

    # determine if we should skip or reprocess files
    reprocess = False
    if len(os.sys.argv) == 3:
        if os.sys.argv[2] == '--reprocess':
            reprocess = True
    save_dir = source_dir.rstrip('/') + '_ATT'
    if os.path.exists(save_dir):
        if reprocess:
            print(f'Output directory already exists, will overwrite any existing files in {save_dir}')
        else:
            print(f'Output directory already exists, will SKIP processing any existing files in {save_dir}')
    else:
        print(f'Creating output directory {save_dir}')
        os.mkdir(save_dir)
    print('Fixing files for Audit Template Tool')
    for bsync_file in glob.glob(os.path.join(source_dir, '*.xml')):
        filename = os.path.basename(bsync_file)

        if not reprocess and os.path.exists(os.path.join(save_dir, filename)):
            # skip this file if we aren't reprocessing and it already exists
            print('S', end='', flush=True)
            continue
        try:
            fix_file(bsync_file, save_dir)
        except Exception as e:
            print(f'\nUnexpected error processing {bsync_file}: {str(e)}')
            print(traceback.format_exc())
        print('.', end='', flush=True)
