# Hunger Games Discord Bot

## Requirements

```bash
Python 3.10
```

## Installation

```bash
pip3 install -r requirements.txt
aerich init -t utils.settings.TORTOISE_ORM
aerich init-db
```

## Enviroment variables

```bash
TOKEN = your bot token
```

## Usage

### Run bot

```bash
python3 main.py
```

### Lint code

```bash
python3 -m black .
```

### Tests

```bash
python3 -m pytest ./tests.py
```

### How to update db with lastest changes

Migrate changes:

```bash
aerich migrate --name <name>
```

Be aware that some field parameters will not be read correctly, for this purpose edit the file in `/migrations` and add for example `DEFAULT []` for default values (tortoise.fields.JSONfield).

Apply changes:

```bash
aerich upgrade
```
