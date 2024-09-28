import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from bs4 import BeautifulSoup
import re

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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        html_content = request.form['htmlContent']
        
        if html_content:
            conn = get_db_connection()
            conn.execute('INSERT INTO main (wallet) VALUES (?)', (html_content,))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/wallets', methods=['GET'])
def wallets():
    conn = get_db_connection()
    wallets = conn.execute('SELECT id FROM main').fetchall()
    conn.close()
    return render_template('wallets.html', wallets=wallets)

@app.route('/analyze_wallet/<int:wallet_id>', methods=['GET'])
def analyze_wallet(wallet_id):
    conn = get_db_connection()
    wallet_data = conn.execute('SELECT wallet FROM main WHERE id = ?', (wallet_id,)).fetchone()
    conn.close()

    if wallet_data is None:
        return "Wallet not found", 404

    html_content = wallet_data['wallet']
    analysis_result = analyze_html_content(html_content)

    return render_template('analyze_wallet.html', wallet_id=wallet_id, analysis=analysis_result)


def analyze_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract all rows from the target table
    rows = soup.select('table.w-full.border-separate.caption-bottom.border-spacing-0 tbody tr')

    if not rows:
        print("No rows found.")
        return {}

    transactions = []

    for row in rows:
        # Extract the first cell for the token information
        token_div = row.select_one('div.flex.gap-1.flex-row.items-center.justify-start.flex-nowrap')

        if token_div:
            # Extract token links
            token_links = token_div.find_all('a')

            # Extract all <td> to find amounts and transaction types
            amounts = row.find_all('td')
            amount_values = []

            for amount_cell in amounts:
                amount_text = amount_cell.get_text(strip=True)
                print(f"Raw amount text: '{amount_text}'")
                
                # Adjust regex to match any amount and token dynamically
                found_amounts = re.findall(r'(\d*\.?\d+)\s*([A-Z0-9#]+)', amount_text)
                for amount, token in found_amounts:
                    amount_values.append((float(amount), token))
                    print(f"Extracted amount: {amount} for token: {token}")

            # Check for transaction context (Buy/Sell)
            transaction_type = "Unknown"
            if "SWAP" in row.get_text() or "BUY" in row.get_text():
                transaction_type = "Buy"
            elif "SELL" in row.get_text():
                transaction_type = "Sell"

            # Debug: Print found tokens
            print(f"Found tokens: {[link.text.strip() for link in token_links]}")
            print(f"Found amounts: {amount_values}")

            if len(token_links) == 2 and amount_values:
                first_token = token_links[0].text.strip()
                second_token = token_links[1].text.strip()

                # Find corresponding amounts for the tokens
                first_amount = next((amt for amt, tok in amount_values if tok == first_token), 0)
                second_amount = next((amt for amt, tok in amount_values if tok == second_token), 0)

                # Debug: Print extracted token and amount information
                print(f"Extracted tokens: {first_token}, {second_token}")
                print(f"Extracted amounts: {first_amount}, {second_amount}")

                # Initialize coin variable for transaction
                coin = None

                # Add transaction to list
                if transaction_type == "Buy":
                    if first_token == "WSOL":
                        coin = second_token
                        transactions.append({
                            'type': transaction_type,
                            'coin': coin,
                            'amount': second_amount
                        })
                    else:
                        coin = first_token
                        transactions.append({
                            'type': transaction_type,
                            'coin': coin,
                            'amount': first_amount
                        })
                elif transaction_type == "Sell":
                    if second_token == "WSOL":
                        coin = first_token
                        transactions.append({
                            'type': transaction_type,
                            'coin': coin,
                            'amount': first_amount
                        })
                    else:
                        coin = second_token
                        transactions.append({
                            'type': transaction_type,
                            'coin': coin,
                            'amount': second_amount
                        })

                # Use coin in the print statement only if it's defined
                print(f"Transaction added: {transaction_type} {coin} {amount}")

    # Calculate total buy and sell amounts for each coin
    summary = {}
    for transaction in transactions:
        coin = transaction['coin']
        amount = transaction['amount']

        if transaction['type'] == "Buy":
            if coin in summary:
                summary[coin]['total_buy'] += amount
            else:
                summary[coin] = {'total_buy': amount, 'total_sell': 0}
        elif transaction['type'] == "Sell":
            if coin in summary:
                summary[coin]['total_sell'] += amount
            else:
                summary[coin] = {'total_buy': 0, 'total_sell': amount}

    # Calculate net profit/loss and profitability
    for coin, data in summary.items():
        data['net_profit_loss'] = data['total_sell'] - data['total_buy']
        total_investment = data['total_buy'] if data['total_buy'] > 0 else 1  # prevent division by zero
        data['profitability'] = (data['net_profit_loss'] / total_investment) * 100

    # Debug: Print the final summary
    print("Summary of Analysis:", summary)

    return summary








def calculate_profit_and_loss(transactions):
    # To keep track of buy and sell transactions for each coin
    buy_amounts = {}
    sell_amounts = {}

    for transaction in transactions:
        coin = transaction['coin']
        amount = transaction['amount']
        
        if transaction['type'] == "Buy":
            if coin not in buy_amounts:
                buy_amounts[coin] = 0
            buy_amounts[coin] += amount
        elif transaction['type'] == "Sell":
            if coin not in sell_amounts:
                sell_amounts[coin] = 0
            sell_amounts[coin] += amount

    # Calculate net profit/loss for each coin
    summary = {}
    for coin in set(list(buy_amounts.keys()) + list(sell_amounts.keys())):
        total_buy = buy_amounts.get(coin, 0)
        total_sell = sell_amounts.get(coin, 0)
        net_profit_loss = total_sell - total_buy
        profitability = "Profit" if net_profit_loss > 0 else "Loss" if net_profit_loss < 0 else "Break-even"

        summary[coin] = {
            "Total Buy Amount": total_buy,
            "Total Sell Amount": total_sell,
            "Net Profit/Loss": net_profit_loss,
            "Profitability": profitability
        }

    return summary


if __name__ == '__main__':
    create_table()
    app.run(debug=True)
