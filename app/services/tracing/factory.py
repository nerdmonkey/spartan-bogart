from functools import lru_cache
from typing import Optional

from app.helpers.environment import env

from .base import BaseTracer
from .cloud import CloudTracer
from .local import LocalTracer


class TracerFactory:
    @staticmethod
    def create_tracer(
        service_name: Optional[str] = None, tracer_type: Optional[str] = None
    ) -> BaseTracer:
        """
        Create a tracer instance.

        Priority for selecting tracer:
        1. Explicit tracer_type parameter (if provided)
        2. TRACER_TYPE environment variable (via app.helpers.environment.env)
        3. Auto-detect: local -> AWS/cloud

        tracer_type values accepted (case-insensitive): 'local', 'cloud', 'aws'
        """
        # 1) parameter override
        chosen = None
        if tracer_type:
            chosen = tracer_type.lower()
        else:
            # 2) env override
            chosen = (env("TRACER_TYPE", None) or "").lower()

        service = service_name or env("APP_NAME", "default-service")
        service = validate_service_name(service)

        if chosen:
            if chosen in ("local",):
                return LocalTracer(service)
            if chosen in ("cloud", "aws", "xray"):
                return CloudTracer(service)
            # unknown explicit value -> raise to surface misconfiguration
            raise ValueError(f"Unknown tracer_type override: {tracer_type!r}")

        environment = str(env("APP_ENVIRONMENT", "local")).lower()
        if environment == "local":
            return LocalTracer(service)

        return CloudTracer(service)


def validate_service_name(service_name):
    """Validate service name"""
    if not service_name or not service_name.strip():
        raise ValueError("Invalid service name")
    return service_name.strip()


@lru_cache
def get_tracer(service_name: Optional[str] = None) -> BaseTracer:
    return TracerFactory.create_tracer(service_name)
