
from functools import wraps
import re
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
import questions
import os

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger= logging.getLogger(__name__)

chat_id = -996265474


admin_id = [2039072512, 285552144, 5924489961, 350046550]

GET_NAME, SHOW_HELP, SHOW_QUESTIONS = range(3)

default_q_schema=90
default_q_mind_schema=124

def only_admins(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id in admin_id:
            return await func(update, context)
        await update.message.reply_text("You are not authorized to generate tokens.")
    return wrapper


def only_authorized(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.args and context.bot_data.get('admin_token'):
            if context.args[0] in context.bot_data.get('admin_token'):
                context.user_data['authorized'] = True
                context.bot_data.get('admin_token').remove(context.args[0])
                return await func(update, context)

        await update.message.reply_text("لطفا از مشاور درخواست لینک ورود کنید!")
    return wrapper


@only_admins
async def generate_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    token = str(uuid.uuid4())
    if context.bot_data.get('admin_token') == None:
        context.bot_data['admin_token'] = set()
        context.bot_data['admin_token'].add(token)
    else:
        context.bot_data['admin_token'].add(token)

    bot_username = context.bot.username
    link = f"https://t.me/{bot_username}?start={token}"
    await update.effective_message.reply_text(
        text=f"لینک ورود به ربات: \n{link}")


@only_authorized
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text('اسم و فامیلت چیه؟')
    return GET_NAME


async def btn_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    await update.callback_query.answer()
    q_key = int(data.split('-')[0])
    q_value = int(data.split('-')[1])
    if context.user_data['answers'].get(q_key) != q_value:
        context.user_data['answers'][q_key]= q_value
        await update.callback_query.edit_message_reply_markup(questions.get_phase(context.user_data.get('phase',1)).keyboard_generator(q_key, active_index=context.user_data['answers'].get(q_key)))


async def next_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    next = int(update.callback_query.data.split('-')[1])
    current = next - 1
    await update.callback_query.answer()
    if context.user_data['answers'].get(current) != None:
        await update.callback_query.edit_message_text(text=questions.get_phase(context.user_data.get('phase')).QUESTIONS.get(next), reply_markup=questions.get_phase(context.user_data.get('phase')).keyboard_generator(next, active_index=context.user_data['answers'].get(next)))


async def prev_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    previous = int(update.callback_query.data.split('-')[1])
    await update.callback_query.answer()

    await update.callback_query.edit_message_text(text=questions.get_phase(context.user_data.get('phase')).QUESTIONS.get(previous), reply_markup=questions.get_phase(context.user_data.get('phase')).keyboard_generator(previous, active_index=context.user_data['answers'].get(previous)))


async def finish_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    last_question = int(update.callback_query.data.split('-')[1])
    if context.user_data['answers'].get(last_question) != None:
        #await update.callback_query.answer('!نتیجه برای مشاور شما ارسال شد')
        await context.bot.send_message(chat_id=chat_id, text=questions.get_phase(context.user_data.get('phase')).show_results(context.user_data))
        # await context.bot.edit_message_text(text=current_phase.current.help_text, chat_id=update._effective_chat.id, message_id=context.user_data.get('help'))
        if context.user_data['phase']==1:
            # await update.message.reply_text(text="آزمون طرحواره پایان یافت و نتیجه برای مشاور شما ارسال شد.")
            # await update.message.reply_text(text="در ادامه آموزش ذهنیت های طرحواره ای:")
            temp=await update.callback_query.edit_message_text(text='<b><i>آزمون طرحواره پایان یافت و نتیجه برای مشاور شما ارسال شد.' + 
                                                               '\n\n' + "در ادامه آزمون ذهنیت های طرحواره ای: </i></b>", 
                                                               reply_markup=None ,
                                                               parse_mode='html')
            context.user_data['phase']=2
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=questions.get_phase(context.user_data.get('phase')).QUESTIONS.get(default_q_mind_schema),
                                           reply_markup=questions.get_phase(context.user_data.get('phase')).keyboard_generator(default_q_mind_schema))
            context.user_data['answers'].clear()
            context.user_data['messages'].append(temp.id)
            
        else:
            await context.bot.delete_message(update.effective_chat.id,context.user_data['messages'][0])
            await context.bot.delete_message(update.effective_chat.id,context.user_data['messages'][1])
            await context.bot.edit_message_text('<b>آزمون تمام شد و نتیجه برای مشاور شما ارسال شد🥳</b> ',
                                                update.effective_chat.id,context.user_data['messages'][2],
                                                parse_mode='html')
            await update.effective_message.delete()    

        return ConversationHandler.END


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = [
        [InlineKeyboardButton('فهمیدم', callback_data='SHOW_HELP')]
    ]
    name = update.message.text
    if len(name) < 3:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=' .نام نا معتبر! دوباره وارد کنید',
                                       reply_to_message_id=update._effective_message.id)
        return GET_NAME

    context.user_data['name'] = name
    if context.user_data.get('authorized'):
        context.user_data['messages'] = list()
        context.user_data['answers'] = dict()
        context.user_data['phase']=1
        help_message = await update.message.reply_text(text=questions.global_help_text(name),reply_markup=InlineKeyboardMarkup(button))
        context.user_data['messages'].append(help_message.id)
    return SHOW_HELP


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = [[InlineKeyboardButton('فهمیدم', callback_data='SHOW_QUESTIONS')]]
    await update.callback_query.edit_message_reply_markup(reply_markup=None)
    
    help_message = await update.effective_message.reply_text(
                                                  text=questions.get_phase(1).help_text,
                                                  reply_markup=InlineKeyboardMarkup(button))
    context.user_data['messages'].append(help_message.id)
    
    return SHOW_QUESTIONS
    



async def show_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_reply_markup(reply_markup=None)
    
    temp=await update.effective_message.reply_text(f"{questions.get_phase(context.user_data.get('phase',1)).QUESTIONS[default_q_schema]}",
                                        reply_markup=questions.get_phase(context.user_data.get('phase')).keyboard_generator(question=default_q_schema, active_index=-1))
    context.user_data['messages'].append(temp.id)
    return ConversationHandler.END


app = ApplicationBuilder().token(os.environ.get(
    'TELEGRAM_TOKEN')).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler(["hello", "start", "salam"], hello)],
    states={
        GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        SHOW_HELP: [CallbackQueryHandler(show_help, re.compile(r'^SHOW_HELP'))],
        SHOW_QUESTIONS: [CallbackQueryHandler(show_questions, re.compile(r'^SHOW_QUESTIONS'))],
    },
    fallbacks=[]
)
app.add_handler(conv_handler)
app.add_handler(CommandHandler(["token"], generate_token))
app.add_handler(CallbackQueryHandler(next_btn, re.compile(r'^next')))
app.add_handler(CallbackQueryHandler(prev_btn, re.compile(r'^previous')))
app.add_handler(CallbackQueryHandler(finish_btn, re.compile(r'^finish')))
app.add_handler(CallbackQueryHandler(btn_click))
app.run_webhook(
    listen='0.0.0.0',
    port=8443,
    secret_token=os.environ.get('TELEGRAM_TOKEN'),
    key='private.key',
    cert='cert.pem',
    webhook_url='https://opoli.store:8443'
)
