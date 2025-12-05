#!/bin/bash

ts=$(date +"%y%m%d_%H%M")
outdir="job_dataset_${ts}"
mkdir "${outdir}"

# Get completed job ID with mask count > 0
statfile=$(ls -t /NetApp/users/deeplearn/Projects/marrow_morphology/cvat_annotation_stat/annotation_label_stat.*.txt |head -1)
awk -F"\t" 'NR>1 && $7>0 && $3>0{print $3}' $statfile > ${outdir}/jobid.list

# Export dataset
/NetApp/users/olivia/anaconda3/envs/cvat_2.47.0/bin/python cvat_export_job_dataset.py --cvat_config /home/olivia/cvat_config.json --annotation_format COCO_CVAT --job_id_file ${outdir}/jobid.list --outdir ${outdir} | tee ${outdir}/export.log


