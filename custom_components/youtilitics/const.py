"""Youtilitics constants."""
import logging

DOMAIN = "youtilitics"
BASE_URL = "https://youtilitics.com"
API_URL = BASE_URL + "/api/v1"
AUTHORIZE_URL = BASE_URL + "/authorize"
TOKEN_URL = BASE_URL + "/token"
SCOPES = ['email', 'download_data']

LOGGER = logging.getLogger(__package__)
