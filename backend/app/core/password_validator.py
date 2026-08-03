import re

from fastapi import HTTPException, status


class PasswordPolicy:
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    MIN_UPPERCASE = 1
    MIN_LOWERCASE = 1
    MIN_DIGITS = 1
    MIN_SPECIAL = 1
    SPECIAL_CHARS = r"[!@#$%^&*(),.?\":{}|<>]"
    COMMON_PASSWORDS = {
        "password",
        "12345678",
        "qwerty123",
        "letmein",
        "admin",
        "welcome",
        "monkey",
        "dragon",
        "login",
        "abc123",
        "password1",
        "123456789",
        "1234567890",
        "iloveyou",
    }

    @classmethod
    def validate(cls, password: str) -> list[str]:
        errors = []
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters")
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must be at most {cls.MAX_LENGTH} characters")
        if not re.search(r"[A-Z]", password):
            errors.append(f"Password must contain at least {cls.MIN_UPPERCASE} uppercase letter(s)")
        if not re.search(r"[a-z]", password):
            errors.append(f"Password must contain at least {cls.MIN_LOWERCASE} lowercase letter(s)")
        if not re.search(r"\d", password):
            errors.append(f"Password must contain at least {cls.MIN_DIGITS} digit(s)")
        if not re.search(cls.SPECIAL_CHARS, password):
            errors.append(f"Password must contain at least {cls.MIN_SPECIAL} special character(s)")
        if password.lower().strip() in cls.COMMON_PASSWORDS:
            errors.append("Password is too common — choose a stronger one")
        if re.match(r"^(.)\1+$", password):
            errors.append("Password cannot be a single repeated character")
        return errors

    @classmethod
    def validate_strict(cls, password: str):
        errors = cls.validate(password)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password does not meet policy requirements",
            )
