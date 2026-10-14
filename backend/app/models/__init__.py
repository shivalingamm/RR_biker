"""Import all models so SQLAlchemy metadata is fully populated."""
from app.models.bike import (
    DOCUMENT_TYPES,
    FUEL_TYPES,
    MaintenanceRecord,
    Motorcycle,
    MotorcycleDocument,
    Reminder,
)
from app.models.catalogue import (
    Motorcycle3DAsset,
    MotorcycleCatalogue,
    MotorcycleSpecification,
)
from app.models.mechanic import (
    MechanicBooking,
    MechanicReview,
    MechanicService,
    MechanicShop,
)
from app.models.notification import Notification
from app.models.shop import (
    ORDER_STATUSES,
    Cart,
    CartItem,
    MotorcycleProductCompatibility,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    ProductImage,
    Seller,
)
from app.models.user import User, UserProfile

__all__ = [
    "DOCUMENT_TYPES",
    "FUEL_TYPES",
    "ORDER_STATUSES",
    "MaintenanceRecord",
    "Motorcycle",
    "MotorcycleDocument",
    "Reminder",
    "Motorcycle3DAsset",
    "MotorcycleCatalogue",
    "MotorcycleSpecification",
    "MechanicBooking",
    "MechanicReview",
    "MechanicService",
    "MechanicShop",
    "Notification",
    "Cart",
    "CartItem",
    "MotorcycleProductCompatibility",
    "Order",
    "OrderItem",
    "Product",
    "ProductCategory",
    "ProductImage",
    "Seller",
    "User",
    "UserProfile",
]
