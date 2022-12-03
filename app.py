# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
from flask_migrate import Migrate
import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
import sys
from datetime import datetime
from models import Venue, Artist, Show

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
db.init_app(app)

migrate = Migrate(app, db)
# # TODO: connect to a local postgresql database
# #----------------------------------------------------------------------------#
# # Models.
# #----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    # get all available city and state in venues
    cities = Venue.query.with_entities(Venue.city, Venue.state).distinct().all()
    for city_state in cities:
        city = city_state[0]
        state = city_state[1]
        venues = Venue.query.filter_by(city=city, state=state).all() # groups venue by city and state
        data.append({
                "city": city,
                "state": state,
                "venues": venues
        })

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '').strip()
    # get the search term from form
    # Use filter, not filter_by when doing LIKE search (i=insensitive to case)
    venues = Venue.query.filter(Venue.name.ilike('%' + search_term + '%')).all()  # Wildcards search before and after
    # print(venues)
    venue_list = []
    now = datetime.now()
    for venue in venues:
        venue_shows = Show.query.filter_by(venue_id=venue.id).all()
        num_upcoming = 0
        for show in venue_shows:
            if show.start_time > now:
                num_upcoming += 1

        venue_list.append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": num_upcoming  # FYI, template does nothing with this
        })

    response = {
        "count": len(venues),
        "data": venue_list
    }

    # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ""))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    data = []
    venue = Venue.query.filter_by(id=venue_id).first()
    shows = db.session.query(Show).filter(Show.venue_id == venue.id)
    past_shows = []
    upcomming_shows = []
    num_past_shows = 0
    num_upcomming_shows = 0
    for show in shows:
        artist = Artist.query.filter_by(id=show.artist_id).first()
        show_details = {
            "artist_id": show.artist_id,
            "artist_name": artist.name,
            "start_time": format_datetime(str(show.start_time)),
            "artist_image_link": artist.image_link
        }
        if show.start_time > datetime.now():
            num_upcomming_shows += 1
            upcomming_shows.append(show_details)
        elif show.start_time < datetime.now():
            num_past_shows += 1
            past_shows.append(show_details)

    data.append({
            "id": venue.id,
            "name": venue.name,
            "genres": venue.genres.split(','),
            "address": venue.address,
            "city": venue.city,
            "state": venue.state,
            "phone": venue.phone,
            "website": venue.website,
            "facebook_link": venue.facebook_link,
            "seeking_talent": venue.seeking_talent,
            "seeking_description": venue.seeking_description,
            "image_link": venue.image_link,
            "past_shows": past_shows,
            "upcoming_shows": upcomming_shows,
            "past_shows_count": num_past_shows,
            "upcoming_shows_count": num_upcomming_shows
    })

    return render_template('pages/show_venue.html', venue=list(data)[0])

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    try:
        data = Venue()
        data.name = request.form.get('name')
        data.genres = ', '.join(request.form.getlist('genres'))
        data.address = request.form.get('address')
        data.city = request.form.get('city')
        data.state = request.form.get('state')
        data.phone = request.form.get('phone')
        data.facebook_link = request.form.get('facebook_link')
        data.image_link = request.form.get('image_link')
        data.website = request.form.get('website_link')
        data.seeking_talent = True if request.form.get('seeking_talent') != None else False
        data.seeking_description = request.form.get('seeking_description')
        db.session.add(data)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if not error:
        flash('Venue ' + request.form.get('name') + ' was successfully listed!')
    else:
        flash('An error occurred. Venue ' + request.form.get('name') + ' could not be listed.')
        abort(500)
    return render_template('pages/home.html')


@app.route('/venues/delete/<venue_id>')
def delete_venue(venue_id):
    try:
        Show.query.filter_by(venue_id=venue_id).delete()
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
        flash(f'Venue was successfully deleted!')
        return redirect(url_for('venues'))
    except:
        flash(f'Venue could not be deleted!')
        db.session.rollback()
        return render_template('pages/show_artist.html')
    finally:
        db.session.close()

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    # TODO: replace with real data returned from querying the database
    data = Artist.query.all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_key = request.form.get('search_term')
    artists = Artist.query.filter(Artist.name.ilike("%"+search_key+"%")).all()
    artist_list = []
    for artist in artists:
        artist_list.append({
            "id":artist.id,
            "name": artist.name
        })
    response = {
        "count": len(artists),
        "data": artist_list
    }

    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    # TODO: replace with real artist data from the artist table, using artist_id
    artist = Artist.query.filter_by(id=artist_id).first()
    artist_show = Show.query.filter_by(artist_id=artist.id).all()
    data = []
    past_show = []
    upcoming_show = []
    past_show_count = 0
    upcoming_show_count = 0
    for show in artist_show:
        venue = Venue.query.filter_by(id=show.venue_id).first()
        show_info={
            "venue_id": venue.id,
            "venue_name": venue.name,
            "start_time": format_datetime(str(show.start_time)),
            "venue_image_link": venue.image_link
        }
        if show.start_time > datetime.now():
            upcoming_show_count+=1
            upcoming_show.append(show_info)

        elif show.start_time < datetime.now():
            past_show_count+=1
            past_show.append(show_info)

    data = {
            "id": artist.id,
            "name": artist.name,
            "genres": artist.genres.split(','),
            "city": artist.city,
            "state": artist.state,
            "phone": artist.phone,
            "website": artist.website,
            "facebook_link": artist.facebook_link,
            "seeking_talent": True,
            "seeking_description": artist.seeking_description,
            "image_link": artist.image_link,
            "past_shows": past_show,
            "upcoming_shows": upcoming_show,
            "past_shows_count": past_show_count,
            "upcoming_shows_count": upcoming_show_count

    }

    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.filter_by(id=artist_id).first()
    form = ArtistForm(obj=artist)
    artist = {
        "id": artist_id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": True,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link
    }
    # TODO: populate form with fields from artist with ID <artist_id>
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # TODO: take values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes
    try:
        form = ArtistForm()
        artist = Artist.query.filter_by(id=artist_id).first()
        artist.name = request.form.get('name')
        artist.genres = request.form.get('genres')
        artist.city = request.form.get('city')
        artist.state = request.form.get('state')
        artist.phone = request.form.get('phone')
        artist.facebook_link = request.form.get('facebook_link')
        artist.website = request.form.get('website_link')
        artist.image_link = request.form.get('image_link')
        artist.seeking_talent = True if request.form.get('seeking_talent') == 'Yes' else False
        artist.seeking_description = request.form.get('seeking_description')
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully updated!')

    except:
        # catch all other errors
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be updated.')
    finally:
        # always close the session
        db.session.close()

    return redirect(url_for('show_artist',artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()

    venue = Venue.query.filter_by(id=venue_id).first()
    form = VenueForm(obj=venue)
    venue = {
        "id": venue_id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        # Put the dashes back into phone number
        "phone": (venue.phone[:3] + '-' + venue.phone[3:6] + '-' + venue.phone[6:]),
        "website_link": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link
    }
    # TODO: populate form with values from venue with ID <venue_id>
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # TODO: take values from the form submitted, and update existing
    # venue record with ID <venue_id> using the new attributes
    try:
        form = VenueForm()
        venue = Venue.query.filter_by(id=venue_id).first()

        venue.name = form.name.data
        venue.genres = form.genres.data
        venue.city = form.city.data
        venue.state = form.state.data
        venue.address = form.address.data
        venue.phone = form.phone.data
        venue.facebook_link = form.facebook_link.data
        venue.website = form.website_link.data
        venue.image_link = form.image_link.data
        venue.seeking_talent = True if form.seeking_talent.data == 'Yes' else False
        venue.seeking_description = form.seeking_description.data
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully updated!')

    except ValidationError as e:
        # catch errors from phone validation

        # rollback session if error
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be listed. ' + str(e))
    except:
        # catch all other errors
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be updated.')
    finally:
        # always close the session
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False
    try:
        data = Artist()
        data.name = request.form.get('name')
        data.genres = ', '.join(request.form.getlist('genres'))
        data.address = request.form.get('address')
        data.city = request.form.get('city')
        data.state = request.form.get('state')
        data.phone = request.form.get('phone')
        data.facebook_link = request.form.get('facebook_link')
        data.image_link = request.form.get('image_link')
        data.website = request.form.get('website_link')
        data.seeking_talent = True if request.form.get('seeking_talent') != None else False
        data.seeking_description = request.form.get('seeking_description')

        db.session.add(data)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if not error:
        flash('Venue ' + request.form.get('name') + ' was successfully listed!')
    else:
        flash('An error occurred. Venue ' + request.form.get('name') + ' could not be listed.')
        abort(500)

    return render_template('pages/home.html')

@app.route('/artist/delete/<artist_id>')
def delete_artist(artist_id):
    error = False
    name = ''

    try:
        Show.query.filter_by(artist_id=artist_id).delete()
        Artist.query.filter_by(id=artist_id).delete()
        db.session.commit()
        flash(f'artist '+artist_id+' was successfully deleted!')
        return redirect(url_for('artists'))

    except:
        error = True
        db.session.rollback()
        flash(f'artist '+artist_id+' Could not be deleted!')
        return redirect(url_for('artists'))
    finally:
        db.session.close()

#  Shows
#  ----------------------------------------------------------------


@app.route('/shows')
def shows():
    # displays list of shows at /shows
    # TODO: replace with real venues data.
    shows = Show.query.all()
    data = []
    if not shows:
        flash('no shows now')
    else:
        for show in shows:
            artist = Artist.query.filter_by(id=show.artist_id).first()
            venue = Venue.query.filter_by(id=show.venue_id).first()
            show_detail = {
                "venue_id": venue.id,
                "venue_name": venue.name,
                "artist_id": artist.id,
                "artist_name": artist.name,
                "artist_image_link": artist.image_link,
                "start_time": format_datetime(str(show.start_time))
            }
            if show.start_time > datetime.now():

                data.append(show_detail)

            else:
                data = []
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    error = False
    try:
        data = Show()
        data.artist_id = request.form.get('artist_id')
        data.venue_id = request.form.get('venue_id')
        start_time = request.form.get('start_time')
        data.start_time = start_time

        db.session.add(data)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if not error:
        flash('Show was successfully created at!')
    else:
        flash('An error occurred. Venue ' + request.form.get('artist_id') + ' could not be listed.')
        abort(500)

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# #----------------------------------------------------------------------------#
# # Launch.
# #----------------------------------------------------------------------------#
app.app_context().push()

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
