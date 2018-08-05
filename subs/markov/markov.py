"""Builds Markov chains from Discord chat history and provides a bot command interface
to display them."""
import ujson
import os
import random
import re
import string
import discord
from discord.ext import commands
from itertools import product
import markovify
import datetime
import traceback

DEFAULT_NAME = 'MathBot'
FILTERED_PREFIXES = ('mk', 'rmk', 'markov', '$', '!', '~', '--', 'fanfic', 'listmarkov', 'rlistmarkov')

MAX_MESSAGE_LENGTH = 1800
MAX_NICKNAME_LENGTH = 30
MAX_NUM_OF_NAMES = 10
MAX_MARKOV_ATTEMPTS = 10
REFLEXIVE_TAG = 'me'
RANDOM_TAG = 'rand'
ALL_TAG = 'all'

RESOURCES_REPO = './subs/markov/resources/'
PEOPLE_REPO = f'{RESOURCES_REPO}people/'
FANFIC_REPO = f'{RESOURCES_REPO}fanfic/'
TIMESTAMP_FILE = f'{RESOURCES_REPO}lastupdate.txt'
MARKOV_MODULE_CREATOR_ID_FILE = f'{RESOURCES_REPO}markovcreatorid.txt'
MASCULINE_WORDS_FILE = f'{FANFIC_REPO}masculinewords.txt'
FEMININE_WORDS_FILE = f'{FANFIC_REPO}femininewords.txt'
CHARACTERS_FILE = f'{FANFIC_REPO}characters.txt'
COMMON_WORDS_FILE = f'{RESOURCES_REPO}commonwords.txt'

MARKOV_PEOPLE = [f for f in os.listdir(PEOPLE_REPO)]
VALID_NAMES = [f[:-5] for f in MARKOV_PEOPLE if f.find('.json') != -1]

MAN_TAGS = ('man', 'male', 'masculine', 'guy', 'boy', 'm')
WOMAN_TAGS = ('woman', 'female', 'feminine', 'girl', 'f')

with open(MASCULINE_WORDS_FILE, 'r', encoding='utf-8') as f:
    MASCULINE_WORDS = f.read().splitlines()

with open(FEMININE_WORDS_FILE, 'r', encoding='utf-8') as f:
    FEMININE_WORDS = f.read().splitlines()

with open(CHARACTERS_FILE, 'r', encoding='utf-8') as f:
    CHARACTERS = f.read().splitlines()

with open(MARKOV_MODULE_CREATOR_ID_FILE, 'r') as f:
    MARKOV_MODULE_CREATORS_ID = int(f.readline())

# Below snippet was intended for use with content-aware fanfic generation. See commented-out snippet in
# generate_fanfic() for more information. If implemented, this snippet must also be uncommented in addition to below.
#
# with open(COMMON_WORDS_FILE, 'r') as f:
#     COMMON_WORDS = f.read().splitlines()

PERMITTED_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-"
PERMISSION_ERROR_STRING = f'Error: You do not have permission to use this command.'


class NameNotFoundError(Exception):
    """Error raised for input that refers to no user."""
    def __init__(self, name):
        self.name = name


class AmbiguousInputError(Exception):
    """Error raised for input that refers to multiple users"""
    def __init__(self, name, output):
        self.name = name
        self.output = output


def save_timestamp(timestamp):
    timestamp_string = timestamp.isoformat(' ')
    with open(TIMESTAMP_FILE, 'w') as f:
        f.write(timestamp_string)


def load_timestamp():
    with open(TIMESTAMP_FILE, 'r') as f:
        timestamp_string = f.readline()
    return datetime.datetime.strptime(timestamp_string, '%Y-%m-%d %H:%M:%S.%f')


def parse_names(names_input, valid_names):
    """Returns a list of possible names from the name substring input."""
    names = []

    for name in names_input:
        current_name = []
        if name == RANDOM_TAG:
            names.append(random.choice(VALID_NAMES))
        elif name == ALL_TAG:
            people = random.sample(VALID_NAMES, 5)
            for person in people:
                names.append(person)
        else:
            for valid_name in valid_names:
                if name == valid_name:
                    names.append(valid_name)
                    break
                if name in valid_name:
                    current_name.append(valid_name)
            else:
                if not current_name:
                    raise NameNotFoundError(name)
                elif len(current_name) == 1:
                    names.append(current_name[0])
                else:
                    raise AmbiguousInputError(name, current_name)
    else:
        return names


def generate_models(repo, names):
    """Generates a Markov model from a given json message repo and a name."""
    models = []
    for name in names:
        try:
            with open(f'{repo}{name}.json', 'r', encoding='utf-8-sig') as json_file:
                models.append(markovify.Text.from_json(ujson.load(json_file)))
        except FileNotFoundError:
            raise FileNotFoundError()

    return models


def generate_markov(person, root):
    """Using a Markov model, generates a text string."""
    namelist = person.lower().split('+')
    num_names = len(namelist)
    if num_names > MAX_NUM_OF_NAMES:
        return [f'Error: Too many inputs ({num_names}).', DEFAULT_NAME]

    try:
        names = parse_names(namelist, VALID_NAMES)
        models = generate_models(PEOPLE_REPO, names)
    except AmbiguousInputError as bad_input:
        return [f'Error: Input maps to multiple users ("{bad_input.name}" -> {bad_input.output}).',
                DEFAULT_NAME]
    except FileNotFoundError as no_file:
        return [f'Error: File not found ({no_file.filename}.json).', DEFAULT_NAME]
    except NameNotFoundError as no_user:
        return [f'Error: User not found ({no_user.name}).', DEFAULT_NAME]
    except Exception:
        return [f'Error: Unknown error.', DEFAULT_NAME]

    nickname = ''
    for name in names:
        if len(nickname) + len(name) < MAX_NICKNAME_LENGTH:
            nickname += name + '+'

    names_in_nickname = nickname[:-1].split('+')

    if len(names_in_nickname) < len(names):
        nickname += str(len(names) - len(names_in_nickname))
    else:
        nickname = nickname[:-1]

    text_model = markovify.combine(models)

    for _ in range(MAX_MARKOV_ATTEMPTS):
        if root is None:
            output = text_model.make_sentence(tries=MAX_MARKOV_ATTEMPTS)
        else:
            output = text_model.make_sentence_with_start(
                root, tries=MAX_MARKOV_ATTEMPTS, strict=False)
        if output is not None:
            return [output, nickname.title()]
    else:
        return ['Error: insufficient data for Markov chain.', DEFAULT_NAME]


def update_markov_people(new_messages, authors):
    """Updates current Markov models and outputs them as .json files. It finally returns a confirmation message."""
    num_of_new_names = 0
    num_of_updated_names = 0
    num_of_messages = len(new_messages)
    models = []
    print("Updating Markov models...")
    for index, author in enumerate(authors, 1):
        print(str(index) + "/" + str(len(authors)) + ": " + author.name)
        corpus = ''
        count = 0

        for message in new_messages:
            if message.author.id == author.id:
                corpus += message.content + '\n'
                count += 1
        if count > 2:
            new_model = markovify.NewlineText(corpus)
            models.append(new_model)
            cleaned_name = "".join(c for c in author.name if c in PERMITTED_CHARS).lower()
            try:
                if cleaned_name in VALID_NAMES:
                    num_of_updated_names += 1
                    with open(f'{PEOPLE_REPO}{cleaned_name}.json', 'r', encoding='utf-8-sig') as json_file:
                        original_model = markovify.NewlineText.from_json(ujson.load(json_file))
                    updated_model = markovify.combine([original_model, new_model])
                    new_json = updated_model.to_json()
                    with open(f"{PEOPLE_REPO}{cleaned_name}.json", 'w') as json_file:
                        ujson.dump(new_json, json_file)
                else:
                    new_json = new_model.to_json()
                    VALID_NAMES.append(cleaned_name)
                    num_of_new_names += 1
                    with open(f"{PEOPLE_REPO}{cleaned_name}.json", 'w') as json_file:
                        ujson.dump(new_json, json_file)
            except FileNotFoundError:
                return f"Error: File not found ({cleaned_name}.json)."
            except Exception:
                traceback.print_exc()
                return f"Error: Unknown Error."
        else:
            print('User skipped due to inactivity.')
    print("Update Successful.")
    return f"Corpus successfully updated with {num_of_messages} new messages, " \
           f"{num_of_updated_names} updated people, and {num_of_new_names} new people."


def assign_name():
    """Assigns a name from a pre-loaded list of characters."""
    index = random.randint(0, len(CHARACTERS) - 1)
    return CHARACTERS[index]


def is_valid_sentence(homosexual, gay, sentence, gender1_tag):
    """Determines based on the type of relationship whether a given sentence makes logical sense within a fanfic."""
    sentence_words = [''.join(c for c in word if c not in string.punctuation) for word in sentence.lower().split()]
    tags = [word.strip("'s") for word in sentence.split() if '$' in word]

    if not homosexual and 'ALE2' in sentence:
        return False

    is_tags_same_length = True
    if len(tags) > 0:
        tag_len = len(tags[0])
        if len(gender1_tag) != tag_len:
            is_tags_same_length = False
        else:
            for tag in tags:
                if tag_len != len(tag):
                    is_tags_same_length = False

    if homosexual and not is_tags_same_length:
        return False

    if homosexual:
        if gay:
            for feminine_word, word in product(FEMININE_WORDS, sentence_words):
                if word == feminine_word:
                    return False
        else:
            for masculine_word, word in product(MASCULINE_WORDS, sentence_words):
                if word == masculine_word:
                    return False
    return True


def generate_fanfic(person1, person2, gender1, gender2):
    """Generates a fanfic with the given people and genders."""
    if person1 is None:
        person1 = assign_name()
    if person2 is None:
        person2 = assign_name()
    if person1 == RANDOM_TAG:
        person1 = random.choice(VALID_NAMES).title()
    if person2 == RANDOM_TAG:
        person2 = random.choice(VALID_NAMES).title()

    homosexual = False   # 'homosexual' refers to whether the two partners are the same sex.
    gay = False   # 'gay' refers to whether the two partners are men.

    if gender1.lower() in MAN_TAGS:
        gender1_tag = '$MALE1'
        if gender2.lower() in MAN_TAGS:
            gender2_tag = '$MALE2'
            homosexual = True
            gay = True
        else:
            gender2_tag = '$FEMALE1'
    else:
        gender1_tag = '$FEMALE1'
        if gender2.lower() in MAN_TAGS:
            gender2_tag = '$MALE1'
        else:
            gender2_tag = '$FEMALE2'
            homosexual = True

    with open(f'{FANFIC_REPO}fanficcorpus.json', 'r', encoding='utf-8-sig') as json_file:
        fanfic_model = markovify.Text.from_json(ujson.load(json_file))

    fanfic_attempts = 0
    paragraph = ''
    topic_of_previous_sentence = ''

    while len(paragraph) < MAX_MESSAGE_LENGTH:
        sentence = fanfic_model.make_sentence() + ' '
        if is_valid_sentence(homosexual, gay, sentence, gender1_tag):
            if len(paragraph) + len(sentence) < MAX_MESSAGE_LENGTH:
                paragraph += sentence
                # This snippet of code is intended to add context-aware generation of fanfics. While it works, it tends
                # to create less interesting and more repetitive paragraphs than leaving it out. If uncommented, the
                # code reading the COMMON_WORDS file must be present and the relevant import code uncommented for this
                # to work. In addition, the above line must be removed (paragraph += sentence).
                #
                # sentence_words = re.sub(r'([^\s\w]|_)+', '', sentence).lower().split()
                # if topic_of_previous_sentence is '':
                #     paragraph += sentence
                #     while True:
                #         topic_of_previous_sentence = sentence_words[random.randint(0, len(sentence_words) - 1)]
                #         if topic_of_previous_sentence not in COMMON_WORDS:
                #             break
                # elif topic_of_previous_sentence in sentence_words:
                #     paragraph += sentence
                #     while True:
                #         topic_of_previous_sentence = sentence_words[random.randint(0, len(sentence_words) - 1)]
                #         if topic_of_previous_sentence not in COMMON_WORDS:
                #             break
            else:
                if gender1_tag in paragraph and gender2_tag in paragraph:
                    break
                else:
                    paragraph = ''
                    fanfic_attempts += 1
                    if fanfic_attempts > 5:
                        break
    if paragraph is not '':
        return paragraph.replace(gender1_tag, person1).replace(gender2_tag, person2)
    else:
        return f'Error: Fanfic could not be created using tags {gender1_tag} and {gender2_tag}.'


class Markov():
    """Defines Markov commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=['mk', 'rmk'], invoke_without_command=True)
    async def markov(self, ctx, person=REFLEXIVE_TAG, root=None):
        """Generates a Markov chain based on a user's previous messages."""
        if person == 'memers':
            person = ALL_TAG
        if REFLEXIVE_TAG in person:
            person = person.replace(REFLEXIVE_TAG, ctx.author.name)
        out = generate_markov(person, root)
        user_tags = set([c for c in out[0].split(' ') if c[0:2] == '<@'])
        current_guild = ctx.message.guild
        bot_self = current_guild.me
        for user_tag in user_tags:
            id = int(re.sub('\D','',user_tag))
            username = current_guild.get_member(id)
            if username is not None:
                username = username.display_name
                out[0] = out[0].replace(user_tag, '@' + username)
            elif user_tag in out[0]:
                out[0] = out.replace(user_tag, "@UNKNOWN_USER")
        if person == ALL_TAG:
            out[1] = ctx.guild.name.title()
        await bot_self.edit(nick=out[1])
        await ctx.send(out[0])

    @markov.command(name='rename', hidden=True)
    async def _rename(self, ctx, before_name, after_name):
        if ctx.author.id == MARKOV_MODULE_CREATORS_ID:
            before_name = before_name.lower()

            if before_name in VALID_NAMES:
                after_name = "".join(c for c in after_name if c in PERMITTED_CHARS).lower()
                with open(f'{PEOPLE_REPO}{before_name}.json', 'r', encoding='utf-8-sig') as json_file:
                    json_model = ujson.load(json_file)
                with open(f"{PEOPLE_REPO}{after_name}.json", 'w') as json_file:
                    ujson.dump(json_model, json_file)
                VALID_NAMES.remove(before_name)
                VALID_NAMES.append(after_name)
                os.remove(f'{PEOPLE_REPO}{before_name}.json')
                await ctx.send(f'{before_name} successfully renamed to {after_name}!')
            else:
                await ctx.send(f'Error: Name not found ({before_name}).')
        else:
            await ctx.send(PERMISSION_ERROR_STRING)

    @markov.command(name='merge', hidden=True)
    async def _merge(self, ctx, name1, name2, out_name):
        if ctx.author.id == MARKOV_MODULE_CREATORS_ID:
            name1 = name1.lower()
            name2 = name2.lower()

            if name1 in VALID_NAMES and name2 in VALID_NAMES:
                if name1 == '' or name2 == '' or out_name == '':
                    await ctx.send(f'Error: At least one argument is blank.')
                out_name = "".join(c for c in out_name if c in PERMITTED_CHARS).lower()
                with open(f'{PEOPLE_REPO}{name1}.json', 'r', encoding='utf-8-sig') as json_file:
                    name1_model = markovify.NewlineText.from_json(ujson.load(json_file))
                with open(f'{PEOPLE_REPO}{name2}.json', 'r', encoding='utf-8-sig') as json_file:
                    name2_model = markovify.NewlineText.from_json(ujson.load(json_file))
                new_model = markovify.combine([name1_model, name2_model])
                new_json = new_model.to_json()
                with open(f"{PEOPLE_REPO}{out_name}.json", 'w') as json_file:
                    ujson.dump(new_json, json_file)
                VALID_NAMES.remove(name1)
                VALID_NAMES.remove(name2)
                VALID_NAMES.append(out_name)
                os.remove(f'{PEOPLE_REPO}{name1}.json')
                os.remove(f'{PEOPLE_REPO}{name2}.json')
                await ctx.send(f'{name1}.json and {name2}.json successfully merged to {out_name}.json!')
            else:
                await ctx.send(f'Error: Name not found ({before_name}).')
        else:
            await ctx.send(PERMISSION_ERROR_STRING)

    @markov.command(name='remove', hidden=True)
    async def _remove(self, ctx, name):
        if ctx.author.id == MARKOV_MODULE_CREATORS_ID:
            name = name.lower()

            if name in VALID_NAMES:
                os.remove(f'{PEOPLE_REPO}{name}.json')
                VALID_NAMES.remove(name)
                await ctx.send(f'{name}.json successfully removed!')
            else:
                await ctx.send(f'Error: Name not found ({before_name}).')
        else:
            await ctx.send(PERMISSION_ERROR_STRING)

    @markov.command(name='listmarkov', aliases=['lm'])
    async def _list(self, ctx):
        """Lists the people from which you can generate Markov chains."""
        out = []
        message = ''
        for valid_name in VALID_NAMES:
            if len(message) + len(valid_name) < MAX_MESSAGE_LENGTH:
                message += valid_name + ', '
            else:
                out.append(message[:-2])
                message = valid_name + ', '
        else:
            out.append(message[:-2])
        for i in range(len(out)):
            await ctx.send(out[i])

    @markov.command(name='updatemarkov', aliases=['um'], hidden=True)
    async def _update(self, ctx):
        """Updates the corpus for the Markov module."""
        if ctx.author.id == MARKOV_MODULE_CREATORS_ID:
            await ctx.send("Beginning update...")
            new_messages = []
            authors = []
            last_timestamp = load_timestamp()
            print("Fetching history...")
            history = await ctx.channel.history(after=last_timestamp, limit=None).flatten()
            print("Filtering messages...")
            for message in history:
                if not message.content.startswith(FILTERED_PREFIXES) and not message.author.bot:
                    new_messages.append(message)
                    authors.append(message.author)
                    creation_time = message.created_at
                    if creation_time > last_timestamp:
                        last_timestamp = creation_time
            await ctx.send(update_markov_people(new_messages, set(authors)))
            save_timestamp(last_timestamp)
        else:
            await ctx.send(PERMISSION_ERROR_STRING)

    @commands.command(aliases=['ff'])
    async def fanfic(self, ctx, person1=None, person2=None, gender1='man', gender2='woman'):
        """Generates a paragraph of Markov sentences based on works from fanfiction.net."""
        if person1 == REFLEXIVE_TAG:
            person1 = ctx.author.name
        if person2 == REFLEXIVE_TAG:
            person2 = ctx.author.name
        out = generate_fanfic(person1, person2, gender1, gender2)
        await ctx.send(out)


def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Markov(bot))
