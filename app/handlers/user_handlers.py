from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import get_main_keyboard, get_referral_keyboard
from app.services.user_service import UserService
from app.services.referral_service import ReferralService
from app.database.core import async_session

user_router = Router()


# ========== Состояния ==========
class UserStates(StatesGroup):
    main_menu = State()
    balance_view = State()
    referral_view = State()


# ========== Команды ==========
@user_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработать команду /start"""
    async with async_session() as session:
        user_service = UserService(session)
        referral_service = ReferralService(session)
        
        # Проверить реферальный код
        args = message.text.split()
        referred_by = None
        
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                ref_code = args[1].replace("ref_", "")
                await referral_service.process_referral_from_code(
                    message.from_user.id,
                    ref_code
                )
                referred_by = int(ref_code.split("_")[0])
            except:
                pass
        
        # Создать или получить пользователя
        user = await user_service.get_or_create_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            is_bot=message.from_user.is_bot,
            referred_by=referred_by
        )
        
        await state.set_state(UserStates.main_menu)
        
        welcome_text = (
            f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
            f"Добро пожаловать в наш Telegram бот! 🤖\n\n"
            f"Здесь ты можешь:\n"
            f"💰 Управлять своим балансом\n"
            f"👥 Приглашать друзей и получать награды\n"
            f"📊 Просматривать статистику\n\n"
            f"Начни с меню ниже 👇"
        )
        
        await message.answer(welcome_text, reply_markup=get_main_keyboard())


@user_router.message(Command("balance"))
async def cmd_balance(message: Message, state: FSMContext):
    """Показать баланс"""
    async with async_session() as session:
        user_service = UserService(session)
        user = await user_service.get_user(message.from_user.id)
        
        if not user:
            await message.answer("❌ Пользователь не найден")
            return
        
        balance_text = (
            f"💰 <b>Ваш баланс</b>\n\n"
            f"Основной баланс: <code>{user.balance}</code> ⭐\n"
            f"Реферальный бонус: <code>{user.referral_bonus}</code> 🎁\n"
            f"Всего: <code>{user.balance + user.referral_bonus}</code> 💎\n"
        )
        
        await message.answer(balance_text, parse_mode="HTML")
        await state.set_state(UserStates.main_menu)


@user_router.message(Command("referral"))
async def cmd_referral(message: Message, state: FSMContext):
    """Показать реферальную информацию"""
    async with async_session() as session:
        user_service = UserService(session)
        referral_service = ReferralService(session)
        
        user = await user_service.get_user(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return
        
        # Получить реферальную ссылку
        ref_link = await referral_service.generate_referral_link(
            message.from_user.id,
            "your_bot_username"  # Замени на имя твоего бота
        )
        
        # Получить статистику
        stats = await referral_service.get_referral_stats(message.from_user.id)
        
        referral_text = (
            f"👥 <b>Твоя реферальная программа</b>\n\n"
            f"Всего рефералов: <code>{stats['total_referrals']}</code>\n"
            f"Активных рефералов: <code>{stats['active_referrals']}</code>\n"
            f"Ожидающих: <code>{stats['pending_referrals']}</code>\n"
            f"Заработано: <code>{stats['referral_bonus']}</code> ⭐\n\n"
            f"<b>Твоя реферальная ссылка:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"Приглашай друзей и получай <b>100 ⭐</b> за каждого!"
        )
        
        await message.answer(
            referral_text,
            reply_markup=get_referral_keyboard(ref_link),
            parse_mode="HTML"
        )
        await state.set_state(UserStates.main_menu)


# ========== Кнопки главного меню ==========
@user_router.message(StateFilter(UserStates.main_menu), F.text == "💰 Баланс")
async def btn_balance(message: Message):
    """Кнопка баланса"""
    await cmd_balance(message, FSMContext({}))


@user_router.message(StateFilter(UserStates.main_menu), F.text == "👥 Рефералы")
async def btn_referral(message: Message):
    """Кнопка рефералов"""
    await cmd_referral(message, FSMContext({}))


@user_router.message(StateFilter(UserStates.main_menu), F.text == "ℹ️ О боте")
async def btn_about(message: Message, state: FSMContext):
    """Кнопка об информации"""
    about_text = (
        "ℹ️ <b>О нашем боте</b>\n\n"
        "Это многофункциональный Telegram бот с поддержкой:\n\n"
        "✅ Реферальной системы - приглашай и зарабатывай\n"
        "✅ Управления балансом - отслеживай свои ⭐\n"
        "✅ Рассылок - получай актуальные новости\n"
        "✅ Администраторского панели - управляй ботом\n\n"
        "<b>Версия:</b> 1.0.0\n"
        "<b>Разработчик:</b> @YourUsername"
    )
    
    await message.answer(about_text, parse_mode="HTML")
    await state.set_state(UserStates.main_menu)


@user_router.message(StateFilter(UserStates.main_menu), F.text == "⚙️ Настройки")
async def btn_settings(message: Message, state: FSMContext):
    """Кнопка настроек"""
    settings_text = (
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь ты можешь настроить уведомления и другие параметры.\n\n"
        "Функция в разработке... 🚀"
    )
    
    await message.answer(settings_text, parse_mode="HTML")
    await state.set_state(UserStates.main_menu)


# ========== Обновление статистики ==========
@user_router.message(StateFilter(UserStates.main_menu))
async def update_message_count(message: Message):
    """Обновить счётчик сообщений"""
    async with async_session() as session:
        user_service = UserService(session)
        await user_service.increment_message_count(message.from_user.id)
        await user_service.update_last_seen(message.from_user.id)
