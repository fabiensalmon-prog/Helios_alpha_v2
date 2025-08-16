import ccxt, os
from dotenv import load_dotenv
load_dotenv()
def build_exchange(name: str):
    ex_class = getattr(ccxt, name.lower())
    params = {'enableRateLimit': True, 'options': {'adjustForTimeDifference': True}}
    api_key=os.getenv('API_KEY',''); api_secret=os.getenv('API_SECRET',''); password=os.getenv('PASSWORD','')
    if api_key and api_secret: params.update({'apiKey': api_key, 'secret': api_secret})
    if password: params['password']=password
    ex = ex_class(params); ex.load_markets(); return ex
