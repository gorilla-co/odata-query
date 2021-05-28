# OData-Query

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=gorillaco_odata-query&metric=alert_status&token=cb35257e036d950788a0f628af7062929318482b)](https://sonarcloud.io/dashboard?id=gorillaco_odata-query)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=gorillaco_odata-query&metric=coverage&token=cb35257e036d950788a0f628af7062929318482b)](https://sonarcloud.io/dashboard?id=gorillaco_odata-query)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`odata-query` is a library that parses [OData v4](https://www.odata.org/) filter strings, and can convert
them to other forms such as
[Django Queries](https://docs.djangoproject.com/en/3.2/topics/db/queries/),
[SQLAlchemy Queries](https://docs.sqlalchemy.org/en/14/orm/loading_objects.html),
or just plain SQL.


## Installation

`odata-query` is available on pypi, so can be installed with the package manager
of your choice:

```bash
pip install odata-query
# OR
poetry add odata-query
# OR
pipenv install odata-query
```

The package defines the following optional `extra`s:

- `django`: If you want to pin a compatible Django version.
- `sqlalchemy`: If you want to pin a compatible SQLAlchemy version.


The following `extra`s relate to the development of this library:

- `linting`: The linting and code style tools.
- `testing`: Packages for running the tests.
- `docs`: For building the project documentation.


You can install `extra`s by adding them between square brackets during
installation:

```bash
pip install odata-query[sqlalchemy]
```


## Contact

Got any questions or ideas? We'd love to hear from you. Check out our
[contributing guidelines](CONTRIBUTING.md) for ways to offer feedback and
contribute.


## License

Copyright (c) [Gorillini NV](https://gorilla.co/).
All rights reserved.

Licensed under the [MIT](LICENSE) License.
