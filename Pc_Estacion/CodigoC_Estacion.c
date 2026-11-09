#include <stdio.h>
#include <stdlib.h> // Proporciona las funciones para memoria dinámica (malloc, realloc, free, qsort)
#include <string.h> // Permite la manipulación de cadenas de texto
#include <math.h>   // Proporciona funciones matemáticas (pow, sqrt) para la desviación estándar

// 1. Estructura de los datos de cada muestra
// Se utiliza typedef para definir un nuevo tipo de dato llamado "Registro"
typedef struct {
    char fecha_hora[64];    // Reservamos un espacio en memoria para 64 caracteres
    float temperatura;      // Almacena el valor numérico decimal de la lectura
    char tendencia[32];     // Reservamos un espacio en memoria para 32 caracteres
} Registro;

// ==========================================
// Comparar_temperaturas
// ==========================================

// Función auxiliar para ordenar las temperaturas (necesario para Mediana y Moda)
// Necesaria para usar la función qsort de C y calcular la Mediana y la Moda
int comparar_temperaturas(const void *a, const void *b) {
    // Convierte los datos de memoria a formato decimal (float)
    float t1 = *(const float *)a;
    float t2 = *(const float *)b;
    // Compara los valores para ordenarlos de menor a mayor
    if (t1 < t2) return -1; // t1 es menor, va primero
    if (t1 > t2) return 1;  // t1 es mayor, va después
    return 0; // Si son iguales, se mantienen en su lugar
}

int main() {

// ==========================================
// Lectura del archivo y Memoria dinamica
// ==========================================
    // Abrimos el archivo "historial.txt" en modo lectura ("r" de read)
    FILE *archivo = fopen("historial.txt", "r");
    // Si el archivo no existe, avisamos y detenemos el programa
    if (archivo == NULL) {
        printf("Error: No se pudo abrir el archivo historial.txt\n");
        return 1;
    }

    // 2. Gestión de memoria dinámica
    int capacidad = 10; // Empezamos reservando espacio para 10 lecturas
    int cantidad = 0;   // Contador para saber cuántas lecturas vamos guardando
    // Reservamos la memoria inicial multiplicando la capacidad (10) por el tamaño de un "Registro"
    Registro *datos = (Registro *)malloc(capacidad * sizeof(Registro));

    char linea[128]; // Espacio temporal para guardar cada renglón del texto

    // Leemos el archivo línea por línea hasta que se termine
    while (fgets(linea, sizeof(linea), archivo)) {
        
        // Si nos quedamos sin espacio (ej: llegamos a la lectura 11)...
        if (cantidad >= capacidad) {
            capacidad *= 2; // Duplicamos la capacidad (de 10 pasa a 20, 40, 80...)
            // Expandimos la memoria dinámicamente sin perder los datos anteriores
            datos = (Registro *)realloc(datos, capacidad * sizeof(Registro));
        }

        // Extraer datos asumiendo el formato: "Fecha Hora,Temperatura,Tendencia"
        // Ejemplo: "07/11/2026 14:30:00,24.5,ALTA"
        // %[^,] guarda la fecha, %f guarda el decimal, y %s guarda la tendencia
        sscanf(linea, "%[^,],%f,%s", datos[cantidad].fecha_hora, &datos[cantidad].temperatura, datos[cantidad].tendencia);
        cantidad++; // Sumamos 1 al contador de lecturas
    }
    fclose(archivo); // Cerramos el archivo


// ==========================================
// Mínimo, Máximo y Media
// ==========================================

    // 3. Variables para las estadísticas
    float suma = 0;                     // Variable para sumar todas las temperaturas
    int indice_min = 0, indice_max = 0; // Guarda la posición donde está la temperatura más baja y alta

    // Creamos un arreglo dinámico temporal solo para las temperaturas.
    float *solo_temps = (float *)malloc(cantidad * sizeof(float)); // Arreglo para facilitar ordenamiento

    // Buscar Min, Max y sumar para la Media
    
    // Recorremos todos los registros uno por uno
    for (int i = 0; i < cantidad; i++) {
        solo_temps[i] = datos[i].temperatura;      // Tomamos solo las temperaturas
        suma += datos[i].temperatura;              // Vamos sumando el valor para el promedio

        // Comparamos para encontrar los extremos
        if (datos[i].temperatura < datos[indice_min].temperatura)
            indice_min = i; // Si encontramos uno menor, actualizamos la posición mínima
        if (datos[i].temperatura > datos[indice_max].temperatura)
            indice_max = i; // Si encontramos uno mayor, actualizamos la posición máxima
    }

    // Calculamos la Media (Promedio)
    // Es la suma de todas las temperaturas dividida por la cantidad total de lecturas.
    float media = suma / cantidad;


// ==========================================
// Desviación Estándar
// ==========================================
    
    // Calcular Desviación Estándar (Dispersión)
    // Medida de dispersión que indica la variación promedio de un conjunto de datos respecto a su media aritmética
    
    float suma_diferencias = 0;
    for (int i = 0; i < cantidad; i++) {
        // Resta la temperatura actual menos el promedio, y lo eleva al cuadrado (pow)
        suma_diferencias += pow(datos[i].temperatura - media, 2);
    }
    // Divide por la cantidad y le saca la raíz cuadrada (sqrt)
    float desviacion_estandar = sqrt(suma_diferencias / cantidad);


// ==========================================
// Mediana y Moda
// ==========================================

    // Ordenar arreglo de temperaturas para Mediana y Moda
    // Utilizamos qsort y le pasamos la función comparar_temperaturas
    qsort(solo_temps, cantidad, sizeof(float), comparar_temperaturas);

    // Mediana
    // Medida de tendencia central que representa el valor que divide la muestra ordenada en dos mitades simétricas
    float mediana;
    if (cantidad % 2 == 0) { // Si la cantidad de lecturas es un número par, no hay un solo centro, hay dos.
        // Agarramos los dos números del centro y los promediamos
        mediana = (solo_temps[cantidad / 2 - 1] + solo_temps[cantidad / 2]) / 2.0;
    } else {
        // Si es impar, simplemente agarramos el número que quedó exactamente en el medio
        mediana = solo_temps[cantidad / 2];
    }

    // Moda
    // Medida de tendencia central que identifica el valor con la mayor frecuencia en la distribución de datos
    float moda = solo_temps[0]; // Empezamos asumiendo que el primero es la moda
    int max_repeticiones = 1; // Guardará la "racha" más larga de repeticiones encontradas
    int conteo_actual = 1;

    // Recorremos las temperaturas ya ordenadas
    for (int i = 1; i < cantidad; i++) { // Recorremos las temperaturas ya ordenadas
        // Si el número actual es igual al anterior, el contador crece
        if (solo_temps[i] == solo_temps[i - 1]) {
            conteo_actual++;
        } else { // Si el número cambió vuelve a 1
            conteo_actual = 1;
        }
        // Si la racha que acabamos de contar le gana a la mayor que teníamos guardada...
        if (conteo_actual > max_repeticiones) {
            max_repeticiones = conteo_actual;   // Guardamos el nuevo récord de repeticiones
            moda = solo_temps[i];               // Y declaramos a esta temperatura como la nueva moda
        }
    }


// ==========================================
// Impresión de Resultados y Limpieza
// ==========================================

    // %d números enteros
    // %.2f muestra el número decimal limitado a 2 decimales
    // %s muestra el texto (string)
    printf("--- REPORTE ESTADÍSTICO DE TEMPERATURA ---\n");
    printf("Cantidad total de lecturas : %d\n", cantidad);
    printf("Temp. Mínima detectada     : %.2f °C (Fecha/Hora: %s)\n", datos[indice_min].temperatura, datos[indice_min].fecha_hora);
    printf("Temp. Máxima detectada     : %.2f °C (Fecha/Hora: %s)\n", datos[indice_max].temperatura, datos[indice_max].fecha_hora);
    printf("Media (Promedio)           : %.2f °C\n", media);
    printf("Mediana                    : %.2f °C\n", mediana);
    printf("Moda                       : %.2f °C\n", moda);
    printf("Desviación Estándar        : %.2f °C\n", desviacion_estandar);

    // Liberar la memoria dinámica utilizada
    free(solo_temps);
    free(datos);

    return 0;
}