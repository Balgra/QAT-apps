from __future__ import annotations


class Address:
    def __init__(self, street: str, city: str, postal_code: str, country: str):
        self.street = street
        self.city = city
        self.postal_code = postal_code
        self.country = country

    def formatted(self) -> str:
        return f"{self.street}, {self.postal_code} {self.city}, {self.country}"


class CustomerProfile:
    def __init__(self, email: str, phone: str, address: Address):
        self.email = email
        self.phone = phone
        self.address = address

    def get_address(self) -> Address:
        return self.address


class Customer:
    def __init__(self, customer_id: str, full_name: str, profile: CustomerProfile):
        self.customer_id = customer_id
        self.full_name = full_name
        self.profile = profile

    def get_profile(self) -> CustomerProfile:
        return self.profile

