from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes
from telegram.ext import filters as Filters
import requests

TOKEN='7370521170:AAE6ExgdxE1pXIurUJp3T20GW-SB14fZ82o'

def get_yuan_to_rub():
    response = requests.get('https://api.exchangerate-api.com/v4/latest/CNY')
    data = response.json()
    return data['rates']['RUB'] + 1


def calculate_cost(amount, intermediary_percent, treasury_percent, item_type, item_weight=0, is_fragile=False):
    yuan_to_rub = get_yuan_to_rub()
    base_cost = amount * yuan_to_rub * (1 + intermediary_percent)

    total_cost = base_cost * (1 + treasury_percent)
    
    if is_fragile:
        total_cost *= 1.1
    
    delivery_cost = 0
    if item_type == 'small':
        delivery_cost = 100
    elif item_type == 'medium':
        delivery_cost = 200
    elif item_type == 'large':
        delivery_cost = 1000 * item_weight
    
    total_cost += delivery_cost
    return total_cost


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[KeyboardButton("Рассчитать стоимость")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
    await update.message.reply_text('Нажмите кнопку для расчета стоимости:', reply_markup=reply_markup)


async def calculate_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Введите стоимость в юанях (например, 57.8):")
    context.user_data['step'] = 'amount'


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data in ['fragile_yes', 'fragile_no']:
        context.user_data['is_fragile'] = query.data == 'fragile_yes'
        await query.edit_message_text(
        text="Выберите тип предмета:\n<b><i>Важно, если вы заказываете чайник, то выбирайте тип \"Большой\" и вводите вес 0.5</i></b>", 
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Малый", callback_data='small')],
            [InlineKeyboardButton("Средний", callback_data='medium')],
            [InlineKeyboardButton("Большой", callback_data='large')]
        ])
)
    elif query.data in ['small', 'medium', 'large']:
        context.user_data['item_type'] = query.data
        if query.data == 'large':
            await query.edit_message_text(text="Введите примерную массу предмета в кг (например, 1.23):")
            context.user_data['step'] = 'weight'
        else:
            await calculate_and_send_result(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'step' not in context.user_data:
        await update.message.reply_text('Пожалуйста, начните с нажатия кнопки "Рассчитать стоимость".')
        return

    step = context.user_data['step']
    text = update.message.text.strip()

    if step == 'amount':
        try:
            amount = float(text)
            context.user_data['amount'] = amount
            context.user_data['step'] = 'fragile'
            await update.message.reply_text('Является ли предмет хрупким?', reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Да", callback_data='fragile_yes')],
                [InlineKeyboardButton("Нет", callback_data='fragile_no')]
            ]))
        except ValueError:
            await update.message.reply_text('Ошибка ввода. Убедитесь, что вы ввели числовое значение для стоимости.')
    elif step == 'weight':
        try:
            weight = float(text)
            context.user_data['item_weight'] = weight
            await calculate_and_send_result(update, context)
        except ValueError:
            await update.message.reply_text('Ошибка ввода. Убедитесь, что вы ввели числовое значение для массы.')

async def calculate_and_send_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    amount = context.user_data['amount']
    item_type = context.user_data['item_type']
    item_weight = context.user_data.get('item_weight', 0)
    is_fragile = context.user_data.get('is_fragile', False)
    
    intermediary_percent = 0.1  # 10% посредника
    treasury_percent = 0.6 if amount <= 100 else 0.4 if amount <= 200 else 0.35 if amount <= 500 else 0.25
    
    total_cost = calculate_cost(amount, intermediary_percent, treasury_percent, item_type, item_weight, is_fragile)
    
    message = update.message if update.message else update.callback_query.message
    await message.reply_text(f'Общая стоимость: {total_cost:.2f} рублей')

    context.user_data.clear()

def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(Filters.TEXT & Filters.Regex('^Рассчитать стоимость$'), calculate_start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(Filters.TEXT & ~Filters.Regex('^Рассчитать стоимость$') & ~Filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()