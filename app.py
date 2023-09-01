from functools import wraps
import re
import uuid
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
import questions
import os

chat_id = -996265474


admin_id = [2039072512, 285552144, 5924489961, 350046550]

GET_NAME = range(1)

class QuestionPhase:
    def __init__(self, question_list) -> None:
        self.current_index = 0
        self.questions = question_list
        self._current = question_list[self.current_index]
    
    @property
    def current(self):
        return self._current
    
    @current.setter
    def current(self, value):
        self._current = value
            
    def reset(self):
        self.current_index = 0
        self._current = self.questions[self.current_index]

    def get_next(self):
        next = self.current_index + 1
        if next < len(self.questions): 
            self.current_index = next
            self._current = self.questions[next]
            return True
        return False

original_phases =[
    questions.Schema_Questions(),
    questions.Schema_Mind_Questions()
]

current_phase = QuestionPhase(original_phases)

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

    if context.user_data.get(q_key) != q_value:
        context.user_data[q_key] = q_value
        await update.callback_query.edit_message_reply_markup(current_phase.current.keyboard_generator(q_key, active_index=context.user_data.get(q_key)))


async def next_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    next = int(update.callback_query.data.split('-')[1])
    current = next - 1
    await update.callback_query.answer()
    if context.user_data.get(current) != None:
        await update.callback_query.edit_message_text(text=current_phase.current.QUESTIONS.get(next), reply_markup=current_phase.current.keyboard_generator(next, active_index=context.user_data.get(next)))


async def prev_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    previous = int(update.callback_query.data.split('-')[1])
    await update.callback_query.answer()

    await update.callback_query.edit_message_text(text=current_phase.current.QUESTIONS.get(previous), reply_markup=current_phase.current.keyboard_generator(previous, active_index=context.user_data.get(previous)))


async def finish_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    last_question = int(update.callback_query.data.split('-')[1])
    if context.user_data.get(last_question) != None:
        #await update.callback_query.answer('!نتیجه برای مشاور شما ارسال شد')
        await context.bot.send_message(chat_id=chat_id, text=current_phase.current.show_results(context.user_data))
        # await context.bot.edit_message_text(text=current_phase.current.help_text, chat_id=update._effective_chat.id, message_id=context.user_data.get('help'))
        if current_phase.get_next():
            # await update.message.reply_text(text="آزمون طرحواره پایان یافت و نتیجه برای مشاور شما ارسال شد.")
            # await update.message.reply_text(text="در ادامه آموزش ذهنیت های طرحواره ای:")
            temp=await update.callback_query.edit_message_text(text='<b><i>آزمون طرحواره پایان یافت و نتیجه برای مشاور شما ارسال شد.' + 
                                                               '\n\n' + "در ادامه آموزش ذهنیت های طرحواره ای: </i></b>", 
                                                               reply_markup=None ,
                                                               parse_mode='html')
            
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=current_phase.current.QUESTIONS.get(123),
                                           reply_markup=current_phase.current.keyboard_generator(123))
            name = context.user_data.get('name',' ')
            help = context.user_data['help']
            context.user_data.clear()
            context.user_data['name']=name
            context.user_data['help']=help
            context.user_data['help2']=temp.id
        else:
            
            await context.bot.delete_message(update.effective_chat.id,context.user_data['help'])
            await context.bot.edit_message_text('<b>آزمون تمام شد و نتیجه برای مشاور شما ارسال شد🥳</b> ',
                                                update.effective_chat.id,context.user_data['help2'],
                                                parse_mode='html')
            current_phase.reset()
            await update.effective_message.delete()    

        return ConversationHandler.END


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if len(name) < 3:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=' .نام نا معتبر! دوباره وارد کنید',
                                       reply_to_message_id=update._effective_message.id)
        return GET_NAME

    context.user_data['name'] = name
    if context.user_data.get('authorized'):
        await update.message.reply_text(text=questions.global_help_text(name))
        help_message = await update.message.reply_text(text=current_phase.current.help_text)
        context.user_data['help1'] = help_message.id
        await update.message.reply_text(f"{current_phase.current.QUESTIONS.get(90)}",
                                        reply_markup=current_phase.current.keyboard_generator(90, active_index=-1))
    return ConversationHandler.END

app = ApplicationBuilder().token(os.environ.get(
    'TELEGRAM_TOKEN','1484846841:AAFwouB27Sys8U83Nm3C6p6nUA63cNNyMGM')).build()

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
