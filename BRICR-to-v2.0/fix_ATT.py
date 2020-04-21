import os
from io import StringIO
import glob

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

        udfs = [["Recommended Resource Savings Category", "Potential Capital Recommendations"]]
        add_udfs(scenario_element, udfs)


    # -- NY Use Case Changes
    # add ID to Facility and Site
    facility_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility'
    tree.xpath(facility_xpath, namespaces=NAMESPACES)[0].set('ID', 'FacilityID')

    site_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site'
    tree.xpath(site_xpath, namespaces=NAMESPACES)[0].set('ID', 'SiteID')

    # IdentifierLabel for Assessor parcel number must be Custom
    assessor_label_xpath = '/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site/auc:Buildings/auc:Building/auc:PremisesIdentifiers/auc:PremisesIdentifier[auc:IdentifierLabel="Assessor parcel number"]/auc:IdentifierValue'
    assessor_label_elem = tree.xpath(assessor_label_xpath, namespaces=NAMESPACES)
    if assessor_label_elem:
        assessor_label_elem[0].text = 'Custom'

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
        print('.', end='', flush=True)
