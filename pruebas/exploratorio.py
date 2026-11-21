# Uso: python pruebas/exploratorio.py   — mensajes que un alumno podría escribir (defectos D-09 a D-12)
import sys, runpy
from pathlib import Path
__file__ = str(Path(__file__).resolve().parent / "pruebas_bot.py")
exec(open(__file__, encoding="utf-8").read().split("R = []")[0])
def prueba(pasos):
    u = Usuario(); r=[]
    for k,v in pasos: r = (u.escribir if k=="e" else u.tocar)(v)
    return textos(r)[:90].replace("\n"," "), urls(r)
for nombre, pasos in [
  ("No.", [("e","formulario"),("e","No.")]),
  ("no gracias", [("e","formulario"),("e","no gracias")]),
  ("sin dinero (esperando requisitos)", [("e","formulario"),("e","sin dinero")]),
  ("Sí cumplo sin pedir antes", [("e","Sí, cumplo")]),
  ("quiero informacion", [("e","quiero información")]),
  ("cuándo pago", [("e","cuándo pago")]),
  ("menú", [("e","menú")]),
  ("emoji solo 👍", [("e","👍")]),
  ("gracias", [("e","gracias")]),
  ("ex encion (typo)", [("e","exension")]),
]:
    print(nombre, "=>", prueba(pasos))
