import glob
import os
import json

def get_errors(file):
    with open(file, 'r') as f:
        lines = f.readlines()
        # don't look at last line, it's just 
        processed_lines = []
        for line in lines:
            split_line = line.split(': ')
            
            # skip lines that aren't describing an error
            if len(split_line) <= 1:
                continue
            
            processed_lines.append(split_line)
        return processed_lines

NOT_ELEMENT = 'NOT_ELEMENT'
def update_errors(errors, error):
    """adds an error to the errors dict"""
    if len(error) == 4:
        filename, short_error, error_details, _ = error
        element_tag = NOT_ELEMENT
    elif len(error) == 5:
        filename, element_tag, short_error, full_element_name, error_details = error
    else:
        print(error)
        raise Exception('Had lines ' + str(len(error)))

    error_details = error_details.strip()
    if short_error not in errors:
        # build the error description
        errors[short_error] = {}
        errors[short_error][element_tag] = {}
        errors[short_error][element_tag][error_details] = {
            'files': [filename]
        }
        return
    
    if element_tag not in errors[short_error]:
        errors[short_error][element_tag] = {}
        errors[short_error][element_tag][error_details] = {
            'files': [filename]
        }
        return
    
    if error_details not in errors[short_error][element_tag]:
        errors[short_error][element_tag][error_details] = {
            'files': [filename]
        }
        return
    
    errors[short_error][element_tag][error_details]['files'].append(filename)


def summarize_errors(directory, filesubset=None, errors=None):
    """Returns a parsed dict of errors from a directory of error files
    
    e.g.
    {
      <short_error>: {
        <element_tag>: {
          <error_details>: {
              'files': [...] # files that had this error
          }
        }
      }
    }
    """
    if errors is None:
        errors = {}

    filespath = os.path.join(directory, '*.xml')
    files = glob.glob(filespath)
    if filesubset is not None:
        files = [file for file in files if os.path.basename(file) in filesubset]

    for file in files:
        for error in get_errors(file):
            update_errors(errors, error)
    
    return errors

if __name__ == '__main__':
    # parse the errors and save as json
    # usage: parse_errors.py <errors_dir> <json_filename>
    errors = summarize_errors(os.sys.argv[1])
    errors_json = json.dumps(errors, indent=2)
    with open(os.sys.argv[2], 'w') as f:
        f.write(errors_json)
