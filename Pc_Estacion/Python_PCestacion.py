import serial #permite la comunicación por el cable USB con el ESP32 para leer y escribir datos.
import time #Se usa para calcular cuánto tiempo se mantiene presionado el botón
import threading #Utilizada para crear los "hilos" en segundo plano
import datetime # Sirve para obtener la hora y fecha exacta del sistema
import socket #Permite la comunicación entre computadoras 

# ==========================================
# VARIABLES GLOBALES Y EVENTOS
# ==========================================
ultimo_tiempo_guardado = 3.5        # Guarda el último tiempo de lectura asignado (Inicialmente 3.5)
tiempo_inicio = 0                   # Guarda el momento exacto en el que apretás el botón
historial_temperaturas = []         # Lista vacía que almacena las lecturas de temperatura en forma numérica
boton_presionado = False            # Variable que refleja el estado actual del botón (inicialmente en falso)
programa_detenido = False           # Variable que refleja el estado actual del programa 

#Eventos de detención de hilos ,Tareas en paralelo 
evento_detener_parpadeo = threading.Event()
evento_detener_temperatura = threading.Event() 

# ==========================================
# CONFIGURACIÓN INICIAL ESP32
# ==========================================
# Abre la comunicación por USB con el ESP32 a 115200 baudios
puerto = "/dev/ttyUSB0"
baudios = 115200
esp32 = serial.Serial(puerto, baudios)
time.sleep(2) # Le da 2 segundos al ESP32


# ==========================================
# CONFIGURACIÓN DE RED 
# ==========================================
IP_PC_PRINCIPAL = '192.168.1.112'       #Ip PC principal
PORT = 5000                             # Puerto de escucha

print("Intentando conectar...")
try:
    # Prepara la "tubería" (socket) usando el protocolo de internet (IPv4) y TCP
    PC_red = socket.socket(socket.AF_INET, socket.SOCK_STREAM)      
    PC_red.connect((IP_PC_PRINCIPAL, PORT))                      # Intenta conectarse 
    print("[RED] ¡Conectado al PC principal!\n")
except:      # En caso de no poder realizar la conexión
    print("[RED] No se encontró la PC. El programa funcionará localmente.\n")
    PC_red = None                                # Variable nula para que el bucle principal sepa que no hay red


# ==========================================
# 1. BOTÓN Y TEMPORIZADOR DE PARPADEO
# ==========================================
def Boton_temporizador_Parpadeo(mensaje):
    """
    Descripción: Mide cuánto tiempo se mantiene presionado el botón del ESP32 para ajustar 
                 el intervalo de muestreo o detener el programa.
    Entradas: 
- mensaje (string): "BOTON_ON" (botón presionado) o "BOTON_OFF" (botón soltado).
    Condición de ejecución: Se invoca desde el bucle principal cuando el ESP32 envía 
                            una señal de estado del botón.
    """
    global tiempo_inicio, ultimo_tiempo_guardado, boton_presionado, programa_detenido 
    
    if mensaje == "BOTON_ON":
        boton_presionado = True          #Registramos el estado actual del botón     
        tiempo_inicio = time.time()      #Guardamos el tiempo actual en el que se presiona
        evento_detener_parpadeo.clear()  #Habilitamos el evento para que el led pueda parpadear
        print("Botón presionado. Contando tiempo y parpadeando...", end="\r")
        parpadeo()                       #Lanzamos el hilo que hace destellar el led
        
    elif mensaje == "BOTON_OFF":
        boton_presionado = False          #Registramos el estado actual del botón 
        tiempo_total = time.time() - tiempo_inicio  # Calcula cuántos segundos fue presionado
        nuevo_tiempo = round(tiempo_total, 2) #Redondeamos el tiempo total a dos decimales
        
        if nuevo_tiempo < 1.0:             #Tiempo menor a un segundo
            programa_detenido = True       #Indicamos que el programa se debe detener
            print(f"\n---> Click rápido ({nuevo_tiempo}s). Programa DETENIDO.")

        elif nuevo_tiempo < 2.5:           #Tiempo menor a 2,5 y mayor a un segundo
            programa_detenido = False      #Indicamos que el programa se debe reanudar
            ultimo_tiempo_guardado = 2.5   #Asignamos el tiempo mínimo de 2,5 segundos
            print(f"\n---> Tiempo corto ({nuevo_tiempo}s). Ajustado al MÍNIMO de {ultimo_tiempo_guardado}s")

        elif nuevo_tiempo > 10.0:          #Tiempo entre 2,5 y 10 segundos
            programa_detenido = False      #Indicamos que el programa se debe reanudar
            ultimo_tiempo_guardado = 10.0   #Asignamos el tiempo máximo de 10 segundos
            print(f"\n---> Tiempo excedido ({nuevo_tiempo}s). Ajustado al MÁXIMO de {ultimo_tiempo_guardado}s")

        else:                              #Tiempo entre 2,5 y 10 segundos
            programa_detenido = False      #Indicamos que el programa se debe reanudar
            ultimo_tiempo_guardado = nuevo_tiempo  #Asignamos el tiempo medido 
            print(f"\n---> Nuevo muestreo fijado en: {ultimo_tiempo_guardado}s")
        
        evento_detener_parpadeo.set() # Envía la orden para terminar el hilo de parpadeo

# ==========================================
# 2. PARPADEO
# ==========================================
def parpadeo():
    """
    Descripción: Genera una señal intermitente en los LEDs del ESP32 utilizando un hilo 
                 en segundo plano para no bloquear el resto del programa. Indica cuando transcurre un segundo
    Entradas: Ninguna.
    Condición de ejecución: Se inicia exclusivamente cuando la función 'Boton_temporizador_Parpadeo' 
                            detecta que el botón ha sido presionado ("BOTON_ON").
    """
    def parpadeo_hilo():
        while not evento_detener_parpadeo.is_set():         # Mientras no se reciba la orden de detener el hilo
            if evento_detener_parpadeo.wait(0.95): break    # Espera casi un segundo, si recibe la orden se cancela
            esp32.write(b'E')                               # Enciende todos los leds 
            if evento_detener_parpadeo.wait(0.05): break    # Espera 50 ms 
            esp32.write(b'X')                               # Se apagan todos los leds     
        esp32.write(b'X')   # Me aseguro que todos los leds estén apagados
    hilo = threading.Thread(target=parpadeo_hilo, daemon=True)  # Prepara esta tarea para correr en segundo plano, se puede detener
    hilo.start()                                            # Arranca el hilo sin frenar el resto del programa

# ==========================================
# 3. TEMPORIZADOR DE TEMPERATURA
# ==========================================
def temporizador_temperatura():
    """
    Descripción: Hilo en segundo plano que envía la letra 'T' al ESP32 cada cierto 
                 intervalo (determinado por 'ultimo_tiempo_guardado') para solicitar una lectura.
    Entradas: Ninguna.
    Condición de ejecución: Se lanza una única vez al iniciar el bucle principal y se ejecuta 
                            continuamente, salvo que el programa se detenga manualmente o el botón esté presionado.
    """
    def ciclo_hilo():
        while not evento_detener_temperatura.is_set(): # Mientras no se reciba la orden de apagar el programa
            if evento_detener_temperatura.wait(ultimo_tiempo_guardado): break # Espera los segundos configurados, si recibe señal de apagado, sale
            # Solo solicita temperatura si el programa NO está pausado y si el usuario NO está presionando el botón
            if not programa_detenido and not boton_presionado:
                esp32.write(b'T')                                 # Manda la orden 'T' al ESP32 para que lea el sensor
    hilo_temp = threading.Thread(target=ciclo_hilo, daemon=True)  # Prepara esta tarea para correr en segundo plano, se puede detener
    hilo_temp.start()                                             # Arranca el hilo sin frenar el resto del programa

# ==========================================
# 4. PROCESAR TEMPERATURA
# ==========================================
def procesar_temperatura(valor_str):
    """
    Descripción: Convierte la lectura de texto a número, la añade al historial y calcula 
                 el promedio de las últimas 5 mediciones para determinar la tendencia.
    Entradas: 
- valor_str (string): El valor numérico crudo proveniente del ESP32 (ej. "24.50").
    Condición de ejecución: Se llama desde el bucle principal cada vez que se recibe un mensaje válido terminado en la letra 'c'.
    """
    N_EVENTOS = 5                                           # Cantidad de muestras a considerar para calcular el promedio
    X_PORCENTAJE = 2.0                                      # Margen de tolerancia (±2%)

    temp_actual = float(valor_str)                          # Convierte el texto recibido a un número con decimales
    historial_temperaturas.append(temp_actual)              # Agrega la nueva lectura al final de la lista 
        
    ultimos_eventos = historial_temperaturas[-N_EVENTOS:]   # Extrae solamente los últimos 5 datos de la lista
        
    if len(ultimos_eventos) < N_EVENTOS:                    # Si todavía no tenemos 5 mediciones
        print(f"---> Temp actual: {temp_actual:.2f}°C | Promedio: | Tendencia: INICIAL")  #Devuelve estado INICIAL, sin promedio
        return "INICIAL"
            
    promedio = sum(ultimos_eventos) / N_EVENTOS # Suma los 5 valores y los divide por 5 para sacar el promedio
    # Calcula la "banda" de normalidad usando el promedio ± 2%    
    limite_superior = promedio + (promedio * X_PORCENTAJE / 100.0)
    limite_inferior = promedio - (promedio * X_PORCENTAJE / 100.0)
        
    if temp_actual > limite_superior:   # Si la temperatura rompe el techo del 2%
            tendencia = "ALTA"
    elif temp_actual < limite_inferior: # Si la temperatura rompe el piso del 2%
            tendencia = "BAJA"
    else:                               # Si se mantiene adentro de los límites
            tendencia = "ESTABLE"
        
    print(f"---> Temp actual: {temp_actual:.2f}°C | Promedio (N=5): {promedio:.2f}°C | Tendencia: {tendencia}")
    return tendencia                    # Devuelve el resultado final (ALTA, BAJA o ESTABLE)


# ==========================================
# 5. GUARDAR EN ARCHIVO
# ==========================================
def guardar_en_archivo(temp_actual, tendencia):
    """
    Descripción: Escribe una nueva línea en el archivo de texto local 'historial.txt' 
                 con la marca de tiempo exacta de la medición.
    Entradas: 
- temp_actual (float): La temperatura procesada.
- tendencia (string): El estado ("ALTA", "BAJA", "ESTABLE", "INICIAL").
    Condición de ejecución: Se ejecuta en el bucle principal si la función 'procesar_temperatura' 
                            devuelve una tendencia válida.
    """
    # Obtiene la fecha y hora actual del sistema operativo y le da un formato(Año-Mes-Día Hora:Minuto:Segundo)
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Abre el archivo en modo "a" (añadir) para agregar datos al final sin borrar lo que ya estaba
    with open("historial.txt", "a", encoding="utf-8") as archivo:    #with cierra automáticamente el archivo
        # Arma el texto a guardar usando un f-string y le agrega un salto de línea (\n) al final
        linea = f"{ahora},{temp_actual},{tendencia}\n"
        archivo.write(linea)   # Inserta esa línea de texto

# ==========================================
# 6. BUCLE PRINCIPAL 
# ==========================================
def bucle_principal():
    global PC_red
    temporizador_temperatura()   # Lanza el hilo encargado de la medición periódica de temperatura
    
    try:
        # Bucle infinito
        while True:

            # Verifica si hay algún mensaje esperando en el puerto serie
            if esp32.in_waiting > 0:        

                # Lee el mensaje, lo decodifica a texto normal y le quita espacios vacíos a los lados
                mensaje = esp32.readline().decode('utf-8').strip()
                
                # si el mensaje contiene "BOTON_ON" o "BOTON_OFF"
                if mensaje == "BOTON_ON" or mensaje == "BOTON_OFF":
                    Boton_temporizador_Parpadeo(mensaje)  #Se llama a la función

                # El mensaje termina en 'c' lo que indica que es un valor de temperatura
                elif mensaje.endswith("c"):               
                    solo_numero = mensaje[:-1]            # Eliminamos el carácter 'c'
                    tendencia = procesar_temperatura(solo_numero)  #Enviamos el texto a la función y almacenamos el retorno
                    
                    if tendencia is not None:              # Si la tendencia es no nula 
                        temp_num = float(solo_numero)      # Transformamos la cadena de texto a numérico tipo float
                        
                        # Guardado local
                        guardar_en_archivo(temp_num, tendencia) # Guardamos los datos
                        
                        # Envío por red
                        if PC_red is not None:
                            try:
                                datos_red = f"{temp_num},{tendencia}\n"     # Prepara el paquete de datos
                                PC_red.send(datos_red.encode('utf-8'))      # Lo envía por el socket
                            except:
                                print("\n[RED] Error: Se perdió la conexión con la PC.")
                                PC_red = None                               # Desactiva la red si falla

                    # Control de Luces
                    if tendencia is not None and not boton_presionado:  # Si la tendencia no es nula y el botón no está presionado

                        # Destello rápido indicador de nuevo dato 
                        esp32.write(b'E')                               # Enciende todos los leds 
                        time.sleep(0.05)
                        esp32.write(b'X')                               # Apaga todos los leds 

                        if tendencia == "INICIAL":
                            esp32.write(b'E')                           # Enciende todos los leds 
                        elif tendencia == "ESTABLE":
                            esp32.write(b'V')                           # Enciende el led verde
                        elif tendencia == "ALTA":
                            esp32.write(b'R')                           # Enciende el led rojo
                        elif tendencia == "BAJA":   
                            esp32.write(b'A')                           # Enciende el led azul
               
    except KeyboardInterrupt:                                           # Ctrl+C para cerrar programa
        print("\nCerrando conexión...")
        evento_detener_parpadeo.set()                                   # Apaga el hilo de parpadeo
        evento_detener_temperatura.set()                                # Apaga el hilo de medición
        esp32.close()                                                   # Cierra el puerto USB
        if PC_red: PC_red.close()                                       # Cierra la conexión de red (el socket)


# ==========================================
# Ejecución 
# ==========================================

bucle_principal()             #Bucle principal