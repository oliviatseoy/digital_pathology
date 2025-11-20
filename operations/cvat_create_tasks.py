#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import argparse
import glob
import os
import re
import json
from datetime import datetime
from cvat_sdk import make_client
from cvat_sdk.api_client import models
from cvat_sdk.core.proxies.tasks import ResourceType


# In[ ]:


class ImagePatchGrouper():
    def __init__(self, cvat_share_path, image_folder, image_extension):
        assert image_extension in ('jpg', 'png', 'tiff')
        self.cvat_share_path = cvat_share_path
        self.image_folder = image_folder
        self.image_extension = image_extension

        self.patches = [] # Image patch path relative to cvat_path
        self.patch_data = []  # List of (row, col, filepath) tuples
        self.grid_rows = 0 # No. of rows detected
        self.grid_cols = 0 # No. of columns detected
        self.task_patches = {} # task_name -> list of image patches
        self.task_regions = {} # task_name -> {row: (row_start, row_end), col: (col_start, col_end)}


    def load_patches(self):
        """ Load all image patches and extract row / column index from filename """
        for image_file in sorted(glob.glob(os.path.join(self.cvat_share_path, self.image_folder, f"*.{self.image_extension}"))):
            self.patches.append(image_file.replace(self.cvat_share_path, ""))
        self._extract_patch_coordinates()

    def _extract_patch_coordinates(self):
        """Extract row and column coordinates from patch filenames"""
        self.patch_data = []

        for patch_path in self.patches:
            filename = os.path.basename(patch_path)
            coords = self._parse_coordinates_from_filename(filename)
            if coords:
                row, col, _, _ = coords
                self.patch_data.append((row, col, patch_path))

        # Get grid dimensions
        rows = set(row for row, col, path in self.patch_data)
        cols = set(col for row, col, path in self.patch_data)
        
        self.grid_rows = max(rows) + 1
        self.grid_cols = max(cols) + 1
        
        print(f"Detected grid: {self.grid_rows} rows x {self.grid_cols} columns")
        print(f"Row range: 0 - {self.grid_rows - 1}")
        print(f"Column range: 0 - {self.grid_cols - 1}")

    def _parse_coordinates_from_filename(self, filename):
        """
        Parse row and column coordinates from filename
        Naming pattern: patch.row_col.yoffset_xoffset.ext
        """
        filename_without_ext = os.path.splitext(filename)[0]
        pattern = r'(\S+)\.(\d+)_(\d+)\.(\d+)_(\d+)' # 25H0340173.148_021.151552_21504.jpg
        match = re.search(pattern, filename_without_ext, re.IGNORECASE)
        if match:
            row = int(match.group(2))
            col = int(match.group(3))
            yoffset = int(match.group(4))
            xoffset = int(match.group(5))
            return row, col, yoffset, xoffset
        return None
    
    def process_tasks(self, tasks):
        """
        Process tasks based on configuration
        
        Config format:
            [
                {
                    "name": "R00",
                    "description": "Row 0-49, Col 0-49",
                    "rows": [0, 49],
                    "cols": [0, 49]
                }
            ]
        """
        print(f"Grid: {self.grid_rows} rows x {self.grid_cols} columns")
        
        for task in tasks:
            self._process_single_task(task)

    def _process_single_task(self, task):
        """
        Process a single task
        task = {'name': task_name, rows:[row_start, row_end], cols:[col_start, col_end]}
        If rows is not specified, use all rows.
        If columns is not specified, use all columns.
        """
        task_name = task["name"]
        
        # Calculate row and column range
        rows = task.get("rows")
        cols = task.get("cols")
        
        if (rows is None) and (cols is None):
            raise ValueError("ERROR: Task '{task_name}' does not have rows or cols.")
        if rows:
            if not isinstance(rows, list) or len(rows) != 2:
                raise ValueError(f"ERROR: Task '{task_name}' has invalid rows. Must be a list of 2 elements.")
        if cols:
            if not isinstance(cols, list) or len(cols) != 2:
                raise ValueError(f"ERROR: Task '{task_name}' has invalid cols. Must be a list of 2 elements.")

        if rows:
            start_row = rows[0]
            end_row = min(rows[1], self.grid_rows - 1)
        else:
            start_row, end_row = (0, self.grid_rows - 1)

        if cols:
            start_col = cols[0]
            end_col = min(cols[1], self.grid_cols - 1)
        else:
            start_col, end_col = (0, self.grid_cols - 1)
        
        # Validate ranges
        if not (0 <= start_row <= end_row < self.grid_rows):
            raise ValueError(f"ERROR: Task '{task_name}' has invalid row range [{start_row}, {end_row}]")
        
        if not (0 <= start_col <= end_col < self.grid_cols):
            raise ValueError(f"ERROR: Task '{task_name}' has invalid column range [{start_col}, {end_col}]")
        
        # Find the image patches within the row and column ranges
        task_patches = []
        for row, col, patch_path in self.patch_data:
            if (start_row <= row <= end_row) and (start_col <= col <= end_col):
                task_patches.append(patch_path)
        print(f"Task '{task_name}': Rows {start_row}-{end_row}, Cols {start_col}-{end_col} -> {len(task_patches)} patches")
        self.task_patches[task_name] = task_patches
        self.task_regions[task_name] = {'row':(start_row, end_row), 'col':(start_col, end_col)}
    
    def get_task_patches(self, task_name):
        return self.task_patches[task_name]
    
def main(args):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load CVAT config
    config = json.load(open(args.cvat_config, 'r', encoding="utf-8"))
    CVAT_URL = config['cvat_url']
    CVAT_USERNAME = config['cvat_username']
    CVAT_PASSWORD = config['cvat_password']
    CVAT_SHARE_PATH = config['cvat_share_path']

    # Load task config
    task_config = json.load(open(args.task_json, 'r', encoding="utf-8"))

    #-----------------------------------------------
    # Group image patches accordint to task config
    #-----------------------------------------------
    print("ASSIGNING IMAGE TO TASKS:")
    grouper = ImagePatchGrouper(CVAT_SHARE_PATH, args.image_folder, args.image_extension)
    grouper.load_patches()
    grouper.process_tasks(task_config['tasks'])

    #-----------------------
    # Create CVAT tasks
    #-----------------------
    print("CREATING CVAT TASKS:")
    with make_client(CVAT_URL, credentials=(CVAT_USERNAME, CVAT_PASSWORD)) as client:
        # Verify project exists
        try:
            project = client.projects.retrieve(args.project_id)
            # Use the organization accovrding to project
            org_id = project.organization_id
            org_slug = client.organizations.retrieve(org_id).slug
            client.organization_slug = org_slug
            print(f"Using project: {project.name}(ID: {project.id}, organization_slug: {org_slug})")
        except ValueError as e:
            print(f"ERROR in accessing project {args.project_id}: {str(e)}")
            
        # Create task
        task_infos = []
        for task_input in task_config['tasks']:
            patch_paths = grouper.get_task_patches(task_input['name'])
            
            task_spec = models.TaskWriteRequest(
                name=f"{args.task_prefix}_{task_input['name']}",
                project_id=args.project_id,
                segment_size=args.segment_size
            )
            data_params = {
                'image_quality': 70,
                'use_zip_chunks': True,
                'use_cache': True,
                'sorting_method': 'lexicographical'
            }

            if not args.dryrun:
                task = client.tasks.create_from_data(
                    spec=task_spec,
                    resource_type=ResourceType.SHARE,
                    resources=patch_paths,
                    data_params=data_params
                )
                frame_count = len(task.get_frames_info())
                row_start, row_end = grouper.task_regions[task_input['name']]['row']
                col_start, col_end = grouper.task_regions[task_input['name']]['col']
                task_infos.append((task.id, task.name, row_start, row_end, col_start, col_end, frame_count, task.jobs.count))
                print(f"CVAT Task was created. ID: {task.id}. Name: {task.name}. Jobs: {task.jobs.count}. Frames: {frame_count}. Row:{row_start}-{row_end}. Cols:{col_start}-{col_end}.")
        if not args.dryrun:
            print("All tasks were created.")

    #-----------------------
    # Write log files
    #-----------------------
    if not args.dryrun:
        log_entries = {}
        log_entries['Timestamp'] = timestamp
        log_entries['CVAT_share_path'] = CVAT_SHARE_PATH
        log_entries['image_folder'] = args.image_folder
        log_entries['image_extension'] = args.image_extension
        log_entries['image_folder_path'] = os.path.join(CVAT_SHARE_PATH, args.image_folder)
        log_entries['image_folder_rows'] = grouper.grid_rows
        log_entries['image_folder_cols'] = grouper.grid_cols
        log_entries['task_prefix'] = args.task_prefix
        log_entries['project_id'] = args.project_id
        log_entries['project_name'] = project.name
        log_entries['project_organization_id'] = org_id
        log_entries['project_organization_slug'] = org_slug
        log_entries['total_image_count_in_folder'] = len(grouper.patches)
        log_entries['total_image_count_in_tasks'] = sum(len(patches) for _, patches in grouper.task_patches.items())
        for task_name, patches in grouper.task_patches.items():
            log_entries[f"image_count_{task_name}"] = len(patches)
            
        with open(f"{args.task_prefix}.create_task.{timestamp}.log", 'w', encoding="utf-8") as fout:
            fout.write("Logs: Create CVAT Task\n")
            fout.write("[Summary]\n")
            for (k,v) in log_entries.items():
                fout.write(f"{k}\t{v}\n")
            fout.write("\n[CVAT_Tasks]\n")
            fout.write("\t".join(["task_id", "task_name", "row_start", "row_end", "col_start", "col_end", "frame_count", "job_count"]) + "\n")
            for (task_id, task_name,  row_start, row_end, col_start, col_end, frame_count, job_count) in task_infos:
                fout.write(f"{task_id}\t{task_name}\t{row_start}\t{row_end}\t{col_start}\t{col_end}\t{frame_count}\t{job_count}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image_folder", required=True, help="Folder name under CVAT share path containing image files")
    parser.add_argument("--image_extension", required=True, choices=["jpg"])
    parser.add_argument("--task_prefix", required=True)
    parser.add_argument("--project_id", type=int, required=True)
    parser.add_argument("--segment_size", type=int, required=True)
    parser.add_argument("--cvat_config", required=True)
    parser.add_argument("--task_json", required=True, help="json file defining the task")
    parser.add_argument("--dryrun", action="store_true")
    #arguments = parser.parse_args("--cvat_share_path /NetApp/users/deeplearn/Projects/marrow_morphology/image_3dhistech/ --image_folder 25H0340173/ --image_extension jpg --task_prefix haha --project_id 47 --segment_size 10 --cvat_config /home/olivia/cvat_config.json --task_json tasks.ROI-test.json".split())
    arguments = parser.parse_args()
    main(arguments)

