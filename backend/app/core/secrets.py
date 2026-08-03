import os
import json
import logging
from typing import Optional

logger = logging.getLogger("sentinel.secrets")


class SecretsProvider:
    def get(self, key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    def get_json(self, key: str, default: dict = None) -> dict:
        val = os.environ.get(key, "")
        if val:
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                pass
        return default or {}


class VaultSecretsProvider(SecretsProvider):
    def __init__(self, vault_url: str = "", vault_token: str = ""):
        self.vault_url = vault_url
        self.vault_token = vault_token

    def get(self, key: str, default: str = "") -> str:
        if not self.vault_url:
            return super().get(key, default)
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.vault_url}/v1/secret/data/sentinel/{key}",
                headers={"X-Vault-Token": self.vault_token},
            )
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())
            return data.get("data", {}).get("data", {}).get("value", default)
        except Exception as e:
            logger.warning("Vault fetch failed for %s: %s, falling back to env", key, e)
            return super().get(key, default)


class AWSSecretsManager(SecretsProvider):
    def __init__(self, region: str = "us-east-1"):
        self.region = region

    def get(self, key: str, default: str = "") -> str:
        try:
            import boto3
            client = boto3.client("secretsmanager", region_name=self.region)
            resp = client.get_secret_value(SecretId=f"sentinel/{key}")
            return resp.get("SecretString", default)
        except Exception as e:
            logger.warning("AWS SecretsManager fetch failed for %s: %s", key, e)
            return super().get(key, default)


secrets = SecretsProvider()
