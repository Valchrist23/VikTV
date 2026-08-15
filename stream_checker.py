import requests
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


# ==========================================
# CONFIGURACIÓN
# ==========================================

M3U_URL = "https://raw.githubusercontent.com/Valchrist23/VikTV/master/x.m3u"

TIMEOUT = 15
FFMPEG_TIME = 8
MAX_WORKERS = 10

RESULTADO = "resultado_streams.txt"
CAIDOS = "streams_caidos.txt"


# ==========================================
# DESCARGAR LA LISTA M3U
# ==========================================

def descargar_lista():
    print("Descargando lista M3U...")

    respuesta = requests.get(
        M3U_URL,
        timeout=TIMEOUT
    )

    respuesta.raise_for_status()

    return respuesta.text


# ==========================================
# COMPROBAR SI UNA LÍNEA PARECE UNA URL
# ==========================================

def es_url(linea):
    return linea.startswith("http://") or linea.startswith("https://")


# ==========================================
# COMPROBAR SI ES UNA URL DE STREAM
# ==========================================

def es_stream(url):
    url_lower = url.lower()

    extensiones = (
    ".mkv",
    ".mp4",
    ".avi",
    ".mpeg",
    ".mpg",
    ".m4v",
    ".ts",
    ".m3u8",
    ".m3u"
)

    if any(extension in url_lower for extension in extensiones):
        return True

    return False


# ==========================================
# EXTRAER CANALES Y URLs
# ==========================================

def obtener_streams(texto):

    lineas = texto.splitlines()

    streams = []

    canal_actual = "Sin nombre"

    for linea in lineas:

        linea = linea.strip()

        # -------------------------------
        # Encontramos un nuevo canal
        # -------------------------------
        if linea.startswith("#EXTINF"):

            if "," in linea:
                canal_actual = linea.split(",", 1)[1].strip()

            else:
                canal_actual = "Sin nombre"

        # -------------------------------
        # Encontramos una URL
        # -------------------------------
        elif es_url(linea):

            if es_stream(linea):

                streams.append({
                    "canal": canal_actual,
                    "url": linea
                })

    return streams


# ==========================================
# PROBAR STREAM CON FFMPEG
# ==========================================

def comprobar_stream(stream):

    canal = stream["canal"]
    url = stream["url"]

    comando = [
        "ffmpeg",

        "-hide_banner",

        "-loglevel", "error",

        "-i", url,

        "-t", str(FFMPEG_TIME),

        "-f", "null",

        "-"
    ]

    try:

        resultado = subprocess.run(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT + FFMPEG_TIME
        )

        error = resultado.stderr.decode(
            "utf-8",
            errors="ignore"
        )

        # FFmpeg devuelve 0 cuando terminó correctamente
        if resultado.returncode == 0:

            return {
                "canal": canal,
                "url": url,
                "estado": "OK",
                "error": ""
            }

        # Algunos streams pueden devolver error
        # aunque hayan entregado datos.
        if "Output file is empty" not in error:

            return {
                "canal": canal,
                "url": url,
                "estado": "CAIDO",
                "error": error[-500:]
            }

        return {
            "canal": canal,
            "url": url,
            "estado": "CAIDO",
            "error": error[-500:]
        }

    except subprocess.TimeoutExpired:

        return {
            "canal": canal,
            "url": url,
            "estado": "TIMEOUT",
            "error": "FFmpeg tardó demasiado"
        }

    except Exception as e:

        return {
            "canal": canal,
            "url": url,
            "estado": "ERROR",
            "error": str(e)
        }


# ==========================================
# GUARDAR RESULTADOS
# ==========================================

def guardar_resultados(resultados):

    with open(RESULTADO, "w", encoding="utf-8") as archivo:

        archivo.write(
            "========================================\n"
        )

        archivo.write(
            "       RESULTADO DEL STREAM CHECKER\n"
        )

        archivo.write(
            "========================================\n\n"
        )

        for resultado in resultados:

            if resultado["estado"] == "OK":
                icono = "🟢"

            elif resultado["estado"] == "TIMEOUT":
                icono = "🟡"

            else:
                icono = "🔴"

            archivo.write(
                f"{icono} {resultado['estado']} | "
                f"{resultado['canal']}\n"
            )

            archivo.write(
                f"URL: {resultado['url']}\n"
            )

            if resultado["error"]:
                archivo.write(
                    f"ERROR: {resultado['error']}\n"
                )

            archivo.write("\n")


# ==========================================
# GUARDAR SOLAMENTE LOS CAÍDOS
# ==========================================

def guardar_caidos(resultados):

    with open(CAIDOS, "w", encoding="utf-8") as archivo:

        archivo.write(
            "========================================\n"
        )

        archivo.write(
            "             STREAMS CAÍDOS\n"
        )

        archivo.write(
            "========================================\n\n"
        )

        for resultado in resultados:

            if resultado["estado"] != "OK":

                archivo.write(
                    f"{resultado['canal']}\n"
                )

                archivo.write(
                    f"{resultado['url']}\n\n"
                )


# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================

def main():

    texto = descargar_lista()

    streams = obtener_streams(texto)

    print()
    print(f"Streams encontrados: {len(streams)}")
    print()

    resultados = []

    total = len(streams)

    # --------------------------------------
    # PROBAR VARIOS STREAMS AL MISMO TIEMPO
    # --------------------------------------

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        tareas = [
            executor.submit(
                comprobar_stream,
                stream
            )
            for stream in streams
        ]

        for numero, tarea in enumerate(
            as_completed(tareas),
            start=1
        ):

            resultado = tarea.result()

            resultados.append(resultado)

            if resultado["estado"] == "OK":

                print(
                    f"[{numero}/{total}] "
                    f"🟢 {resultado['canal']}"
                )

            elif resultado["estado"] == "TIMEOUT":

                print(
                    f"[{numero}/{total}] "
                    f"🟡 TIMEOUT "
                    f"{resultado['canal']}"
                )

            else:

                print(
                    f"[{numero}/{total}] "
                    f"🔴 {resultado['canal']}"
                )

    # Ordenamos por nombre del canal
    resultados.sort(
        key=lambda x: x["canal"].lower()
    )

    guardar_resultados(resultados)

    guardar_caidos(resultados)

    # --------------------------------------
    # ESTADÍSTICAS
    # --------------------------------------

    funcionando = sum(
        1 for r in resultados
        if r["estado"] == "OK"
    )

    caidos = sum(
        1 for r in resultados
        if r["estado"] != "OK"
    )

    print()
    print("========================================")
    print("              TERMINADO")
    print("========================================")
    print()
    print(f"Total revisados : {len(resultados)}")
    print(f"Funcionando     : {funcionando}")
    print(f"Caídos/errores  : {caidos}")
    print()
    print(f"Reporte completo: {RESULTADO}")
    print(f"Solo caídos     : {CAIDOS}")
    print()


# ==========================================
# INICIAR
# ==========================================

if __name__ == "__main__":
    main()
