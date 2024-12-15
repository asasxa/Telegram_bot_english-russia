import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    user_id = sq.Column(sq.BigInteger, primary_key=True, autoincrement=False)
    username = sq.Column(sq.String, unique=True, nullable=False) 
    created_date = sq.Column(sq.DateTime, default=datetime.now)

    words = relationship('User_word', back_populates='user', cascade='all, delete')
    activities = relationship('User_activity', back_populates='user', cascade='all, delete')

class Word(Base):
    __tablename__ = 'words'
    
    word_id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    word_ru = sq.Column(sq.String, nullable=False)
    word_en = sq.Column(sq.String, nullable=False)

    user_words = relationship('User_word', back_populates='word')

class User_word(Base):
    __tablename__ = 'user_words'
    
    user_word_id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    user_id = sq.Column(sq.BigInteger, sq.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False) 
    word_id = sq.Column(sq.Integer, sq.ForeignKey('words.word_id', ondelete='CASCADE'), nullable=False)

    user = relationship('User', back_populates='words')
    word = relationship('Word', back_populates='user_words')

class User_activity(Base):
    __tablename__ = 'user_activity'
    
    activity_id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    user_id = sq.Column(sq.BigInteger, sq.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)  
    activity_type = sq.Column(sq.String, nullable=False)
    activity_datetime = sq.Column(sq.DateTime, default=datetime.now)

    user = relationship('User', back_populates='activities')

class Common_word(Base):
    __tablename__ = 'common_words'
    
    word_id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    word_ru = sq.Column(sq.String, nullable=False)
    word_en = sq.Column(sq.String, nullable=False)

def create_tables(engine):
    try:
        Base.metadata.create_all(engine)
        print("Таблицы успешно созданы.")
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")   

def drop_tables(engine):
    Base.metadata.drop_all(engine)
    print("Все таблицы успешно удалены.")