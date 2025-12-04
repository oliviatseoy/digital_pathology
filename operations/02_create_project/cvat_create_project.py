#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import argparse
import json
from datetime import datetime
from cvat_sdk import make_client
from cvat_sdk.api_client import models
from cvat_sdk.core.proxies.tasks import ResourceType


# In[ ]:


def main(args):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load CVAT config
    config = json.load(open(args.cvat_config, 'r', encoding="utf-8"))
    CVAT_URL = config['cvat_url']
    CVAT_USERNAME = config['cvat_username']
    CVAT_PASSWORD = config['cvat_password']

    # Load labels from json file
    lst_labels = json.load(open(args.labels_json, 'r', encoding="utf-8"))

    # Create prject accroding to labels
    with make_client(CVAT_URL, credentials=(CVAT_USERNAME, CVAT_PASSWORD)) as client:
        # Set organization
        client.organization_slug = args.organization

        # Prepare labels
        labels = []
        for label_config in lst_labels:
            label_kwargs = {
                "name": label_config["name"],
                "type": label_config["type"]
            }
            # Specify color if specified in JSON
            if "color" in label_config:
                label_kwargs["color"] = label_config["color"]
            label_request = models.PatchedLabelRequest(**label_kwargs)

            # Add attributes if specified
            if "attributes" in label_config:
                label_request.attributes = [
                    models.AttributeRequest(
                        name=attr["name"],
                        input_type=attr["input_type"],
                        mutable=attr["mutable"],
                        values=attr["values"],
                        default_value=attr["default_value"]
                    ) for attr in label_config["attributes"]
                ]
                
            labels.append(label_request)
        
        # Create project
        project = client.projects.create(
            models.ProjectWriteRequest(
                name=args.project_name,
                labels=labels
            )
        )

        # Retrieve information of prject created.
        project_created = client.projects.retrieve(project.id)
        labels_created = project_created.get_labels()
        org_id = project_created.organization_id
        org_slug = client.organizations.retrieve(org_id).slug

        # Write log file
        with open(f"{args.op}.create_project.{timestamp}.log", 'w', encoding="utf-8") as fout:
            fout.write("Logs: Create CVAT Project\n")
            fout.write("[Summary]\n")
            fout.write(f"Timestamp\t{timestamp}\n")
            fout.write(f"Project_id\t{project.id}\n")
            fout.write(f"Project_name\t{project_created.name}\n")
            fout.write(f"Organization_id\t{org_id}\n")
            fout.write(f"Organization_slug\t{org_slug}\n")
            fout.write(f"Num_labels\t{len(labels_created)}\n")
            fout.write("[Labels]\n")
            for label in labels_created:
                fout.write(f"{label.id}\t{label.name}\t{label.type}\n")

        # Print message
        print(f"Project was created. ID: {project.id}. Name: {project_created.name}. Num of labels: {len(labels_created)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels_json", required=True, help="labels.json")
    parser.add_argument("--project_name", required=True)
    parser.add_argument("--organization", required=True)
    parser.add_argument("--cvat_config", required=True)
    parser.add_argument("--op", required=True)
    #arguments = parser.parse_args("--labels_json labels.json --project_name test --organization testorg --cvat_config /home/olivia/cvat_config.json --op haha".split())
    arguments = parser.parse_args()
    main(arguments)

