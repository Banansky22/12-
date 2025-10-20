import os
import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получаем токен из переменных окружения
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не установлен!")
    exit(1)

print("✅ Токен успешно загружен!")
print("🚀 Запускаю упрощенную версию бота...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [KeyboardButton("📊 Полный анализ"), KeyboardButton("🎯 Выборочный анализ")],
        [KeyboardButton("📈 Анализ ликвидности"), KeyboardButton("💎 Анализ рентабельности")],
        [KeyboardButton("🏛️ Финансовая устойчивость"), KeyboardButton("📋 Сравнение с нормативами")],
        [KeyboardButton("🔮 Прогноз тенденций"), KeyboardButton("📄 Экспорт в TXT")],
        [KeyboardButton("ℹ️ Помощь"), KeyboardButton("📁 Загрузить файл")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🤖 **ФИНАНСОВЫЙ АНАЛИЗАТОР**\n\n"
        "🚀 Бот запущен и готов к работе!\n\n"
        "📁 Для начала работы загрузите Excel файл с отчетностью.\n\n"
        "💡 Используйте кнопки ниже для навигации:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
🤖 **ФИНАНСОВЫЙ АНАЛИЗАТОР - ПОМОЩЬ**

📊 **Доступные функции:**
• Полный финансовый анализ
• Выборочный анализ показателей  
• Анализ ликвидности
• Анализ рентабельности
• Анализ финансовой устойчивости
• Сравнение с отраслевыми нормативами
• Прогнозирование тенденций
• Экспорт отчетов в TXT

📁 **Как использовать:**
1. Загрузите Excel файл с финансовой отчетностью
2. Выберите нужный тип анализа
3. Получите детальный отчет

💡 **Формат файла:**
Excel файл с данными за несколько периодов
"""
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений с кнопок"""
    text = update.message.text
    
    if text == "📊 Полный анализ":
        await update.message.reply_text("🔍 Выполняю полный финансовый анализ...\n\n⚠️ Функция в разработке")
    elif text == "🎯 Выборочный анализ":
        await update.message.reply_text("🎯 Начинаю выборочный анализ...\n\n⚠️ Функция в разработке")
    elif text == "📈 Анализ ликвидности":
        await update.message.reply_text("💧 Анализирую ликвидность...\n\n⚠️ Функция в разработке")
    elif text == "💎 Анализ рентабельности":
        await update.message.reply_text("💎 Анализирую рентабельность...\n\n⚠️ Функция в разработке")
    elif text == "🏛️ Финансовая устойчивость":
        await update.message.reply_text("🏛️ Анализирую финансовую устойчивость...\n\n⚠️ Функция в разработке")
    elif text == "📋 Сравнение с нормативами":
        await update.message.reply_text("🏭 Сравниваю с нормативами...\n\n⚠️ Функция в разработке")
    elif text == "🔮 Прогноз тенденций":
        await update.message.reply_text("🔮 Строю прогноз...\n\n⚠️ Функция в разработке")
    elif text == "📄 Экспорт в TXT":
        await update.message.reply_text("📄 Создаю текстовый отчет...\n\n⚠️ Функция в разработке")
    elif text == "📁 Загрузить файл":
        await update.message.reply_text("📎 Пожалуйста, загрузите Excel файл с отчетностью\n\n⚠️ Функция в разработке")
    elif text == "ℹ️ Помощь":
        await help_command(update, context)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки файлов"""
    await update.message.reply_text("📎 Спасибо за файл! Обработка файлов временно недоступна.\n\n⚠️ Функция в разработке")

async def main():
    """Основная функция"""
    print("🔧 Инициализация бота...")
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот успешно запущен!")
    print("🌐 Режим: POLLING")
    print("🚀 Бот готов к работе!")
    
    # Запускаем бота
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
