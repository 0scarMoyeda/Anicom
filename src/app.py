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


# Manga template for testing
@app.route('/plantilla_manga')
def manga_template():
    comments = get_all_comments(1)
    print(comments)
    return render_template('plantilla_manga.html', username=session['username'], comments=comments)


@app.route('/add_comment', methods=['POST'])
def add_comment():
    # get the manga/comic data to use it later on
    content_data = get_content(1)
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

    return render_template('plantilla_manga.html', comments=comments)


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
    # cursor.execute('SELECT * FROM comments WHERE content_id = %s', (content_id,))
    # comments = cursor.fetchall()
    # return comments

    query = '''
        SELECT comments.id, comments.content_id, comments.user_id, users.username, comments.comment_text, comments.comment_date
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.content_id = %s
        ORDER BY comments.comment_date DESC
        '''
    cursor.execute(query, (content_id,))
    return cursor.fetchall()


# Run the app
if __name__ == '__main__':
    app.run(debug=True, port=4000)
