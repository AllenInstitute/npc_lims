class MissingCredentials(KeyError):
    """Raised when a required credential is not found in environment variables."""

    pass


class NoSessionInfo(ValueError):
    """Raised when a session is not found in the tracked-sessions database."""

    pass
