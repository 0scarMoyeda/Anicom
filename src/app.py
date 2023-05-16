from flask import Flask, render_template, request, session, redirect, url_for
import os
import mysql.connector

# Connection to MySQL database
connection = mysql.connector.connect(
    host='localhost', port='3306', database='anicom', user='root'
)

# variable to execute queries like INSERT or SELECT
cursor = connection.cursor()

# The directories where the app will find the assets
template_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
template_dir = os.path.join(template_dir, 'src', 'templates')

# Set up the app
app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'super secret key'


# App routes (needed to navigate throughout the pages)
# ----------------------------------------------------
# login page (the first page the user will see)
@app.route('/')
def index():
    return render_template('index-login.html')


# Main page index
@app.route('/home')
def home():
    return render_template('home.html', username=session['username'])


# Mangas
@app.route('/mangas')
def mangas():
    return render_template('mangas_index.html', username=session['username'])


# Comics
@app.route('/comics')
def comics():
    return render_template('comics_index.html', username=session['username'])


# Manga template for testing
@app.route('/manga/<int:manga_id>')
def manga_template(manga_id):
    content_data = get_content(manga_id)
    user_data = get_current_user(session['username'])
    comments = get_all_comments(manga_id)

    print(content_data)
    print(user_data)

    try:
        user_rating = get_user_rating(content_data[0], user_data[0])
        user_rating = user_rating[3]
    except TypeError as error:
        print("The user hasn't liked nor disliked the content yet")
        user_rating = 0

    content_score = get_content_score(content_data[0])
    print(content_data)

    print('Rating es: '+str(user_rating))

    return render_template('plantilla_manga.html', username=session['username'],
                           content=content_data, comments=comments, rating_value=user_rating, content_score=content_score)


@app.route('/add_comment/<int:content_id>', methods=['POST'])
def add_comment(content_id):

    # get the manga/comic data to use it later on
    content_data = get_content(content_id)
    # and the user's data
    user_data = get_current_user(session['username'])

    # content_id = request.form['content_id']
    # user_id = request.form['user_id']
    comment_text = request.form['comment_text']

    # Process the comment (e.g., insert into the database)
    try:
        cursor.execute('INSERT INTO comments VALUES(NULL, %s, %s, %s, NULL)', (content_data[0], user_data[0], comment_text))
        connection.commit()
        print("Comment added")

    except mysql.connector.Error as error:
        print("Comment failed: " + str(error))

    # get all the comments to display them
    comments = get_all_comments(content_data[0])

    # get data so it won't cause data to hide
    try:
        user_rating = get_user_rating(content_data[0], user_data[0])
        user_rating = user_rating[3]
    except TypeError as error:
        print("The user hasn't liked nor disliked the content yet")
        user_rating = 0
    content_score = get_content_score(content_data[0])

    return render_template('plantilla_manga.html', username=session['username'], content=content_data,
                           comments=comments, rating_value=user_rating, content_score=content_score)


# Like and Dislike rating system in each manga/comic
@app.route('/add_rating/<int:content_id>', methods=['POST'])
def add_rating(content_id):
    content_data = get_content(content_id)
    user_data = get_current_user(session['username'])

    # Get the like or dislike value from the user
    rating_value = 1 if request.form['rating_value'] == 'like' else -1

    # Now add the like or dislike value to the ratings table
    # Make sure the user hadn't liked before
    cursor.execute('SELECT * FROM ratings WHERE content_id = %s AND user_id = %s', (content_data[0], user_data[0]))
    existing_rating = cursor.fetchone()

    if existing_rating:
        # If the user has already rated, check if the rating value is the same
        if existing_rating[3] == rating_value:
            # If the rating value is the same, delete the rating
            cursor.execute('DELETE FROM ratings WHERE id = %s', (existing_rating[0],))
            print("Rating deleted")
        else:
            # If the rating value is different, update the rating value
            cursor.execute('UPDATE ratings SET rating_value = %s WHERE id = %s',
                           (rating_value, existing_rating[0]))
            print("Rating updated")
    else:
        # If the user hasn't rated, insert the rating
        cursor.execute('INSERT INTO ratings VALUES (NULL, %s, %s, %s)', (content_data[0], user_data[0], rating_value))
        print("Rating added")

    connection.commit()

    # Redirect the user back to the page or show a success message
    #return redirect(url_for('manga_template'))
    return render_template('plantilla_manga.html', username=session['username'], content=content_data,
                           comments=get_all_comments(content_id), rating_value=rating_value,
                           content_score=get_content_score(content_id))


# login page logic (getting the username and password to validate)
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute('SELECT * FROM users WHERE username=%s AND password=%s', (username, password))
        record = cursor.fetchone()

        if record:
            session['loggedin'] = True
            session['username'] = record[1]
            return redirect(url_for('home'))

        else:
            # We return an output message telling the user if their username or password are incorrect
            message = 'Usuario o contraseña incorrectas. Intentelo de nuevo.'
            print(message)
    return render_template('index-login.html', message=message)


# Register page, where users create their accounts
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        # Get the user inputs
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if the username or email already exists
        if check_existing_value('username', username):
            message = 'Ese usuario ya existe. Intenta con otro.'
        elif check_existing_value('email', email):
            message = 'Ya existe una cuenta asociada a ese correo.'
        else:
            # Create a new user
            cursor.execute('INSERT INTO users VALUES (NULL, %s, %s, %s)', (username, email, password))
            connection.commit()

            session['loggedin'] = True
            session['username'] = username
            return redirect(url_for('home'))

    return render_template('register.html', message=message)


# Logout action
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    print("Logged out")
    return redirect(url_for('login'))


# utility functions
def check_existing_value(column, value):
    cursor.execute(f'SELECT * FROM users WHERE {column}=%s', (value,))
    record = cursor.fetchone()
    return record is not None


def get_content(id):
    cursor.execute(f'SELECT * FROM content WHERE id=%s', (id,))
    return cursor.fetchone()


def get_current_user(user_session):
    cursor.execute(f'SELECT * FROM users WHERE username=%s', (user_session,))
    return cursor.fetchone()


def get_all_comments(content_id):
    query = '''
        SELECT comments.id, comments.content_id, comments.user_id, users.username, comments.comment_text, comments.comment_date
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.content_id = %s
        ORDER BY comments.comment_date DESC
        '''
    cursor.execute(query, (content_id,))
    return cursor.fetchall()


# This is the user rating they upload when clicking like or dislike
def get_user_rating(content_id, user_id):
    cursor.execute('SELECT * FROM ratings WHERE content_id = %s AND user_id = %s', (content_id, user_id))
    return cursor.fetchone()


# This is the contents total score by 100%, given the content id
def get_content_score(content_id):
    cursor.execute('SELECT CASE WHEN COUNT(*) > 0 THEN ROUND((SUM(rating_value) / COUNT(*) + 1) * 50, 2)'
                   'ELSE 0 END AS total_score FROM ratings WHERE content_id = %s', (content_id,))
    result = cursor.fetchone()
    return result[0]


# Run the app
if __name__ == '__main__':
    app.run(debug=True, port=4000)
