# Welcome to Curie :test_tube:

Curie is a command line interface for ETL pipelines and local data workflows. It is designed to be simple, flexible, and extensible. It is written in Python and uses [JinjaSQL]() to write SQL queries.

## Table of Contents

1. [Getting Started](#getting-started-100)
    1. [Command Line Interface](#command-line-interface-110)
    2. [Configuration Files](#configuration-files-120)
    3. [Pipelining](#pipeline-blueprints-130)
    4. [Project Structure](#project-structure-140)

# Getting Started 1.0.0 

**Definitions:**
* **project:** A project is a collection of pipelines. It is the highest level of organization in Curie.
* **pipeline:** A pipeline is a collection of tables/nodes. It is the second level of organization in Curie. And it is the core of Curie.
* **tables and nodes:** Tables and nodes are the same thing. They are the smallest unit of organization in Curie. They can be thought of as a single actionable unit.
* **variants:** Variants are the different ways that a table can be run. They are defined in the pipeline definitions, only for Save operations. They are used to define the different ways that a table can be saved. For example, you may want to save a table as a CSV and as a JSON. You can define these as variants in the pipeline definition, and then call them when you run the pipeline. Variants also enable more complex save strategies like saving one csv for each categorical item in a field. Some use cases will be provided later.
* **modes:** Modes are the different ways that a table can be run. There are two actionable modes that should be used in pipeline definitions: __run__ and __save__. __run__ will execute the pipeline and __save__ will download the data specified in the pipeline. Each will allow you to specify a list of dependencies that will be executed before the table is run, and a query that will generate the data. Of course, __run__ will execute the query and affect the database, and __save__ will download the data generated by the query.

### Command Line Interface 1.1.0


1. **Initialize a new project** - Change your working directory to the location where you want to create your project. Then run the following command:

    ```bash
    curie init <project>
    ```

2. **Compile your project** - Compiling your project will generate the scripts that will be used to run your pipeline. By default these will be stored in `<root>/scripts/compiled/Unknown/` if no `compile_path` is defined in `project.yaml`. 

    Change your working directory to the location of your project. Then run either of the following commands:

    ```bash
    curie etl <mode> <pipeline> --compile
    ```
3. **Running your pipeline** - Running your pipeline will execute the scripts generated during compilation (all scripts will be recompiled with each run). This action affects your database. Common uses include: updating tables, building a new dataset, refreshing dependencies.

    Change your working directory to the location of your project. Then run either of the following commands:

    ```bash
    curie etl run <pipeline> [start] [--tables <t1 t2 t3 ... tn (.)> ][--connection <myDB-Conn-Name>][--override-name <var1 var2 var3 ... varn>][--override-values <vala valb valc ... valn>]
    ```
4. **Saving your pipeline** - Saving your pipeline will download selections of the tables specified in the command according to terms defined in your config file. By default these will be stored in `<root>/data/Unknown/` if not specified in the `project.yaml`. This action does not affect your database. Common uses include: downloading data for analysis, downloading data for sharing. **Variant executions are supported in this mode.**

    Change your working directory to the location of your project. Then run either of the following commands:

    ```bash
    curie etl save <pipeline> [start] [--tables <t1 t2 t3 ... tn (.)> ][--connection <myDB-Conn-Name>][--override-name <var1 var2 var3 ... varn>][--override-values <vala valb valc ... valn>]
    ```
5. **Cleaning your pipeline** - Cleaning your pipeline will remove all artifacts generated by the pipeline or project. This action does not affect your database. Common uses include: removing downloaded data, removing compiled scripts.

    Change your working directory to the location of your project. Then run the following command:
    ```bash
    curie etl clean <pipeline (.)>
    ```

    Alternatively, you can avail yourself to the included Makefile which supplies a number of commands to selectively remove artificts.

6. **Automated Documentation** - Curie is self-documenting, with plenty of options to add more insight. To generate documentation for your project, run the following command:

    Change your working directory to the location of your project. Then run the following command:
    ```bash
    curie docs generate
    ```
    And to view the documentation, run the following command:
    ```bash
    curie docs serve
    ```
    This will launch a local server that will allow you to view your documentation in your browser.

### Configuration Files 1.2.0

Curie requires three configuration files to be operational; `project.yaml` in the root directory, `connections.yaml` in the `config/` directory, and a configuration file for each pipeline in the `pipelines/` directory.

#### Project Configuration 1.2.1

The root `project.yaml` file is the core of the project. It defines the project name, the project description, the project version, and the project author. It also defines the default connection to be used for all pipelines. `Project` is the root-most key and all definitions will be defined inside this key. The following is an example of a `project.yaml` file:

```yaml
Project:
  Documentation:
    site: # Variables to modify how the generated documentation looks
      name: My Curie project
      description: This is a description of my project
      primary_color: blue
    Connections: ./config/connections.yaml # Path to the connections file
    Pipelines:
      # The following is a list of pipeline definitions.
      - name: PipelineX
        pipeline: ./pipelines/PipelineX.yaml # Path to the pipeline definition
        compile_path: ./scripts/compiled/PipelineX # Path to the compiled scripts
        download: ./data/PipelineX/raw # Path to the saved data
        connection: my-db-conn # Connection to use for this pipeline
        meta: # ALL META IS OPTIONAL
          description: This is a description of the pipeline
          created_at: 2023-09-29
          authors:
            - name: Eric DiGioacchino
              email: test@email.com
          tags:
            - tag1
            - tag2              

```

#### Connections Configuration 1.2.2

The `connections.yaml` file defines the connections that will be used by the pipelines. It is a list of connections, each with a unique name. Secrets can be integrated into the connections file using Jinja and specific YAML, the following example demonstrates this as well as the default configuration method.

```yaml

Redshift:
  secret-redshift:
    secrets:
      env_file:
        path: ./config/.env
    host: '{{REDSHIFT_HOST}}'
    port: '{{REDSHIFT_PORT}}'
    database: private
    user: '{{REDSHIFT_USER}}'
    password: '{{REDSHIFT_PASSWORD}}'
    reminder: 'This is a reminder to turn on your VPN' # This is a comment that will appear if any connection issues occur.

MySQL:
  default-mysql:
    host: localhost
    port: 3306
    database: public
    user: root
    password: password

```

#### Pipeline Defintions 1.3.0

Pipeline definitions are the core of Curie. They define the tables that will be run, the queries that will be executed, and the dependencies that will be requierd. They are written in YAML and are stored in the `pipelines/` directory. The following is an example of a pipeline definition:

```yaml
arguments: # Arguments are optional and are used to pass variables to the pipeline.
  limit: 100
  stateAbbrev: CA

etl: # The core definition
  
  facilities:
    run:
      script: ./scripts/pipeline1/facilities.sql
      method: seed
    save:
      store_results: true # This indicates to Curie that the results of this query should be used for context in other queries.
      query: SELECT id,name FROM facilities WHERE stateAbbrev = '{{stateAbbrev}}' LIMIT {{limit}}
      outputs: # Passes fields out of this node as parameters that can be called later.
        - id
    meta:
      description: This is a description of the table
      fields:
        - name: id
          description: This is a description of the field
          type: integer
          nullable: false
          primary_key: true
        - name: name
          description: This is a description of the field
          type: string
          nullable: false
  # An employees table that is seeded from a query.
  # And generates a csv for the employees at each facility for analysis.
  employees:
    run:
      script: ./scripts/pipeline1/employees.sql
      method: seed
    save:
        query: SELECT id,name,tenure,salary FROM employees WHERE facility_id = {{facility_id}}
        depends_on:
          - facilities
        variants:
          - name: "facility-{{id}}" # The prefix of the file name that will be saved.
            filetype: csv # The filetype of the file to be saved
            iterate_on:
                id: "{{facilities.id}}" # The field to iterate on from any previous nodes. (Must be a dependency)
            arguments:
                facility_id: "{{id}}" # The argument to pass to the query.

```




* **Modal Elements:** There are two modes supported: `run` and `save`. `run` will execute the pipeline and `save` will download the data specified in the pipeline. Each will allow you to specify a list of dependencies that will be executed before the pipeline is run, and a query that will generate the data. Of course, `run` will execute the query and affect the database, and `save` will download the data generated by the query.
    * **query:** The query is a string that will be executed by the database. It is the core of the pipeline. These should be written in Jinja SQL.

    * **script:** Scripts are Jinja SQL files that will be compiled then run to execute the pipeline. Store them where you prefer, but please reserve the `scripts/compiled/<pipeline>` directory for compiled JinjaSQL scripts.

    > **script** and **query** are mutually exclusive. If both are specified, **script** will be used.

    * **depends_on:** Defines a list of tables that must be formed before the current table is run. This allows the program to form a dependency graph and execute the tables in the correct order. This matters in procedural ETLs and in forming good data models.

    > ### Run Mode Only
    >    * **method:** Defines the manner in which a table is affected: `replace`, `truncate`, `merge`, `append`,`seed`. `replace` will drop the table and replace it with the new data. `truncate` will delete all rows from the table and insert the new data. `merge` will update the table with the new data using an identifier. `append` will insert the new data into the table. `seed` will not wrap the query in any additional logic. It will simply execute the query and insert the data into the table. This is useful for creating tables that will be used as dependencies for other tables.

### Project Structure 1.4.0

```
<PROJECT ROOT>
    |
    ├── pipelines
    │   └── pipeline1.yaml
    |   └── ...
    |
    ├── config
    │   ├── connections.yaml
    │   └── .env
    ├── data
    │   └── pipeline1
    │       └── table1.csv
    ├── scripts
    │   ├── compiled
    │   │   └── pipeline1
    │   │       └── table1.sql (compiled)
    |   |
    │   └── pipeline1
    │       └── table1.sql (jinjasql)
    ├── docs
    │   ├── stylesheets (default for curie's mkdocs)
    │   ├── pipes (generated by curie)
    │   └── index.md
    |   └── project.md
    |
    └── README-curie.md

```

# Deployment 2.0.0

Curie was build with cross-platform deployment in mind. Rather than requiring any special infrastructure, Curie is designed to be deployed on any machine that can run Python. This includes Windows, Mac, and Linux machines. More specifically Curie can be deployed to cloud infrastructure through github actions.

## Github Actions 2.1.0

### Submit Code to a Storage Bucket 2.1.1

#### AWS S3
    
    ```yaml
    - name: Deploy ETL Code to S3
      run: |
        cd CurieProject

        pip install -r requirements.txt

        curie etl run "My Pipeline" --compile

        if [ ! -d "scripts/compiled/My Pipeline" ]; then
          echo "Compiled scripts not found"
          exit 1
        fi

        aws s3 sync scripts/compiled/My Pipeline s3://my-bucket/My Pipeline --delete
    ```

    Then you can also include a step to deploy Cloudformation for a Glue Job to run the ETL on a schedule.

## AWS Deployment 2.2.0
### AWS Glue 2.2.1

The following code uses 4 parameters to run a Curie pipeline. This Job can be modified to run on a schedule by adding triggers. The parameters are as follows:
- s3-bucket: The bucket where the pipeline scripts are stored
- pipeline-keys: A list of keys to the scripts to be executed (the paths within the bucket)
- connection-names: The name of the glue connection to use (optional will default to the connection specified on the Job settings)
- database: The name of the database to use (optional)

The script resolves all database connections available to Glue in your cloud environment, and makes them accessible by name. This allows you to use the same script for multiple databases without having to modify the script. The script also resolves secrets from AWS Secrets Manager. This allows you to store your database credentials in Secrets Manager and reference them in your Glue connection. This is a more secure way to store your credentials than storing them in the Glue connection itself.

1. Create a new Glue Job with the code below.
2. Add a trigger with a schedule to run the job on a schedule.
3. Add the parameters to the trigger.
4. Let it run!

```python
import os
import sys
import boto3
import logging as log
import json
import redshift_connector
import pandas as pd
from awsglue.utils import getResolvedOptions

region = os.environ['AWS_REGION']
client = boto3.client('glue', region_name=region)
secrets_client = boto3.client('secretsmanager', region_name=region)
s3_client = boto3.client('s3', region_name=region)

def prepare_connection_properties(client, connection_name, database=None):
    def get_connection(name , connections):
        for connection in connections:
            if connection['Name'] == name:
                return connection
        raise Exception(f'Connection {name} not found')
    def derive_secrets(connection_properties):
        props = {}
        if 'SECRET_ID' in connection_properties:
            secret = secrets_client.get_secret_value(SecretId=connection_properties['SECRET_ID'])
            secret = json.loads(secret['SecretString'])
            props['user'] = secret['username']
            props['password'] = secret['password']
        if 'PASSWORD' in connection_properties:
            props['password'] = connection_properties['PASSWORD']
        if 'USERNAME' in connection_properties:
            props['user'] = connection_properties['USERNAME']
        if 'user' not in props or 'password' not in props:
            raise Exception(f'Could not derive username and password from connection properties for {connection_name}')
        return props
    response = client.get_connections()
    connections = response['ConnectionList']

    props = {}
    connection_properties = get_connection(connection_name, connections)['ConnectionProperties']
    if 'JDBC_CONNECTION_URL' in connection_properties:
        props['host'] = connection_properties['JDBC_CONNECTION_URL'].split('/')[2].split(':')[0]
        props['port'] = int(connection_properties['JDBC_CONNECTION_URL'].split('/')[2].split(':')[1])
        props['database'] = connection_properties['JDBC_CONNECTION_URL'].split('/')[3]
    if 'HOST' in connection_properties:
        props['host'] = connection_properties['HOST']
    if 'PORT' in connection_properties:
        props['port'] = int(connection_properties['PORT'])
    if 'DATABASE' in connection_properties:
        props['database'] = connection_properties['DATABASE']

    props.update( derive_secrets(connection_properties) )
    
    if database is not None:
        props['database'] = database
    return props

# Load Args from Glue Job using sys.argv
# s3_bucket: s3 bucket name
# pipeline_keys: list of files to be processed
# connection_names: glue connection name
# database: database name
default_arg_keys = ['s3-bucket', 'pipeline-keys', 'connection-names']
if '--connection' in sys.argv:
    default_arg_keys.append('connection')
if '--database' in sys.argv:
    default_arg_keys.append('database')
args = getResolvedOptions(sys.argv, default_arg_keys)

# Database connection properties
conn_name = args['connection_names'] if '--connection' not in sys.argv else args['connection']
database = args['database'] if '--database' in sys.argv else None
props = prepare_connection_properties(client, conn_name, database)
print(f"Connecting to {props['host']}:{props['port']}:{props['database']} as {props['user']}")

def execute_query(query):
    conn = redshift_connector.connect(**props)
    cursor = conn.cursor()
    steps = query.split(';')
    for step in steps:
        if len(step) > 0:
            cursor.execute(step)
    if cursor.description is not None:
        print(cursor.description)
        df = pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])
        print(df)
    conn.commit()
    conn.close()

def validate_file_exists(s3_client, bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
    except Exception as e:
        raise Exception(f'File {key} does not exist in {bucket}')

def s3_read(client, bucket, key):
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    return obj['Body'].read().decode('utf-8')

print(f"Beginning execution of scripts from {args['s3_bucket']} on {args['connection_names']}")
for key in json.loads(args['pipeline_keys']):
    validate_file_exists(s3_client, args['s3_bucket'], key)
    print(f"Reading file {key}")
    script = s3_read(s3_client, args['s3_bucket'], key)
    try:
        print(f"Executing script {key}")
        execute_query(script)
    except Exception as e:
        print(f'Error executing script {key}: {e}')
        raise Exception(f'Error executing script {key}: {e}')
```