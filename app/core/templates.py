from datetime import datetime
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

# helpers globales
templates.env.globals.update(
    now=datetime.now,       # {{ now() }}
)