import yaml, os
cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__),'brand.yml')))
APP_NAME = cfg.get('app_name','HELIOS ONE — V8')
TAGLINE = cfg.get('tagline','One-tap pro signals · P&L portfolio tracking')
LOGO_PATH = cfg.get('logo_path','assets/logo.png')
