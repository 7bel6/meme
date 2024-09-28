import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DATABASE = 'db.db'

# Function to connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Create the main table if it does not exist
def create_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS main (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Index route to display the form and handle form submission
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        html_content = request.form['htmlContent']
        
        if html_content:
            # print("Form content:", html_content)  # Debugging print statement
            conn = get_db_connection()
            conn.execute('INSERT INTO main (wallet) VALUES (?)', (html_content,))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
        else:
            print("No content provided!")  # Debugging print statement

    return render_template('index.html')


# Route to display all wallet IDs
@app.route('/wallets', methods=['GET'])
def wallets():
    conn = get_db_connection()
    wallets = conn.execute('SELECT id FROM main').fetchall()
    conn.close()
    return render_template('wallets.html', wallets=wallets)

# Route to analyze a specific wallet by ID
@app.route('/analyze_wallet/<int:wallet_id>', methods=['GET'])
def analyze_wallet(wallet_id):
    return render_template('analyze_wallet.html', wallet_id=wallet_id)


if __name__ == '__main__':
    create_table()
    app.run(debug=True)
