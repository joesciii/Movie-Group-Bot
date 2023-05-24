from collections import defaultdict
from discord.ext import commands, tasks
from discord import Intents
from tmdbv3api import TMDb, Genre, Discover
import random
import os
import datetime

bot = commands.Bot(command_prefix="/", intents=Intents.all())

tmdb = TMDb()
tmdb.api_key = ''
# Maps genre names to TMDB genre IDs
genre = Genre()
discover = Discover()
genre_map = {g['name'].lower(): g['id'] for g in genre.movie_list()}

# Store genre votes
genre_votes = defaultdict(int)

# Boolean for controlling voting period
vote_open = False

# Store the current movie announcement message
current_movie_message = None

@bot.command(name='startvote')
async def start_vote(ctx):
    global vote_open
    if vote_open:
        await ctx.send('Voting is already open.')
    else:
        vote_open = True
        genre_votes.clear()  # Reset previous votes
        await ctx.send('Voting has started. Vote for a genre with /genre and then a minimum rating with /rating.')

@bot.command(name='genre')
async def votegenre(ctx, *, genre: str):
    if not vote_open:
        await ctx.send('Voting is not currently open.')
    elif genre.lower() not in genre_map:
        await ctx.send('Invalid genre.')
    else:
        genre_votes[genre.lower()] += 1
        await ctx.send(f'Vote for {genre} recorded.')

# Store rating votes
rating_votes = defaultdict(int)

@bot.command(name="rating")
async def voterating(ctx, *, rating: str):
    """Place a vote for a minimum rating."""
    rating_map = {'no minimum': -1, '70%': 70, '80%': 80, '90%': 90}
    rating = rating.lower()
    if rating in rating_map:
        rating_votes[rating_map[rating]] += 1
        await ctx.send(f"Vote for {rating} minimum rating has been placed! Would you like the film to be new? Do /releasedate new or /releasedate any.")
    else:
        await ctx.send(f"{rating} is not a valid rating. Please choose from 'no minimum', '70%', '80%', or '90%'.")

# Store release date votes
release_date_votes = {'new': 0, 'any': 0}

@bot.command(name='releasedate')
async def release_date_vote(ctx, *, release_date):
    """Handles release date voting"""
    global release_date_votes
    release_date = release_date.lower()
    if release_date not in release_date_votes:
        await ctx.send('Invalid release date. Please vote for either "new" or "any".')
    else:
        release_date_votes[release_date] += 1
        await ctx.send(f'Your vote for "{release_date}" has been recorded.')

winning_genre = None
winning_rating = None
winning_release_date = None


@bot.command(name='closevote')
async def close_vote(ctx):
    global vote_open, current_movie_message
    if not vote_open:
        await ctx.send('Voting is not currently open.')
    else:
        vote_open = False
        bot.winning_genre = max(genre_votes, key=genre_votes.get)
        bot.winning_rating = max(rating_votes, key=rating_votes.get)
        bot.winning_release_date = max(release_date_votes, key=release_date_votes.get)

        genre_votes.clear()
        rating_votes.clear()
        release_date_votes.clear()

        discover_params = {
            'with_genres': genre_map[bot.winning_genre],
            'sort_by': 'popularity.desc'
        }

        if bot.winning_rating > -1:
            discover_params['vote_average.gte'] = bot.winning_rating / 10

        if bot.winning_release_date == 'new':
            last_year_date = datetime.date.today() - datetime.timedelta(days=365)
            discover_params['primary_release_date.gte'] = last_year_date.strftime("%Y-%m-%d")

        movies = discover.discover_movies(discover_params)

        selected_movie = random.choice(movies)
        bot.selected_movie = selected_movie
        movie_url = f"https://www.themoviedb.org/movie/{selected_movie.id}"
        message = await ctx.send(f'Voting has closed. The winning genre is {bot.winning_genre} with a minimum rating of {bot.winning_rating}%. The selected movie is {bot.selected_movie.title}. {movie_url}\nReact with ✅ to keep this movie, or ❌ to reroll.')
        current_movie_message = message
        # Add reactions to the message
        await message.add_reaction('✅')
        await message.add_reaction('❌')

@bot.event
async def on_reaction_add(reaction, user):
    global current_movie_message
    # Check if the reaction is on the current movie message, and if the reaction is a cross, and if voting is not open
    if reaction.message == current_movie_message and str(reaction.emoji) == '❌' and not vote_open:
        # If the number of cross reactions is more than 1, reroll the movie
        if reaction.count > 1:
            discover_params = {
                'with_genres': genre_map[bot.winning_genre],
                'sort_by': 'popularity.desc'
            }

            if bot.winning_rating > -1:
                discover_params['vote_average.gte'] = bot.winning_rating / 10

            if bot.winning_release_date == 'new':
                last_year_date = datetime.date.today() - datetime.timedelta(days=365)
                discover_params['primary_release_date.gte'] = last_year_date.strftime("%Y-%m-%d")

            movies = discover.discover_movies(discover_params)

            selected_movie = random.choice(movies)
            movie_url = f"https://www.themoviedb.org/movie/{selected_movie.id}"
            bot.selected_movie = selected_movie
            await current_movie_message.edit(content=f'The movie has been rerolled. The new selected movie is {bot.selected_movie.title}. {movie_url}')

@bot.event
async def on_ready():
    bot.selected_movie = None
    print("Bot is ready")

bot.run('')
