# Blueprints

## Overview

Blueprints are a way of defining pipeline architecture. They are YAML files that define the structure of a pipeline, including the tasks that are run, the order in which they are run, and the dependencies between them. Blueprints are used to generate pipeline DAGs, which are then used to run pipelines.

## Blueprint Structure

Root keys in a blueprint are: `arguments`, `etl`, and `save`.

### Arguments

Pretty straigforward. This is where you define the arguments that will be passed to the pipeline. These arguments are then available to all tasks in the pipeline. They should be called using Jinja templating, e.g. `{{argument_name}}`.

### Save

Describes how to save the output of the pipeline.

- `target`: The target to save to. Defaults to `./data/<etl-name>/raw`.
- `overwrite`: Whether to overwrite the target if it already exists. Defaults to `true` to save space.
- `format`: The format to save the data in. Defaults to `csv`. Can be `csv`, `json`, or `parquet`. <mark>Currently only "csv" is supported.</mark>

### ETL

Each entry in this element represents a table. The key is the name of the table, and the value is a list of tasks to either run/generate that table or save/download the table. Metadata like `fields` will be documented in the table definition here.

**Example:**

```yaml
etl:
  table_name:
    manifest: table
    schema: public
    save:
      query: SELECT * FROM table_name LEFT JOIN parent_table_name ON table_name.id = parent_table_name.id
      depends_on:
        - parent_table_name
    run:
      script: scripts/table_name.sql
      depends_on:
        - parent_table_name
    fields: # (Optional)
      - name: id
        type: integer
        description: The ID of the table
        primary_key: true
        foreign_key: false
        default_value: Null
        nullable: false
      - name: name
        type: string
        description: The name of the table
```

!!! tip "`script` and `query` are interchangeable."
     `script` is preferred for more complex queries as it specifies a file to run, while `query` is preferred for simple queries as it specifies a query as a string literal.

!!! tip "The `depends_on` key is optional."
     If a task has no dependencies, it will be considered a root. 

!!! tip "The `fields` key is optional."
     `fields` is for documentation purposes only. It is not relevant to operating the pipeline.

!!! tip "**Awesome documentation tip.**"
     When documentation is generated, a DAG visual will be generated to describe the pipeline. Adding headless root tables to the DAG will make it easier to read. For example, if you have a table that is a join of two other tables, you can add the two tables as headless roots to the DAG to make it easier to read.

     ```yaml
     # Headless root
     headless_table:
      manifest: table
      schema: public
     ```
    Will be shown as:
    ```mermaid
    stateDiagram
      direction LR
      headless_table --> table_1
      headless_table --> table_2
      table_1 --> table_3
      table_2 --> table_3
    ```