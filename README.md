<p align="center"><img src="docs/ssf_banner.png" alt="Social Card of Spartan"></p>

<h1 align="center">Bogart — Spartan for AWS</h1>

<p align="center">
  <a href="https://github.com/nerdmonkey/spartan-bogart/actions/workflows/lint.yml"><img src="https://github.com/nerdmonkey/spartan-bogart/actions/workflows/lint.yml/badge.svg" alt="Lint"></a>
  <a href="https://github.com/nerdmonkey/spartan-bogart/actions/workflows/tests.yml"><img src="https://github.com/nerdmonkey/spartan-bogart/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/nerdmonkey/spartan-bogart/actions/workflows/security.yml"><img src="https://github.com/nerdmonkey/spartan-bogart/actions/workflows/security.yml/badge.svg" alt="Security"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+">
</p>

## About

Bogart is the AWS variant of the Spartan Serverless Framework — "the Swiss Army knife for serverless development on AWS." It streamlines your development process and ensures code consistency, allowing you to build scalable and efficient applications on AWS with ease.

Bogart is versatile and can be used to efficiently develop:

- RESTful APIs
- Workflows or State Machines
- Small or medium-sized ETL pipelines
- Containerized microservices
- Agentic AI (coming soon)

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [Security Vulnerabilities](#security-vulnerabilities)
- [Credits](#credits)
- [License](#license)

## Features

| **Feature Category**           | **Status**                   | **Details**                                                          |
| ------------------------------ | ---------------------------- | --------------------------------------------------------------------- |
| **AWS Lambda Handlers**        | ✅ Excellent                  | API Gateway triggers, event-driven, typed Lambda handlers             |
| **Database & Migrations**      | ✅ Full Support               | SQLAlchemy models, Alembic migrations, seeders                        |
| **DynamoDB Support**           | ✅ Built-in                   | DynamoDB models, repository pattern                                   |
| **Pydantic Integration**       | ✅ Full Support               | Validation, serialization, EmailStr, type safety                      |
| **Architecture Patterns**      | ✅ Robust                     | Repository + service pattern, clean separation of concerns            |
| **Testing Framework**          | ✅ Fully Integrated           | pytest, moto mocking, coverage tools                                  |
| **Code Quality Tools**         | ✅ Complete                   | Black, isort, flake8, mypy, bandit, pre-commit                        |
| **Development Workflow**       | ✅ Streamlined                | Poetry, Tox, environment support                                      |
| **Cloud-Native Features**      | ✅ Advanced                   | Lambda handlers, middlewares, multi-cloud hooks                       |
| **Observability & Monitoring** | ✅ Enterprise-Grade           | Structured logging, tracing, exception handling                       |
| **Developer Experience**       | ✅ High                       | Docker, Serverless Framework, .env support                            |
| **Security Best Practices**    | ✅ Strong                     | Hashing, input validation, secrets handling                           |
| **Scalability Features**       | ✅ Built-in                   | Pagination, filtering, bulk operations                                |
| **Logging Support**            | ✅ Advanced                   | Factory logger types (file, stream, cloud, both), structured output   |
| **Reusability**                | ✅ High                       | Abstract base classes, reusable modules                               |
| **Modular Architecture**       | ✅ Excellent                  | Factory design, reusable services/utilities                           |
| **Configuration Management**   | ✅ Centralized                | Pydantic + .env + environment-detection                               |
| **Cross-Platform Support**     | ✅ Multi-Cloud Ready          | AWS, GCP, Azure, local support via abstraction layers                 |
| **Code Consistency**           | ✅ Consistent with minor gaps | Naming conventions, model structures, unified patterns                |

## Requirements

- Python 3.11+
- pip (or [Poetry](https://python-poetry.org/), which the project's tox environments use)
- [`python-spartan`](https://pypi.org/project/python-spartan/) CLI (`pip install python-spartan`) — used for migrations, seeding, and serving the app

## Installation

Clone the repo:

```bash
git clone https://github.com/nerdmonkey/spartan-bogart.git
cd spartan-bogart
```

Set up your environment:

<details>
<summary><strong>▶️ For Linux / macOS</strong></summary>

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>🪟 For Windows PowerShell</strong></summary>

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>🪟 For Windows CMD / DOS</strong></summary>

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

</details>

Copy and configure environment variables:

```bash
cp .env.example .env  # Linux/macOS
```

```powershell
copy .env.example .env  # PowerShell
```

```cmd
copy .env.example .env  # CMD
```

## Usage

### Run Database Migrations

```bash
spartan migrate init -d sqlite
spartan migrate upgrade
```

### Seed Dummy Data

```bash
spartan db seed
```

### Run the App

```bash
spartan serve
```

## Project Structure

```
spartan-bogart/
├── app/
│   ├── exceptions/        # Custom exception types
│   ├── helpers/           # Utility helpers (logger, environment, context, tracer)
│   ├── middlewares/       # Request/response middlewares
│   ├── models/
│   │   ├── db/            # SQLAlchemy models
│   │   └── ddb/           # DynamoDB models
│   ├── repositories/      # Data access layer
│   ├── requests/          # Request/input models
│   ├── responses/         # Response/output models
│   └── services/
│       ├── logging/       # Logger implementations (file, stream, cloud, both)
│       └── tracing/       # Distributed tracing implementations
├── config/                # Configuration files
├── database/
│   ├── migrations/        # Alembic migrations
│   └── seeders/           # Database seeders
├── docs/                  # Documentation (banner, CONTRIBUTING, CODE_OF_CONDUCT)
├── handlers/              # Lambda entrypoint handlers
├── scripts/               # Release tooling (CHANGELOG promotion, etc.)
├── tests/                 # Test suites
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── requirements.txt       # Python dependencies
└── pyproject.toml         # Poetry configuration
```

## Testing

Install the dev dependencies (`requirements-dev.txt` currently omits `pytest-xdist`, which `pytest.ini` requires via `-n auto`, and `jsonpickle`, which `app/services/app.py` imports — install both manually on a fresh `.venv`):

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install pytest-xdist jsonpickle
```

Run the unit test suite with coverage:

```bash
python -m pytest tests/unit -q --cov=app --cov=handlers --cov=config --cov-report=term-missing
```

Alternatively, via tox (installs dependencies through Poetry):

```bash
tox -e coverage
```

## Changelog

Please see [CHANGELOG](CHANGELOG.md) for more information on what has changed recently.

## Contributing

Please see [CONTRIBUTING](./docs/CONTRIBUTING.md) for details.

## Security Vulnerabilities

Please review [our security policy](../../security/policy) on how to report security vulnerabilities.

## Credits

- [Sydel Palinlin](https://github.com/nerdmonkey)
- [All Contributors](../../contributors)

## License

The MIT License (MIT). Please see [License File](LICENSE) for more information.
