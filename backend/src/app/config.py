from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/cartorio_mosaico"
    )
    secret_key: str = "change-me-in-production"
    debug: bool = False

    tile_provider: str = "esri"
    mapbox_token: str | None = None
    nominatim_url: str = "https://nominatim.openstreetmap.org"

    default_utm_epsg: int = 31983
    default_geodetic_epsg: int = 4674

    # CORS — origens separadas por vírgula. Vazio = sem CORS (mesma origem).
    cors_origins: str = ""


settings = Settings()
