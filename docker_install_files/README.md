# Introduction
This folder contains example scripts to enable you to do a **Docker** based installation for the DRAW client in your computer.

Please copy the files or their content in your local computer and rename them as per the table below:

| File Name | Suggested File name|
|----|-----|
|example.docker-compose.yml | docker-compose.yml |
|example_nginx.conf| nginx.conf|
|example_env | .env|

Please remember that the .env file will be hidden usually by your file explorer.

To unhide the file please use the following steps:

## Windows
To unhide files in Windows:
1. Open File Explorer
2. Click on the "View" tab
3. Check the "Hidden items" box in the "Show/hide" section

## Mac
To unhide files in Mac:
1. Open Finder
2. Press Command+Shift+. (period) to toggle hidden files
3. Press the same combination again to hide them

>**Important**:
>
> Do not forget to change the sensitive information like passwords and secret keys in the .env file. Remember to correctly setup the proxy configuration if you need a proxy to be configured for internet access.


## Docker Based Installation method

#### Windows
1. Download Docker Desktop from [Docker's website](https://www.docker.com/products/docker-desktop/)
2. Run the installer and follow the on-screen instructions
3. Start Docker Desktop after installation

#### macOS
1. Download Docker Desktop from [Docker's website](https://www.docker.com/products/docker-desktop/)
2. Drag Docker to your Applications folder
3. Launch Docker Desktop
4. Follow the on-screen instructions to complete setup

#### Linux
```
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```
Log out and back in for group changes to take effect.

### DRAW Client Installation

1. Create a project directory and navigate to it:
```
mkdir draw-client
cd draw-client
```

> **IMPORTANT**: The datastore folder is the location where your DICOM files are stored and where the DRAW client will look for new files to process. This folder must exist and be accessible to Docker. The DRAW client will monitor this folder for new DICOM files and will also save the processed RTStruct files back to this location. Note that this can be a network storage folder where the DICOM data are saved before importing to the TPS. A periodic task will fetch new images from the directory and process them for autosegmentation.


2. Ensure that you have the correct folder path for the **datastore folder** at the bottom. See the commented section in the docker-compose.yml file below. Ensure that the folder exists. Additionally if in Windows then change all \ to a / in the folder path. 

The other folders are as follows:

| Host Folder Name | Docker Folder Name | Purpose |
| ---- | ----- | ---- |
| staticfiles | /app/staticfiles | This folder stores the static files |
| dicom | /app/folders | This folder stores the dicom data that is being processed |
| yaml-templates | /app/yaml-templates | This folder has all the autosegmentation templates created for the DRAW client |

See the file example_docker-compose.yml file inside the docker_install_files folder repository and copy the contents into a new file called docker-compose.yml. 
Please note there is a docker-compose.yml file in the main repository which allows you to "BUILD" the docker image. The example_docker-compose.yml file allows you to "PULL" the latest image from the dockerhub repository.


3. Create a .env file in the same directory. Please make sure that the file name is correct and note the presence of the . before the name which indicates that this is a hidden file. See the file called .env.docker.example for the content that has to be included in this file.

  
> **Important**: Configuring the correct proxy settings is needed if you hospital connects to the internet through a proxy server. Please contact your IT personnel to get the complete string as it may require special authentication also. The above example is for a proxy which does not require authentication.

4. Create a nginx.conf file (required for the nginx container) by copying the contents of the  example_nginx.conf file in the repository

5. Start the services:
```
docker-compose up -d
```

6. Access the DRAW client interface at http://localhost:8001

7. To stop the services:
```
docker-compose down
```

## Datastore Path Configuration

### Shared Network Storage / Folder

It is likely that your DICOM datastore is located at a remote server which has a shared network folder. In order for this network folder to be correctly configured at the bottom of the example_docker-compose.yml provides the configuration for the CIFS storage configuration to be done. This is as follows:

``` yaml
volumes:
  postgres_data:
  app_data:
  dicomdata:
    driver_opts:
      type: cifs
      o: "username=${NETWORK_USER},domain=${NETWORK_DOMAIN},password=${NETWORK_PASSWORD},rw"
      device: ${NETWORK_PATH}  
```
Note in this case dicomdata volume of docker is pointed to the CIFS storage defined by the storage device at NETWORK_PATH. You may need to get this from your IT support. Additionally the NETWORK_USER, NETWORK_DOMAIN and NETWORK_PASSWORD need to be provided. These should be added to the .env file to keep these credentials separate. Ensure that the user account being created has READ and WRITE privileges to the folder. 

### Local Computer based storage

#### Unix / Mac

Sometimes the datastore folder may be located on a local storage path. In such case the section should be modified as follow:

``` yaml
volumes:
  postgres_data:
  app_data:
  dicomdata:
    driver: local
    driver_opts:
      o: bind
      type: none
      device: /path/to/your/directory
```
Here the /path/to/your/directory is the full path to your directory.

#### Windows

 In case of Windows do remember to change the **\ to /** in the path and enclose the path with ***double quotes*** like this 

``` yaml
volumes:
  postgres_data:
  app_data:
  dicomdata:
    driver: local
    driver_opts:
      o: bind
      type: none
      device: "C:/data/dicomdata"
```

Here the C:/data/dicomdata represents the folder which is the datastore.