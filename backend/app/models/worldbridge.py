"""MEMBRA CompanyOS — WorldBridge models."""
from sqlalchemy import Column, String, Text, JSON, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, ULIDMixin


class WorldAsset(Base, ULIDMixin):
    """A real-world asset connected to MEMBRA."""

    asset_type = Column(String(64), nullable=False, index=True)
    # apartment, vehicle, window, wearable, tool, storage, person, vendor, route
    asset_category = Column(String(64), nullable=False, index=True)
    # ad_inventory, rental_sku, delivery_capacity, task_supply, media_surface, device
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_wallet = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="active", index=True)  # active, inactive, pending_verification, suspended
    location_json = Column(JSON, default=dict)  # address, gps, zone
    capabilities_json = Column(JSON, default=dict)  # what the asset can do
    pricing_json = Column(JSON, default=dict)  # rates per unit / hour / action
    media_json = Column(JSON, default=dict)  # photos, videos, 3d scans
    proof_hash = Column(String(128))
    metadata_json = Column(JSON, default=dict)

    listings = relationship("AssetListing", back_populates="asset", lazy="selectin")


class AssetListing(Base, ULIDMixin):
    """A marketplace listing for a WorldBridge asset."""

    asset_id = Column(String(26), ForeignKey("worldassets.id"), index=True)
    listing_type = Column(String(64), nullable=False, index=True)
    # ad_space, rental, delivery, task, media, sale
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(24, 8), default=0)
    currency = Column(String(16), default="USDC")
    status = Column(String(32), default="draft", index=True)  # draft, pending_approval, active, paused, sold, expired
    availability_json = Column(JSON, default=dict)
    requirements_json = Column(JSON, default=dict)
    metadata_json = Column(JSON, default=dict)

    asset = relationship("WorldAsset", back_populates="listings")
