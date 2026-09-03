# -*- coding: utf-8 -*-
"""
nucleo — el MOTOR compartido de finauto.

Todo lo que NO es específico de un banco vive acá y se reusa entre Galicia,
Comafi, Santander y los bancos que se sumen. Un banco nuevo es solo un
"adaptador" chico en bots/<banco>/bot.py que implementa el contrato de
bots/base.py; el recorrido (login -> por empresa: cuenta -> saldos -> fechas
-> descarga -> Drive), la regla de fechas, el estado anti-duplicado, el log y
las salidas a Drive los pone el núcleo.

Este código sale de los bots probados bot_galicia.py y bot_comafi.py; se movió
a módulos SIN cambiar la lógica. Antes de reemplazar producción con esto hay
que correrlo una vez contra el banco real (ver docs/MANANA_THOMAS.md).
"""

__version__ = "0.1.0"
