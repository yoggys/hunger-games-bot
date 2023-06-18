TORTOISE_ORM = {
    "connections": {
        "default": "sqlite://main.db",
    },
    "apps": {
        "models": {
            "models": ["utils.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
