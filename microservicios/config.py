"""Configuracion comun de los microservicios."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ==========================================
    # Influx - Monitor de red
    # ==========================================

    influx_red_url: str = ""
    influx_red_verify_ssl: bool = False
    influx_red_org: str = ""
    influx_red_token: str = ""
    influx_red_bucket: str = ""
    influx_red_timeout_ms: int = 10000

    # ==========================================
    # Influx - Trafico Temperatura OLTs
    # ==========================================

    influx_temp_url: str = ""
    influx_temp_verify_ssl: bool = False
    influx_temp_org: str = ""
    influx_temp_token: str = ""
    influx_temp_bucket: str = ""
    influx_temp_timeout_ms: int = 10000

    # ==========================================
    # Influx - CMTS
    # ==========================================

    influx_cmts_url: str = ""
    influx_cmts_verify_ssl: bool = False
    influx_cmts_org: str = ""
    influx_cmts_token: str = ""
    influx_cmts_bucket: str = ""
    influx_cmts_timeout_ms: int = 60000

    # ==========================================
    # MySQL
    # ==========================================

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_unix_socket: str = ""
    mysql_user: str = ""
    mysql_password: str = ""
    mysql_database: str = ""
    mysql_connect_timeout: int = 10

    # Oracle Helix, conectado mediante el puente local existente.
    oracle_helix_host: str = ""
    oracle_helix_port: int = 12101
    oracle_helix_service_name: str = ""
    oracle_helix_user: str = ""
    oracle_helix_password: str = ""
    oracle_helix_cache_seconds: int = 120
    oracle_helix_call_timeout_ms: int = 15000
    oracle_helix_query_budget_seconds: int = Field(
        default=45,
        validation_alias=AliasChoices(
            "ORACLE_HELIX_QUERY_BUDGET_SECONDS",
            "ORACLE_HELIX_BUDGET_SECONDS",
        ),
    )

    # ==========================================
    # Grafana proxy local
    # ==========================================

    grafana_proxy_enabled: bool = False
    grafana_url: str = ""
    grafana_user: str = ""
    grafana_password: str = ""
    grafana_verify_ssl: bool = False
    grafana_timeout_seconds: int = 30

    # Topologias OLT (servidor de archivos remoto)
    topologias_ssh_host: str = "100.66.80.175"
    topologias_ssh_port: int = 22
    topologias_ssh_user: str = ""
    topologias_ssh_password: str = ""
    topologias_ssh_timeout_seconds: int = 15
    topologias_base_path: str = "/data/filebrowser/files/TOPOLOGIAS/TOPOLOGIAS OLTS"
    topologias_cache_path: str = "/data/AdminBOA/topologias_api_cache"
    topologias_local_dir: str = "data/topologias"
    topologias_public_base: str = "/api/olt/topologias/media"
    topologias_cache_ttl_horas: int = 24

    # Monitoreo CMTS INIT (CSV privado, fuera del document root de XAMPP).
    cmts_init_enabled: bool = False
    cmts_user: str = ""
    cmts_password: str = ""
    cmts_init_interval_seconds: int = 900
    cmts_init_max_workers: int = 1
    cmts_init_data_path: str = "data/cmts_inits"
    cmts_known_hosts: str = ""
    cmts_init_ssh_port: int = Field(default=22, ge=1, le=65535)
    cmts_init_connect_timeout_seconds: int = Field(default=30, ge=1, le=300)
    cmts_init_cli_timeout_seconds: int = Field(default=90, ge=1, le=600)
    cmts_init_retention_days: int = 90
    cmts_init_inventory_path: str = ""
    # Salto SSH exclusivo de CMTS INIT; credenciales privadas en .env.
    cmts_init_jump_enabled: bool = False
    cmts_init_jump_host: str = ""
    cmts_init_jump_port: int = Field(default=22, ge=1, le=65535)
    cmts_init_jump_user: str = ""
    cmts_init_jump_password: str = ""
    cmts_init_threshold_attention_max: int = 9
    cmts_init_threshold_risk_max: int = 49

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
