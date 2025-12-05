#!/bin/bash
set -euo pipefail

ts=$(date +"%y%m%d_%H%M")
outdir="task_dataset_${ts}"
mkdir "${outdir}"

if [ "$#" -gt 0 ]; then
    # Use provided task IDs from command line arguments
    printf "%s\n" "$@" > "${outdir}/taskid.list"
else
    /NetApp/users/olivia/anaconda3/envs/cvat_2.47.0/bin/cvat-cli --org  marrowmorphology --server-host http://localhost:8080 --auth "${CVAT_USERNAME}:${CVAT_PASSWORD}" task ls > "${outdir}/taskid.list"
fi

logfile="${outdir}/export.log"
exec > >(tee -a "${logfile}") 2>&1

# Export Task dataset
cat "${outdir}/taskid.list" | while read -r taskid; do 
    echo -e "\nExporting task dataset. Task ID: ${taskid}. Format: COCO 1.0"
    /NetApp/users/olivia/anaconda3/envs/cvat_2.47.0/bin/cvat-cli --org marrowmorphology --server-host http://localhost:8080 --auth ${CVAT_USERNAME}:${CVAT_PASSWORD} task export-dataset --format "COCO 1.0" ${taskid} ${outdir}/task${taskid}.coco10.zip && touch ${outdir}/task${taskid}.coco10.export_dataset.done
    unzip -p "${outdir}/task${taskid}.coco10.zip" annotations/instances_default.json > "${outdir}/task${taskid}.coco10.json"
    echo -e "Task dataset was successfully exported. Task ID: ${taskid}. Format: COCO 1.0"
    
    echo -e "\nExporting task dataset. Task ID: ${taskid}. Format: CVAT for images 1.1"
    /NetApp/users/olivia/anaconda3/envs/cvat_2.47.0/bin/cvat-cli --org marrowmorphology --server-host http://localhost:8080 --auth ${CVAT_USERNAME}:${CVAT_PASSWORD} task export-dataset --format "CVAT for images 1.1" ${taskid} ${outdir}/task${taskid}.cvat11.zip && touch ${outdir}/task${taskid}.cvat11.export_dataset.done
    unzip -p "${outdir}/task${taskid}.cvat11.zip" annotations.xml > "${outdir}/task${taskid}.cvat11.xml"
    echo -e "Task dataset was successfully exported. Task ID: ${taskid}. Format: CVAT for images 1.1"
done