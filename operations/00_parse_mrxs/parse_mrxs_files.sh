#!/bin/bash
set -euo pipefail

if [ $# -ne 2 ];then
    echo "Usage: $0 <dir-to-mrxs files> <is rotate label image 0/1>"
fi  

dir_mrxs=$1
rotate=$2
bin=$(dirname $0)

for x in ${dir_mrxs}/*.mrxs; do 
    b=$(basename $x .mrxs)
    echo -ne "${b}\t"
    /home/olivia/anaconda3/envs/openslide/bin/python ${bin}/parse_mrxs.py $x size
    if [ ${rotate} -eq 1 ];then 
        /home/olivia/anaconda3/envs/openslide/bin/python ${bin}/parse_mrxs.py $x label_image ${b}.label.jpg --rotate
    else
        /home/olivia/anaconda3/envs/openslide/bin/python ${bin}/parse_mrxs.py $x label_image ${b}.label.jpg
    fi
done > $(basename $PWD).mrxs.log

