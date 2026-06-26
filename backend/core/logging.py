import logging
from collections.abc import Iterable


class SecretFilter(logging.Filter):
    """Removes known secrets from log records before they are emitted."""

    def __init__(self, secrets: Iterable[str | None]):
        super().__init__()
        self.secrets = [value for value in secrets if value]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self.secrets:
            message = message.replace(secret, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


def configure_logging(secrets: Iterable[str | None]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    root = logging.getLogger()
    root.addFilter(SecretFilter(secrets))
