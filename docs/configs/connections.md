# Database Connection Configuration Documentation

This document provides information about the database connection configurations present in the YAML schema.

## Database Connections
Multiple root keys can be defined in the `connections.yaml` file, each representing a different database class.

- `Redshift`: A Redshift database connection. *Currently the only stable database class.*
  - `connection-key`:
    A unique identifier for a specific database connection configuration.
    - `host`: The hostname or IP address of the database server (e.g., `localhost`).
    - `port`: The port number for the database server (e.g., `5432` for PostgreSQL).
    - `database`: The name of the database to connect to (e.g., `test`).
    - `user`: The username for authenticating the database connection (e.g., `postgres`).
    - `password`: A placeholder (`{{secret_password}}`) for a secret password. This indicates that the actual password should be securely stored and provided during runtime.
    - `schema`: The default database schema to use (e.g., `public`).
    - `secrets`:
      A section for defining secret-related configurations.
      - `EnvironmentsFile`:
        A label for the type of secret configuration. This could be customized based on your needs.
        - `path`: The path to the secret environment file (`../envs/dummy.env`). This is a relative path from the project root directory.


## Example
```yaml
Redshift:
  redshift-test:
    secrets:
      EnvironmentFile:
        path: ../dummy/.env
    host: "{{REDSHIFT_HOST}}"
    port: 5439
    database: gale
    user: "{{REDSHIFT_USER}}"
    password: "{{REDSHIFT_PASSWORD}}"
MongoDB:
  mongo-test:
    host: localhost
    port: 27017
    database: test
    user: test
    password: test
    schema: test
```

