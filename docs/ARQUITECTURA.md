# Arquitectura de finauto (Fase 1)

## El flujo de una corrida

```
python orquestador/correr.py --cliente maga --banco galicia --modo prueba
        │
        ▼
orquestador/correr.py
  · lee clientes/maga/perfil.json ............... nucleo/config.py
  · arma el Contexto (rutas + settings) ......... nucleo/contexto.py
  · lee credenciales del llavero ................. nucleo/credenciales.py (keyring)
  · elige el adaptador del banco ................ REGISTRO_BANCOS → bots/galicia
        │
        ▼
nucleo/loop.py  (el recorrido, IGUAL para todo banco)
  · abre el navegador ........................... nucleo/navegador.py (Playwright)
  · bot.hacer_login()
  · bot.capturar_empresa_activa()
  · bot.descubrir_empresas()
  · POR CADA empresa:
        · calcula qué días bajar .............. nucleo/fechas.py (ayer+hoy / backfill)
        · bot.cambiar_a_empresa()  (si hace falta)
        · bot.ir_a_cuenta()
        · bot.capturar_saldos()
        · bot.aplicar_filtro_fechas()
        · bot.descargar_csv()  → carpeta de Drive
        · guarda estado ...................... nucleo/estado.py (anti-duplicado)
        · si falla: la anota y sigue
  · escribe _ESTADO_ y _SALDOS_ ................. nucleo/salidas.py → Drive
```

## Quién sabe qué

- **El núcleo** sabe el *recorrido* pero NO sabe nada de un banco puntual.
- **El adaptador** (bots/<banco>) sabe *cómo* hacer cada paso en ESE banco (los selectores),
  pero NO controla el recorrido.
- **El perfil** (clientes/<c>) sabe lo del *cliente* (carpetas, filtros), pero NO es código.

Esa separación es lo que hace que el sistema escale: un banco nuevo toca solo su adaptador,
un cliente nuevo toca solo su perfil, y el motor no se duplica nunca más.

## Por qué así (vs. los bots viejos)

Antes, `bot_galicia.py` y `bot_comafi.py` tenían el mismo motor **copiado** (login flow, loop,
fechas, estado, Drive). Arreglar algo = arreglarlo dos veces, y cada banco nuevo era otra copia.
Ahora el motor está una sola vez; Galicia quedó en ~1 archivo de selectores, Comafi igual, y
Santander es casi solo completar los métodos vacíos.
```
```
