# app/seed_comunas_biobio.py
from app.db import SessionLocal
from app.models.pacientes import Comuna

BIOBIO = [
    "Concepción","Talcahuano","Hualpén","San Pedro de la Paz","Chiguayante",
    "Penco","Tomé","Hualqui","Santa Juana","Coronel","Lota",
    "Los Ángeles","Nacimiento","Laja","San Rosendo","Santa Bárbara",
    "Quilaco","Quilleco","Mulchén","Negrete","Tucapel","Antuco",
    "Cabrero","Yumbel","Alto Biobío",
    "Curanilahue","Arauco","Lebu","Los Álamos","Cañete","Contulmo","Tirúa",
]

def run():
    db = SessionLocal()
    for nombre in BIOBIO:
        if not db.query(Comuna).filter(Comuna.nombre == nombre).first():
            db.add(Comuna(nombre=nombre))  # si tu modelo tiene region_id, agrega acá el id de Biobío
    db.commit()
    db.close()

if __name__ == "__main__":
    run()
