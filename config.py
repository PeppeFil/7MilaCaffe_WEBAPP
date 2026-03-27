import os


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ITEMS_PER_PAGE = 25


class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}",
    )
    DEBUG = True


class TestingConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    TESTING = True


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///production.db")
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
