import random
import traceback
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dateutil.relativedelta import relativedelta

from anypay_api import AnyPay


class AdmPanel:
    def __init__(self, bot_token, conn, api_id, api_key, project_id):
        self.bot = Bot(token=bot_token)
        self.conn = conn
        self.cur = self.conn.cursor()
        self.any_pay = AnyPay(api_id=api_id, api_key=api_key, project_id=project_id)

    async def admin_panel(self, message, is_edit):
        admin_start_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Каналы", callback_data='channels')],
            [InlineKeyboardButton(text="Статистика", callback_data='stat')],
            [InlineKeyboardButton(text="Ссылки", callback_data='links')],
            [InlineKeyboardButton(text="Экспорт чатов", callback_data='export')],
            [InlineKeyboardButton(text="Сгенерировать вип код", callback_data='vip_code')],
        ])
        if is_edit:
            await message.edit_text("Выберите функцию", reply_markup=admin_start_keyboard)
        else:
            await self.bot.send_message(message.chat.id, "Выберите функцию", reply_markup=admin_start_keyboard)

    async def admin_stat(self, message):

        cur_date = str(datetime.today().strftime('%d/%m/%Y'))
        yesterday_date = str((datetime.today() - relativedelta(days=1)).strftime('%d/%m/%Y'))
        self.cur.execute(f"SELECT members_count FROM conf WHERE start_date='" + cur_date + "'")
        list_today = list(self.cur.fetchall())

        members_today_count = 0

        for i in list_today:
            try:
                members_today_count += i[0]
            except:
                pass
        self.cur.execute(f"SELECT members_count FROM conf WHERE start_date='" + yesterday_date + "'")

        list_yesterday = list(self.cur.fetchall())
        members_yest_count = 0
        for i in list_yesterday:
            try:
                members_yest_count += int(i[0])
            except:
                pass

        self.cur.execute(f"SELECT members_count FROM conf")

        list_all = list(self.cur.fetchall())
        members_all = 0

        for i in list_all:
            try:
                members_all += i[0]
            except:
                pass
        print(3)
        self.cur.execute(f"SELECT user1 FROM users_statistic")

        unic = list(self.cur.fetchall())

        unic = list(set(unic))
        markup = InlineKeyboardMarkup(row_width=1)
        item1 = InlineKeyboardButton("Назад", callback_data='admin_panel')
        markup.add(item1)
        balance = None
        try:
            balance = (await self.any_pay.get_balance())['result']['balance']
        except:
            pass

        await message.edit_text(f'''
Баланс anypay: {balance}  
Вчера
Новые юзеры (приватные чаты): {members_yest_count}
Новые групы: {len(list_yesterday)}

Сегодня
Новые юзеры (приватные чаты): {members_today_count}
Новые групы: {len(list_today)}

Общее:
Кол-во уникальных юзеров во всех чатах: {len(unic)}
Кол-во юзеров во всех чатах: {members_all}
Кол-во груп: {len(list_all)}''', reply_markup=markup)

    async def add_vip(self, message):

        vip_code = random.randint(0, 99999)
        self.cur.execute(f"INSERT INTO vip_codes(Codes) VALUES('{str(vip_code)}')")
        await self.bot.send_message(message.chat.id, "Ваш вип код " + str(vip_code)
                                    + " активация /vip_active <код> в нужной беседе")
        self.conn.commit()

    async def links(self, message, do_type):
        if do_type == 'add_lnk':
            await self.bot.send_message(message.chat.id, "Введите имя ссылки")
            return 'add_lnk'
        elif do_type == 'del_lnk':
            await self.bot.send_message(message.chat.id, "Введите id каналов")
            return 'del_lnk'
        elif do_type == 'list_lnk':
            self.cur.execute('SELECT * FROM links')
            list_chn = list(self.cur.fetchall())
            text = ''
            for chn in list_chn:
                text += str(chn[0]) + " " + str(chn[1]) + "\n"

            await self.bot.send_message(message.chat.id, "Список ссылок:\n" + text)
            return None

    async def channels(self, message, do_type):
        if do_type == 'add_chn':
            await self.bot.send_message(message.chat.id, "Введите ID канала")
            return 'add_chn'
        elif do_type == 'del_chn':
            await self.bot.send_message(message.chat.id, "Введите номера каналов через запятую"
                                                   " для удаления их из базы данных")
            return 'del_chn'
        elif do_type == 'list_chn':
            self.cur.execute('SELECT * FROM channels')
            list_chn = list(self.cur.fetchall())
            text = ''
            for chn in list_chn:
                text += str(chn[0]) + " " + str(chn[1]) + "\n"

            await self.bot.send_message(message.chat.id, "Список каналов:\n" + text)
            return None

    async def export(self, message, export_type):
        if export_type == 'users_export':
            self.cur.execute(f"SELECT user1 FROM users_statistic")

            unic = list(self.cur.fetchall())

            unic = list(set(unic))
            text = ''
            count = 0
            for un in unic:
                count += 1
                text += str(count) + ' ' + str(un[0]) + '\n'

            with open("export_users.txt", "w") as file:
                file.write(text)
                file.close()
            with open("export_users.txt", "rb") as file:
                await self.bot.send_document(chat_id
                                             =message.chat.id, document=file)

        elif export_type == 'group_export':
            self.cur.execute(f"SELECT * FROM conf")

            unic = list(self.cur.fetchall())

            unic = list(set(unic))

            text = ''
            for un in unic:
                text += str(un[0]) + ' ' + str(un[1]) + '\n'

            with open("export_groups.txt", "w") as file:
                file.write(text)
                file.close()
            with open("export_groups.txt", "rb") as file:
                await self.bot.send_document(chat_id
                                             =message.chat.id, document=file)
