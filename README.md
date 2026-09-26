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

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [Security Vulnerabilities](#security-vulnerabilities)
- [Credits](#credits)
- [License](#license)

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

## Usage

1. Create a virtual environment and install the required packages:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

3. Configure the migration:

   ```bash
   spartan migrate init -d sqlite
   ```

4. Create all the tables:

   ```bash
   spartan migrate upgrade
   ```

5. Insert dummy data:

   ```bash
   spartan db seed
   ```

6. Run the app:

   ```bash
   spartan serve
   ```

## Testing

1. Install the dev dependencies (`requirements-dev.txt` currently omits `pytest-xdist`, which `pytest.ini` requires via `-n auto`, and `jsonpickle`, which `app/services/app.py` imports — install both manually on a fresh `.venv`):

   ```bash
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   pip install pytest-xdist jsonpickle
   ```

2. Run the unit test suite with coverage:

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
