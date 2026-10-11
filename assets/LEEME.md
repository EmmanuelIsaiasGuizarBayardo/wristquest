# Arte del juego (paper cut)

`assets/sprites/` guarda una pieza por PNG, con fondo transparente. `tools/inyectar_assets.py` las
convierte a WebP y las incrusta en `web/wristquest.html`; el chat de desarrollo nunca las ve.

## Cambiar o agregar una pieza

1. Reemplaza el PNG con el mismo nombre (fondo transparente, recortado al borde de la figura).
2. `uv run --with pillow python tools/inyectar_assets.py`
3. Abre el juego y revisa. Si falta una pieza, el juego dibuja la versión por código.

## Nombres y dónde se usan

| Grupo | Piezas |
|---|---|
| Personajes jugables | `pers_conejo` (con dos variantes de color), `pers_rana`, `pers_mapache`, `pers_castor` |
| Clientes | `oso`, `ardilla`, `pers_jabali`, `buho` |
| Ingredientes y objetos | `cristal`, `mortero`, `roca_runica`, `pocion_azul`, `pocion_verde`, `llave`, `cofre`, `caldero` |
| Menús | `pocion_lava`, `pocion_vid`, `pocion_corazon` (principal); `pocion_verde`, `pocion_gema`, `pocion_hongo`, `pocion_h` (dificultad) |
| Mano guía | `mano_flexion`, `mano_extension`, `mano_dorso`, `mano_palma`, `brazo_giro` |
| Escenario | `pinos`, `bosque_capas`, `suelo` |
| Miniaturas de escenarios | `esc_noche`, `esc_sol`, `esc_casa`, `esc_rio`, `esc_hongo` |
| Aún sin usar | `cadenas`, `avatar`, `carton`, `libro`, `runa_chica`, `esc_selva` (no se extrajo) |

Resolución: las piezas miden unos 300 px de alto. En pantallas 4K se ven suaves; si hace falta más
nitidez, genera las hojas al doble de tamaño y vuelve a correr `tools/extraer_sprites.py`.

Procedencia: ilustraciones generadas con un modelo de imágenes a partir de `prompt_paper_cut.md`.
