#!/bin/bash
set -euo pipefail

if [ $# -ne 1 ];then 
    echo "Usage: $0 <timestamp e.g. 251208_0957>"
    exit 1 
fi 

ts=$1

datadir="job_dataset_${ts}"
outdir="share_${ts}"

if [ ! -d ${datadir} ];then 
    echo "ERROR: Folder not exist! (${datadir})"
    exit 1 
fi

if [ -d ${outdir} ];then 
    echo "ERROR: Output directory already exists! (${outdir})"
    exit 1
fi 

mkdir ${outdir} 
mkdir ${outdir}/images
mkdir ${outdir}/coco

# Images
cat ${datadir}/*.coco10.images.txt | sed 's|^|/NetApp/users/deeplearn/Projects/marrow_morphology/image_3dhistech/|' >  ${outdir}/images.list
cat ${outdir}/images.list | while read imagefile; do 
    if [ ! -e ${imagefile} ]; then 
        echo "ERROR: ${imagefile} does not exist"
        exit 1
    fi 

    folder=$(basename $(dirname ${imagefile}))
    if [ ! -d ${outdir}/images/${folder} ]; then mkdir ${outdir}/images/${folder}; fi 
    ln -s ${imagefile} ${outdir}/images/${folder}
done

# COCO
ls ${datadir}/*.coco10.json > ${outdir}/coco.list
cat ${outdir}/coco.list | while read x; do 
    cocofile=$(readlink -f $x)
    ln -s ${cocofile} ${outdir}/coco
done

# Compress
cd ${outdir} && tar -czvhf share_${ts}.tar.gz coco/ images/ && cd -

