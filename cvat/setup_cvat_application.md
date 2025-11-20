# Set up CVAT (v2.47.0)

- CVAT: `/NetApp/users/olivia/Projects/2025_digital_pathology/CVAT_production/cvat-2.47.0/`
- cvat_data: `/NetApp/users/olivia/Projects/2025_digital_pathology/CVAT_production/cvat_data/`
- cvat_db: `/NetApp/users/olivia/Projects/2025_digital_pathology/CVAT_production/cvat_db/`
- images: `/NetApp/users/deeplearn/Projects/marrow_morphology/image_3dhistech/`

## Quick start

- (Optional) Remove nuctl function: `nuctl delete function pth-facebookresearch-sam-vit-h`
- (Optional) `docker compose -f docker-compose.yml -f docker-compose.override.yml -f components/serverless/docker-compose.serverless.yml down`
- Start containers: `docker compose -f docker-compose.yml -f docker-compose.override.yml -f components/serverless/docker-compose.serverless.yml up -d`
- Deploy SAM: `serverless/deploy_gpu.sh serverless/pytorch/facebookresearch/sam/`
- Create superuser: `docker exec -it cvat_server bash -ic 'python3 ~/manage.py createsuperuser'`

## Basic setup

- Download CVAT: `wget https://github.com/cvat-ai/cvat/archive/refs/tags/v2.47.0.tar.gz`
- Copy files for v2.47.0
  - [docker-compose.override.yml](../cvat/cvat-2.47.0/docker-compose.override.yml)
  - [components/serverless/docker-compose.serverless.yml](../cvat/cvat-2.47.0/components/serverless/docker-compose.serverless.yml)
- `docker-compose.override.yml` was created for the below settings:
  - Set timezone

     ```text
     services:
       cvat_server:
         environment:
           - TZ=Asia/Hong_Kong
     ```

  - Set share path

   ```text
   services:
     cvat_server:
       volumes:
         - cvat_share:/home/django/share:ro
     cvat_worker_import:
       volumes:
         - cvat_share:/home/django/share:ro
     cvat_worker_export:
       volumes:
         - cvat_share:/home/django/share:ro
     cvat_worker_annotation:
       volumes:
         - cvat_share:/home/django/share:ro
     cvat_worker_chunks:
       volumes:
         - cvat_share:/home/django/share:ro

   volumes:
     cvat_share:
       driver_opts:
         type: none
         device: /NetApp/users/deeplearn/Projects/marrow_morphology/image_3dhistech/
         o: bind
   ```

  - Set database location

     ```text
     volumes:
       cvat_data:
         driver_opts:
           device: /NetApp/users/olivia/Projects/2025_digital_pathology/CVAT_production/cvat_data/
           o: bind
           type: none
       cvat_db:
         driver_opts:
           device: /NetApp/users/olivia/Projects/2025_digital_pathology/CVAT_production/cvat_db/
           o: bind
           type: none
     ```

- `components/serverless/docker-compose.serverless.yml` was uploaded for the below setting:
  - `services/cvat_server/environment/CVAT_NUCLIO_HOST: 'nuclio'`
  - `services/cvat_server/environment/CVAT_NUCLIO_INVOKE_METHOD: 'dashboard'`

## Automatic annotation

- Installion of components needed for semi-automatic and automatic annotation: <https://docs.cvat.ai/docs/administration/advanced/installation_automatic_annotation/>
- Serverless tutorial: <https://docs.cvat.ai/docs/manual/advanced/serverless-tutorial/>

- Install `nuclio`

   ```bash
   wget https://github.com/nuclio/nuclio/releases/download/1.13.0/nuctl-1.13.0-linux-amd64
   sudo chmod +x nuctl-1.13.0-linux-amd64
   sudo ln -sf $(pwd)/nuctl-1.13.0-linux-amd64 /usr/local/bin/nuctl
   ```

- Dashboard: <localhost:8070/>

- Deploy SAM

   ```bash
   # gpu
   serverless/deploy_gpu.sh serverless/pytorch/facebookresearch/sam/
   # cpu
   serverless/deploy_cpu.sh serverless/pytorch/facebookresearch/sam/
   ```

  - Check deployed functions

   ```bash
   $ nuctl get functions
   NAMESPACE | NAME                           | PROJECT | STATE | REPLICAS | NODE PORT 
   nuclio    | pth-facebookresearch-sam-vit-h | cvat    | ready | 1/1      | 49153     
   ```

   ```bash
   $ docker ps -a  |grep sam |grep -v Exit
   5f47ffe0a4b0   cvat.pth.facebookresearch.sam.vit_h:latest-gpu      "processor"              6 minutes ago    Up 6 minutes (healthy)       0.0.0.0:49153->8080/tcp, :::49153->8080/tcp                                                    nuclio-nuclio-pth-facebookresearch-sam-vit-h
   ```

  - Restart / Redeploy the function

   ```bash
   nuctl delete function pth-facebookresearch-sam-vit-h
   serverless/deploy_gpu.sh serverless/pytorch/facebookresearch/sam/
   ```

## Manage CVAT using docker

- Start docker application

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.override.yml -f components/serverless/docker-compose.serverless.yml up -d
   ```

  - `docker compose up` create and start containers
  - `-d`, `--detach`: Detached mode: Run the containers in the background

- Create superuser account in CVAT: `docker exec -it cvat_server bash -ic 'python3 ~/manage.py createsuperuser'`

- Stop and remove CVAT Docker containers

   ```bash
    docker compose -f docker-compose.yml -f docker-compose.override.yml -f components/serverless/docker-compose.serverless.yml down
   ```

  - include all compose configuration file that are used
  - How it works:
    - Stop containers
    - Remove containers
    - Remove networks
    - Remove volumes (optional): `-v, --volumes`. Add this flag to remove data.
    - Remove images (optional): `--rmi`
  - Troubleshoot:
    - Network is still in use

     ```bash
     $ docker compose -f docker-compose.yml -f docker-compose.override.yml -f components/serverless/docker-compose.serverless.yml down
     ! Network cvat_cvat                        Resource is still in use
     
     # List all containers connected to cvat_cvat network
     $ docker network inspect cvat_cvat --format '{{range .Containers}}{{.Name}} {{end}}'
     nuclio-nuclio-pth-facebookresearch-sam-vit-h
     
     # Solution 1: Delete the deployed function
     $ nuctl delete function pth-facebookresearch-sam-vit-h

     # Solution 2: Stop and remove the related containers
     $ docker stop $(docker ps -aq --filter network=cvat_cvat)
     $ docker rm $(docker ps -aq --filter network=cvat_cvat)
     ```

- Health check

   ```bash
   $ docker exec -t cvat_server python manage.py health_check
   Cache backend: default   ... working
   Cache backend: media     ... working
   DatabaseBackend          ... working
   DiskUsage                ... working
   MemoryUsage              ... working
   OPAHealthCheck           ... working
   ```

- Check logs: `docker logs cvat_server`
- Check timezone: `docker exec cvat_server date`
- Inpsect docker volume: `docker volume ls`
- Inspect docker network: `docker network ls`
