from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

from WeatherManager import WeatherManager


BOT_TOKEN = ''
WEATHER_API_KEY = ''

WEATHER_SERVICE_URL = "http://127.0.0.1:5000"

bot = Bot(token=BOT_TOKEN)
weather_manager = WeatherManager(WEATHER_API_KEY)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class WeatherStates(StatesGroup):
    waiting_for_cities = State()
    waiting_for_days = State()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = """
👋 Привет! Я бот для прогноза погоды.

Я помогу узнать прогноз погоды по маршруту вашего путешествия.

Что я умею:
• Показывать прогноз погоды для городов (даже на несколько дней)
• Отображать температуру, скорость ветра и состояние погоды
• Визуализировать данные

Используйте:
/weather - получить прогноз погоды
/help - показать информацию
"""
    await message.answer(welcome_text)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
⭐️ Доступные команды:

/start - начать работу с ботом
/weather - получить прогноз погоды
/help - показать это сообщение

🌧 Как получить прогноз погоды:
1. Введите команду /weather
2. Укажите города маршрута через запятую
3. Выберите количество дней для прогноза
"""
    await message.answer(help_text)


@dp.message(Command("weather"))
@dp.callback_query(lambda c: c.data.startswith('new_route'))
async def cmd_weather(message: types.Message, state: FSMContext):
    if isinstance(message, types.CallbackQuery):
        message = message.message

    await message.answer("Введите города маршрута через запятую (например, 'Челябинск, Казань, Уфа')")
    await state.set_state(WeatherStates.waiting_for_cities)


@dp.message(WeatherStates.waiting_for_cities)
async def process_start_city(message: types.Message, state: FSMContext):
    cities = [city.strip() for city in message.text.split(',')]

    if len(cities) < 2:
        await message.answer("Пожалуйста, введите как минимум 2 города через запятую")
        return

    await state.update_data(cities=cities)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="1 день", callback_data="1_days"),
                types.InlineKeyboardButton(text="2 дня", callback_data="2_days"),
            ],
            [
                types.InlineKeyboardButton(text="3 дня", callback_data="3_days"),
                types.InlineKeyboardButton(text="4 дня", callback_data="4_days"),
            ],
            [
                types.InlineKeyboardButton(text="5 дней", callback_data="5_days")
            ]
        ]
    )

    await message.answer("Выберите количество дней для прогноза:", reply_markup=keyboard)
    await state.set_state(WeatherStates.waiting_for_days)


@dp.callback_query(lambda c: c.data.endswith('_days'))
async def process_days_selection(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    processing_msg = await callback.message.answer("⏳ Получаю данные о погоде...")

    user_data = await state.get_data()
    if 'cities' not in user_data:
        await callback.message.answer(
            "Произошла ошибка: данные о городах не найдены.\n"
            "Пожалуйста, начните заново с команды /weather"
        )
        await processing_msg.delete()
        await state.clear()
        return

    interval = int(callback.data.split('_')[0])
    cities = user_data['cities']

    try:
        weather_data = {}
        for city in cities:
            weather_data[city] = weather_manager.get_weather_data(city, interval)

        for city, data in weather_data.items():
            summary_text = f"🌤 Прогноз погоды для {city}:\n\n"
            for date, values in data.items():
                summary_text += (
                    f"📅 {date}\n"
                    f"🌡 Температура: {values['temperature']:.2f}°C\n"
                    f"💨 Скорость ветра: {values['wind_speed']:.1f} м/с\n"
                    f"☔️ Состояние погоды: {', '.join(values['precipitation'])}\n\n"
                )

            await callback.message.answer(summary_text)

        keyboard_new_route = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="Новый маршрут",
                    callback_data="new_route"
                )
            ]]
        )

        await callback.message.answer("Вот информация о погоде в выбранных городах ⬆️", reply_markup=keyboard_new_route)

        await state.update_data(weather_data=weather_data)
        await processing_msg.delete()

    except Exception as e:
        print(f"Ошибка: {str(e)}")
        keyboard_exception = keyboard_new_route = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="Начать сначала",
                    callback_data="new_route"
                )
            ]]
        )
        await processing_msg.delete()
        await callback.message.answer(
            f"😔 Произошла ошибка при получении прогноза: {e}\n"
            "Пожалуйста, проверьте названия городов и попробуйте снова.",
            reply_markup=keyboard_exception
        )

    await state.set_state(WeatherStates.waiting_for_cities)


@dp.message()
async def process_messages(message: types.Message):
    await bot.send_message(message.chat.id, "Я вас не понял! Пожалуйста, введите одну из команд:\n/start\n/help\n/weather")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print('Бот остановлен')
