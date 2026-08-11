from enum import Enum


class Environment(Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TESTING = "testing"


class ImagingTechnique(Enum):
    EO = "EO"
    IR = "IR"
    SAR = "SAR"
    NIR = "NIR"

    @property
    def hebrew(self):
        hebrew_enum = {
            ImagingTechnique.EO: "אופטי",
            ImagingTechnique.IR: "תרמי",
            ImagingTechnique.SAR: "סאר"
        }
        return hebrew_enum[self]

    def to_dict(self):
        return self.value

    @classmethod
    def from_dict(cls, value):
        return cls(value)
    

class UserPermissions(Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    ADMIN = "admin"

    @property
    def hebrew(self):
        hebrew_enum = {
            UserPermissions.VIEWER: "צפייה",
            UserPermissions.ANALYST: "מפענח",
            UserPermissions.DEVELOPER: "פיתוח",
            UserPermissions.OPERATOR: "מפעיל",
            UserPermissions.ADMIN: "אדמין"
        }
        return hebrew_enum[self]


class Sensor(Enum):
    SENTINEL = "Sentinel"
    TEST_SENSOR = "TestSensor"

    @property
    def hebrew(self):
        hebrew_enum = {
            Sensor.SENTINEL: "סנטינל",
            Sensor.TEST_SENSOR: "סנסור טסט"
        }
        return hebrew_enum[self]

    def to_dict(self):
        return self.value

    @classmethod
    def from_dict(cls, value):
        return cls(value)


ALLOWED_IMAGING_TECHNIQUES = {
    Sensor.SENTINEL: [ImagingTechnique.EO, ImagingTechnique.SAR],
    Sensor.TEST_SENSOR: [ImagingTechnique.EO]
}


for sensor in list(Sensor):
    assert sensor.hebrew
    assert sensor in ALLOWED_IMAGING_TECHNIQUES
