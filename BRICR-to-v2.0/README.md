## Setup
```
python3 -m pip install -r requirements.txt
```
For validation, might need to install [xmllint](https://linux.die.net/man/1/xmllint) if not on a Mac or Ubuntu machine.
Download the v2.0 schema locally
```bash
curl -o schema_2_0.xsd https://raw.githubusercontent.com/BuildingSync/schema/v2.0/BuildingSync.xsd
```
## Steps
Overview:
- generate validation errors for original files
- using those errors, fix the files
- validate the fixed files
- replace the original files with the fixed files

First step is to generate validation errors for the files.
```bash
# stdin: line separated paths to files to validate
# arg1: label for this validation run - e.g. initial_validation
# arg2: path to the local v2.0 xsd
# output:
#   the names of files that failed validation are put in failed_<label>.txt
#   errors for failed files are found in <label>_errors directory
for i in <path to files>/backup/media/buildingsync_files/*.xml; do echo $i; done \
  | ./validate.sh initial_validation schema_2_0.xsd
```

Optionally you can generate a json file summarizing the errors
```bash
python3 parse_errors.py initial_validation_errors parsed_errors.json
```

Fix the files by running the python script:
```bash
# Fix files - change the path to the files
# The script will put the files at the same path, but within a new dir with the
# same name but with '_fixed' appended. e.g. ./foo/bar fixed files go to ./foo/bar_fixed
python3 main.py <path to files>/backup/media/buildingsync_files initial_validation_errors
```

Verify the files were fixed by running xmllint on them.
```bash
# !! make sure you point the path to the _fixed directory !!
for i in <path to files>/backup/media/buildingsync_files_fixed/*.xml; do echo $i; done \
  | ./validate.sh validate1 schema_2_0.xsd
```
Check the output file, failed_validate1.txt to see what files failed. Only the files mentioned below should fail, and you should either delete or manually edit them accordingly.

Lastly, replace the original directory with the '_fixed' directory.

## Exceptional files
These files are special cases that should be manually edited or removed

### Files to manually edit
These files contain additional Address and Lat/Long that are in the wrong sequence order. Just manually remove auc:Address, auc:Latitude, and auc:Longitude elements at `/auc:BuildingSync/auc:Facilities/auc:Facility/auc:Sites/auc:Site` (the data can still be found in Buildings/Building)
- buildingsync_property_6463_HVkGvAY.xml
- buildingsync_property_6463.xml

### Files to delete
These files are old, v0.3 and can be removed
- ID0023002_505_Beach_Street_0_report_Gu6y955.xml
- ID0023002_505_Beach_Street_0_report_X19eD1L.xml
- ID0023002_505_Beach_Street_0_report.xml
- 12.xml

This file is just a one-off bad file which uses non-existing elements (auc:AnnualElectricity)
- building_151_results.xml
