from flask import Flask
import subprocess

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Scraper en ligne. Pour lancer, allez sur /run'

@app.route('/run')
def run_scraper():
    # Remplace 'mon_script.py' par le nom de ton script
    subprocess.run(['python', 'vinted2.py'])
    return 'Scraping lancé !'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)