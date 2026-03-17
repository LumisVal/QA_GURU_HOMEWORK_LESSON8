from dataclasses import dataclass
from enum import StrEnum
from datetime import datetime
from copy import deepcopy

# Перечисление статусов письма
class Status(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SENT = "sent"
    FAILED = "failed"
    INVALID = "invalid"


# Класс, представляющий email-адрес
class EmailAddress:
    def __init__(self, address: str):
        self.address = address          # сохраняем исходный адрес
        self.normalize()                 # нормализуем
        self.validate()                   # проверяем корректность

    def normalize(self):
        self.address = self.address.strip().lower()

    def validate(self):
        if '@' not in self.address or not self.address.endswith(('.com', '.ru', '.net')):
            raise ValueError("Некорректный email")

    @property
    def masked(self):
        local, domain = self.address.split('@', 1)
        return local[:2] + "***@" + domain


# Класс письма (dataclass)
@dataclass
class Email:
    subject: str
    body: str
    sender: EmailAddress
    recipients: list[EmailAddress]
    date: datetime | None = None
    short_body: str | None = None
    status: Status = Status.DRAFT

    def __post_init__(self):
        # Преобразуем отправителя, если передана строка
        if isinstance(self.sender, str):
            self.sender = EmailAddress(self.sender)
        # Если получатели не список, делаем список
        if not isinstance(self.recipients, list):
            self.recipients = [self.recipients]
        # Каждый элемент списка получателей приводим к EmailAddress
        self.recipients = [
            EmailAddress(addr) if isinstance(addr, str) else addr
            for addr in self.recipients
        ]

    def add_short_body(self):
        if self.body and len(self.body) > 50:
            self.short_body = self.body[:50] + "..."
        else:
            self.short_body = self.body

    def prepare(self):
        # Очистка от пробелов
        self.subject = self.subject.strip() if self.subject else ""
        self.body = self.body.strip() if self.body else ""

        # Проверка заполненности обязательных полей
        if (self.subject and self.body and self.sender and self.recipients):
            self.status = Status.READY
        else:
            self.status = Status.INVALID

        # Формируем короткое тело
        self.add_short_body()

    def __repr__(self):
        recipients_str = ', '.join(addr.masked for addr in self.recipients)
        return (f"Email(status={self.status.value}, subject={self.subject!r}, "
                f"sender={self.sender.masked}, recipients=[{recipients_str}])")


# Базовый сервис отправки
class EmailService:
    def send_email(self, email: Email) -> list[Email]:
        sent_emails = []
        for recipient in email.recipients:
            # Глубокая копия исходного письма
            new_email = deepcopy(email)
            # Заменяем получателей на одного конкретного
            new_email.recipients = [recipient]

            # Определяем статус и дату
            if email.status == Status.READY:
                new_email.status = Status.SENT
                new_email.date = datetime.now()
            else:
                new_email.status = Status.FAILED
                # date остаётся None

            sent_emails.append(new_email)
        return sent_emails


# Сервис отправки с логированием
class LoggingEmailService(EmailService):
    def send_email(self, email: Email) -> list[Email]:
        # Вызываем родительский метод
        result = super().send_email(email)

        # Запись в лог
        with open('send.log', 'a', encoding='utf-8') as log_file:
            log_entry = (
                f"{datetime.now().isoformat()} | "
                f"Тема: {email.subject} | "
                f"Отправитель: {email.sender.masked} | "
                f"Получатели: {', '.join(addr.masked for addr in email.recipients)} | "
                f"Статус отправки: {email.status.value}\n"
            )
            log_file.write(log_entry)

        return result


# Пример использования (выполняется только при запуске файла)
if __name__ == "__main__":
    # Создаём письмо со смешанными типами получателей
    email = Email(
        subject="  Важное сообщение  ",
        body="Привет! Это тестовое письмо с достаточно длинным текстом, чтобы проверить сокращение.",
        sender="  admin@site.ru  ",
        recipients=["user1@gmail.com", EmailAddress("user2@yandex.ru")]
    )

    print("До подготовки:")
    print(email)
    print(f"Статус: {email.status}\n")

    # Подготавливаем письмо
    email.prepare()
    print("После подготовки:")
    print(email)
    print(f"Короткий текст: {email.short_body}\n")

    # Отправка через обычный сервис
    service = EmailService()
    sent_emails = service.send_email(email)
    print("Отправленные письма (EmailService):")
    for e in sent_emails:
        print(f"  -> {e.recipients[0].masked}, статус {e.status}, дата {e.date}")

    # Отправка через логирующий сервис
    log_service = LoggingEmailService()
    log_service.send_email(email)
    print("\nЛогирование выполнено. Проверьте файл send.log")