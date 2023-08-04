# Welcome to your Curie Project!



This is the beginning of your pipeline project. Please make note of the project structure in your file explorer. And make note that any reference to a file path should be relative to the root of your project.

> **What is a KETL Pipeline?**: Our devs derived the name from the intended nature of the program. KETL stands for "Kinetic Extract Transform Load." It was found to best align with their goal of producing a system that would allow users to easily build and run pipelines from a mono-repo architecture. Given it's ability to simplify the process of building, running, and deploying pipelines, the name stuck.

> **Due Diligence**: Please make sure you have read the [Getting Started](#getting-started) section before continuing.
> 1. "( . )" indicates a location where the user can indicate they want to affect **all** items, by swapping the list for the dot. For example, `curie --clean .` will clean all pipelines, and `curie --clean pipeline1 pipeline2 .` will clean `pipeline1` and `pipeline2`.

# Getting Started 1.0.0 

### Command Line Interface 1.1.0

1. **Initialize a new project** - Change your working directory to the location where you want to create your project. Then run either of the following commands:

    ```bash
    curie etl --init <project>
    curie etl -i <project>
    ```
2. **Compile your project** - Compiling your project will generate the scripts that will be used to run your pipeline. By default these will be stored in `<root>/scripts/compiled/<pipeline>/`. 

    Change your working directory to the location of your project. Then run either of the following commands:

    ```bash
    curie etl --run <pipeline> --compile
    curie etl -r <pipeline> -c
    ```
3. **Running your pipeline** - Running your pipeline will execute the scripts generated in the previous step. This action affects your database. Common uses include: updating tables, building a new dataset, refreshing dependencies.

    Change your working directory to the location of your project. Then run either of the following commands:

    ```bash
    curie etl --run <pipeline> --tables <t1 t2 t3 ... tn (.)>
    curie etl -r <pipeline> <mode> --tables <t1 t2 t3 ... tn (.)>
    ```
4. **Saving your pipeline** - Saving your pipeline will download selections of the tables specified in the command according to terms defined in your config file. By default these will be stored in `<root>/data/<pipeline>/`.

    Change your working directory to the location of your project. Then run either of the following commands:

    ```bash
    curie etl --save <pipeline> --tables <t1 t2 t3 ... tn (.)>
    curie etl -s <pipeline> --tables <t1 t2 t3 ... tn (.)>
     TODO: alter to allow multiple file types
    ```
5. **Cleaning your pipeline** - Cleaning your pipeline will remove all files generated by the pipeline. This action does not affect your database. Common uses include: removing downloaded data, removing compiled scripts.

    Change your working directory to the location of your project. Then run the following command:
    ```bash
    curie etl --clean <pipeline (.)> --facet <facet (.)>
    ```

### Configuration Files 1.2.0

There are two primary configuration files that you will need to edit to get your project up and running. These are `connections.yaml` and `pathways.yaml`. `connections.yaml` contains the information needed to connect to your database. `pathways.yaml` contains the information needed to associate pipeline blueprints with your database connection. 

After you have initialized your project, you will find these files in `<root>/config/`.

To declare a new connection, add a new entry to `connections.yaml` in the following format:
```yaml
DatabaseClass:
    connection_name:
        user: username
        password: password
        host: host
        port: 1123
        database: database
        schema: schema
```
The format of the connection arguments is subject to the rules around the database class you are using. For example, if you are using a `Postgres` object, you will need to provide a `schema` argument. If you are using a `SQLite` object, you will not need to provide a `schema` argument.

To declare a new pathway, add a new entry to `pathways.yaml` in the following format:
```yaml
# Where to find connection information:
Connections:
    config:
        file: connections.yaml
# Pipeline declarations:
Pathways:
    pipeline_name:
        connection: connection_name
        blueprint: blueprints/this_pipeline.yaml
```

### Pipeline Blueprints 1.3.0
Pipeline blueprints are as they sound. They outline the steps that will be taken to run a pipeline. They are written in YAML and are stored in `<root>/blueprints/`. It allows a user to define a pipeline in a way that is both human-readable and machine-readable. 

**Three things to note:**
1. The order of the tables in the blueprint does not matter. Tables will be executed according to their dependencies.
2. The order of the dependencies in the blueprint does not matter. The program will form a dependency graph and execute the tables in the correct order.
3. Should a dependency not exist, the program may fault. This is a feature, not a bug. It is a good idea to check your dependencies before running a pipeline.

**Root Tags:** The root tags of a pipeline blueprint are `SYNC`, `ARGUMENTS`, and `ETL`. `SYNC` defines the target for downloaded tables. `ARGUMENTS` defines the arguments that will be passed to the pipeline. `ETL` defines the tables that will be executed in the pipeline.

**SYNC:** The `SYNC` tag defines the target for downloaded tables. This is a string that will be used to define the target directory for downloaded tables. By default, this will be `<root>/data/<pipeline>/`.

**ARGUMENTS:** The `ARGUMENTS` tag defines the arguments that will be passed to the pipeline. This is a dictionary that will be passed to the pipeline. It is a good idea to define the arguments that will be passed to the pipeline here. This will allow you to change the arguments without changing the pipeline blueprint. 

> You can call these arguments from your queries using Jinja format. For example if I have a variable `offset: 5000` in my arguments, I can call it in my query using `{{ offset }}`.

**ETL:** The `ETL` tag defines the tables that will be executed in the pipeline. This is a dictionary of tables that will be executed in the pipeline. The key is the name of the table, and the value is a dictionary of the table's attributes.

**Table Attributes:** The table attributes are `manifest`, `schema`, `save`, and `run`. `manifest` defines how the query should be manifested in the database: table, view, etc. `schema` defines the schema of the table. `save` defines how the table should be saved (See "Modal Elements"). `run` defines how the table should be run (See "Modal Elements"). 

* **Modal Elements:** There are two modes supported: `run` and `save`. `run` will execute the pipeline and `save` will download the data specified in the pipeline. Each will allow you to specify a list of dependencies that will be executed before the pipeline is run, and a query that will generate the data. Of course, `run` will execute the query and affect the database, and `save` will download the data generated by the query.
    * **query:** The query is a string that will be executed by the database. It is the core of the pipeline. These should be written in Jinja SQL.

    * **script:** Scripts are Jinja SQL files that will be compiled then run to execute the pipeline. Store them where you prefer, but please reserve the `scripts/compiled/<pipeline>` directory for compiled scripts.

    > **script** and **query** are mutually exclusive. If both are specified, **script** will be used.

    * **dependencies:** Dependencies is a list of tables that must be formed before the current table is run. This allows the program to form a dependency graph and execute the tables in the correct order. This matters in procedural ETLs and in forming good data models.

    > ### Save Mode Only
    > * **target:** The target is a string that will be used to define the target directory for downloaded tables. By default, this will be `<root>/data/<pipeline>/`. 
    > * **filetype:** The filetype is a string that will be used to define the filetype for downloaded tables. By default, this will be `csv`. 


    > ### Run Mode Only
    >    * **method:** Defines the manner in which a table is affected: `replace`, `truncate`, `merge`, `append`. `replace` will drop the table and replace it with the new data. `truncate` will delete all rows from the table and insert the new data. `merge` will update the table with the new data using an identifier. `append` will insert the new data into the table.
    

**Example Pipeline:**
```yaml
SYNC:
  target: ./data/pipeline1/raw
  overwrite: true
ARGUMENTS:
  limit: 100
ETL:
  table_name:
    manifest: table
    schema: public
    save:
      query: SELECT * FROM table limit {{limit}}
```


----------

----------
### Project Structure 1.4.0

```
├── blueprints
│   └── pipeline1.yaml
├── config
│   ├── connections.yaml
│   └── pathways.yaml
├── data
│   └── pipeline1
│       └── table1.csv
├── scripts
│   ├── compiled
│   │   └── pipeline1
│   │       └── table1.sql (compiled)
│   └── pipeline1
│       └── table1.sql (jinjasql)
├── logs
│   └── pipeline1
│       └──table1.log
└── README-curie.md

```