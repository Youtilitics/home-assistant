"""Youtilitics constants."""
import logging

DOMAIN = "youtilitics"
API_URL = "https://youtilitics.com/api/v1"
AUTHORIZE_URL = "https://youtilitics.com/authorize"
TOKEN_URL = "https://youtilitics.com/token"
SCOPES = ['email', 'download_data']

LOGGER = logging.getLogger(__package__)
