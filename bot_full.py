import os
import logging
import asyncio
import pandas as pd
import io
import numpy as np
from datetime import datetime
import re
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

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
print("🚀 БУХГАЛТЕРСКИЙ АНАЛИЗАТОР ЗАПУЩЕН...")

# Создаем папку для временных файлов
os.makedirs("temp_files", exist_ok=True)

# Состояния для ConversationHandler
SELECT_INDICATORS, SELECT_INDUSTRY = range(2)

# Словари и константы из вашего оригинального кода
BALANCE_ITEMS = {
    # АКТИВЫ
    'внеоборотные активы': ['внеоборотные', 'non-current', 'основные средства', 'нематериальные', 'нма'],
    'основные средства': ['основные средства', 'fixed assets', 'property plant', 'основной', 'ося'],
    'нематериальные активы': ['нематериальные', 'intangible', 'нма'],
    'запасы': ['запасы', 'inventories', 'inventory', 'товарно-материальные', 'тмц'],
    'дебиторская задолженность': ['дебиторская', 'accounts receivable', 'receivables', 'дебитор'],
    'денежные средства': ['денежные средства', 'cash', 'cash and equivalents', 'деньги', 'касса', 'расчетный счет'],
    'оборотные активы': ['оборотные активы', 'current assets', 'оборотные'],
    'активы всего': ['активы', 'актив всего', 'total assets', 'итого активы', 'баланс актив'],
    
    # ПАССИВЫ
    'капитал': ['капитал', 'собственный капитал', 'equity', 'share capital', 'уставный'],
    'уставный капитал': ['уставный капитал', 'authorized capital', 'уставной'],
    'нераспределенная прибыль': ['нераспределенная прибыль', 'retained earnings', 'прибыль отчетного года'],
    'долгосрочные обязательства': ['долгосрочные обязательства', 'long-term liabilities', 'долгосрочные'],
    'краткосрочные обязательства': ['краткосрочные обязательства', 'short-term liabilities', 'current liabilities', 'краткосрочные'],
    'кредиты займы': ['кредиты', 'займы', 'loans', 'borrowings', 'кредит'],
    'кредиторская задолженность': ['кредиторская задолженность', 'accounts payable', 'кредиторская'],
    'обязательства всего': ['обязательства', 'пассив всего', 'total liabilities', 'итого пассивы', 'баланс пассив'],
    
    # ОФР
    'выручка': ['выручка', 'revenue', 'sales', 'доход', 'объем продаж'],
    'себестоимость': ['себестоимость', 'cost of sales', 'cost', 'себестоимость продаж'],
    'валовая прибыль': ['валовая прибыль', 'убыток', 'gross profit', 'прибыль валовая'],
    'операционные расходы': ['операционные расходы', 'operating expenses', 'коммерческие расходы', 'управленческие расходы'],
    'прибыль до налогообложения': ['прибыль до налогообложения', 'profit before tax', 'прибыль до налога'],
    'чистая прибыль': ['чистая прибыль', 'net profit', 'net income', 'прибыль чистая']
}

INDUSTRY_STANDARDS = {
    'retail': {
        'name': 'Розничная торговля',
        'standards': {
            'Коэффициент текущей ликвидности': (1.2, 2.0),
            'Коэффициент абсолютной ликвидности': (0.2, 0.5),
            'Рентабельность продаж (ROS)': (3.0, 8.0),
            'Рентабельность активов (ROA)': (5.0, 12.0),
            'Коэффициент автономии': (0.3, 0.6),
            'Оборачиваемость активов': (1.5, 3.0)
        }
    },
    'manufacturing': {
        'name': 'Производство',
        'standards': {
            'Коэффициент текущей ликвидности': (1.5, 2.5),
            'Коэффициент абсолютной ликвидности': (0.1, 0.3),
            'Рентабельность продаж (ROS)': (8.0, 15.0),
            'Рентабельность активов (ROA)': (6.0, 14.0),
            'Коэффициент автономии': (0.4, 0.7),
            'Оборачиваемость активов': (0.8, 1.5)
        }
    },
    'services': {
        'name': 'Сфера услуг',
        'standards': {
            'Коэффициент текущей ликвидности': (1.0, 1.8),
            'Коэффициент абсолютной ликвидности': (0.3, 0.6),
            'Рентабельность продаж (ROS)': (10.0, 20.0),
            'Рентабельность активов (ROA)': (8.0, 18.0),
            'Коэффициент автономии': (0.4, 0.7),
            'Оборачиваемость активов': (1.0, 2.5)
        }
    }
}

INDICATOR_GROUPS = {
    'Выручка и прибыль': ['выручка', 'чистая прибыль', 'валовая прибыль', 'прибыль до налогообложения'],
    'Активы и обязательства': ['активы всего', 'оборотные активы', 'внеоборотные активы', 'капитал', 'краткосрочные обязательства'],
    'Ликвидность': ['денежные средства', 'дебиторская задолженность', 'запасы'],
    'Рентабельность': ['выручка', 'чистая прибыль', 'активы всего', 'капитал'],
    'Финансовая устойчивость': ['капитал', 'обязательства всего', 'активы всего'],
    'Оборачиваемость': ['выручка', 'запасы', 'дебиторская задолженность', 'активы всего']
}

# === ОСНОВНЫЕ ФУНКЦИИ АНАЛИЗА ===

def read_excel_file(file_bytes, file_name):
    """Читает Excel файл с поддержкой разных форматов"""
    try:
        if file_name.endswith('.xls'):
            return pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')
        else:
            return pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
    except Exception as e:
        try:
            return pd.read_excel(io.BytesIO(file_bytes))
        except Exception as e2:
            raise Exception(f"Не удалось прочитать файл: {str(e2)}")

def detect_periods(df):
    """Определяет периоды в столбцах DataFrame"""
    periods = []
    
    for col in df.columns:
        col_str = str(col).lower().strip()
        
        # Поиск дат в различных форматах
        date_patterns = [
            r'\d{2}.\d{2}.\d{4}',  # 31.12.2023
            r'\d{4}-\d{2}-\d{2}',   # 2023-12-31
            r'\d{2}/\d{2}/\d{4}',   # 31/12/2023
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, col_str)
            if matches:
                try:
                    date_str = matches[0]
                    if '.' in date_str and len(date_str.split('.')[0]) == 2:
                        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                    elif '-' in date_str:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    elif '/' in date_str:
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                    
                    periods.append({
                        'column': col,
                        'date': date_obj,
                        'formatted': date_obj.strftime('%d.%m.%Y'),
                        'year': date_obj.year
                    })
                    break
                except:
                    continue
        
        # Поиск периодов в текстовом формате
        period_keywords = {
            'за 2024': '2024',
            'за 2023': '2023',
            'за 2022': '2022',
        }
        
        for keyword, year in period_keywords.items():
            if keyword in col_str:
                periods.append({
                    'column': col,
                    'date': datetime(int(year), 12, 31),
                    'formatted': f"31.12.{year}",
                    'year': int(year)
                })
                break
    
    # Сортируем периоды по году
    periods.sort(key=lambda x: x['year'])
    return periods

def find_balance_item(column_name, df_columns):
    """Находит соответствие столбца статьям баланса"""
    column_name = str(column_name).lower().strip()
    
    for item, keywords in BALANCE_ITEMS.items():
        for keyword in keywords:
            if keyword in column_name:
                return item
    
    return None

def extract_financial_data_by_period(df, periods):
    """Извлекает финансовые данные по периодам"""
    financial_data = {}
    
    # Инициализируем данные для каждого периода
    for period in periods:
        financial_data[period['formatted']] = {}
    
    # Ищем столбец с наименованиями показателей
    indicator_column = None
    for col in df.columns:
        if 'наименование' in str(col).lower() or 'показатель' in str(col).lower():
            indicator_column = col
            break
    
    if not indicator_column:
        return financial_data
    
    # Проходим по всем строкам и извлекаем данные
    for row_idx in range(len(df)):
        indicator_name = str(df[indicator_column].iloc[row_idx]).strip()
        
        # Пропускаем пустые строки
        if not indicator_name or indicator_name in ['Актив', 'Пассив', 'Наименование показателя']:
            continue
        
        # Определяем тип показателя
        item = find_balance_item(indicator_name, [indicator_name])
        
        if item:
            # Извлекаем значения для каждого периода
            for period in periods:
                period_key = period['formatted']
                col_name = period['column']
                
                try:
                    value = pd.to_numeric(df[col_name].iloc[row_idx], errors='coerce')
                    if not pd.isna(value) and value != 0:
                        financial_data[period_key][item] = value
                except:
                    continue
    
    return financial_data

def calculate_financial_ratios_for_period(data):
    """Рассчитывает финансовые коэффициенты для одного периода"""
    ratios = {}
    
    try:
        # Извлекаем данные
        assets = data.get('активы всего', 0)
        current_assets = data.get('оборотные активы', 0)
        cash = data.get('денежные средства', 0)
        receivables = data.get('дебиторская задолженность', 0)
        inventory = data.get('запасы', 0)
        
        # Если нет оборотных активов, но есть их компоненты - рассчитываем
        if current_assets == 0:
            current_assets = cash + receivables + inventory
        
        equity = data.get('капитал', 0)
        current_liabilities = data.get('краткосрочные обязательства', 0)
        total_liabilities = data.get('обязательства всего', 0)
        
        revenue = data.get('выручка', 0)
        net_profit = data.get('чистая прибыль', 0)
        
        # 1. КОЭФФИЦИЕНТЫ ЛИКВИДНОСТИ
        if current_liabilities > 0:
            ratios['Коэффициент текущей ликвидности'] = current_assets / current_liabilities
            ratios['Коэффициент абсолютной ликвидности'] = cash / current_liabilities
        
        # 2. РЕНТАБЕЛЬНОСТЬ
        if assets > 0:
            ratios['Рентабельность активов (ROA)'] = (net_profit / assets) * 100
        if equity > 0:
            ratios['Рентабельность капитала (ROE)'] = (net_profit / equity) * 100
        if revenue > 0:
            ratios['Рентабельность продаж (ROS)'] = (net_profit / revenue) * 100
        
        # 3. ФИНАНСОВАЯ УСТОЙЧИВОСТЬ
        if assets > 0:
            ratios['Коэффициент автономии'] = equity / assets
        
        # 4. ДЕЛОВАЯ АКТИВНОСТЬ
        if assets > 0:
            ratios['Оборачиваемость активов'] = revenue / assets
        
    except Exception as e:
        print(f"Ошибка расчета коэффициентов: {e}")
    
    return ratios

# === ФУНКЦИИ ГЕНЕРАЦИИ ОТЧЕТОВ ===

def generate_period_analysis_report(periods_data):
    """Генерирует расширенный отчет анализа по периодам"""
    if not periods_data:
        return "❌ Не удалось извлечь данные по периодам."
    
    report = "📊 **ФИНАНСОВЫЙ АНАЛИЗ ПО ПЕРИОДАМ**\n\n"
    
    # Основные показатели по периодам
    report += "💰 **ДИНАМИКА ОСНОВНЫХ ПОКАЗАТЕЛЕЙ:**\n\n"
    
    key_indicators = ['выручка', 'чистая прибыль', 'активы всего', 'капитал']
    
    for indicator in key_indicators:
        values = []
        for period, data in periods_data.items():
            if data and indicator in data:
                values.append((period, data[indicator]))
        
        if values:
            report += f"📈 **{indicator.title()}:**\n"
            for period, value in values:
                report += f"• {period}: {value:,.0f} руб.\n"
            
            # Анализ динамики
            if len(values) >= 2:
                first_val = values[0][1]
                last_val = values[-1][1]
                change_abs = last_val - first_val
                change_rel = ((last_val - first_val) / first_val * 100) if first_val != 0 else 0
                trend = "📈" if change_rel > 0 else "📉" if change_rel < 0 else "➡️"
                report += f"  {trend} Изменение: {change_abs:+,.0f} руб. ({change_rel:+.1f}%)\n"
            
            report += "\n"
    
    # Анализ коэффициентов
    report += "📊 **ФИНАНСОВЫЕ КОЭФФИЦИЕНТЫ:**\n\n"
    
    for period, data in periods_data.items():
        if data:
            ratios = calculate_financial_ratios_for_period(data)
            if ratios:
                report += f"**{period}:**\n"
                for ratio_name, value in ratios.items():
                    if 'рентабельность' in ratio_name.lower():
                        report += f"• {ratio_name}: {value:.1f}%\n"
                    else:
                        report += f"• {ratio_name}: {value:.2f}\n"
                report += "\n"
    
    return report

def generate_liquidity_analysis_report(periods_data):
    """Генерирует отчет по анализу ликвидности"""
    report = "💧 **АНАЛИЗ ЛИКВИДНОСТИ**\n\n"
    
    for period, data in periods_data.items():
        if data:
            ratios = calculate_financial_ratios_for_period(data)
            if 'Коэффициент текущей ликвидности' in ratios:
                cr = ratios['Коэффициент текущей ликвидности']
                report += f"**{period}:**\n"
                report += f"• Коэффициент текущей ликвидности: {cr:.2f}\n"
                
                if cr >= 2.0:
                    report += "  ✅ Отличная ликвидность\n"
                elif cr >= 1.5:
                    report += "  ⚠️ Нормальная ликвидность\n"
                elif cr >= 1.0:
                    report += "  🟡 Пониженная ликвидность\n"
                else:
                    report += "  ❌ Критическая ликвидность\n"
                
                report += "\n"
    
    return report

# === ОСНОВНЫЕ ОБРАБОТЧИКИ ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [KeyboardButton("📊 Полный анализ"), KeyboardButton("🎯 Выборочный анализ")],
        [KeyboardButton("📈 Анализ ликвидности"), KeyboardButton("💎 Анализ рентабельности")],
        [KeyboardButton("🏛️ Финансовая устойчивость"), KeyboardButton("📋 Сравнение с нормативами")],
        [KeyboardButton("🔮 Прогноз тенденций"), KeyboardButton("📄 Экспорт в TXT")],
        [KeyboardButton("ℹ️ Помощь"), KeyboardButton("📁 Загрузить файл")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🤖 **ФИНАНСОВЫЙ АНАЛИЗАТОР**\n\n"
        "🚀 Бот с полным функционалом запущен!\n\n"
        "📁 Загрузите Excel файл и выберите тип анализа:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
🤖 **ФИНАНСОВЫЙ АНАЛИЗАТОР - ПОЛНАЯ ВЕРСИЯ**

📊 **Доступные функции:**
• 📊 Полный анализ - комплексная оценка
• 🎯 Выборочный анализ - нужные показатели  
• 📈 Ликвидность - платежеспособность
• 💎 Рентабельность - эффективность
• 🏛️ Устойчивость - стабильность
• 📋 Сравнение - отраслевые нормативы
• 🔮 Прогноз - будущие тренды
• 📄 TXT - текстовый отчет

📁 **Формат файла:**
Excel с данными за периоды:
• 31.12.2023, 31.12.2022
• За 2023 год, За 2022 год
"""
    await update.message.reply_text(help_text)

async def receive_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки Excel файлов"""
    try:
        if not update.message.document:
            await update.message.reply_text("📎 Пожалуйста, пришлите Excel файл")
            return

        file = update.message.document
        file_name = file.file_name.lower()

        if not (file_name.endswith('.xlsx') or file_name.endswith('.xls')):
            await update.message.reply_text("❌ Пожалуйста, пришлите файл в формате Excel (.xlsx или .xls)")
            return

        await update.message.reply_text("⏳ Анализирую структуру файла...")

        # Скачиваем файл
        file_obj = await file.get_file()
        file_bytes = await file_obj.download_as_bytearray()

        # Читаем Excel файл
        try:
            df = read_excel_file(file_bytes, file_name)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка чтения файла: {str(e)}")
            return
        
        # Определяем периоды
        periods = detect_periods(df)
        
        if not periods:
            await update.message.reply_text("❌ Не удалось определить периоды в файле")
            return
        
        # Извлекаем данные по периодам
        periods_data = extract_financial_data_by_period(df, periods)
        
        # Сохраняем данные в контекст пользователя
        context.user_data.update({
            'periods_data': periods_data,
            'file_name': file_name
        })
        
        extracted_count = sum(len(data) for data in periods_data.values())
        await update.message.reply_text(
            f"✅ Файл успешно обработан!\n"
            f"📊 Извлечено показателей: {extracted_count}\n"
            f"📅 Периодов: {len(periods)}\n\n"
            f"🎯 Теперь выберите тип анализа!"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при анализе: {str(e)}")

async def perform_full_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение полного анализа"""
    if 'periods_data' not in context.user_data:
        await update.message.reply_text("❌ Сначала загрузите файл с данными")
        return
    
    await update.message.reply_text("🔍 Выполняю полный финансовый анализ...")
    
    periods_data = context.user_data['periods_data']
    report = generate_period_analysis_report(periods_data)
    
    # Сохраняем для возможного экспорта
    context.user_data['last_analysis'] = report
    
    if len(report) > 4000:
        parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(report)

async def perform_liquidity_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Анализ ликвидности"""
    if 'periods_data' not in context.user_data:
        await update.message.reply_text("❌ Сначала загрузите файл с данными")
        return
    
    await update.message.reply_text("💧 Анализирую ликвидность...")
    
    periods_data = context.user_data['periods_data']
    report = generate_liquidity_analysis_report(periods_data)
    
    context.user_data['last_analysis'] = report
    
    await update.message.reply_text(report)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    
    if text == "📊 Полный анализ":
        await perform_full_analysis(update, context)
    elif text == "📈 Анализ ликвидности":
        await perform_liquidity_analysis(update, context)
    elif text == "💎 Анализ рентабельности":
        await update.message.reply_text("💎 Анализирую рентабельность...\n\n🔧 Функция в разработке")
    elif text == "🏛️ Финансовая устойчивость":
        await update.message.reply_text("🏛️ Анализирую устойчивость...\n\n🔧 Функция в разработке")
    elif text == "📋 Сравнение с нормативами":
        await update.message.reply_text("🏭 Сравниваю с нормативами...\n\n🔧 Функция в разработке")
    elif text == "🔮 Прогноз тенденций":
        await update.message.reply_text("🔮 Строю прогноз...\n\n🔧 Функция в разработке")
    elif text == "📄 Экспорт в TXT":
        await update.message.reply_text("📄 Создаю отчет...\n\n🔧 Функция в разработке")
    elif text == "🎯 Выборочный анализ":
        await update.message.reply_text("🎯 Выборочный анализ...\n\n🔧 Функция в разработке")
    elif text == "📁 Загрузить файл":
        await update.message.reply_text("📎 Пожалуйста, загрузите Excel файл с отчетностью")
    elif text == "ℹ️ Помощь":
        await help_command(update, context)

def main():
    """Основная функция"""
    print("🔧 Инициализация полной версии бота...")
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, receive_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Полная версия бота успешно запущена!")
    print("🌐 Режим: POLLING")
    print("🚀 Бот готов к работе!")
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
