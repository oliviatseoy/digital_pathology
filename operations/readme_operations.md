
# Image patch operations

- Environments:
  - `/NetApp/users/olivia/anaconda3/envs/cvat_2.47.0`

## Prepare image patches from MRXS file

- Script: [mrxs_to_image_patches.py](./mrxs_to_image_patches.py)
  - `/home/olivia/anaconda3/envs/openslide/bin/python mrxs_to_image_patches.py --mrxs ${mrxs} --op ${sample} --patch_size 1024 --output_image_format JPEG --outdir /NetApp/users/deeplearn/Projects/marrow_morphology/image_3dhistech`

## Create CVAT project

- Script: [cvat_create_project.py](./cvat_create_project.py)
  - JSON defining the label: [cell_labels.json](./cell_labels.json)
  - `/NetApp/users/olivia/anaconda3/envs/cvat_2.47.0/bin/python cvat_create_project.py --labels_json cell_labels.json  --project_name Cell-Classification --organization marrowmorphology --cvat_config /home/olivia/cvat_config.json --op Cell-Classification`

## Create CVAT tasks

- Script: [cvat_create_tasks.py](./cvat_create_tasks.py)
  - Example JSON file defining the region for each task
    - 50 rows per task: [tasks.50rows.json](./tasks.50rows.json)
    - Custom ROI per task: [tasks.ROI-test.json](./tasks.ROI-test.json)
  - `/NetApp/users/olivia/anaconda3/envs/cvat_2.47.0/bin/python cvat_create_tasks.py  --image_folder 25H0340173 --image_extension jpg --task_prefix 25H0340173 --project_id 1 --segment_size 10 --cvat_config /home/olivia/cvat_config.json --task_json tasks.50rows.json --dryrun`
  - Remove `--dryrun` to create tasks in CVAT

## CVAT CLI

- Create task:
  - `cvat-cli --org <org_slug> --server-host http://localhost --server-port 8080 --auth <user>:<password> task create <taskname> share /<path-relative-to-CVAT-share-path> --project_id 25  --segment_size 10`
- Delete project:
  - `cvat-cli  --org <org_slug> --server-host http://localhost --server-port 8080 --auth <user>:<password> project delete <project_id>`
