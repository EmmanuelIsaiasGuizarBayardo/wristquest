# Puente del decodificador

Conecta el motor de decodificación de SynapVolit con WristQuest:

```
ESP32 ──serie (ND-JSON)──▶ puente: valida el contrato ──WebSocket──▶ navegador: WQ.feedDecoder
```

## Contrato

Una línea ND-JSON por decisión (cada ~125 ms: ventana de 250 ms con 50% de traslape).

| Campo | Tipo | Rango | Notas |
|---|---|---|---|
| `clase` | entero | 0 a 4 | reposo, extensión, flexión, pronación, supinación |
| `intensidad` | número | 0 a 1.5 | fracción de la MVC calibrada |
| `confianza` | número | 0 a 1 | bajo `CFG.minConf` (0.6) el juego lo trata como reposo |
| `t` | número | ≥ 0 | marca temporal del dispositivo, en ms |
| `coactivacion` | número | 0 a 1 | opcional; coactivación antagonista |

Una línea inválida se descarta y se cuenta; nunca se corrige ni se rellena con reposo.

El puente envía al juego dos tipos de mensaje:
- `{"tipo":"decodificador", ...contrato}` por cada línea válida.
- `{"tipo":"estado","fuente":"serie|simulada|ninguna","activa":bool,"descartadas":n}` cada segundo.

El juego muestra siempre la fuente en el HUD. Nunca presenta una señal simulada como real.

## Uso

Dependencias, una sola vez:

```powershell
uv add websockets pyserial
```

El puente exige declarar la fuente; no hay valor por defecto. Elige una:

```powershell
# Sin hardware: decodificador simulado y reproducible (semilla 42)
uv run python -m wristquest.puente --fuente simulada

# Con el módulo de adquisición (ajusta el puerto y los baudios del firmware)
uv run python -m wristquest.puente --fuente serie --puerto-serie COM3 --baudios 115200

# Solo el latido de estado, para comprobar la ausencia explícita
uv run python -m wristquest.puente --fuente ninguna
```

En otra terminal, sirve el juego y ábrelo con el parámetro `puente`:

```powershell
uv run python -m http.server 8000 --bind 127.0.0.1 --directory web
```

Luego abre `http://127.0.0.1:8000/wristquest.html?puente=ws://127.0.0.1:8765` en el navegador.

Sin el parámetro `puente`, el juego usa el teclado. La versión publicada como artefacto no permite conexiones de red, así que ahí siempre es teclado.

## Pruebas sin hardware

```powershell
uv run pytest -q tests
```

Son 20 pruebas:
- el contrato: casos válidos e inválidos, incluidos `NaN`, booleanos y rangos;
- la fuente simulada: reproducible, las cinco clases y cadencia de 8 Hz;
- el puerto serie: con `loop://` de pyserial, sin dispositivo;
- el servidor completo: difusión, descarte de líneas inválidas y ausencia explícita.

## Privacidad

- El puente escucha solo en `127.0.0.1`. Si se cambia `--host`, avisa que la señal de un paciente quedaría expuesta en la red.
- El puente no escribe nada a disco.
- Cualquier registro de sesiones vive fuera del repositorio: los datos de niños nunca entran a él, sea público o privado (regla dura de la plantilla).

## Operación en vivo

1. Arranca el puente declarando la fuente. Con `simulada`, la consola lo advierte en cada inicio.
2. Antes de empezar, verifica la etiqueta del HUD:
   - "Señal: decodificador": hardware real.
   - "Señal: puente simulado": demostración.
   - "Puente sin señal: usando teclado": el puente está conectado pero no llegan datos válidos.
3. En una demostración con fuente simulada, dilo al público.

## Pendientes

- Confirmar baudios y formato exacto del firmware del ESP32.
- Agregar `coactivacion` al contrato del motor, para que coincida con las tres salidas que describe el resumen ejecutivo.
