from typing import Final
from replit import db
import openai
import os
from ai import generate_image, generate_audio, gen_prompt, summarize_chats, transcribe_audio
from random import randint
import requests
import json
from urllib.request import urlopen

openai.api_key = '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'
elevenlabs_apikey = "50fe0a62f01a21c90ef8f9ad62b5149e"

# pip install python-telegram-bot
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes

print('Starting up bot...')

TOKEN: Final = '6316949448:AAEKza5zY_tCAjtZzjiVJc1BDpSCOEaHnAg'
BOT_USERNAME: Final = '@tele_ai_companion_bot'


# Lets us use the /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello, There. We can start chatting right away!')
  
    username = str(update.message.chat.id)
    if db.get(username) is None:
      db[username] = {
        'config': {
                  'name': "Buddy",
                  'auto-voice': True,
                  'mood': 'friendly' 
      },
        'chat': [
          {"role": f"system", "content": "You are a helpful synthetic friend, your new alias is Buddy. Here are some details on your you new human companion: \n  His name is: {update.message.chat.first_name}"}  
        ]
      }



# command to help the user with commands
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Here is the commands: \n 1. /start to start the bot  \n 2. /image {image description } to generate a image \n 3. /voice {text} the bot will reply with the answer in text format')



# command to send the user voice messages
async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = gen_prompt(openai, "".join(context.args), update.message.chat.id, tokens=100)
  audio = generate_audio(text, elevenlabs_apikey)
  await update.message.reply_audio(audio=audio)
  os.remove(audio)



# command to send the user images
async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  image = generate_image(openai, "".join(context.args))
  if image is None:
    await update.message.reply_photo(photo=open('./assets/no_image.jpeg'))
  await update.message.reply_photo(photo=image)



def handle_response(user_input: str, id, update: Update) -> str:  

  if user_input[0] == '/':
    return None, None, None
  
  # Check if the message len is less than the max
  if len(user_input) > 2500:
    return "Sorry, the Message is too long..", None, None

  # Setup the chat
  completion = gen_prompt(openai, user_input, id)
  
  if completion is None:
    return 'Error chatting, wait a while...'
    
  summarize_chats(openai, id)
  
  send = randint(1, 25)
  image = None
  audio = None
  if send > 10 and send < 16:
    image = generate_image(openai, completion, promptimp=True)

  if send > 15 and send < 2:
    completion = gen_prompt(openai, f" Can you please summarize this, reply only with the answer: {completion}", id, tokens=100)
    audio = generate_audio(completion, elevenlabs_apikey)
    
  return completion, image, audio



async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get basic info of the incoming messag
    message_type: str = update.message.chat.type
    text: str = update.message.text

    audio = update.message.audio
    audio = audio if audio is not None else update.message.voice
    if audio is not None:
      response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getFile?file_id={audio.file_id}')
      response = json.loads(response.content)
      name = f"temp/{randint(0, 100000)}.mp3"
      with open(name, 'wb') as f:
        file = urlopen(f"https://api.telegram.org/file/bot{TOKEN}/{response['result']['file_path']}")
        f.write(file.read())
      text = transcribe_audio(openai, id, name)
      os.remove(name)
    if update.message.photo:
      return "Can't read images... Try audio instead"
    
    if text is not None:
      # React to group messages only if users mention the bot directly
      if message_type == 'group':
          # Replace with your bot username
          if BOT_USERNAME in text:
              new_text: str = text.replace(BOT_USERNAME, '').strip()
              response, img, audio = handle_response(new_text, update.message.chat.id, update)
          else:
              return  # We don't want the bot respond if it's not mentioned in the group
      else:
          response, img, audio= handle_response(text, update.message.chat.id, update)
  
    if audio is not None:
      await update.message.reply_audio(audio=audio)
      os.remove(audio)
      
    if response is not None and audio is None:
      await update.message.reply_text(response)

    if img is not None:
      await update.message.reply_photo(photo=img)

    # Reply normal if the message is in private
    print('Bot:', response)

# Log errors
# Run the program
if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('voice', voice_command))
    app.add_handler(CommandHandler('image', image_command))
  
    # Messages
    app.add_handler(MessageHandler(filters=None, callback=handle_message))

    # Log all errors

    print('Polling...')
    # Run the bot
    app.run_polling(poll_interval=5)
