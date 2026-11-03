"""Adaptadores de repositorio (design D1): implementan los puertos del dominio.

`en_memoria` no depende de `sqlite3`; `sqlite_turnos` y `recursos` sí. El
`__init__.py` se mantiene sin importar adaptadores para que importar
`src.repositories.en_memoria` no arrastre `sqlite3` hacia el dominio.
"""
