import telebot
import httplib2
import google_auth_httplib2
import googleapiclient
from telebot import types
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload,MediaFileUpload
from googleapiclient.discovery import build
from bot_token import TOKEN


G_SPREADSHEET_ID = '1IyJ_mmmj4i61B23BJnWLKTc70JvfYVMLbCewBoo2QS8'
G_SHEET_ID = '0'
bot = telebot.TeleBot(TOKEN.bot_token)

class GENDERS:
    MAN = 'Мужской'
    WOMAN = 'Женский'


def get_service_acc():

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = "./mybodybot-94a1b4ae7af4.json"
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    return build('sheets', 'v4', credentials=credentials)


@bot.message_handler(commands=["start"])
def start(m, res=False):
    '''Функция обработки слэш-команды /start'''
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button1 = types.KeyboardButton("Поехали!")
    markup.add(button1)
    bot.send_message(
        m.chat.id,
        'Добрый день! \n\nИндекс массы тела (ИМТ) – величина, позволяющая оценить степень соответствия '\
        'массы человека и его роста и тем самым, '\
        'косвенно, оценить, является ли масса недостаточной, нормальной или избыточной. '\
        '\n\nРассчитайте свой ИМТ и получите подарок от MyGenetics!',
        reply_markup=markup
    )


@bot.message_handler(regexp="Начать заново")
@bot.message_handler(regexp="Поехали!")
def handle_text(message):

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button1 = types.KeyboardButton(GENDERS.MAN)
    button2 = types.KeyboardButton(GENDERS.WOMAN)
    markup.add(button1, button2)
    message = bot.send_message(message.chat.id, text="Укажите свой пол", reply_markup = markup)
    bot.send_message(message.chat.id, text="А вы знали что у мужчин и женщин разное…")
    bot.register_next_step_handler(message, gendre_pass, person={})


def gendre_pass(message, person):

    if message.text not in [GENDERS.MAN, GENDERS.WOMAN]:
        bot.send_message(message.chat.id, text=person['gender'])
        bot.send_message(message.chat.id, text='Указан неправильный пол, попробуйте ещё раз')
        return handle_text(message)
    person['gender'] = message.text
    message = bot.send_message(message.chat.id, text="Укажите ваш рост в сантиметрах")
    bot.send_message(message.chat.id, text="Рост человека напрямую влияет…")
    bot.register_next_step_handler(message, height_pass, person=person)


def height_pass(message, person):

    if message.text.isnumeric():
        person['height'] = int(message.text)
        message = bot.send_message(message.chat.id, text="Укажите ваш вес в килограммах")
        bot.send_message(message.chat.id, text="Вес человека меняется в зависимости от…")
        bot.register_next_step_handler(message, weight_pass, person=person)
    else:
        bot.send_message(message.chat.id, text='Указан неверный рост, попробуйте ещё раз')
        bot.register_next_step_handler(message, height_pass, person=person)


def weight_pass(message, person):

    if message.text.isnumeric():
        person['weight'] = int(message.text)
        person['imt'] = (person['weight']/((person['height']/100)*(person['height']/100)))
        bot.send_message(
            message.chat.id, 
            text="Укажите Ваш возраст, \nЭто позволит нам максимально точно расчитать результаты"
        )
        bot.register_next_step_handler(message, contact_req, person=person)
    else:
        bot.send_message(message.chat.id, text='Указан неверный вес, попробуйте ещё раз')
        bot.register_next_step_handler(message, weight_pass, person=person)


def contact_req(message, person):
    '''кнопка запроса контакта у пользователя'''
    if message.text.isnumeric():
        person['age'] = int(message.text)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        button1 = types.KeyboardButton("Поделиться контактом", request_contact=True)
        markup.add(button1)
        bot.send_message(
            message.chat.id, 
            text='Ваши результаты почти готовы! \nНажмите “Поделиться контактом”, чтобы'\
                ' получить значение вашего ИМТ, а также подарок от MyGenetics!',
                reply_markup=markup
        )
        bot.register_next_step_handler(message, contact_send, person=person)
    else:
        bot.send_message(message.chat.id, text='Указан неверный возраст, попробуйте ещё раз')
        bot.register_next_step_handler(message, contact_req, person=person)


@bot.message_handler(content_types=['contact'])
def contact_send(message, person):

    person['name'] = message.contact.phone_number
    person['phone'] = message.contact.first_name
    body = {
        'values':[
            [person['name'], person['phone']],
        ]
    }
    request = get_service_acc().spreadsheets().values().append(
                                                                spreadsheetId=G_SPREADSHEET_ID, 
                                                                range="Лист1!A1",
                                                                valueInputOption='RAW',
                                                                body=body)
    request.execute()

    return imt_pass(message, person)


def imt_pass(message, person):
    f_let = 'На основе введенных вами данных ваш ИМТ = '
    s_let_low = ', что говорит о недостаточной массе тела при соответствующих показателях роста, пола и возраста.'
    s_let_norm =', что соответствует нормальному весу.\n\nСтановиться лучшей версией себя – это отлично, надеемся,'\
                'что в этом вам поможет наш подарок, '\
                'чек-лист “____”, который вы можете получить по этой ссылке: '\
                '*КАКОЙ ССЫЛКЕ??*.'\
                '\n\nБольше о ваших индивидуальных особенностях питания, усвоения белков, жиров и углеводах, '\
                'подходящих именно вам спорте и диетах, '\
                'а также о многом другом вы можете с помощью ДНК-тестов MyWellness и MyExpert.'\
                '\n\nНапишите нашим экспертам, которые помогут подобрать тест, который поможет вам выбрать '\
                'ДНК-тест совершенно бесплатно: @МЕНЕДЖЕР??.'
    s_let_hi = ', что свидетельствует о небольшом количестве избыточного веса.'
    s_let_12 = ', что соответствует ожирению 1-2 степени, согласно данным Всемирной организации здравоохранения.'
    s_let_3 = ', что соответствует ожирению 3 степени, согласно данным Всемирной организации здравоохранения.'    
    if(person['age']<18):
        bot.send_message(
                        message.chat.id, 
                        text='Простите-извините, но вы ещё слишком юны, чтобы заморачиваться с '\
                        'этим\nЖивите и радуйтесь жизни'
        ) 
    if(person['gender'] == GENDERS.WOMAN):
        if((person['age']<=24)&(person['age']>=18)):
            if(person['imt']<19):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']>=19)&(person['imt']<=24)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=29)&(person['imt']>24)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=39)&(person['imt']>29)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>39):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif((person['age']<=34)&(person['age']>=25)):
            if(person['imt']<20):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=25)&(person['imt']>=20)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=30)&(person['imt']>25)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=40)&(person['imt']>30)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>40):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif((person['age']<=44)&(person['age']>=35)):
            if(person['imt']<21):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=26)&(person['imt']>=21)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=31)&(person['imt']>26)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=41)&(person['imt']>31)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>41):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif((person['age']<=54)&(person['age']>=45)):
            if(person['imt']<22):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=27)&(person['imt']>=22)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=32)&(person['imt']>27)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=42)&(person['imt']>32)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>42):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif((person['age']<=64)&(person['age']>=55)):
            if(person['imt']<23):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=28)&(person['imt']>=23)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=33)&(person['imt']>28)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=43)&(person['imt']>33)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>43):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif(person['age']>=65):
            if(person['imt']<24):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=29)&(person['imt']>=24)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=34)&(person['imt']>29)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=44)&(person['imt']>34)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>44):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
    elif(person['gender'] == GENDERS.MAN):
        if((person['age']<=24)&(person['age']>=18)):
            if(person['imt']<20):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']>=20)&(person['imt']<=25)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=30)&(person['imt']>25)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=40)&(person['imt']>30)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>40):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif((person['age']<=34)&(person['age']>=25)):
            if(person['imt']<21):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=26)&(person['imt']>=21)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=31)&(person['imt']>26)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=41)&(person['imt']>31)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>41):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif((person['age']<=44)&(person['age']>=35)):
            if(person['imt']<22):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=27)&(person['imt']>=22)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=32)&(person['imt']>27)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=42)&(person['imt']>32)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>42):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif((person['age']<=54)&(person['age']>=45)):
            if(person['imt']<23):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=28)&(person['imt']>=23)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=33)&(person['imt']>28)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=43)&(person['imt']>33)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>43):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif((person['age']<=64)&(person['age']>=55)):
            if(person['imt']<24):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=29)&(person['imt']>=24)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=34)&(person['imt']>29)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=44)&(person['imt']>34)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>44):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
        elif(person['age']>=65):
            if(person['imt']<25):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_low)
            elif((person['imt']<=30)&(person['imt']>=25)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_norm)
            elif((person['imt']<=35)&(person['imt']>30)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_hi)
            elif((person['imt']<=45)&(person['imt']>35)):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_12)
            elif(person['imt']>45):
                bot.send_message(message.chat.id, text=f_let+str(person['imt'])+s_let_3)                
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button1 = types.KeyboardButton("Начать заново")
    button2 = types.KeyboardButton("Поделиться")
    markup.add(button1, button2)
    bot.send_message(
        message.chat.id, 
        text='Наша команда каждый день ломает голову, как бы выдать побольше пользы.'\
            '\nОцените, насколько бот смог помочь вам: 1-10, где 1 - красивый, но не помогло, а 10'\
            '- спасибо, это прекрасно, а есть еще?', 
        reply_markup = markup
    )
       

if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0)