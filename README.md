<p align="center"><img src="docs/ssf_banner.png" alt="Social Card of Spartan"></p>

# Bogart — Spartan for AWS

## About
Bogart is the AWS variant of the Spartan Serverless Framework — "the Swiss Army knife for serverless development on AWS." It streamlines your development process and ensures code consistency, allowing you to build scalable and efficient applications on AWS with ease.

#### Bogart is versatile and can be used to efficiently develop:
- RESTful API
- Workflows or State Machines
- Small or Medium-sized ETL Pipelines
- Containerized Microservices
- Agentic AI (Coming Soon)


## Installation
1. To install the spartan command line tool
```bash
pip install python-spartan
```

2. Try
```bash
spartan --help
```

## Usage
1. Install all the required packages
```bash
python -m venv .venv
pip install -r requirements.txt
```
2. Copy the .env.example to .env

3. Configure the migration
```bash
spartan migrate init -d sqlite
```

4. Create all the tables
```bash
spartan migrate upgrade
```

5. Insert dummy data
```bash
spartan db seed
```

6. Then run it using the following command
```bash
spartan serve
```

## Testing
```bash
pytest
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
