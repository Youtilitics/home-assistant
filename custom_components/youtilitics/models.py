"""Data classes for Youtilitics API responses."""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from homeassistant.util import dt as dt_util

@dataclass
class ServiceType:
    """Represents service types (e.g., Electricity, Gas, Water)."""
    electricity: Optional[int] = None
    gas: Optional[int] = None
    water: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'ServiceType':
        """Create from API response."""
        return cls(
            electricity=data.get("Electricity"),
            gas=data.get("Gas"),
            water=data.get("Water")
        )

@dataclass
class Utility:
    """Represents a utility provider."""
    id: str
    slug: str
    name: str
    services: List[int]
    url: Optional[str] = None
    url_help: Optional[str] = None
    logo: Optional[str] = None
    supports_api_sync: Optional[bool] = None
    supports_green_button: Optional[bool] = None
    gb_authorization_url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Utility':
        """Create from API response."""
        return cls(
            id=data["id"],
            slug=data["slug"],
            name=data["name"],
            services=data["services"],
            url=data.get("url"),
            url_help=data.get("url_help"),
            logo=data.get("logo"),
            supports_api_sync=data.get("supports_api_sync"),
            supports_green_button=data.get("supports_green_button"),
            gb_authorization_url=data.get("gb_authorization_url")
        )

@dataclass
class Service:
    """Represents a single service (e.g., electricity meter)."""
    id: str
    type: int
    remote_id: str
    last_sync_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Service':
        """Create from API response."""
        return cls(
            id=data["id"],
            type=data["type"],
            remote_id=data["remote_id"],
            last_sync_at=dt_util.parse_datetime(data["last_sync_at"]) if data.get("last_sync_at") else None,
            created_at=dt_util.parse_datetime(data["created_at"]) if data.get("created_at") else None,
            updated_at=dt_util.parse_datetime(data["updated_at"]) if data.get("updated_at") else None
        )

@dataclass
class Account:
    """Represents an account with associated services."""
    id: str
    utility: Utility
    services: List[Service]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Account':
        """Create from API response."""
        return cls(
            id=data["id"],
            utility=Utility.from_dict(data["utility"]),
            services=[Service.from_dict(s) for s in data["services"]],
            created_at=dt_util.parse_datetime(data["created_at"]) if data.get("created_at") else None,
            updated_at=dt_util.parse_datetime(data["updated_at"]) if data.get("updated_at") else None
        )

@dataclass
class Reading:
    """Represents a meter reading for a 15-minute interval."""
    id: int
    timestamp: datetime
    reading: float
    unit: str
    raw_reading: float
    raw_unit: str
    cost: float

    @classmethod
    def from_dict(cls, data: Dict) -> 'Reading':
        """Create from API response."""
        convert_to_cubic_meters = data["unit"] == "L" and data["raw_unit"].lower() == 'therm'
        return cls(
            id=data["id"],
            timestamp=dt_util.parse_datetime(data["timestamp"]),
            reading=data["reading"] / 1000 if convert_to_cubic_meters else data["reading"],
            unit='m³' if convert_to_cubic_meters else data["unit"],
            raw_reading=data["raw_reading"],
            raw_unit=data["raw_unit"],
            cost=data["cost"]
        )