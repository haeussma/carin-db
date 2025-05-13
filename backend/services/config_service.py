import json
import os
from pathlib import Path
from typing import Optional

from loguru import logger

from ..models.appconfig import AppConfig, DatabaseInfo


class ConfigService:
    """Service for managing application configuration."""

    CONFIG_FILE = "config.json"

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the path to the configuration file."""
        path = (
            Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            / cls.CONFIG_FILE
        )
        logger.info(f"Config path: {path}")
        return path

    @classmethod
    def load_config(cls) -> AppConfig:
        """Load the application configuration from file."""
        config_path = cls.get_config_path()
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    data = json.load(f)
                    logger.debug("Configuration loaded successfully")
                    return AppConfig(**data)
            else:
                logger.error("No configuration file found, creating default")
                return AppConfig()
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            return AppConfig()

    @classmethod
    def save_config(cls, config: AppConfig) -> None:
        """Save the application configuration to file."""
        config_path = cls.get_config_path()
        try:
            with open(config_path, "w") as f:
                json.dump(config.model_dump(), f, indent=2)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            raise

    @classmethod
    def get_database(cls) -> DatabaseInfo:
        """Gets the first database configuration.

        Returns:
            The database configuration

        Raises:
            ValueError: If the database with the given URI doesn't exist
        """
        config = cls.load_config()
        db = next((db for db in config.databases), None)
        if db is None:
            raise ValueError("No database configured")
        return db

    @classmethod
    def add_database(cls, database: DatabaseInfo) -> None:
        """Add a new database configuration."""
        config = cls.load_config()
        # Remove existing database with same URI if exists
        config.databases = [db for db in config.databases if db.uri != database.uri]
        config.databases.append(database)
        cls.save_config(config)

    @classmethod
    def update_database(cls, uri: str, database: DatabaseInfo) -> None:
        """Update an existing database configuration."""
        config = cls.load_config()
        for i, db in enumerate(config.databases):
            if db.uri == uri:
                config.databases[i] = database
                cls.save_config(config)
                return
        raise ValueError(f"Database with URI {uri} not found")

    @classmethod
    def delete_database(cls, uri: str) -> None:
        """Delete a database configuration."""
        config = cls.load_config()
        config.databases = [db for db in config.databases if db.uri != uri]
        cls.save_config(config)

    @classmethod
    def get_openai_key(cls) -> Optional[str]:
        """Get the OpenAI API key."""
        config = cls.load_config()
        return config.openai_api_key

    @classmethod
    def set_openai_key(cls, api_key: str) -> None:
        """Set the OpenAI API key."""
        config = cls.load_config()
        config.openai_api_key = api_key
        cls.save_config(config)

    @classmethod
    def clear_openai_key(cls) -> None:
        """Clear the OpenAI API key."""
        config = cls.load_config()
        config.openai_api_key = None
        cls.save_config(config)

    @classmethod
    def get_db_by_uri(cls, uri: str) -> DatabaseInfo:
        """Get a database configuration by URI."""
        config = cls.load_config()
        db = next((db for db in config.databases if db.uri == uri), None)
        if db is None:
            raise ValueError(f"Database with URI {uri} not found")
        return db

    @classmethod
    def get_openai_api_key(cls) -> str:
        """Get the OpenAI API key."""
        config = cls.load_config()
        openai_api_key = config.openai_api_key
        if openai_api_key is None:
            raise ValueError("OpenAI API key is not set")
        return openai_api_key

    @classmethod
    def get_first_database(cls) -> DatabaseInfo:
        """Get the first database configuration.

        Returns:
            The first database configuration

        Raises:
            ValueError: If no database is configured
        """
        config = cls.load_config()
        if not config.databases:
            raise ValueError("No database configured")
        return config.databases[0]

    @classmethod
    def update_first_database(cls, database: DatabaseInfo) -> None:
        """Update the first database configuration.

        If no database exists, it will be added.
        """
        config = cls.load_config()
        if not config.databases:
            config.databases.append(database)
        else:
            config.databases[0] = database
        cls.save_config(config)
