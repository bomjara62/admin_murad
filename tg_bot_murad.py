# -*- coding: utf-8 -*-
import sqlite3
from threading import Thread
from time import sleep
from aiogram.dispatcher import FSMContext
from bs4 import BeautifulSoup
import requests
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from transformers import AutoTokenizer, AutoModelWithLMHead
import re
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
from anypay_api import AnyPay
from admin_panel import AdmPanel
import torch

device = "cuda:0" if torch.cuda.is_available() else "cpu"

print(device)

with open("/root/python_projects/murad_bot/murad_phrases.txt", 'r', encoding='utf-8') as f:
    murad_phrases = f.read().splitlines()
    f.close()

with open("/root/python_projects/murad_bot/info_murad_phrases.txt", 'r', encoding='utf-8') as f:
    murad_phrases_info = f.read().splitlines()
    f.close()

with open("/root/python_projects/murad_bot/bot_token.txt", 'r', encoding='utf-8') as f:
    token = f.read()
    f.close()

with open("/root/python_projects/murad_bot/payment_token.txt", 'r', encoding='utf-8') as f:
    paytokens = f.read().splitlines()
    f.close()

with open("/root/python_projects/murad_bot/admin_list.txt", 'r', encoding='utf-8') as f:
    nicks = f.read().splitlines()
    f.close()

"""
with open("murad_phrases.txt", 'r', encoding='utf-8') as f:
    murad_phrases = f.read().splitlines()
    f.close()

with open("info_murad_phrases.txt", 'r', encoding='utf-8') as f:
    murad_phrases_info = f.read().splitlines()
    f.close()

with open("bot_token.txt", 'r', encoding='utf-8') as f:
    token = f.read()
    f.close()

with open("payment_token.txt", 'r', encoding='utf-8') as f:
    paytokens = f.read().splitlines()
    f.close()

with open("admin_list.txt", 'r', encoding='utf-8') as f:
    nicks = f.read().splitlines()
    f.close()
"""
api_id = paytokens[0].replace('api_id = ', '')
api_key = paytokens[1].replace('api_key = ', '')
project_id = int(paytokens[2].replace('project_id = ', ''))

any_pay = AnyPay(api_id=api_id, api_key=api_key, project_id=project_id)

conn = sqlite3.connect("/root/python_projects/murad_bot/members_info.db")


#conn = sqlite3.connect("members_info.db")

adp = AdmPanel(token, conn, api_id, api_key, project_id)

cur = conn.cursor()

bot = Bot(token=token)

tokenizer = AutoTokenizer.from_pretrained('/root/python_projects/murad_bot/text_models/', add_prefix_space=True)
model = AutoModelWithLMHead.from_pretrained('/root/python_projects/murad_bot/text_models/')

#tokenizer = AutoTokenizer.from_pretrained('./text_models', add_prefix_space=True)
#model = AutoModelWithLMHead.from_pretrained('./text_models')

model.to(device)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

PRICE = types.LabeledPrice(label="Подписка на 1 месяц", amount=299 * 100)


def timechecker():
    while True:
        conn2 = sqlite3.connect("/root/python_projects/murad_bot/members_info.db")
        #conn2 = sqlite3.connect("members_info.db")
        cur2 = conn2.cursor()
        cur2.execute("SELECT * FROM conf")
        conf_list = list(cur2.fetchall())
        for conf in conf_list:
            if str(conf[10]) == str(datetime.today().strftime('%d/%m/%Y')):
                cur2.execute(f"UPDATE conf SET vip=0, vip_date='0/0/0' WHERE conf_id={conf[1]}")
                conn2.commit()
        sleep(30000)


@dp.message_handler(commands=['pro'])
async def buy(message: types.Message):
    payd = random.randint(100, 99999)
    url = await any_pay.create_form_of_payment(pay_id=5154, amount=10.0)
    markup = InlineKeyboardMarkup(row_width=1)
    item1 = InlineKeyboardButton("Проверить оплату", callback_data=f'checkpay_{payd}')
    item2 = InlineKeyboardButton("💰 Оплатить", url=url)
    markup.add(item1, item2)
    await bot.send_message(message.chat.id, """PRO версия даёт возможность контролировать активность
Подробнее о командах для контроля активности /commands 
💰 Стоимость: 299 рублей / месяц""", reply_markup=markup)


@dp.message_handler(commands=['admin'])
async def admins(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in nicks:
        await adp.admin_panel(message, False)


@dp.message_handler(commands=['vip_active'])
async def active(message: types.Message):
    cur.execute(f"SELECT Codes FROM vip_codes WHERE Codes={message.text.replace('/vip_active ', '')}")
    col = cur.fetchone()
    if col is not None:
        date_after_month = datetime.today() + relativedelta(months=1)
        cur.execute(
            f"UPDATE conf SET vip=1, vip_date='{date_after_month.strftime('%d/%m/%Y')}' WHERE conf_id={str(message.chat.id)}")
        await bot.send_message(message.chat.id, "Випка активирована, бля")
        cur.execute(
            f"DELETE FROM vip_codes WHERE Codes='{col[0]}'")
        conn.commit()
    else:
        await bot.send_message(message.chat.id, "Код не найден")


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    cur.execute(f'SELECT * FROM channels')
    channels_list = list(cur.fetchall())
    cur.execute(f"SELECT * FROM users_info WHERE user_id='{message.from_user.id}'")
    user = cur.fetchone()
    if user is None:
        cur.execute(f"INSERT INTO users_info(user_id) VALUES('{message.from_user.id}')")

    conn.commit()
    if channels_list:
        text = ''
        for chn in channels_list:
            text += chn[2] + '\n'
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton(text="Проверить", callback_data='channels_check')
        markup.add(item1)
        await bot.send_message(message.chat.id,
                               f"Для начала использования бота, подпишитесь на эти каналы:\n{text}",
                               reply_markup=markup)

    else:
        if message.text.replace('/start', '') == '':
            markup = InlineKeyboardMarkup(row_width=1)
            item1 = InlineKeyboardButton(text="Добавить бота в чат", url="https://t.me/Murad_Aibot?startgroup=true")
            item2 = InlineKeyboardButton(text="PRO версия", callback_data='pro')
            markup.add(item1, item2)
            await bot.send_message(message.chat.id, f"""
Здарова, братишка <b>{message.from_user.first_name}</b>, я, бля, Мурад —
Я чат-бот который умеет базарить и отвечать на вопросы.
        
Че я могу?
        
1. Базарить со всеё шерстью в беседе.
2. Рассказать историю.
3. Шлю саламы новичкам.
4. Покажу статистику в вашей конфе.
5. Скажу погоду почти в любом городе.
6. Ставить рейтинг участникам, бля.
        
Больше информации о моих умениях вы можете узнать по команде /commands
        """,
                                   reply_markup=markup, parse_mode='html')
        else:
            try:
                link = message.text.replace('/start ', '')
                cur.execute(f'SELECT * FROM links WHERE link_id="{link}"')
                link = list(cur.fetchone())
                if link:
                    cur.execute(f'UPDATE links SET ref_col={link[2] + 1} WHERE ID={link[0]}')
                    cur.execute(f"UPDATE users_info SET user_link='{link[1]}'")
                    conn.commit()
            except:
                pass
            markup = InlineKeyboardMarkup(row_width=1)
            item1 = InlineKeyboardButton(text="Добавить бота в чат", url="https://t.me/Murad_Aibot?startgroup=true")
            item2 = InlineKeyboardButton(text="PRO версия", callback_data='pro')
            markup.add(item1, item2)
            await bot.send_message(message.chat.id, f"""
Здарова, братишка <b>{message.from_user.first_name}</b>, я, бля, Мурад —
Я чат-бот который умеет базарить и отвечать на вопросы.

Че я могу?

1. Базарить со всеё шерстью в беседе.
2. Рассказать историю.
3. Шлю саламы новичкам.
4. Покажу статистику в вашей конфе.
5. Скажу погоду почти в любом городе.
6. Ставить рейтинг участникам, бля.

Больше информации о моих умениях вы можете узнать по команде /commands
                    """,
                                   reply_markup=markup, parse_mode='html')


@dp.message_handler(commands=['commands'])
async def commands_list(message: types.Message):
    markup = InlineKeyboardMarkup(row_width=1)
    item1 = InlineKeyboardButton("Разговор с Мурадом", callback_data='speech')
    item2 = InlineKeyboardButton("Спросить вероятность инфу", callback_data='info')
    item3 = InlineKeyboardButton("Спросить что-то у Мурада", callback_data='ask')
    item5 = InlineKeyboardButton("Спросите погоду", callback_data='weather')
    item6 = InlineKeyboardButton("Другое", callback_data='other')
    markup.add(item1, item2, item3, item5, item6)
    await bot.send_message(chat_id=message.chat.id,
                           text="Ниже представлены возможности бота",
                           reply_markup=markup)


@dp.message_handler(content_types=['new_chat_members'])
async def send_welcome(message: types.Message):
    bot_obj = await bot.get_me()
    bot_id = bot_obj.id
    is_bot = False
    for chat_member in message.new_chat_members:
        if chat_member.id == bot_id:
            count = await bot.get_chat_members_count(message.chat.id)
            cur.execute(f"SELECT * FROM conf WHERE conf_id={message.chat.id}")
            chats = cur.fetchone()
            if chats is None:
                cur.execute("INSERT INTO conf(conf_id, activity, hello, karm, admin, vip, messages, activity_stat, "
                            "speak, start_date, members_count) "
                            f"VALUES({message.chat.id},0,0,0,0,0,0,0,0,'{str(datetime.today().strftime('%d/%m/%Y'))}',{count})")
                conn.commit()
            await bot.send_message(message.chat.id, "Яхаааааййййййй бляяяяяя!!! Дали мне админку быстро, бля")
            is_bot = True

    if not is_bot:
        cur.execute("SELECT * FROM conf WHERE conf_id")
        params = list(cur.fetchone())
        if params[3]:
            await bot.send_message(message.chat.id, "Здарова, братишка")


@dp.message_handler(content_types='text')
async def all_messages_handler(message: types.Message, state: FSMContext):
    if str(message.from_user.id) in nicks and message.chat.type == 'private':
        async with state.proxy() as adata:
            if 'stage' in adata:
                stage = adata['stage']

                if stage == 'add_chn':
                    adata['chn_id'] = message.text
                    adata['stage'] = 'add_chn_2'
                    await bot.send_message(message.chat.id, "Введите ссылку на канал")

                elif stage == 'add_chn_2':
                    chn_id = adata['chn_id']
                    adata['stage'] = None
                    cur.execute(f"INSERT INTO channels(channel_id,channel_link) VALUES('{chn_id}','{message.text}')")
                    conn.commit()
                    await bot.send_message(message.chat.id, "Канал был успешно добавлен")
                    markup = InlineKeyboardMarkup(row_width=1)
                    cur.execute('SELECT * FROM channels')
                    list_chn = list(cur.fetchall())
                    count = 0

                    for i in range(0, len(list_chn)):
                        count += 1
                        markup.add(InlineKeyboardButton(str(list_chn[i][1]),
                                                        callback_data='chnl_' + str(list_chn[i][0])))
                        if count == 5:
                            break

                    item1 = InlineKeyboardButton("<", callback_data='prev_chn')
                    item2 = InlineKeyboardButton(">", callback_data='next_chn')
                    item3 = InlineKeyboardButton("Добавить ссылку", callback_data='add_chn')
                    item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
                    markup.row(item1, item2)
                    markup.add(item3, item4)
                    async with state.proxy() as adata:
                        adata['list_chn'] = list_chn
                        adata['count'] = count
                    await bot.send_message(message.chat.id, "Выберите действие", reply_markup=markup)

                elif stage == 'del_chn':
                    channels_list = message.text.rsplit(',')
                    for channel in channels_list:
                        cur.execute(f"DELETE FROM channels WHERE ID={channel})")
                        conn.commit()
                    adata['stage'] = None
                    await bot.send_message(message.chat.id, "Каналы были успешно удалены")

                elif stage == 'add_lnk':
                    link = message.text

                    cur.execute(f"INSERT INTO links(link_id,ref_col,chat_col) VALUES('{link}',0,0)")
                    conn.commit()
                    adata['stage'] = None
                    markup = InlineKeyboardMarkup(row_width=1)
                    cur.execute('SELECT * FROM links')
                    list_lnk = list(cur.fetchall())
                    count = 0

                    for i in range(0, len(list_lnk)):
                        count += 1
                        markup.add(InlineKeyboardButton(str(list_lnk[i][1]),
                                                        callback_data='link_' + str(list_lnk[i][0])))
                        if count == 5:
                            break

                    item1 = InlineKeyboardButton("<", callback_data='prev')
                    item2 = InlineKeyboardButton(">", callback_data='next')
                    item3 = InlineKeyboardButton("Добавить ссылку", callback_data='add_lnk')
                    item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
                    markup.row(item1, item2)
                    markup.add(item3, item4)
                    async with state.proxy() as adata:
                        adata['list_lnk'] = list_lnk
                        adata['count'] = count

                    await bot.send_message(message.chat.id, "Ссылка была успешно добавлены")
                    await bot.send_message(message.chat.id, "Выберите действие", reply_markup=markup)

                elif stage == 'del_lnk':
                    links_list = message.text.rsplit(',')
                    for link in links_list:
                        cur.execute(f"DELETE FROM links WHERE ID={link})")
                        conn.commit()
                    adata['stage'] = None
                    await bot.send_message(message.chat.id, "Каналы были успешно удалены")

    elif message.chat.type != 'private':
        print(1)
        try:
            cur.execute(f"SELECT * FROM conf WHERE conf_id={message.chat.id}")
            params = list(cur.fetchone())
        except:
            cur.execute("INSERT INTO conf(conf_id, activity, hello, karm, admin, vip, messages, activity_stat, "
                        "speak, start_date) "
                        f"VALUES({message.chat.id},0,0,0,0,0,0,0,0,'{str(datetime.today().strftime('%d/%m/%Y'))}')")
            cur.execute(f"SELECT * FROM conf WHERE conf_id={message.chat.id}")
            params = list(cur.fetchone())
            conn.commit()
        if "мурад, инфа что " == message.text[:16].lower():
            cur.execute(f"UPDATE conf SET activity_stat={int(params[8]) + 1} WHERE conf_id={message.chat.id}")
            text = message.text[16:]
            percent = random.randint(0, 100)
            id3 = random.randint(0, len(murad_phrases_info) - 1)
            await bot.send_message(message.chat.id, murad_phrases_info[id3] + " вероятность, что " + text + " <b>" +
                                   str(percent) + "%</b>", parse_mode="html")

        elif "мурад, скажи погоду в " in message.text.lower():
            cur.execute(f"UPDATE conf SET activity_stat={int(params[8]) + 1} WHERE conf_id={message.chat.id}")
            city = message.text[22:]
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
            }

            res = requests.get(
                f'https://www.google.com/search?q={city} погода&oq={city} погода&aqs=chrome.0.35i39l2j0l4j46j69i60.6128j1j7&sourceid=chrome&ie=UTF-8',
                headers=headers, verify=False
            )

            soup = BeautifulSoup(res.text, 'html.parser')

            time = soup.select('#wob_dts')[0].getText().strip()
            precipitation = soup.select('#wob_dc')[0].getText().strip()
            weather = soup.select('#wob_tm')[0].getText().strip()

            await bot.send_message(message.chat.id, f"Отвечаю, бля, братишка погода в {city}:\n\n"
                                                    f"День недели и время: {time}\n"
                                                    f"Информация об осадках: {precipitation}\n"
                                                    f"Температура воздуха: {weather}°C\n")

        elif message.text.lower() == "мурад, моя репутация":
            cur.execute(
                f"SELECT * FROM users_statistic WHERE user2='{str(message.from_user.id)}' AND rep='+'")
            count_plus = list(cur.fetchall())
            cur.execute(
                f"SELECT * FROM users_statistic WHERE user2='{str(message.from_user.id)}' AND rep='-'")
            count_minus = list(cur.fetchall())
            rep = len(count_plus) - len(count_minus)
            if rep > 0:
                await bot.send_message(message.chat.id,
                                       f"Братишка @{message.from_user.username}, твоя репутация {str(rep)}")
            elif rep < 0:
                await bot.send_message(message.chat.id,
                                       f"Шерсть ебучая @{message.from_user.username}, твоя репутация {str(rep)}")
            else:
                await bot.send_message(message.chat.id,
                                       f"Ты бля хуй знает че @{message.from_user.username}, твоя репутация {str(rep)}")

        elif message.text.lower() == "мурад, статистика":
            await bot.send_message(message.chat.id,
                                   "Статистика в чате:\n"
                                   f"<b>1. Количество сообщений в чате: {params[7]}\n"
                                   f"2. Уровень моей активности: {str((params[8] / params[7]) * 100)}</b>",
                                   parse_mode="html")

        elif message.text.lower() == "мурад, отключи карму":
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.is_chat_admin() or int(params[5]) == 0:
                await bot.send_message(message.chat.id,
                                       f"Карма <b>отключена</b>, бля.", parse_mode="html")
                cur.execute(f"UPDATE conf SET karm=1 WHERE conf_id={message.chat.id}")

        elif message.text.lower() == "мурад, включи карму":
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.is_chat_admin() or int(params[5]) == 0:
                await bot.send_message(message.chat.id,
                                       f"Карма <b>включена</b>, бля.", parse_mode="html")
                cur.execute(f"UPDATE conf SET karm=0 WHERE conf_id={message.chat.id}")

        elif message.text.lower() == "мурад, включись":
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.is_chat_admin() or int(params[5]) == 0:
                if int(params[6]) == 1:
                    await bot.send_message(message.chat.id,
                                           f"ЯХааааааааайййй бляяяяяяяяя!!! Я тут, бля.")
                    cur.execute(f"UPDATE conf SET speak=1 WHERE conf_id={message.chat.id}")
                else:
                    await bot.send_message(message.chat.id,
                                           f"Это только для випки, бля.")

        elif message.text.lower() == "мурад, отключись":
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.is_chat_admin() or int(params[5]) == 0:
                if int(params[6]) == 1:
                    await bot.send_message(message.chat.id,
                                           f"Ай идите нахуй, я съёбываю.")
                    cur.execute(f"UPDATE conf SET speak=0 WHERE conf_id={message.chat.id}")
                else:
                    await bot.send_message(message.chat.id,
                                           f"Это только для випки, бля.")

        elif message.text[:26].lower() == "мурад, уровень активности " and params[6] == 1:
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.is_chat_admin() or int(params[5]) == 0:
                if int(params[6]) == 1:
                    lvl = int(message.text[26:])
                    await bot.send_message(message.chat.id,
                                           f"Понял бля")

                    cur.execute(f"UPDATE conf SET activity={lvl} WHERE conf_id={message.chat.id}")
                else:
                    await bot.send_message(message.chat.id,
                                           f"Это только для випки, бля.")
        elif message.text.lower() == "мурад, команды только для админов":
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.is_chat_admin():
                await bot.send_message(message.chat.id,
                                       f"Понял бля")
                cur.execute(f"UPDATE conf SET admin=1 WHERE conf_id={message.chat.id}")
            else:
                await bot.send_message(message.chat.id,
                                       f"Такое может только админ бля")

        elif message.text.lower() == "мурад, команды для всех":
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.is_chat_admin():
                await bot.send_message(message.chat.id,
                                       f"Понял бля")
                cur.execute(f"UPDATE conf SET admin=0 WHERE conf_id={message.chat.id}")
            else:
                await bot.send_message(message.chat.id,
                                       f"Такое может только админ бля")

        elif message.text.lower() == "мурад, никого не приветствуй":
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.is_chat_admin() or int(params[5]) == 0:
                await bot.send_message(message.chat.id,
                                       f"Понял бля")
                cur.execute(f"UPDATE conf SET hello=0 WHERE conf_id={message.chat.id}")

        elif message.text.lower() == "мурад, приветствуй всех":
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.is_chat_admin() or int(params[5]) == 0:
                await bot.send_message(message.chat.id,
                                       f"Понял бля")
                cur.execute(f"UPDATE conf SET hello=1 WHERE conf_id={message.chat.id}")

        elif "мурад," == message.text[:6].lower():
            cur.execute(f"UPDATE conf SET activity_stat={int(params[8]) + 1} WHERE conf_id={message.chat.id}")
            text = message.text[6:]
            inputs = tokenizer(f'@@ПЕРВЫЙ@@{text} @@ВТОРОЙ@@',
                               return_tensors='pt').to(device)
            force_words = []
            for word in murad_phrases:
                force_words.append(tokenizer(word, add_special_tokens=True).input_ids)

            generated_token_ids = model.generate(
                **inputs,
                top_k=10,
                top_p=0.95,
                num_beams=20,
                num_return_sequences=1,
                do_sample=False,
                no_repeat_ngram_size=2,
                temperature=1.0,
                repetition_penalty=1.2,
                force_words_ids=[force_words],
                length_penalty=1.0,
                eos_token_id=50257,
                max_time=0.5,
                max_new_tokens=50
            ).to(device)

            context_with_response = [tokenizer.decode(sample_token_ids) for sample_token_ids in generated_token_ids]

            result = re.search('@@ВТОРОЙ@@(.*)@@ПЕРВЫЙ@@', str(context_with_response[0]))

            if result is None:
                result = str(context_with_response[0]).split("@@ВТОРОЙ@@", 1)[1]
                await bot.send_message(message.chat.id, result)
            else:
                await bot.send_message(message.chat.id, result.group(1))

        elif message.reply_to_message is not None and int(params[4]) == 0:
            user1 = message.from_user.id
            user2 = message.reply_to_message.from_user.id
            if message.text == '+':
                cur.execute(
                    f"SELECT * FROM users_statistic WHERE user1='{str(user1)}' AND user2='{str(user2)}' AND rep='+'")
                count = cur.fetchall()
                if not count:
                    cur.execute(
                        f"DELETE FROM users_statistic WHERE user1='{str(user1)}' AND user2='{str(user2)}' AND rep='-'")
                    await bot.send_message(message.chat.id,
                                           f"Ты, бля, повысил уровень репутации братишке @{message.reply_to_message.from_user.username}")
                    cur.execute(
                        f"INSERT INTO users_statistic(user1,user2,rep) VALUES('{str(user1)}','{str(user2)}', '+')")
            elif message.text == '-':
                cur.execute(
                    f"SELECT * FROM users_statistic WHERE user1='{str(user1)}' AND user2='{str(user2)}' AND rep='-'")

                count = cur.fetchall()
                if not count:
                    cur.execute(
                        f"DELETE FROM users_statistic WHERE user1='{str(user1)}' AND user2='{str(user2)}' AND rep='+'")
                    await bot.send_message(message.chat.id,
                                           f"Ты, бля, понизил уровень репутации шерсти ебучей @{message.reply_to_message.from_user.username}")
                    cur.execute(
                        f"INSERT INTO users_statistic(user1,user2,rep) VALUES('{str(user1)}','{str(user2)}', '-')")

            conn.commit()

        elif params[9] == 1 and params[6] == 1:
            cur.execute(f"UPDATE conf SET activity_stat={int(params[8]) + 1} WHERE conf_id={message.chat.id}")
            chance = random.randint(0, 100)
            if chance < params[2]:
                text = message.text
                inputs = tokenizer(f'@@ПЕРВЫЙ@@{text} @@ВТОРОЙ@@',
                                   return_tensors='pt')
                force_words = []
                for word in murad_phrases:
                    force_words.append(tokenizer(word, add_special_tokens=True).input_ids)

                generated_token_ids = model.generate(
                    **inputs,
                    top_k=10,
                    top_p=0.95,
                    num_beams=20,
                    num_return_sequences=1,
                    do_sample=False,
                    no_repeat_ngram_size=2,
                    temperature=1.0,
                    repetition_penalty=1.2,
                    force_words_ids=[force_words],
                    length_penalty=1.0,
                    eos_token_id=50257,
                    max_time=2,
                    max_new_tokens=50
                )

                context_with_response = [tokenizer.decode(sample_token_ids) for sample_token_ids in generated_token_ids]

                result = re.search('@@ВТОРОЙ@@(.*)@@ПЕРВЫЙ@@', str(context_with_response[0]))

                if result is None:
                    result = str(context_with_response[0]).split("@@ВТОРОЙ@@", 1)[1]
                    await bot.send_message(message.chat.id, result)
                else:
                    await bot.send_message(message.chat.id, result.group(1))
        cur.execute(f"UPDATE conf SET messages={int(params[7]) + 1} WHERE conf_id={message.chat.id}")
        conn.commit()
    else:
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton(text="Добавить бота в чат", url="https://t.me/Murad_Aibot?startgroup=true")
        item2 = InlineKeyboardButton(text="PRO версия", callback_data='pro')
        markup.add(item1, item2)
        await bot.send_message(message.chat.id, """Я работаю только в групповых чатах.
    
Тыкни на кнопку внизу чтобы добавить меня в свои чаты👇
    """, reply_markup=markup)


@dp.callback_query_handler()
async def callback_inline(call, state: FSMContext):

    if call.data == "back":

        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Разговор с Мурадом", callback_data='speech')
        item2 = InlineKeyboardButton("Спросить вероятность инфу", callback_data='info')
        item3 = InlineKeyboardButton("Спросить что-то у Мурада", callback_data='ask')
        item5 = InlineKeyboardButton("Спросите погоду", callback_data='weather')
        item6 = InlineKeyboardButton("Другое", callback_data='other')
        markup.add(item1, item2, item3, item5, item6)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Ниже представлены возможности бота",
                                    reply_markup=markup)

    elif call.data == "podcat":
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Разговор с Мурадом", callback_data='speech')
        item2 = InlineKeyboardButton("Спросить вероятность инфу", callback_data='info')
        item3 = InlineKeyboardButton("Спросить что-то у Мурада", callback_data='ask')
        item5 = InlineKeyboardButton("Спросить погоду", callback_data='weather')
        item6 = InlineKeyboardButton("Другое", callback_data='other')
        item7 = InlineKeyboardButton("Назад", callback_data='back')
        markup.add(item1, item2, item3, item5, item6, item7)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Ниже представлены возможности бота",
                                    reply_markup=markup)

    elif call.data == "statistic":
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Назад", callback_data='back')
        markup.add(item1)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Вы можете попросить информацию у Мурада о вашей репутации.\n\n"
                                         "<b>1.Мурад, моя репутация</b>.",
                                    reply_markup=markup, parse_mode="html")

    elif call.data == 'channels_check':
        cur.execute('SELECT * FROM channels')
        chn_list = list(cur.fetchall())
        passed = True
        for chn in chn_list:
            user_channel_status = await bot.get_chat_member(chat_id=chn[1], user_id=call.from_user.id)
            if user_channel_status["status"] == 'left':
                passed = False
                break

        if passed:
            markup = InlineKeyboardMarkup(row_width=1)
            item1 = InlineKeyboardButton(text="Добавить бота в чат", url="https://t.me/Murad_Aibot?startgroup=true")
            item2 = InlineKeyboardButton(text="PRO версия", callback_data='pro')
            markup.add(item1, item2)
            await bot.send_message(call.message.chat.id, f"""
Здарова, братишка <b>{call.message.from_user.first_name}</b>, я, бля, Мурад —
Я чат-бот который умеет базарить и отвечать на вопросы.

Че я могу?

1. Базарить со всеё шерстью в беседе.
2. Рассказать историю.
3. Шлю саламы новичкам.
4. Покажу статистику в вашей конфе.
5. Скажу погоду почти в любом городе.
6. Ставить рейтинг участникам, бля.

Больше информации о моих умениях вы можете узнать по команде /commands
                """,
                                   reply_markup=markup, parse_mode='html')
        else:
            await bot.send_message(call.message.chat.id, "Вы не подписаны на все каналы.")

    elif call.data == "info":
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Назад", callback_data='back')
        markup.add(item1)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Вы можете спросить у Мурада вероятность того или иного "
                                         "события.\n\nПример:\n\n"
                                         "<b>1.Мурад, инфа что сегодня будет второе пришествие Иисуса\n"
                                         "2.Мурад, инфа что ты наебёшь таксиста\n"
                                         "3.Мурад, инфа что завтра ко мне приедет Путин</b>.",
                                    reply_markup=markup, parse_mode="html")

    elif call.data == "speech":
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Назад", callback_data='back')
        markup.add(item1)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Вы можете поговорить с Мурадом на"
                                         "разные темы.\n\nПример:\n\n"
                                         "<b>1.Мурад, как дела?\n"
                                         "2.Мурад, что с таксистом было?\n"
                                         "3.Мурад, яхаааааааай бляяяяяяяя</b>.",
                                    reply_markup=markup, parse_mode="html")

    elif call.data == "ask":
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Назад", callback_data='back')
        markup.add(item1)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Вы можете задать Мураду разные вопросы.\n\nПример:\n\n"
                                         "<b>1.Мурад, ты наебал того таксиста?\n"
                                         "2.Мурад, кто такой Путин?\n"
                                         "3.Мурад, что такое баран?</b>.",
                                    reply_markup=markup, parse_mode="HTML")

    elif call.data == "weather":
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Назад", callback_data='back')
        markup.add(item1)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Вы можете спросить у Мурада погоду.\n\nПример:\n\n"
                                         "<b>Мурад, скажи погоду в Москве</b>",
                                    reply_markup=markup, parse_mode="HTML")

    elif call.data == "other":
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Назад", callback_data='back')
        markup.add(item1)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="У Мурада присутствуют следующие фукнции:\n\n"
                                         "1. Статистика:\n"
                                         "<b>Мурад, статистика.</b>\n\n"
                                         "2. Отключение и включение кармы:\n"
                                         "<b>Мурад, отключи карму\n"
                                         "Мурад, включи карму</b>.\n\n"
                                         "3. Приветствие новых членов в беседе:\n"
                                         "<b>Мурад, приветствуй всех\n"
                                         "Мурад, никого не приветствуй</b>\n\n"
                                         "4. Включение команд только для админов(Может вызвать только сам админ)\n:"
                                         "<b>Мурад, команды для всех\n"
                                         "Мурад, команды только для админов\n\n</b>"
                                         "5. Регулировка активности(бот будет отвечать на все сообщения в чате. Только вип):\n"
                                         "<b>Мурад, включись.\n"
                                         "Мурад, отключись.\n"
                                         "Мурад, уровень активности (целое число).</b>",
                                    reply_markup=markup, parse_mode="HTML")

    elif "checkpay_" in call.data:
        payd = int(str(call.data).replace("checkpay_"))
        res = any_pay.get_payments(pay_id=payd)
        id = list(res['result']['payments'])[len(list(res['result']['payments'])) - 1]
        status = res['result']['payments'][id]['status']
        if status == 'paid':
            date_after_month = datetime.today() + relativedelta(months=1)
            cur.execute(
                f"UPDATE conf SET vip=1, vip_date='{date_after_month.strftime('%d/%m/%Y')}' WHERE conf_id={call.message.text.replace('/pro_active ', '')}")
            await bot.send_message(call.message.chat.id, "Випка активирована, бля")
            conn.commit()
        else:
            await bot.send_message(call.message.chat.id, "Оплата не прошла бля")

    elif call.data == 'pro':
        await buy(call.message)

    elif call.data == 'pre_pro':
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Купить PRO версию", callback_data='pro')
        markup.add(item1)
        await bot.send_message(call.message.chat.id, """PRO версия даёт контроль над активностью, от 0 до 100%

Упал актив в чате, скучно или нечего делать? Включи Мурада. Поверьте, PRO версия Мурада сможет удивить весь чат

Подробнее о командах для контроля активности /commands 

💰 Стоимость: 299 рублей / месяц

Внимание! Активировать и оплачивать нужно только в нужном групповом чате!
""", reply_markup=markup)

    elif call.data == 'stat':
        await adp.admin_stat(call.message)

    elif call.data == 'admin_panel':
        await adp.admin_panel(call.message, True)

    elif call.data == 'links':
        markup = InlineKeyboardMarkup(row_width=1)
        cur.execute('SELECT * FROM links')
        list_lnk = list(cur.fetchall())
        count = 0

        for i in range(0, len(list_lnk)):
            count += 1
            markup.add(InlineKeyboardButton(str(list_lnk[i][1]),
                                            callback_data='link_' + str(list_lnk[i][0])))
            if count == 5:
                break

        item1 = InlineKeyboardButton("<", callback_data='prev')
        item2 = InlineKeyboardButton(">", callback_data='next')
        item3 = InlineKeyboardButton("Добавить ссылку", callback_data='add_lnk')
        item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
        markup.row(item1, item2)
        markup.add(item3, item4)
        async with state.proxy() as adata:
            adata['list_lnk'] = list_lnk
            adata['count'] = count
        await call.message.edit_text("Выберите действие", reply_markup=markup)

    elif call.data == 'vip_code':
        await adp.add_vip(call.message)
    elif call.data == 'next':
        async with state.proxy() as adata:
            list_lnk = adata['list_lnk']
            count = adata['count']
        if count < len(list_lnk):
            markup = InlineKeyboardMarkup(row_width=1)
            end_count = count + 5
            for i in range(count, end_count):
                if i == len(list_lnk):
                    count = len(list_lnk) + (5 - (len(list_lnk) % 5))
                    break
                count += 1
                markup.add(InlineKeyboardButton(str(list_lnk[i][1]),
                                                callback_data='link_' + str(list_lnk[i][0])))

            item1 = InlineKeyboardButton("<", callback_data='prev')
            item2 = InlineKeyboardButton(">", callback_data='next')
            item3 = InlineKeyboardButton("Добавить ссылку", callback_data='add_lnk')
            item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
            markup.row(item1, item2)
            markup.add(item3, item4)
            await call.message.edit_text("Выберите действие", reply_markup=markup)
            async with state.proxy() as adata:
                adata['list_lnk'] = list_lnk
                adata['count'] = count

    elif call.data == 'prev':
        async with state.proxy() as adata:
            list_lnk = adata['list_lnk']
            count = adata['count']
        if count > 5:
            markup = InlineKeyboardMarkup(row_width=1)
            end_count = count - 5
            count = count - 10

            if end_count < 0:
                end_count = 0

            for i in range(count, end_count):
                count += 1
                markup.add(InlineKeyboardButton(str(list_lnk[i][1]),
                                                callback_data='link_' + str(list_lnk[i][0])))

            item1 = InlineKeyboardButton("<", callback_data='prev')
            item2 = InlineKeyboardButton(">", callback_data='next')
            item3 = InlineKeyboardButton("Добавить ссылку", callback_data='add_lnk')
            item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
            markup.row(item1, item2)
            markup.add(item3, item4)

            await call.message.edit_text("Выберите действие", reply_markup=markup)
            async with state.proxy() as adata:
                adata['list_lnk'] = list_lnk
                adata['count'] = count

    elif 'link' in call.data:
        id = str(call.data).replace('link_', '')
        cur.execute(f'SELECT * FROM links WHERE ID={id}')
        link = list(cur.fetchone())
        cur.execute(f'SELECT * FROM users_info WHERE user_link="{link[1]}"')
        conn.commit()
        users_count = list(cur.fetchall())
        cur.execute('SELECT * FROM conf')
        conf_list = list(cur.fetchall())
        count = 0
        for user in users_count:
            for conf in conf_list:
                try:
                    user_channel_status = await bot.get_chat_member(chat_id=conf[1], user_id=user[1])
                    if user_channel_status["status"] != 'left':
                        count += 1
                except:
                    pass
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("❌ Удалить", callback_data='del_lnks_1' + id)
        item2 = InlineKeyboardButton("Назад", callback_data='links')
        markup.add(item1, item2)
        await call.message.edit_text(f'''
Название: {link[1]}
URL: https://t.me/Murad_Aibot?start={link[1]}

Переходов: {link[2]}
Новых юзеров (приватные чаты): {count}
                ''', reply_markup=markup)

    elif call.data[:10] == 'del_lnks_1':
        id = str(call.data).replace('del_lnks_1', '')
        print(id)
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Удалить", callback_data='del_lnks_2' + id)
        item2 = InlineKeyboardButton("Назад", callback_data='links')
        markup.add(item1, item2)

        await call.message.edit_text("Вы точно хотите удалить ссылку?", reply_markup=markup)

    elif call.data[:10] == 'del_lnks_2':
        id = str(call.data).replace('del_lnks_2', '')
        print(id)
        cur.execute(f"DELETE FROM links WHERE ID={id}")
        conn.commit()
        markup = InlineKeyboardMarkup(row_width=1)
        cur.execute('SELECT * FROM links')
        list_lnk = list(cur.fetchall())
        count = 0

        for i in range(0, len(list_lnk)):
            count += 1
            markup.add(InlineKeyboardButton(str(list_lnk[i][1]),
                                            callback_data='link_' + str(list_lnk[i][0])))
            if count == 5:
                break

        item1 = InlineKeyboardButton("<", callback_data='prev')
        item2 = InlineKeyboardButton(">", callback_data='next')
        item3 = InlineKeyboardButton("Добавить ссылку", callback_data='add_lnk')
        item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
        markup.row(item1, item2)
        markup.add(item3, item4)
        async with state.proxy() as adata:
            adata['list_lnk'] = list_lnk
            adata['count'] = count
        await call.message.edit_text("Выберите действие", reply_markup=markup)

    elif call.data == 'channels':
        markup = InlineKeyboardMarkup(row_width=1)
        cur.execute('SELECT * FROM channels')
        list_chn = list(cur.fetchall())
        count = 0

        for i in range(0, len(list_chn)):
            count += 1
            markup.add(InlineKeyboardButton(str(list_chn[i][1]),
                                            callback_data='chnl_' + str(list_chn[i][0])))
            if count == 5:
                break

        item1 = InlineKeyboardButton("<", callback_data='prev_chn')
        item2 = InlineKeyboardButton(">", callback_data='next_chn')
        item3 = InlineKeyboardButton("Добавить канал", callback_data='add_chn')
        item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
        markup.row(item1, item2)
        markup.add(item3, item4)
        async with state.proxy() as adata:
            adata['list_chn'] = list_chn
            adata['count'] = count
        await call.message.edit_text("Выберите действие", reply_markup=markup)

    elif call.data == 'next_chn':
        async with state.proxy() as adata:
            list_chn = adata['list_chn']
            count = adata['count']
        if count < len(list_chn):
            markup = InlineKeyboardMarkup(row_width=1)
            end_count = count + 5
            for i in range(count, end_count):
                if i == len(list_chn):
                    count = len(list_chn) + (5 - (len(list_chn) % 5))
                    break
                count += 1
                markup.add(InlineKeyboardButton(str(list_chn[i][1]),
                                                callback_data='chnl_' + str(list_chn[i][0])))

            item1 = InlineKeyboardButton("<", callback_data='prev_chn')
            item2 = InlineKeyboardButton(">", callback_data='next_chn')
            item3 = InlineKeyboardButton("Добавить канал", callback_data='add_chn')
            item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
            markup.row(item1, item2)
            markup.add(item3, item4)
            await call.message.edit_text("Выберите действие", reply_markup=markup)
            async with state.proxy() as adata:
                adata['list_chn'] = list_chn
                adata['count'] = count

    elif call.data == 'prev_chn':
        async with state.proxy() as adata:
            list_chn = adata['list_chn']
            count = adata['count']
        if count > 5:
            markup = InlineKeyboardMarkup(row_width=1)
            end_count = count - 5
            count = count - 10

            if end_count < 0:
                end_count = 0

            for i in range(count, end_count):
                count += 1
                markup.add(InlineKeyboardButton(str(list_chn[i][1]),
                                                callback_data='chnl_' + str(list_chn[i][0])))

            item1 = InlineKeyboardButton("<", callback_data='prev_chn')
            item2 = InlineKeyboardButton(">", callback_data='next_chn')
            item3 = InlineKeyboardButton("Добавить ссылку", callback_data='add_chn')
            item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
            markup.row(item1, item2)
            markup.add(item3, item4)

            await call.message.edit_text("Выберите действие", reply_markup=markup)
            async with state.proxy() as adata:
                adata['list_chn'] = list_chn
                adata['count'] = count

    elif 'chnl' in call.data:
        id = str(call.data).replace('chnl', '')

        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("❌ Удалить", callback_data='del_chns_1' + id)
        item2 = InlineKeyboardButton("Назад", callback_data='channels')
        markup.add(item1, item2)
        await call.message.edit_text("Выберите действие", reply_markup=markup)

    elif call.data[:10] == 'del_chns_1':
        id = str(call.data).replace('del_chns_1', '')
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Удалить", callback_data='del_chns_2' + id)
        item2 = InlineKeyboardButton("Назад", callback_data='links')
        markup.add(item1, item2)

        await call.message.edit_text("Вы точно хотите удалить канал?", reply_markup=markup)

    elif call.data[:10] == 'del_chns_2':
        id = str(call.data).replace('del_chns_2_', '')
        cur.execute(f"DELETE FROM channels WHERE ID={id}")
        conn.commit()
        markup = InlineKeyboardMarkup(row_width=1)
        cur.execute('SELECT * FROM channels')
        list_lnk = list(cur.fetchall())
        count = 0

        for i in range(0, len(list_lnk)):
            count += 1
            markup.add(InlineKeyboardButton(str(list_lnk[i][1]),
                                            callback_data='chnl_' + str(list_lnk[i][0])))
            if count == 5:
                break

        item1 = InlineKeyboardButton("<", callback_data='prev_chn')
        item2 = InlineKeyboardButton(">", callback_data='next_chn')
        item3 = InlineKeyboardButton("Добавить канал", callback_data='add_chn')
        item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
        markup.row(item1, item2)
        markup.add(item3, item4)
        async with state.proxy() as adata:
            adata['list_chn'] = list_lnk
            adata['count'] = count
        await call.message.edit_text("Выберите действие", reply_markup=markup)

    elif call.data[:8] == 'del_chns':
        id = str(call.data).replace('del_chns_', '')
        cur.execute(f"DELETE FROM channels WHERE ID={id}")
        conn.commit()
        markup = InlineKeyboardMarkup(row_width=1)
        cur.execute('SELECT * FROM channels')
        list_chn = list(cur.fetchall())
        count = 0

        for i in range(0, len(list_chn)):
            count += 1
            markup.add(InlineKeyboardButton(str(list_chn[i][0]) + " " + str(list_chn[i][1]),
                                            callback_data='chnl_' + str(list_chn[i][0])))
            if count == 5:
                break

        item1 = InlineKeyboardButton("<", callback_data='prev_chn')
        item2 = InlineKeyboardButton(">", callback_data='next_chn')
        item3 = InlineKeyboardButton("Добавить ссылку", callback_data='add_lnk')
        item4 = InlineKeyboardButton("Назад", callback_data='admin_panel')
        markup.row(item1, item2)
        markup.add(item3, item4)
        async with state.proxy() as adata:
            adata['list_chn'] = list_chn
            adata['count'] = count
        await call.message.edit_text("Выберите действие", reply_markup=markup)

    elif 'lnk' in call.data:
        print(call.data)
        async with state.proxy() as adata:
            adata['stage'] = await adp.links(call.message, call.data)

    elif 'chn' in call.data:
        print(call.data)
        async with state.proxy() as adata:
            adata['stage'] = await adp.channels(call.message, call.data)

    elif call.data == 'export':
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Юзеры (приватные чаты)", callback_data='users_export')
        item2 = InlineKeyboardButton("Группы", callback_data='group_export')
        item3 = InlineKeyboardButton("Назад", callback_data='admin_panel')
        markup.add(item1, item2, item3)
        await call.message.edit_text("Выберите действие", reply_markup=markup)

    elif 'export' in call.data:
        await adp.export(call.message, call.data)


if __name__ == '__main__':
    th = Thread(target=timechecker)
    th.start()
    executor.start_polling(dp, skip_updates=True)
