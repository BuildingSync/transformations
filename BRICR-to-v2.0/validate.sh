#!/bin/bash
# arg: name
# arg: schema
# stdin: lines of paths to files to process
failure_file="failed_${1}.txt"
errors_dir="${1}_errors"
mkdir $errors_dir
while read -r f; do
  xmllint $f --schema $2 --noout &> ignore.txt
  if [[ $? != 0 ]]; then
    echo $f >> $failure_file
    cp ignore.txt ./${errors_dir}/$(basename -- $f)
  fi
done <&0;

rm ignore.txt
