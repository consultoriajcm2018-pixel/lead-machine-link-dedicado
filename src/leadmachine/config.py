from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    app_name: str = 'LeadMachine Link Dedicado'
    database_url: str = 'sqlite:///./leadmachine.db'
    poll_interval_seconds: int = 30
    followup_24h_hours: int = 24
    followup_72h_hours: int = 72
    message_min_delay_seconds: int = 8
    message_max_delay_seconds: int = 32

    whatsapp_provider: str = 'evolution'
    evolution_api_url: str = ''
    evolution_api_key: str = ''
    evolution_instance: str = ''

    smtp_host: str = ''
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_pass: str = ''
    smtp_from: str = ''


settings = Settings()
