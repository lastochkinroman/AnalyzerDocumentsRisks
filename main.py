import os
import tempfile
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from langchain_gigachat import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage
from PyPDF2 import PdfReader
from docx import Document
import ssl

load_dotenv()
ssl._create_default_https_context = ssl._create_unverified_context

giga = GigaChat(
    scope='GIGACHAT_API_CORP',
    auth_url="https://sm-auth-sd.prom-88-89-apps.ocp-geo.ocp.sigma.sbrf.ru/api/v2/oauth",
    credentials=os.getenv('GIGACHAT_TOKEN'),
    model='GigaChat-2-Max'
)

DOCUMENT_ANALYSIS_PROMPT = """
Вы эксперт по анализу документов. Проанализируйте предоставленный текст документа на предмет потенциальных рисков и проблем.

Найдите следующие типы рисков в документе:

Начните с общей сводки по документу

1. ФИНАНСОВЫЕ РИСКИ:
- Неясные условия оплаты или платежей
- Отсутствие штрафов за несоблюдение
- Неоднозначные структуры затрат

2. ЮРИДИЧЕСКИЕ РИСКИ:
- Ссылки на внешние документы, которые не приложены
- Неоднозначная юридическая терминология
- Устаревшие или неуказанные нормативные акты

3. ОПЕРАЦИОННЫЕ РИСКИ:
- Неясные обязанности или сроки
- Отсутствие механизмов разрешения споров
- Недостаточный мониторинг или требования к отчетности

Формат ответа для каждого найденного риска:
- Тип риска: [Финансовый/Юридический/Операционный]
- Цитата: "точная цитата из текста"
- Описание риска: краткое объяснение опасности
- Рекомендация: как исправить

Отвечайте только по существу, без вводных фраз.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        '👋 Привет! Я бот для анализа документов на предмет потенциальных рисков.\n\n'
        '📄 Отправьте мне документ в формате PDF или Word (DOCX), и я проверю его на:\n'
        '1. Финансовые риски (неясные условия оплаты)\n'
        '2. Юридические риски (отсутствующие ссылки)\n'
        '3. Операционные риски (неясные обязанности)\n\n'
        'Просто загрузите файл, и я предоставлю подробный анализ!'
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    file_name = document.file_name
    file_extension = os.path.splitext(file_name)[1].lower()

    if file_extension not in ['.pdf', '.docx']:
        await update.message.reply_text('❌ Пожалуйста, загрузите файл в формате PDF или Word (DOCX)')
        return

    try:
        await update.message.reply_text('🔍 Анализирую документ... Это может занять 1-2 минуты')

        file = await context.bot.get_file(document.file_id)
        file_url = file.file_path

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_path = temp_file.name
            response = requests.get(file_url)
            temp_file.write(response.content)

        if file_extension == '.pdf':
            reader = PdfReader(temp_path)
            text = ''
            for page in reader.pages:
                text += page.extract_text() + '\n'
        else:
            doc = Document(temp_path)
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])

        os.unlink(temp_path)

        response = giga.invoke([
            SystemMessage(content=DOCUMENT_ANALYSIS_PROMPT),
            HumanMessage(content=f"Проанализируйте этот документ:\n\n{text}")
        ])

        if 'не найдено' in response.content.lower() or 'не обнаружено' in response.content.lower():
            await update.message.reply_text('✅ В документе не найдено значительных рисков по проверяемым категориям')
        else:
            await update.message.reply_markdown(f'⚠️ *Найденные риски в документе*:\n\n{response.content}')

    except Exception as error:
        print(f'Error: {error}')
        await update.message.reply_text('❌ Произошла ошибка при анализе документа. Попробуйте еще раз.')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Пожалуйста, загрузите документ в формате PDF или Word (DOCX) для анализа')

def main() -> None:
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling()

if __name__ == '__main__':
    main()
