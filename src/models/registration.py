"""Registration data models matching the JSON schema in registration-schema.json."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BookingDay:
    day: str   # "monday", "wednesday", "thursday"
    type: str  # "indoor", "outdoor"


@dataclass
class Booking:
    playgroup_types: list = field(default_factory=list)   # ["indoor", "outdoor"]
    selected_days: list = field(default_factory=list)      # list[BookingDay]


@dataclass
class ChildInfo:
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None   # YYYY-MM-DD
    special_needs: Optional[str] = None   # text or "None"


@dataclass
class ParentGuardian:
    full_name: Optional[str] = None
    street_address: Optional[str] = None
    postal_code: Optional[str] = None     # 4-digit Swiss code
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class EmergencyContact:
    full_name: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class RegistrationData:
    child: ChildInfo = field(default_factory=ChildInfo)
    parent_guardian: ParentGuardian = field(default_factory=ParentGuardian)
    emergency_contact: EmergencyContact = field(default_factory=EmergencyContact)
    booking: Booking = field(default_factory=Booking)

    def is_complete(self) -> bool:
        """Return True when all required schema fields are present."""
        return (
            bool(self.child.full_name)
            and bool(self.child.date_of_birth)
            and self.child.special_needs is not None
            and bool(self.parent_guardian.full_name)
            and bool(self.parent_guardian.street_address)
            and bool(self.parent_guardian.postal_code)
            and bool(self.parent_guardian.city)
            and bool(self.parent_guardian.phone)
            and bool(self.parent_guardian.email)
            and bool(self.emergency_contact.full_name)
            and bool(self.emergency_contact.phone)
            and len(self.booking.playgroup_types) > 0
            and len(self.booking.selected_days) > 0
        )

    def to_dict(self) -> dict:
        return {
            "child": {
                "fullName": self.child.full_name,
                "dateOfBirth": self.child.date_of_birth,
                "specialNeeds": self.child.special_needs,
            },
            "parentGuardian": {
                "fullName": self.parent_guardian.full_name,
                "streetAddress": self.parent_guardian.street_address,
                "postalCode": self.parent_guardian.postal_code,
                "city": self.parent_guardian.city,
                "phone": self.parent_guardian.phone,
                "email": self.parent_guardian.email,
            },
            "emergencyContact": {
                "fullName": self.emergency_contact.full_name,
                "phone": self.emergency_contact.phone,
            },
            "booking": {
                "playgroupTypes": self.booking.playgroup_types,
                "selectedDays": [
                    {"day": d.day, "type": d.type}
                    for d in self.booking.selected_days
                ],
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegistrationData":
        reg = cls()
        if child := data.get("child", {}):
            reg.child = ChildInfo(
                full_name=child.get("fullName"),
                date_of_birth=child.get("dateOfBirth"),
                special_needs=child.get("specialNeeds"),
            )
        if parent := data.get("parentGuardian", {}):
            reg.parent_guardian = ParentGuardian(
                full_name=parent.get("fullName"),
                street_address=parent.get("streetAddress"),
                postal_code=parent.get("postalCode"),
                city=parent.get("city"),
                phone=parent.get("phone"),
                email=parent.get("email"),
            )
        if emergency := data.get("emergencyContact", {}):
            reg.emergency_contact = EmergencyContact(
                full_name=emergency.get("fullName"),
                phone=emergency.get("phone"),
            )
        if booking := data.get("booking", {}):
            reg.booking = Booking(
                playgroup_types=booking.get("playgroupTypes", []),
                selected_days=[
                    BookingDay(day=d["day"], type=d["type"])
                    for d in booking.get("selectedDays", [])
                ],
            )
        return reg
