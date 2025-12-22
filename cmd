#Restart Backend:
docker compose up // run back end
docker-compose down
docker compose up --build


# Compiler
pio run

# Upload (ESP32 connecté en USB)
pio run --target upload

# Monitor série
pio device monitor


# clean and run
platformio run -t fullclean
platformio run -e esp32dev
