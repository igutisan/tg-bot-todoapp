"""
Manages the state of the bot.
"""

class BotState:
    def __init__(self):
        self.user_tokens: dict[int, str] = {} # Almacena el token por user_id
        self.waiting_for_email: dict[int, bool] = {} # Indica si estamos esperando un correo
        self.waiting_for_password: dict[int, bool] = {} # Indica si estamos esperando una contraseña
        self.temp_emails: dict[int, str] = {} # Almacena temporalmente el correo durante la autenticación

    def is_waiting_for_email(self, user_id: int) -> bool:
        return self.waiting_for_email.get(user_id, False)

    def is_waiting_for_password(self, user_id: int) -> bool:
        return self.waiting_for_password.get(user_id, False)

    def get_user_token(self, user_id: int) -> str | None:
        return self.user_tokens.get(user_id)

    def set_user_token(self, user_id: int, token: str):
        self.user_tokens[user_id] = token

    def set_waiting_for_email(self, user_id: int, status: bool):
        self.waiting_for_email[user_id] = status

    def set_waiting_for_password(self, user_id: int, status: bool):
        self.waiting_for_password[user_id] = status

    def get_temp_email(self, user_id: int) -> str | None:
        return self.temp_emails.get(user_id)

    def set_temp_email(self, user_id: int, email: str):
        self.temp_emails[user_id] = email

    def clear_user_auth_session(self, user_id: int):
        if user_id in self.waiting_for_email:
            del self.waiting_for_email[user_id]
        if user_id in self.waiting_for_password:
            del self.waiting_for_password[user_id]
        if user_id in self.temp_emails:
            del self.temp_emails[user_id]

bot_state = BotState()
