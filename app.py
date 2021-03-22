import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
import pytz
from datetime import datetime,date
from faunadb import query as q
from faunadb.objects import Ref
from faunadb.client import FaunaClient


telegram_bot_token = "telegram-token"
client = FaunaClient(secret="fauna-secret-key")

updater = Updater(token=telegram_bot_token, use_context=True)
dispatcher = updater.dispatcher



def start(update, context):
    chat_id = update.effective_chat.id
    first_name = update["message"]["chat"]["first_name"]
    username = update["message"]["chat"]["username"]

    try:
        client.query(q.get(q.match(q.index("users_index"), chat_id)))
        context.bot.send_message(chat_id=chat_id, text="Welcome to Fauna Appointment Scheduler Bot \n\n To schedule an appointment enter /add_appointment \n To list al appointment enter /list_appointments \n To list all appoint,emts you have today enter /list_today_appointments")
    except:
        user = client.query(q.create(q.collection("Users"), {
            "data": {
                "id": chat_id,
                "first_name": first_name,
                "username": username,
                "last_command": "",
                "date": datetime.now(pytz.UTC)
            }
        }))
        context.bot.send_message(chat_id=chat_id, text="Welcome to Fauna Appointment Scheduler Bot, your details have been saved 😊 \n\n To schedule an appointment enter /add_appointment \n To list al appointment enter /list_appointments \n To list all appointments you have today enter /list_today_appointments")




def add_appointment(update, context):
    chat_id = update.effective_chat.id

    user = client.query(q.get(q.match(q.index("users_index"), chat_id)))
    client.query(q.update(q.ref(q.collection("Users"), user["ref"].id()), {"data": {"last_command": "add_appointment"}}))
    context.bot.send_message(chat_id=chat_id, text="Enter the appointment event you want to add along with its due in this format(mm/dd/yyyy) date seperated by a comma 😁")



def echo(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text

    user = client.query(q.get(q.match(q.index("users_index"), chat_id)))
    last_command = user["data"]["last_command"]

    if last_command == "add_appointment":
        events = client.query(q.create(q.collection("Appointments"), {
            "data": {
                "user_id": chat_id,
                "event": message.split(",")[0],
                "completed": False,
                "date_due": message.split(",")[1]
            }
        }))
        client.query(q.update(q.ref(q.collection("Users"), user["ref"].id()), {"data": {"last_command": ""}}))
        context.bot.send_message(chat_id=chat_id, text="Successfully added appointment event 👍")


def list_appointments(update, context):
   chat_id = update.effective_chat.id

   event_message = ""
   events = client.query(q.paginate(q.match(q.index("appointment_index"), chat_id)))
   for i in events["data"]:
       event = client.query(q.get(q.ref(q.collection("Appointments"), i.id())))
       if event["data"]["completed"]:
           event_status = "Completed"
       else:
           event_status = "Not Completed"
       event_message += "{}\nStatus:{} \nDate Due: {}\nUpdate Link: /update_{}\nDelete Link: /delete_{}\n\n".format(event["data"]["event"], event_status, event["data"]["date_due"], i.id(), i.id())
   if event_message == "":
       event_message = "You dont hava any appointments saved, type /add_appointment to schedule one now 😇"
   context.bot.send_message(chat_id=chat_id, text=event_message)


def update_appointment(update, context):
   chat_id = update.effective_chat.id
   message = update.message.text
   event_id = message.split("_")[1]

   event = client.query(q.get(q.ref(q.collection("Appointments"), event_id)))
   if event["data"]["completed"]:
       new_status = False
   else:
       new_status = True
   client.query(q.update(q.ref(q.collection("Appointments"), event_id), {"data": {"completed": new_status}}))
   context.bot.send_message(chat_id=chat_id, text="Successfully updated appointment status 👌")


def list_today_appointments(update, context):
   chat_id = update.effective_chat.id
   event_message = ""
   today = date.today()
   date1=today.strftime("%m/%d/%Y")
   events = client.query(q.paginate(q.match(q.index("appointment_today_index"), chat_id, date1 )))
   for i in events["data"]:
       event = client.query(q.get(q.ref(q.collection("Appointments"), i.id())))
       if event["data"]["completed"]:
           event_status = "Completed"
       else:
           event_status = "Not Completed"
       event_message += "{}\nStatus:{} \nDate Due: {}\nUpdate Link: /update_{}\nDelete Link: /delete_{}\n\n".format(event["data"]["event"], event_status, event["data"]["date_due"], i.id(), i.id())
   if event_message == "":
       event_message = "You dont have any appointments saved, type /add_appointment to schedule one now 😇"
   context.bot.send_message(chat_id=chat_id, text=event_message)


def delete_appointment(update, context):
   chat_id = update.effective_chat.id
   message = update.message.text
   event_id = message.split("_")[1]

   client.query(q.delete(q.ref(q.collection("Appointments"), event_id)))
   context.bot.send_message(chat_id=chat_id, text="Successfully deleted appointment👌")




dispatcher.add_handler(CommandHandler("add_appointment", add_appointment))
dispatcher.add_handler(CommandHandler("list_appointments", list_appointments))
dispatcher.add_handler(CommandHandler("list_today_appointments", list_today_appointments))
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.regex("/update_[0-9]*"), update_appointment))
dispatcher.add_handler(MessageHandler(Filters.regex("/delete_[0-9]*"), delete_appointment))
dispatcher.add_handler(MessageHandler(Filters.text, echo))
updater.start_polling()
