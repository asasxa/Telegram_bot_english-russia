import json
import random
import telebot
from telebot import types
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, delete
from tables.models import create_tables, drop_tables, User, Word, User_word, User_activity, Common_word, Base
from dotenv import load_dotenv
import os
from datetime import datetime
from text.welcome_text import welcome_text
from text.help_text import help_text
from tables.Common_words import common_words
