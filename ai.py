from random import choice
from replit import db
from random import randint
from elevenlabs import generate, save
from gtts import gTTS

import time


backoff = 1
def generate_image(openai, prompt, promptimp=True):
  print(prompt)
  if promptimp:
    prompt = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-16k",
    messages=[{'role':'assistant', 'content': 'Your Job is to convert this message into a simple yet effective image prompt for example: And you should understand that sunflowers have a special ability, output: animated sunflower facing the sun'},
              {'role':'user', 'content':str(prompt)}],
    max_tokens=100
    )
  try:
    r = openai.Image.create(
    prompt=prompt.choices[0].message.content,
    n=1,
    size=choice(['256x256', '512x512', '1024x1024'])
    )
    return r.data[0]['url']
  except:
    return None
  return None


def generate_audio(prompt, apikey):
  name = f"temp/{randint(0, 100000)}.mp3"
  try:
    audio = generate(
      text=prompt,
      voice="Antoni",
      model="eleven_monolingual_v1",
      api_key=apikey
    )
    save(audio, name)
  except Exception as e:
    print(e)
    text = prompt
    tts = gTTS(text)
    tts.save(name)
    
  return name
  

  
def gen_prompt(openai, text, id, tokens=500):
  global backoff
  user = db[str(id)]
  
  if text[0] == '/':
    return '...'
  
  # Check if the message len is less than the max
  if len(text) > 2500:
    return "Sorry, the Message is too long.."

  # Setup the chat
  messages = []
  user_message = {"role": "user", "content": text}
  
  if len(user['chat']) > 15:
    for item in user['chat'][-15:]:
      messages.append(item.value)
  else:
    for item in user['chat']:
      messages.append(item.value)
  messages.append(user_message)

  completion = None
  try:
    completion = openai.ChatCompletion.create(
      model="gpt-3.5-turbo-16k",
      messages=messages,
      max_tokens=tokens
    )
  except openai.error.APIError:
    return "Something went wrong on the backend, Wait 5 minutes then try again."
  except openai.error.Timeout:
    return "The request took to long to complete, Wait 5 minutes then try again."
  except openai.error.RateLimitError:
    time.sleep(backoff)
    backoff *= 2
    gen_prompt(openai, text, id)
  except openai.error.APIConnectionError:
    return "There is currently planned or unplanned maintanence, check the status page \n       https://status.openai.com/ \n and if the error persists please contact the owner: https://t.me/adoniscodes \n Thank you for your time!"
  except openai.error.ServiceUnavailableError:
    return "The server running the LLM might be unable to handle your request at the moment. Check the status page \n https://status.openai.com/ \n and if the error persists please contact the owner: https://t.me/adoniscodes \n Thank you for your time!"

  backoff = 0
  if completion is None:
    return 'Hello'
    
  messages.append(completion.choices[0].message)
  db[str(id)]['chat'].append(user_message)
  db[str(id)]['chat'].append(completion.choices[0].message)

  return completion.choices[0].message.content

  
def summarize_chats(openai, id):
  global backoff
  user = db[str(id)]
  if len(user['chat']) % 10 == 0:
    sum =  " This is the chat history, Your job is to summarize it including all important info Please include this as the header of the response 'THIS IS A SUMMARY OF THE PAST 10 CHATS': \n"
    for item in user['chat'][-11:]:
      sum += f"{item.value.role}: {item.value.content}"
    try:
      sum = openai.ChatCompletion.create(
      model="gpt-3.5-turbo-16k",
      messages=[{'role':'assistant', 'content': 'Your Job is to summarize the chat history into the important parts based on the user input'},
                {'role':'user', 'content':sum}],
      max_tokens=2000
      )
    except openai.error.APIError:
      return "Something went wrong on the backend, Wait 5 minutes then try again."
    except openai.error.Timeout:
      return "The request took to long to complete, Wait 5 minutes then try again."
    except openai.error.RateLimitError:
      time.sleep(backoff)
      backoff *= 2
      gen_prompt(openai, text, id)
    except openai.error.APIConnectionError:
      return "There is currently planned or unplanned maintanence, check the status page \n       https://status.openai.com/ \n and if the error persists please contact the owner: https://t.me/adoniscodes \n Thank you for your time!"
    except openai.error.ServiceUnavailableError:
      return "The server running the LLM might be unable to handle your request at the moment. Check the status page \n https://status.openai.com/ \n and if the error persists please contact the owner: https://t.me/adoniscodes \n Thank you for your time!"
    db[str(id)]['chat'].append(sum.choices[0].message)


def transcribe_audio(openai, id, audio):
  response = openai.Audio.transcribe("whisper-1", file=open(audio, 'rb'))
  transcript = f"{response['text']}"
  return transcript
