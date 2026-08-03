from sqlalchemy.types import Text, TypeDecorator


class EncryptedText(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        from app.core.security import encrypt_text

        return encrypt_text(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        from app.core.security import decrypt_text

        return decrypt_text(value)
