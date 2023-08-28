import re
import uuid
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from questions import Question
chat_id = -996265474

admin_id = [2039072512, 285552144, 5924489961, 350046550]  # Replace with the admin's user ID

GET_NAME = range(1)

async def generate_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id in admin_id:
        token = str(uuid.uuid4())  # Generate a unique token
        if context.bot_data.get('admin_token') == None:
            context.bot_data['admin_token'] = set()
            context.bot_data['admin_token'].add(token)
        else:
            context.bot_data['admin_token'].add(token)

        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start={token}"
        await update.effective_message.reply_text(
            text=f"لینک ورود به ربات: \n{link}")
    else:
        await update.message.reply_text("You are not authorized to generate tokens.")


def show_results(name , **data):
    ret=""
    result = Question.resault_tempalte
    for key, value in result.items():
        result[key] = 0
    ret = f'Entered name : {name}\n\n'

    for key, value in result.items():
        for i in Question.resault_map[key]:
            temp_key = 'Q'+str(i)
            if data.get(temp_key) != None:
                result[key] += int(data[temp_key])

    for key, value in result.items():
        ret = ret + key + ' : ' + str(value)+'\n'
        # اضافه کردن ریز پاسخ ها
    # for key, value in data.items():
    #     ret += key+' : '+str(value)+'\n'
    return ret


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if context.args and context.bot_data.get('admin_token'):
        if context.args[0] in context.bot_data.get('admin_token'):
            context.user_data['authorized'] = True
            context.bot_data.get('admin_token').remove(context.args[0])
            await update.effective_message.reply_text('اسم و فامیلت چیه؟')
            return GET_NAME
    else:
        await update.message.reply_text("لطفا از مشاور درخواست لینک ورود کنید!")


async def btn_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    await update.callback_query.answer()
    q_key, q_value = data.split('-')

    if context.user_data.get(q_key) != int(q_value):
        context.user_data[q_key] = int(q_value)
        await update.callback_query.edit_message_reply_markup(Question.keyboard_generator(q_key, active_index=context.user_data.get(q_key)))


async def next_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    next = update.callback_query.data.split('-')[1]
    current = 'Q' + str(int(next[1:]) - 1)
    await update.callback_query.answer()
    if context.user_data.get(current) != None:
        await update.callback_query.edit_message_text(text=Question.QUESTIONS.get(next), reply_markup=Question.keyboard_generator(next, active_index=context.user_data.get(next)))


async def prev_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    previous = update.callback_query.data.split('-')[1]
    await update.callback_query.answer()

    await update.callback_query.edit_message_text(text=Question.QUESTIONS.get(previous), reply_markup=Question.keyboard_generator(previous, active_index=context.user_data.get(previous)))


async def finish_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    last_question = update.callback_query.data.split('-')[1]
    if context.user_data.get(last_question) != None:
        name = context.user_data.pop('name')
        text = show_results(name ,**context.user_data)
        # کدی که رفت داخل ریزالت و دهنمون رو سرویس کرد اینجا نوشته شده بود
        detail = 'نتیجه برای مشاور شما ارسال شد.'

        await context.bot.send_message(chat_id=chat_id, text=text)
        await update.callback_query.edit_message_text(text=detail, reply_markup=None)
        context.user_data.clear()
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    # if re.match("^*{3,}*$", name) == None:
    if len(name)<3:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=' .نام نا معتبر! دوباره وارد کنید',
                                       reply_to_message_id=update._effective_message.id)
        return GET_NAME

    context.user_data['name'] = name
    if context.user_data.get('authorized'):
        await update.message.reply_text(text=Question.help_text)
        await update.message.reply_text(f"{Question.QUESTIONS.get('Q1')}",
                                        reply_markup=Question.keyboard_generator('Q1', active_index=-1))
    return ConversationHandler.END

app = ApplicationBuilder().token(secretsData.TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler(["hello", "start", "salam"], hello)],
    states={
        GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
    },
    fallbacks=[]
)
app.add_handler(conv_handler)
app.add_handler(CommandHandler(["token"], generate_token))
app.add_handler(CallbackQueryHandler(next_btn, re.compile(r'^next')))
app.add_handler(CallbackQueryHandler(prev_btn, re.compile(r'^previous')))
app.add_handler(CallbackQueryHandler(finish_btn, re.compile(r'^finish')))
app.add_handler(CallbackQueryHandler(btn_click))
app.run_polling()
