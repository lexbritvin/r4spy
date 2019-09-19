class UnsupportedDeviceException(Exception):
    """Exception when the discovered is not r4s or not implemented yet."""
    pass


class R4sUnexpectedResponse(Exception):
    """Exception when the response is not for the request.

    The error is raised when the counter or cmd differs from the last requested command.
    """
    pass


class R4sAuthFailed(Exception):
    """Exception when authentication failed.

    Happens when the key is not registered on a device yet.
    """
    pass
