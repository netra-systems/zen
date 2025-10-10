"""Runtime loader for telemetry credentials from environment variables."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account

#_ENV_B64 = "COMMUNITY_CREDENTIALS"
_ENV_B64 = "ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAibmV0cmEtdGVsZW1ldHJ5LXB1YmxpYyIsCiAgInByaXZhdGVfa2V5X2lkIjogImVjOWM4ZGNlZGZmMTUzNjM5YTUxOTcyMzc0MjYyNjkwNjZkNzAxYTQiLAogICJwcml2YXRlX2tleSI6ICItLS0tLUJFR0lOIFBSSVZBVEUgS0VZLS0tLS1cbk1JSUV2Z0lCQURBTkJna3Foa2lHOXcwQkFRRUZBQVNDQktnd2dnU2tBZ0VBQW9JQkFRREhUcmZFOHlQdUFCTDNcbk5aS3diZ1AwamRyaWRnY0UwMUlLMks1YkZ1bWFrUHVrRGxzV0dVaUswOXEyaVNYTWVUQmJPZDF0VjFoc3VJcUhcbnpQK0pZd0NTcVp4S0pIQS8yWUdVcERqeWhHRVd3QTNtS3laVXVUUS9yUTBUK20yV0cwdEMxUzBpQzB6U211cEpcbjBNeGhUUDRjKzYreEczSDVSWEF1YjdONmx6eFFWVnJSY3FHMTYydlF5SFA2OWIrd2RidTJHM0o5UkJVN1VUK1FcbkU2RHB2K01YaEp3MnRPdHZLbFBQT3BnWm9Sb0pmeXU1WlpzbHlJZCtzY3FhUTY5ZjBaSmpIRjlYQVdlT25mUTRcbmExbmV0LzJqRjZibWpuZmQ2MjhBODA5cEluTXJEL0FwZjJzUWJJdXJIYUI4am5uTEQ0eDMrbVhXRTgyMFJLNktcbjViZ0FQanNoQWdNQkFBRUNnZ0VBQmZERVZMWVlDakFkb0pscnpyOHF0a056cEpnV3Y3ZXlQSEZHcWgraDFSbndcbjdDd0Mza0xnNlFWbFFaZFBKWHZ2dTJwYlBaYnl3MlBST2ppN25adFNNU3pseEFaM3c0bHV2YkRTNHpTYnBiZFJcbityd3F3Mi8xUFJnaCtZaFhjNWZLNjVvcHd4Zmg0VzJkWWRlYnZlTXkrRWR1cmtsV2dYTG13L1dQbkkzdExlbzlcbjV1elZjbU42Qk04YkU3azFYK1M0RURBS0VRWlprUEdzTFQ4RXN4UmdWOWtnT1Zicm5VQ1Z0dXA1Q0NGbUR3U1Bcbmg0U25wMEsvTUp3b1U3NG4reTlFMXYxUXRnajE5TkhaNHJ2dFpnUlVaandHQy9Cc3ZkcE1PazArZTJEMlgvRk9cblZnc29xS2tDaklWUzRMcG5YSEpZbU5oajZWNHRXUnZ1OW1NTXhTL3FBUUtCZ1FEb3hZenlsdEZKL242ZEQvUHlcbnZLOFRaTHd5dFdCcjBXU3ZHU2VzM0JYRGZoKzBFbU4rRHpnZGdUb0ovbkhpazM5R21QM0tLN2htOFVvaFFHRy9cbkh0SFRuS0lBQlhrSU8yd2Z3N0h0V2pPTXRocHp2dFQxcmVEVHVjVk0wc2lCMHpjTldCMjFUamdQL3JYY2Q3NWVcbklERmNBN0hTbUJDLzB4bzk3aC8wV2YvOW9RS0JnUURiTWtnbjlVR2Y2SVRMNmxTcDdrYWJGL0NuaE4yU2VTMVdcbnd3R21iRThxTTU0UitDcVRUeHk2UHBRaFVSczlHM1VpVmQ1SXZWVDhuT095ZVBZVFJEbnFCYjJ4S214SFRodlZcbnVQcTgwQXB3anBMbzh6VkFDSy9iVFVjSmlKVGFBdXFHaXI1Ykc4YUlldVpIc0pLeWJ1NmhoNkhXMldwWXVVV1BcbkZ3TTl4elpOZ1FLQmdRQzg5dHJVZVJFUVE3VGZwbnJBM09JNEdUZ2E1bG1QVFo2eDh2YmRncEY4Y2FBbEhDUitcbnlyWWdaYThMTysrU0kzRllpNHpFR2pnS0FlblBFcWdIY21xZW9uSjFGL3hJYll6NlFIRHFJYWJsblZQZUVOWnJcblY2dkQxZlRReC9FVVM3Wk9jL0V5Slh5bnAzeFZyVFB5ejZtaWJERm9xQ0E0eVpSdElDbjZ3VEZxNFFLQmdFWFJcbnAxQXErOE0rb2dYOTF3ZmxvTkhIOTF5MG9vc0VWQis5cjZuZDkvMWVRYXhCbXZZZkRleDVBRi80WUsrL0xqbElcbmxxd2V1cEpZT3VMZlNxcHFZZlFiN2djZmx5dkRRblI2SGt2RURIODd1cW0reGlobVcvV0RrT3dGZUR4VkQzVFpcbmZyYXdpelZ2eUNmdm8xcDRvVVFNV3MxL3BUTXJtRzl5aWhMRWdKU0JBb0dCQU1GWm50ZUtUUDZrVVdrVmpOcndcbmUvQzBDbjJ6dk1YNXVnZURkS1FWNkwrY25mRWlRSzdzZ3R5eFp5ek5kMC82QXJ0YnBrcS9wcVlaYXpwVzVFMkxcbkxVMUF3MmdHT25GRlh2ZXg4aXpOZXViMGdvUVE4d3BtL3lrMVNVekR6VTV1dCtPbVFFRmpsbUYrNDkza0ZYcC9cbnc1MWh2WjVVL2loL1NYbjN6cjdEWE5QYlxuLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLVxuIiwKICAiY2xpZW50X2VtYWlsIjogInplbi1jb21tdW5pdHktdGVsZW1ldHJ5QG5ldHJhLXRlbGVtZXRyeS1wdWJsaWMuaWFtLmdzZXJ2aWNlYWNjb3VudC5jb20iLAogICJjbGllbnRfaWQiOiAiMTE0NzAwMDA0NzA1MDUxODg5NTY4IiwKICAiYXV0aF91cmkiOiAiaHR0cHM6Ly9hY2NvdW50cy5nb29nbGUuY29tL28vb2F1dGgyL2F1dGgiLAogICJ0b2tlbl91cmkiOiAiaHR0cHM6Ly9vYXV0aDIuZ29vZ2xlYXBpcy5jb20vdG9rZW4iLAogICJhdXRoX3Byb3ZpZGVyX3g1MDlfY2VydF91cmwiOiAiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vb2F1dGgyL3YxL2NlcnRzIiwKICAiY2xpZW50X3g1MDlfY2VydF91cmwiOiAiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vcm9ib3QvdjEvbWV0YWRhdGEveDUwOS96ZW4tY29tbXVuaXR5LXRlbGVtZXRyeSU0MG5ldHJhLXRlbGVtZXRyeS1wdWJsaWMuaWFtLmdzZXJ2aWNlYWNjb3VudC5jb20iLAogICJ1bml2ZXJzZV9kb21haW4iOiAiZ29vZ2xlYXBpcy5jb20iCn0K%"
_ENV_PATH = "ZEN_COMMUNITY_TELEMETRY_FILE"
_ENV_PROJECT = "ZEN_COMMUNITY_TELEMETRY_PROJECT"
_DEFAULT_PROJECT = "netra-telemetry-public"


def _load_service_account_dict() -> Optional[dict]:
    """Load service account JSON from environment variables."""
    encoded = os.getenv(_ENV_B64)
    if encoded:
        try:
            raw = base64.b64decode(encoded)
            return json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            return None

    path = os.getenv(_ENV_PATH)
    if path:
        candidate = Path(path).expanduser()
        if candidate.exists():
            try:
                return json.loads(candidate.read_text())
            except json.JSONDecodeError:
                return None
    return None


def get_embedded_credentials():
    """Return service account credentials or None."""
    info = _load_service_account_dict()
    if not info:
        return None
    try:
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/trace.append"],
        )
    except Exception:
        return None


def get_project_id() -> str:
    """Return GCP project ID for telemetry."""
    info = _load_service_account_dict()
    if info and "project_id" in info:
        return info["project_id"]
    return os.getenv(_ENV_PROJECT, _DEFAULT_PROJECT)
