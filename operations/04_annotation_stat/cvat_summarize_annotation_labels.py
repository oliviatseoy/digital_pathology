#!/usr/bin/env python
# coding: utf-8

# In[1]:


import argparse
import json
import pandas as pd
from datetime import datetime
from cvat_sdk.api_client import Configuration, ApiClient, exceptions
from cvat_sdk import make_client


# In[ ]:


class Cvat_Stat():
    def __init__(self, cvat_url, cvat_username, cvat_password, project_id):
        # API Client
        self.api_client = ApiClient(
            Configuration(host = cvat_url, username = cvat_username, password = cvat_password)
            )
        
        self.project_id = project_id
        self.organization_slug = self._get_organization_slug(self.project_id)
    
        # Python SDK Client
        self.client = make_client(cvat_url, credentials=(cvat_username, cvat_password))
        self.client.organization_slug = self.organization_slug 

        self.completed_jobs = {} # dict task_id -> job_id
        self.project_labels = {} # dict label_id -> (label_name, label_type)
        self.job_label_counter = {} # dict job_id -> label_id -> count
        self.merged_label_counter = {} # dict label_id -> count
        #self.label_counter = {} # dict label_type(mask/tag) ->  label_name -> count

        # Main
        self.stat_labels()

    def stat_labels(self):
        self.project_labels = self._get_label_name(self.project_id)
        self.completed_jobs = self._get_completed_jobs(self.project_id)
        for (task_id, job_ids) in self.completed_jobs.items():
            #task_name = self._get_task_name(task_id)
            for job_id in job_ids:
                self.job_label_counter[job_id] = self._retrieve_annotation(job_id)
                for (label_id, count) in self.job_label_counter[job_id].items():
                    self.merged_label_counter[label_id] = self.merged_label_counter.get(label_id, 0) + count

    def get_summary_table(self):
        summary_rows = []
        mask_label_ids = [k for (k, v) in self.project_labels.items() if v[1]=='mask']
        mask_label_names = [v[0] for (k, v) in self.project_labels.items() if v[1]=='mask']
        tag_label_ids = [k for (k, v) in self.project_labels.items() if v[1]=='tag']
        tag_label_names = [v[0] for (k, v) in self.project_labels.items() if v[1]=='tag']
        for (task_id, job_ids) in self.completed_jobs.items():
            task_name = self._get_task_name(task_id)
            for job_id in job_ids:
                job_detail = self._get_job_detail(job_id)
                label_counts = self.job_label_counter[job_id]
                row = {
                    'task_id': task_id,
                    'task_name': task_name,
                    'job_id': job_id, 
                    'assignee': job_detail.get('assignee', '.'),
                    'updated_date': job_detail.get('updated_date', '.'),
                    'frame_count': job_detail.get('frame_count', 0),
                    'mask_count': sum(v for (k,v) in label_counts.items() if k in mask_label_ids),
                    'tag_count': sum(v for (k,v) in label_counts.items() if k in tag_label_ids)
                }
                
                for label_id, label_name in zip(mask_label_ids, mask_label_names):
                    row[label_name] = label_counts.get(label_id, 0)
                for label_id, label_name in zip(tag_label_ids, tag_label_names):
                    row[label_name] = label_counts.get(label_id, 0)
                summary_rows.append(row)
        df_summary_job = pd.DataFrame(summary_rows)
        df_summary_job.sort_values('job_id', inplace=True)

        # Add summary row
        label_columns = [name for name in df_summary_job.columns if name not in ['task_id', 'task_name', 'job_id', 'assignee', 'updated_date', 'frame_count']]
        summary_row = {col: '' for col in df_summary_job.columns}
        summary_row['task_id'] = -1
        summary_row['task_name'] = 'SUMMARY'
        summary_row['job_id'] = -1
        summary_row['assignee'] = '.'
        summary_row['updated_date'] = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_row['frame_count'] = df_summary_job['frame_count'].sum() if 'frame_count' in df_summary_job.columns else ''
        for label in label_columns:
            summary_row[label] = df_summary_job[label].sum()
        df_summary = pd.concat([df_summary_job, pd.DataFrame([summary_row])], ignore_index=True)
        return df_summary

    # Projects
    def _get_label_name(self, project_id):
        try:
            project_labels = {}
            page = 1
            while True:
                (data, response) = self.api_client.labels_api.list(project_id=project_id, page=page, page_size=100)
                for label in data['results']:
                    project_labels[label.id] = (label.name, label.type)
                if not data['next']:
                    assert len(project_labels) == data['count']
                    break
                page += 1 
            return project_labels
        except exceptions.ApiException as e:
            print("Exception when calling LabelsApi.list(): %s\n" % e)

    def _get_organization_slug(self, project_id):
        try:
            (data_proj, response_proj) = self.api_client.projects_api.retrieve(project_id)
            try: 
                (data_org, response_org) = self.api_client.organizations_api.retrieve(data_proj.organization_id)
                return data_org['name']
            except exceptions.ApiException as e:
                print("Exception when calling OrganizationsApi.list(): %s\n" % e)
        except exceptions.ApiException as e:
            print("Exception when calling PojectsApi.list(): %s\n" % e)

    # Jobs
    def _get_completed_jobs(self, project_id):
        try:
            completed_jobs = {}
            completed_job_count = 0
            page = 1
            while True:
                (data, response) = self.api_client.jobs_api.list(
                    org=self.organization_slug, 
                    project_id=project_id, 
                    state="completed", 
                    page=page, page_size=50)
                for job in data['results']:
                    task_id = job['task_id']
                    completed_jobs.setdefault(task_id, []).append(job.id)
                    completed_job_count += 1
                if not data['next']:
                    assert data['count'] == completed_job_count
                    break
                page += 1
            return completed_jobs
        except exceptions.ApiException as e:
            print("Exception when calling JobsApi.list(): %s\n" % e)

    def _get_job_detail(self, job_id):
        job_detail = {}
        try:
            (data, response) = self.api_client.jobs_api.retrieve(job_id)
            job_detail = {'frame_count': data['frame_count']}
            if data['updated_date']:
                job_detail['updated_date'] = data['updated_date'].strftime("%Y%m%d_%H%M%S")
            if data['assignee']:
                job_detail['assignee'] = data['assignee']['username']
            return job_detail
        except exceptions.ApiException as e:
            print("Exception when calling JobsApi.retrieve(): %s\n" % e)
 
    def _retrieve_annotation(self, job_id):
        label_counter_job= {}
        try:
            (data, response) = self.api_client.jobs_api.retrieve_annotations(job_id)
            for data_type in ('tags', 'shapes'):
                for annot in data[data_type]:
                    label_id = annot['label_id']
                    label_counter_job[label_id] = label_counter_job.get(label_id, 0) + 1
            return label_counter_job
        except exceptions.ApiException as e:
            print("Exception when calling JobsApi.retrieve_annotations(): %s\n" % e)
        
    # Tasks
    def _get_task_name(self, task_id):
        try:
            # tasks_api.retrieve: Retrieve task detail 
            (data, response) = self.api_client.tasks_api.retrieve(task_id)
        except exceptions.ApiException as e:
            print("Exception when calling TasksApi.retrieve(): %s\n" % e)
        return data['name']

def main(args):
    # Load CVAT config
    config = json.load(open(args.cvat_config, 'r', encoding="utf-8"))
    CVAT_URL = config['cvat_url']
    CVAT_USERNAME = config['cvat_username']
    CVAT_PASSWORD = config['cvat_password']

    cvat_stat = Cvat_Stat(CVAT_URL, CVAT_USERNAME, CVAT_PASSWORD, args.project_id)
    df_summary = cvat_stat.get_summary_table()
    df_summary.to_csv(args.output_file, sep="\t", index=None)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--cvat_config', required=True)
    parser.add_argument('--project_id', type=int, required=True)
    parser.add_argument('--output_file', required=True)
    #arguments = parser.parse_args("--cvat_config /home/olivia/cvat_config.json --project_id 1 --output_file haha.txt".split())
    arguments = parser.parse_args()
    main(arguments)

