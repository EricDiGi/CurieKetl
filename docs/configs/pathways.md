# Configuration YAML Documentation

## Connections
The `Connections` section defines the various connections that can be used in the system.

- `file`: The path to the YAML file (`config/connections.yaml`) containing connection configurations.

## Documentation
The `Documentation` section provides information about the documentation for the system.

- `site`:
  - `description`: A description of the system's documentation ("Documentation for Curie").
  - `name`: The title of the documentation site ("Curie Documentation").
  - `primary_color`: The primary color associated with the documentation site (red).

## Pathways
The `Pathways` section outlines different pipelines in the system, each representing a series of steps or actions.

- `pathway-name`: The key for the pathway (`test-postgres-etl`).
  - `blueprint`: (Required) The path to the YAML file (`blueprints/blueprint.yaml`) containing the pathway's blueprint.
  - `connection`: (Required) The connection key (`test-postgres`) used by the pathway.
  - `description`: A brief description of the pathway ("This is a test pathway")(Optional).
  - `meta`: (Optional) Additional information about the pathway.
    - `authors`: A list of authors contributing to the pathway.
      - > - `email`: The email address of the author (`eric.digioacchino01@gmail.com`).
        > - `is_primary`: Indicates whether the author is the primary author (true).
        > - `name`: The name of the author ("Eric DiGioacchino").
    - `tags`: Tags associated with the pathway as a list (e.g., `test`, `etl`, `postgres`).


## Example
```yaml
Connections:
  file: config/connections.yaml
Documentation:
    site:
        description: Documentation for Curie
        name: Curie Documentation
        primary_color: red
Pathways:
    test-etl:
        blueprint: blueprints/blueprint.yaml
        connection: test-redshift
        description: This is a test pathway
```