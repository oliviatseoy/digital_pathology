#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import argparse
import json
import os
import time
import zipfile
import requests
from cvat_sdk.api_client import Configuration, ApiClient, exceptions

def main(args):
    # Load CVAT config
    config = json.load(open(args.cvat_config, 'r', encoding="utf-8"))
    CVAT_URL = config['cvat_url']
    CVAT_USERNAME = config['cvat_username']
    CVAT_PASSWORD = config['cvat_password']

    # Parse Job ID
    job_ids = []
    if args.job_ids:
        job_ids = args.job_ids
    else:
        with open(args.job_id_file, 'r', encoding="utf-8") as f:
            job_ids = [int(line.strip()) for line in f if line.strip()]

    # Parse anntation format
    annotation_formats = []
    if args.annotation_format == "COCO":
        annotation_formats = ["COCO 1.0"]
    elif args.annotation_format == "CVAT":
        annotation_formats = ["CVAT for images 1.1"]
    elif args.annotation_format == "COCO_CVAT":
        annotation_formats = ["COCO 1.0", "CVAT for images 1.1"]

    with ApiClient(Configuration(host = CVAT_URL, username = CVAT_USERNAME, password = CVAT_PASSWORD)) as api_client:
        for job_id in job_ids:
            for annotation_format in annotation_formats:
                if annotation_format == "COCO 1.0":
                    annotation_alias = "coco10"
                    annotation_file = "annotations/instances_default.json"
                    annotation_file_ext = "json"
                elif annotation_format == "CVAT for images 1.1":
                    annotation_alias = "cvat11"
                    annotation_file = "annotations.xml"
                    annotation_file_ext = "xml"
                else:
                    raise ValueError(f"Unsupported annotation format ({annotation_format}).")

                output_zip_file = f"{args.outdir}/job{job_id}.{annotation_alias}.zip"
                output_annotation_file = f"{args.outdir}/job{job_id}.{annotation_alias}.{annotation_file_ext}"
                output_coco_image_file = f"{args.outdir}/job{job_id}.coco10.images.txt"

                try:
                    # Initialize process to export resource as a dataset in a specific format
                    # Example request id: 'action=export&target=job&target_id=1058&user_id=1&format=COCO_1~0&subresource=annotations'
                    print(f"\nExporting dataset. Job ID: {job_id}. Format: {annotation_format}.")
                    (data, response) = api_client.jobs_api.create_dataset_export(
                        annotation_format, 
                        job_id,
                        filename=os.path.basename(output_zip_file),
                        location='local',
                        save_images=False
                    )
                    rq_id = data['rq_id']

                    # Poll for export status
                    # Example results_url: http://localhost:8080/api/jobs/1058/dataset/download?rq_id=action%3Dexport%26target%3Djob%26target_id%3D1058%26user_id%3D1%26format%3DCOCO_1~0%26subresource%3Dannotations
                    while True:
                        (status_request, _) = api_client.requests_api.retrieve(id=rq_id)
                        if status_request.status.value == "finished":
                            break
                        if status_request.status.value == "failed":
                            raise RuntimeError("ERROR: Export failed: CVAT did not complete the export successfully.")
                        else:
                            time.sleep(5)

                    # Download file
                    if status_request.status.value == "finished":
                        response = requests.get(status_request.result_url, auth=(CVAT_USERNAME, CVAT_PASSWORD), stream=True, timeout=300) # 5 mins timeout
                        response.raise_for_status()
                        
                        with open(output_zip_file, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        print(f"Exported dataset downloaded to {output_zip_file}. Job ID: {job_id}. Format: {annotation_format}.")

                        with zipfile.ZipFile(output_zip_file, 'r') as zip_ref:
                            try:
                                with zip_ref.open(annotation_file) as src, open(output_annotation_file, "wb") as dst:
                                    dst.write(src.read())
                                print(f"Copied {annotation_file} to {output_annotation_file}. Job ID: {job_id}. Format: {annotation_format}.")
                                
                                # Extract image file name from COCO.json
                                if annotation_format == "COCO 1.0":
                                    with open(output_coco_image_file, "w", encoding="utf-8") as fout:
                                        coco = json.load(open(output_annotation_file, encoding="utf-8"))
                                        for image in coco['images']:
                                            fout.write(image['file_name'] + "\n")

                            except KeyError as e:
                                raise FileNotFoundError(f"{annotation_file} not found in the zip file.") from e
                            except Exception as e:
                                raise RuntimeError(f"An error occurred while processing the zip file: {e}") from e
                except exceptions.ApiException as e:
                    print(f"Exception when calling JobsApi.create_dataset_export(): {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cvat_config", required=True)
    parser.add_argument("--annotation_format", choices=['COCO', 'CVAT', 'COCO_CVAT'], required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--job_ids", type=int, nargs='*')
    parser.add_argument("--job_id_file")
    #arguments = parser.parse_args("--cvat_config /home/olivia/cvat_config.json --annotation_format COCO_CVAT --job_ids 259 260".split())
    #arguments = parser.parse_args("--cvat_config /home/olivia/cvat_config.json --annotation_format COCO_CVAT --job_id_file jobid.list".split())
    arguments = parser.parse_args()

    if not arguments.job_ids and not arguments.job_id_file:
        raise ValueError("ERROR: You must provide either --job_ids or --job_id_file as input.")

    if not os.path.exists(arguments.outdir):
        raise ValueError(f"ERROR: args.outdir [{arguments.outdir}] does not exist!")
    main(arguments)

