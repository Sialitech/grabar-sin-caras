#!/bin/bash

# Colores para los mensajes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color
YELLOW='\033[1;33m'

# Función para limpiar y salir
cleanup() {
    echo -e "\n${YELLOW}Deteniendo y limpiando contenedores...${NC}"
    docker-compose down
    echo -e "${GREEN}Limpieza completada. ¡Hasta luego!${NC}"
    exit 0
}

# Capturar señal de interrupción (Ctrl+C)
trap cleanup SIGINT

echo -e "${GREEN}Iniciando el sistema de grabación...${NC}"

# Asegurarse de que no hay contenedores previos ejecutándose
echo -e "${YELLOW}Limpiando contenedores previos si existen...${NC}"
docker-compose down

# Levantar los contenedores
echo -e "${GREEN}Levantando contenedores...${NC}"
docker-compose up -d

# Mostrar logs y esperar a que termine
echo -e "${GREEN}Mostrando logs del contenedor principal...${NC}"
echo -e "${YELLOW}El sistema se detendrá automáticamente cuando termine la grabación${NC}"
echo -e "${YELLOW}También puedes presionar Ctrl+C para detener manualmente${NC}"

# Esperar a que aparezca el mensaje de finalización en los logs
docker-compose logs -f main | while read line; do
    echo "$line"
    if [[ $line == *"Ejecución finalizada"* ]]; then
        echo -e "\n${GREEN}Grabación completada exitosamente.${NC}"
        cleanup
        break
    fi
done 
