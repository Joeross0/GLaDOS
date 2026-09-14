from pydantic import BaseModel, Field


class PortalConfig(BaseModel):
    """Local HTTP portal so a remote web UI can talk to this GLaDOS instance."""

    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 9119
    pin: str = Field(default="9119", description="Shared PIN required on every request.")
