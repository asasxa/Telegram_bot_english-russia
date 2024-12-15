from dirty_main import *

load_dotenv()

token_telegram = os.getenv("TOKEN_TELEGRAM")
type_db = os.getenv("DB_TYPE")
login = os.getenv("DB_LOGIN")
password = os.getenv("DB_PASSWORD")
name_db = os.getenv("DB_NAME")

DSN = f'{type_db}://{login}:{password}@localhost:5432/{name_db}'
engine = sqlalchemy.create_engine(DSN)

Session = sessionmaker(bind=engine)
session = Session()

bot = telebot.TeleBot(token_telegram)

def safe_commit(action):
    try:
        action()
        session.commit()
    except Exception as e:
        print(f"Ошибка: {e}")
        session.rollback()

def create_tables(engine):
    Base.metadata.create_all(engine)

    with engine.connect() as connection:
        for word_ru, word_en in common_words:
            if not connection.execute(select(Common_word).where(Common_word.word_ru == word_ru)).fetchone():
                connection.execute(Common_word.__table__.insert().values(word_ru=word_ru, word_en=word_en))
        connection.commit()

def add_user(user_id, username):
    def action():
        new_user = User(user_id=user_id, username=username)
        session.add(new_user)
    safe_commit(action) 

def add_word(word_ru, word_en, user_id):
    if session.query(Common_word).filter(Common_word.word_ru == word_ru).first():
        print(f"Слово '{word_ru}' уже существует в общих словах.")
        return None, None

    new_word = Word(word_ru=word_ru, word_en=word_en)
    session.add(new_word)
    session.commit()
    word_id = new_word.word_id

    link_user_word(user_id, word_id)  

    count_of_words = session.query(User_word).filter(User_word.user_id == user_id).count()

    return word_id, count_of_words
    
def link_user_word(user_id, word_id):
    if session.query(User_word).filter(User_word.user_id == user_id, User_word.word_id == word_id).first():
        return
    user_word = User_word(user_id=user_id, word_id=word_id)
    safe_commit(lambda: session.add(user_word))

def remove_word_from_dictionary(word_ru, user_id):
    print(f"Попытка удалить слово: '{word_ru}' для пользователя: {user_id}")
    
    word = session.query(Word).filter(Word.word_ru.ilike(word_ru)).first()
    common_word = session.query(Common_word).filter(Common_word.word_ru.ilike(word_ru)).first()

    if common_word:
        print(f"Слово '{word_ru}' является общим и не может быть удалено.")
        return False

    if word:
        deleted = session.query(User_word).filter(User_word.word_id == word.word_id, User_word.user_id == user_id).delete(synchronize_session=False)
        remaining_users = session.query(User_word).filter(User_word.word_id == word.word_id).count() 
        if deleted and remaining_users == 0:
            session.delete(word)
            print(f"Слово: '{word.word_ru}' удалено из базы данных.")
        
        session.commit() 
        
        if deleted:
            print(f"Слово: '{word.word_ru}' успешно удалено для пользователя: {user_id}.")
            add_user_activity(user_id, "Удаление слова")
            return True
    else:
        print(f"Слово '{word_ru}' не найдено в базе данных.")
    return False

def add_user_activity(user_id, activity_type):
    new_activity = User_activity(user_id=user_id, activity_type=activity_type, activity_datetime=datetime.now())
    safe_commit(lambda: session.add(new_activity))

def view_dictionary(user_id):
    user_words = session.query(User_word).filter(User_word.user_id == user_id).all()
    word_ids = [user_word.word_id for user_word in user_words]
    
    if not word_ids:
        return "Ваш словарь пуст. Вы можете воспользоватсья базовым словарем"
    
    words = session.query(Word).filter(Word.word_id.in_(word_ids)).all()
    words_list = [f"{word.word_ru} - {word.word_en}" for word in words]
    
    return "\n".join(words_list) if words_list else "Ваш словарь пуст. Вы можете воспользоватсья базовым словарем"

def check_word_exists(word):
    return session.query(Word).filter(Word.word_ru == word).first() is not None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    if not session.query(User).filter(User.user_id == user_id).first():
        add_user(user_id, username)
        print(f"Добавлен новый пользователь: {username} (ID: {user_id})")

    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_keyboard())

def create_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Помощь", "Обучение", "Добавить слово", "Удалить слово"]
    keyboard.add(*buttons)
    return keyboard

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id, help_text, reply_markup=create_main_keyboard())

@bot.message_handler(commands=['view_dictionary'])
def view_dictionary_command(message):
    user_id = message.from_user.id
    words = view_dictionary(user_id)
    count_of_words = session.query(User_word).filter(User_word.user_id == user_id).count()
    bot.send_message(message.chat.id, f"Ваш словарь ({count_of_words} слов):\n{words}")

def learning_process(message):
    user_id = message.from_user.id

    user_words_ids = select(User_word.word_id).filter(User_word.user_id == user_id).subquery()

    user_words = session.query(Word).filter(Word.word_id.in_(user_words_ids)).all()
    print(f"Пользовательские слова: {[word.word_ru for word in user_words]}")

    common_words = session.query(Common_word).all()
    print(f"Общие слова: {[word.word_ru for word in common_words]}")

    all_words = user_words + common_words

    selected_words = random.sample(all_words, min(4, len(all_words)))

    word_options = [word.word_en for word in selected_words]
    correct_answer = random.choice(word_options)
    correct_answer_ru = next((word.word_ru for word in selected_words if word.word_en == correct_answer), "")

    bot.send_message(message.chat.id, f"Выберите правильный перевод для слова '{correct_answer_ru}':", 
                     reply_markup=create_learning_keyboard(word_options))
    bot.register_next_step_handler(message, lambda m: check_answer(m, correct_answer, word_options))
    add_user_activity(user_id, "Перевод: вопрос о переводе")

def check_answer(message, correct_answer, word_options):
    user_id = message.from_user.id
    
    if message.text == '🏠 Вернуться в меню':
        return_to_main_menu(message)
        return
    if message.text == correct_answer:
        bot.send_message(message.chat.id, f"Правильно! 🎉, продолжайте в том же духе!")
        learning_process(message)
        add_user_activity(user_id, "Обучение: правильный ответ")
    else:
        bot.send_message(message.chat.id, f"Неправильно! Правильный ответ: {correct_answer}. ❌")
        learning_process(message)
        add_user_activity(user_id, "Обучение: неправильный ответ")

@bot.message_handler(func=lambda message: message.text == '🏠 Вернуться в меню')
def return_to_main_menu(message):
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=create_main_keyboard())

@bot.message_handler(func=lambda message: message.text in ["Помощь", "Обучение", "Добавить слово", "Удалить слово"])
def handle_main_buttons(message):
    if message.text == "Помощь":
        bot.send_message(message.chat.id, help_text)
    elif message.text == "Обучение":
        learning_process(message)
    elif message.text == "Добавить слово":
        bot.send_message(message.chat.id, "Введите слово на русском:")
        bot.register_next_step_handler(message, process_add_word)
    elif message.text == "Удалить слово":
        bot.send_message(message.chat.id, "Введите слово на русском для удаления:")
        bot.register_next_step_handler(message, process_remove_word)

def process_add_word(message):
    user_id = message.from_user.id
    word_ru = message.text.strip()
    
    if check_word_exists(word_ru):
        bot.send_message(message.chat.id, "Это слово уже существует в общей базе данных.")
        return

    bot.send_message(message.chat.id, "Введите слово на английском:")
    bot.register_next_step_handler(message, lambda m: add_word_to_db(m, word_ru, user_id))

def add_word_to_db(message, word_ru, user_id):
    word_en = message.text.strip().lower()

    if check_word_exists(word_en):
        bot.send_message(message.chat.id, "Это слово уже существует в общей базе данных.")
        return

    word_id, count = add_word(word_ru, word_en, user_id)
    if word_id:
        bot.send_message(message.chat.id, f"Слово '{word_ru}' добавлено! Теперь у вас {count} слов в словаре.")
        add_user_activity(user_id, "Добавление слова")
    else:
        bot.send_message(message.chat.id, "Ошибка при добавлении слова.")

def process_remove_word(message):
    word_ru = message.text.strip()
    user_id = message.from_user.id
    
    if not check_word_exists(word_ru):
        bot.send_message(message.chat.id, f"Слово '{word_ru}' не найдено в базе данных.")
        return

    if remove_word_from_dictionary(word_ru, user_id):
        bot.send_message(message.chat.id, f"Слово '{word_ru}' удалено из вашего словаря. 🔙")
    else:
        bot.send_message(message.chat.id, f"Слово '{word_ru}' не найдено в вашем словаре.")

def create_learning_keyboard(word_options):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for option in word_options:
        keyboard.add(option)
    keyboard.add('🏠 Вернуться в меню')
    return keyboard  

def save_to_json(filename='data.json'):
    users = session.query(User).all()
    words = session.query(Word).all()
    user_words = session.query(User_word).all()
    user_activities = session.query(User_activity).all()
    common_words = session.query(Common_word).all()

    data = {
        "common_words": [{"word_id": word.word_id, "word_ru": word.word_ru, "word_en": word.word_en} for word in common_words], 
        "users": [{"user_id": user.user_id, "username": user.username} for user in users],
        "words": [{"word_id": word.word_id, "word_ru": word.word_ru, "word_en": word.word_en} for word in words],
        "user_words": [{"user_id": user_word.user_id, "word_id": user_word.word_id} for user_word in user_words],
        "user_activities": [{"user_id": activity.user_id, "activity_type": activity.activity_type, "activity_datetime": str(activity.activity_datetime)} for activity in user_activities],
    }

    with open(filename, 'w', encoding='utf-8') as f: 
        json.dump(data, f, ensure_ascii=False, indent=4)  

if __name__ == '__main__':
    drop_tables(engine)
    create_tables(engine)  
    save_to_json()
    print('Бот запущен...')
    try:
        bot.infinity_polling() 
    except Exception as e:
        print(f'Произошла ошибка: {e}')
    finally:
        session.close()

