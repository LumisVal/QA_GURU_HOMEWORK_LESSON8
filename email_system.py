from dataclasses import dataclass
from enum import StrEnum
from datetime import datetime
from copy import deepcopy
import unittest
import os

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
        # Удаляет пробелы по краям и приводит к нижнему регистру
        self.address = self.address.strip().lower()

    def validate(self):
        # Проверяет наличие @, непустую локальную часть и окончание .com/.ru/.net
        if '@' not in self.address:
            raise ValueError("Некорректный email")
        local, domain = self.address.split('@', 1)
        if not local or not domain.endswith(('.com', '.ru', '.net')):
            raise ValueError("Некорректный email")

    @property
    def masked(self):
        # Возвращает маскированный адрес (первые два символа локальной части + ***@домен)
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
        # Формирует сокращённую версию тела письма (первые 50 символов + '...' если длиннее)
        if self.body and len(self.body) > 50:
            self.short_body = self.body[:50] + "..."
        else:
            self.short_body = self.body

    def prepare(self):
        # Подготавливает письмо к отправке: очищает поля, проверяет валидность,
        # устанавливает статус и создаёт короткое тело.
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
        # Представление письма с маскированными адресами
        recipients_str = ', '.join(addr.masked for addr in self.recipients)
        return (f"Email(status={self.status.value}, subject={self.subject!r}, "
                f"sender={self.sender.masked}, recipients=[{recipients_str}])")


# Базовый сервис отправки
class EmailService:
    def send_email(self, email: Email) -> list[Email]:
        # Имитирует отправку письма каждому получателю.
        # Возвращает список новых писем (по одному на получателя).
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
        # Отправляет письмо и записывает информацию в файл send.log
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


# Автотесты для самопроверки
class TestEmailSystem(unittest.TestCase):
    # Автотесты для проверки работы всех компонентов системы

    def test_email_address_normalization(self):
        # EmailAddress: нормализация адреса
        addr = EmailAddress("  USER@MAIL.RU  ")
        self.assertEqual(addr.address, "user@mail.ru")

    def test_email_address_validation_valid(self):
        # EmailAddress: валидация корректных адресов
        valid_addresses = ["user@example.com", "test@mail.ru", "info@domain.net"]
        for addr_str in valid_addresses:
            addr = EmailAddress(addr_str)
            self.assertEqual(addr.address, addr_str)  # проверяем, что исключение не выброшено

    def test_email_address_validation_invalid(self):
        # EmailAddress: невалидные адреса вызывают ValueError
        invalid_addresses = ["usermail.ru", "user@", "@domain.com", "user@domain.org", "user@domain.ua"]
        for addr_str in invalid_addresses:
            with self.assertRaises(ValueError):
                EmailAddress(addr_str)

    def test_email_address_masked(self):
        # EmailAddress: свойство masked работает корректно
        addr = EmailAddress("john.doe@gmail.com")
        self.assertEqual(addr.masked, "jo***@gmail.com")
        # Короткая локальная часть
        addr2 = EmailAddress("a@mail.ru")
        self.assertEqual(addr2.masked, "a***@mail.ru")

    def test_email_post_init_converts_strings(self):
        # Email: __post_init__ преобразует строковые адреса в EmailAddress и recipients в список
        email = Email(
            subject="Test",
            body="Body",
            sender="sender@mail.ru",
            recipients="recipient@mail.ru"
        )
        self.assertIsInstance(email.sender, EmailAddress)
        self.assertIsInstance(email.recipients, list)
        self.assertEqual(len(email.recipients), 1)
        self.assertIsInstance(email.recipients[0], EmailAddress)

    def test_email_prepare_ready(self):
        # Email: prepare при заполненных полях делает статус READY и добавляет short_body
        email = Email(
            subject="  Subject  ",
            body="This is a very long body text that exceeds fifty characters so we can test the shortening logic.",
            sender="sender@mail.ru",
            recipients=["rec1@mail.ru", "rec2@mail.ru"]
        )
        email.prepare()
        self.assertEqual(email.status, Status.READY)
        self.assertEqual(email.subject, "Subject")
        self.assertEqual(email.body, email.body.strip())
        self.assertIsNotNone(email.short_body)
        self.assertTrue(len(email.short_body) <= 53)  # 50 + "..."

    def test_email_prepare_invalid_missing_subject(self):
        # Email: prepare делает статус INVALID, если тема пустая
        email = Email(
            subject="  ",
            body="Body",
            sender="sender@mail.ru",
            recipients=["rec@mail.ru"]
        )
        email.prepare()
        self.assertEqual(email.status, Status.INVALID)

    def test_email_prepare_invalid_missing_body(self):
        # Email: prepare делает статус INVALID, если тело пустое
        email = Email(
            subject="Subject",
            body="",
            sender="sender@mail.ru",
            recipients=["rec@mail.ru"]
        )
        email.prepare()
        self.assertEqual(email.status, Status.INVALID)

    def test_email_repr_contains_masked_addresses(self):
        # Email: __repr__ использует маскированные адреса
        email = Email(
            subject="Test",
            body="Body",
            sender="sender@mail.ru",
            recipients=["rec1@mail.ru", "rec2@yandex.ru"]
        )
        repr_str = repr(email)
        self.assertIn("se***@mail.ru", repr_str)   # маскированный отправитель
        self.assertIn("re***@mail.ru", repr_str)   # маскированный получатель
        self.assertIn("re***@yandex.ru", repr_str)

    def test_email_service_send_ready(self):
        # EmailService: отправка готового письма создаёт копии со статусом SENT и датой
        email = Email(
            subject="Ready",
            body="Body",
            sender="sender@mail.ru",
            recipients=["rec1@mail.ru", "rec2@mail.ru"]
        )
        email.prepare()  # статус READY
        service = EmailService()
        sent = service.send_email(email)

        self.assertEqual(len(sent), 2)
        for e in sent:
            self.assertEqual(e.status, Status.SENT)
            self.assertIsNotNone(e.date)

        # Проверяем, что оригинал не изменился
        self.assertEqual(email.status, Status.READY)
        # Сравниваем адреса, а не объекты EmailAddress
        self.assertEqual(
            [addr.address for addr in email.recipients],
            ["rec1@mail.ru", "rec2@mail.ru"]
        )
        # Каждое отправленное письмо должно иметь одного получателя
        self.assertEqual(len(sent[0].recipients), 1)
        self.assertEqual(sent[0].recipients[0].address, "rec1@mail.ru")
        self.assertEqual(sent[1].recipients[0].address, "rec2@mail.ru")

    def test_email_service_send_not_ready(self):
        # EmailService: отправка неготового письма создаёт копии со статусом FAILED и без даты
        email = Email(
            subject="Not ready",
            body="",
            sender="sender@mail.ru",
            recipients=["rec1@mail.ru"]
        )
        # Не вызываем prepare, статус DRAFT
        service = EmailService()
        sent = service.send_email(email)

        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0].status, Status.FAILED)
        self.assertIsNone(sent[0].date)

    def test_logging_email_service_creates_log(self):
        # LoggingEmailService: записывает информацию в файл send.log
        email = Email(
            subject="Log test",
            body="Body",
            sender="sender@mail.ru",
            recipients=["rec@mail.ru"]
        )
        email.prepare()
        log_file = "send.log"
        # Удаляем лог-файл перед тестом, если существует
        if os.path.exists(log_file):
            os.remove(log_file)

        service = LoggingEmailService()
        service.send_email(email)

        # Проверяем, что файл создан
        self.assertTrue(os.path.exists(log_file))
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("Log test", content)
        self.assertIn("se***@mail.ru", content)
        self.assertIn("re***@mail.ru", content)
        self.assertIn(Status.READY.value, content)

        # Удаляем файл после теста
        os.remove(log_file)


if __name__ == "__main__":
    unittest.main()